"""
repository.py — Transactional SQLite data access layer for career-ops.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import STATUS_RANK, get_db_path, resolve_root
from .db import get_db_connection, init_db
from .models import VagaInput
from .utils import (
    compute_content_hash,
    normalize_company,
    normalize_role,
    normalize_url,
)

VALID_LIFECYCLE_STATUSES: set[str] = {
    "evaluated",
    "applied",
    "interview",
    "offer",
    "rejected",
    "discarded",
    "skip",
}

TERMINAL_LIFECYCLE_STATUSES: set[str] = {
    "rejected",
    "discarded",
    "skip",
}

ACTIVE_LIFECYCLE_STATUSES: set[str] = {
    "evaluated",
    "applied",
    "interview",
    "offer",
}


def generate_vaga_id() -> str:
    """Generate a deterministic-format unique identifier using standard library primitives."""
    return f"vaga_{int(time.time() * 1000):x}_{uuid.uuid4().hex[:6]}"


class CareerOpsRepository:
    """
    Repository encapsulating transactional SQLite operations across
    `vagas`, `vaga_descricoes`, and `tracking_lifecycle`.
    """

    def __init__(self, db_path: Path | None = None, auto_init: bool = True) -> None:
        self.db_path = Path(db_path) if db_path is not None else get_db_path()
        if auto_init:
            init_db(self.db_path)

    def insert_vaga(
        self,
        vaga: VagaInput,
        descricao: str = "",
        description_clean: str | None = None,
    ) -> tuple[str, bool]:
        """
        Insert a job opportunity and its full-text description within an atomic
        `BEGIN IMMEDIATE` transaction.

        If `canonical_url` collides with an existing record:
        1. Preserves the oldest record's `id` and `created_at`.
        2. Backfills `vaga_descricoes` if missing or empty when incoming `descricao` is non-empty.
        3. Updates `vaga_descricoes` and touches `vagas.updated_at` if incoming `descricao`
           is non-empty and its `content_hash` differs from the stored hash.
        4. Returns `(existing_id, False)`.

        If unique, inserts into both `vagas` and `vaga_descricoes` and returns `(new_id, True)`.
        """
        canonical_url = vaga.canonical_url or normalize_url(vaga.original_url)
        company_norm = vaga.company_norm or normalize_company(vaga.company)
        role_norm = vaga.role_norm or normalize_role(vaga.role)
        content_hash = compute_content_hash(descricao)

        candidate_id = getattr(vaga, "id", None) or generate_vaga_id()
        status_triagem = getattr(vaga, "status_triagem", None) or "queued"

        with get_db_connection(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                try:
                    cur = conn.execute("SELECT COALESCE(MAX(seq_num), 0) + 1 FROM vagas;")
                    next_seq = cur.fetchone()[0]
                    conn.execute(
                        """
                        INSERT INTO vagas (
                            id, seq_num, canonical_url, original_url, company, company_norm,
                            role, role_norm, source_portal, location, remote_type, status_triagem
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            candidate_id,
                            next_seq,
                            canonical_url,
                            vaga.original_url,
                            vaga.company,
                            company_norm,
                            vaga.role,
                            role_norm,
                            vaga.source_portal,
                            vaga.location,
                            vaga.remote_type,
                            status_triagem,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO vaga_descricoes (
                            vaga_id, description_raw, description_clean, content_hash
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (
                            candidate_id,
                            descricao,
                            description_clean,
                            content_hash,
                        ),
                    )
                    conn.commit()
                    return candidate_id, True

                except sqlite3.IntegrityError:
                    existing_row = conn.execute(
                        "SELECT id, created_at FROM vagas WHERE canonical_url = ?",
                        (canonical_url,),
                    ).fetchone()

                    if existing_row is None:
                        raise

                    existing_id: str = existing_row["id"]
                    desc_row = conn.execute(
                        """
                        SELECT description_raw, content_hash
                        FROM vaga_descricoes
                        WHERE vaga_id = ?
                        """,
                        (existing_id,),
                    ).fetchone()

                    incoming_non_empty = bool(descricao and descricao.strip())

                    if desc_row is None:
                        conn.execute(
                            """
                            INSERT INTO vaga_descricoes (
                                vaga_id, description_raw, description_clean, content_hash
                            ) VALUES (?, ?, ?, ?)
                            """,
                            (
                                existing_id,
                                descricao,
                                description_clean,
                                content_hash,
                            ),
                        )
                        if incoming_non_empty:
                            conn.execute(
                                "UPDATE vagas SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                (existing_id,),
                            )
                    else:
                        stored_raw: str = desc_row["description_raw"] or ""
                        stored_hash: str = desc_row["content_hash"] or ""
                        should_backfill = not stored_raw.strip() and incoming_non_empty
                        should_update_revision = (
                            incoming_non_empty and content_hash != stored_hash
                        )

                        if should_backfill or should_update_revision:
                            conn.execute(
                                """
                                UPDATE vaga_descricoes
                                SET description_raw = ?,
                                    description_clean = COALESCE(?, description_clean),
                                    content_hash = ?,
                                    fetched_at = CURRENT_TIMESTAMP
                                WHERE vaga_id = ?
                                """,
                                (
                                    descricao,
                                    description_clean,
                                    content_hash,
                                    existing_id,
                                ),
                            )
                            conn.execute(
                                "UPDATE vagas SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                (existing_id,),
                            )

                    conn.commit()
                    return existing_id, False

            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise

    def resolve_vaga_id(self, identifier: str | int | None) -> str | None:
        """
        Resolve polymorphic identifier (integer, zero-padded string '062',
        cardinal '#62', or canonical hash 'vaga_...') to canonical vagas.id.
        """
        if identifier is None:
            return None
        raw_str = str(identifier).strip()
        cleaned = raw_str.lstrip("#").strip()
        with get_db_connection(self.db_path) as conn:
            if cleaned.isdigit():
                seq = int(cleaned)
                row = conn.execute(
                    """
                    SELECT id FROM vagas
                    WHERE seq_num = ? OR id = ?
                    ORDER BY (CASE WHEN id = ? THEN 0 ELSE 1 END)
                    LIMIT 1
                    """,
                    (seq, raw_str, raw_str),
                ).fetchone()
                if row is not None:
                    return str(row["id"])
            row = conn.execute(
                "SELECT id FROM vagas WHERE id = ?",
                (raw_str,),
            ).fetchone()
            return str(row["id"]) if row is not None else None

    def get_vaga(self, vaga_id: str | int) -> dict[str, Any] | None:
        """
        Read metadata row from `vagas` left-joined with `tracking_lifecycle`.
        Resolves polymorphic sequence number or canonical hash ID.
        Does not load heavy text from `vaga_descricoes`.
        """
        canonical_id = self.resolve_vaga_id(vaga_id)
        if canonical_id is None:
            return None

        with get_db_connection(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT
                    v.id,
                    v.id AS vaga_id,
                    v.seq_num,
                    v.canonical_url,
                    v.original_url,
                    v.company,
                    v.company_norm,
                    v.role,
                    v.role_norm,
                    v.source_portal,
                    v.location,
                    v.remote_type,
                    v.status_triagem,
                    v.created_at,
                    v.updated_at,
                    COALESCE(t.status, v.status_triagem) AS status,
                    t.score,
                    t.archetype,
                    t.application_date,
                    t.status_updated_at,
                    t.report_path,
                    t.cv_pdf_path,
                    t.notes
                FROM vagas v
                LEFT JOIN tracking_lifecycle t ON v.id = t.vaga_id
                WHERE v.id = ?
                """,
                (canonical_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def get_vaga_description(self, vaga_id: str | int) -> str | None:
        """Read `description_raw` from `vaga_descricoes` on demand (resolving polymorphic ID)."""
        canonical_id = self.resolve_vaga_id(vaga_id)
        if canonical_id is None:
            return None

        with get_db_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT description_raw FROM vaga_descricoes WHERE vaga_id = ?",
                (canonical_id,),
            ).fetchone()
            return row["description_raw"] if row is not None else None

    def list_vagas(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        *,
        status_triagem: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query `vagas LEFT JOIN tracking_lifecycle` without reading `vaga_descricoes`.
        When `status` (or `status_triagem`) is specified, filters via
        `COALESCE(tracking_lifecycle.status, vagas.status_triagem)`.
        """
        effective_filter = status if status is not None else status_triagem

        query = """
            SELECT
                v.id,
                v.seq_num,
                v.canonical_url,
                v.original_url,
                v.company,
                v.company_norm,
                v.role,
                v.role_norm,
                v.source_portal,
                v.location,
                v.remote_type,
                v.status_triagem,
                v.created_at,
                v.updated_at,
                COALESCE(t.status, v.status_triagem) AS status,
                t.score,
                t.archetype,
                t.application_date,
                t.status_updated_at,
                t.report_path,
                t.cv_pdf_path,
                t.notes
            FROM vagas v
            LEFT JOIN tracking_lifecycle t ON v.id = t.vaga_id
        """
        params: list[Any] = []

        if effective_filter is not None:
            norm_filter = effective_filter.strip().lower()
            if norm_filter == "triaged":
                query += " WHERE LOWER(v.status_triagem) = ?"
                params.append(norm_filter)
            else:
                query += " WHERE LOWER(COALESCE(t.status, v.status_triagem)) = ?"
                params.append(norm_filter)

        query += " ORDER BY v.created_at ASC, v.rowid ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with get_db_connection(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def update_lifecycle(
        self,
        vaga_id: str | int,
        status: str,
        score: float | None = None,
        archetype: str | None = None,
        application_date: str | None = None,
        report_path: str | None = None,
        cv_pdf_path: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Upsert candidate lifecycle progress in `tracking_lifecycle` and set
        `vagas.status_triagem = 'triaged'`.

        - Resolves polymorphic sequence number or canonical hash ID to canonical `vagas.id`.
        - Manages active lifecycle states (`evaluated`, `applied`, `interview`, `offer`,
          `rejected`, `discarded`, `skip`).
        - Terminal exit states (`rejected`, `discarded`, `skip`) are permitted from any
          prior active stage.
        - Active stages cannot be downgraded to a lower-ranked active stage.
        - Raises `KeyError` if `vaga_id` does not exist.
        """
        canonical_id = self.resolve_vaga_id(vaga_id)
        if canonical_id is None:
            raise KeyError(f"Vaga '{vaga_id}' does not exist.")

        normalized_status = status.strip().lower()
        if normalized_status not in VALID_LIFECYCLE_STATUSES:
            raise ValueError(
                f"Invalid lifecycle status {status!r}. "
                f"Expected one of: {sorted(VALID_LIFECYCLE_STATUSES)}"
            )

        with get_db_connection(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                vaga_row = conn.execute(
                    "SELECT id FROM vagas WHERE id = ?",
                    (canonical_id,),
                ).fetchone()
                if vaga_row is None:
                    raise KeyError(f"Vaga '{vaga_id}' does not exist.")

                existing_lifecycle = conn.execute(
                    "SELECT status FROM tracking_lifecycle WHERE vaga_id = ?",
                    (canonical_id,),
                ).fetchone()

                effective_status = normalized_status
                if existing_lifecycle is not None:
                    current_status = (existing_lifecycle["status"] or "").strip().lower()
                    if (
                        current_status in ACTIVE_LIFECYCLE_STATUSES
                        and normalized_status in ACTIVE_LIFECYCLE_STATUSES
                        and STATUS_RANK.get(normalized_status, 0)
                        < STATUS_RANK.get(current_status, 0)
                    ):
                        effective_status = current_status

                conn.execute(
                    """
                    INSERT INTO tracking_lifecycle (
                        vaga_id, status, score, archetype, application_date,
                        status_updated_at, report_path, cv_pdf_path, notes
                    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
                    ON CONFLICT(vaga_id) DO UPDATE SET
                        status = excluded.status,
                        score = COALESCE(excluded.score, tracking_lifecycle.score),
                        archetype = COALESCE(excluded.archetype, tracking_lifecycle.archetype),
                        application_date = COALESCE(
                            excluded.application_date, tracking_lifecycle.application_date
                        ),
                        status_updated_at = CURRENT_TIMESTAMP,
                        report_path = COALESCE(
                            excluded.report_path, tracking_lifecycle.report_path
                        ),
                        cv_pdf_path = COALESCE(
                            excluded.cv_pdf_path, tracking_lifecycle.cv_pdf_path
                        ),
                        notes = COALESCE(excluded.notes, tracking_lifecycle.notes)
                    """,
                    (
                        canonical_id,
                        effective_status,
                        score,
                        archetype,
                        application_date,
                        report_path,
                        cv_pdf_path,
                        notes,
                    ),
                )

                conn.execute(
                    "UPDATE vagas SET status_triagem = 'triaged' WHERE id = ?",
                    (canonical_id,),
                )
                conn.commit()
            except Exception:
                if conn.in_transaction:
                    conn.rollback()
                raise

        result = self.get_vaga(canonical_id)
        assert result is not None
        return result

    def get_pipeline_stats(self) -> dict[str, Any]:
        """
        Compute fast pipeline aggregates grouped by
        `COALESCE(tracking_lifecycle.status, vagas.status_triagem)`.
        """
        with get_db_connection(self.db_path) as conn:
            status_rows = conn.execute(
                """
                SELECT
                    COALESCE(t.status, v.status_triagem) AS effective_status,
                    COUNT(*) AS cnt
                FROM vagas v
                LEFT JOIN tracking_lifecycle t ON v.id = t.vaga_id
                GROUP BY effective_status
                """
            ).fetchall()

            by_status: dict[str, int] = {
                row["effective_status"]: int(row["cnt"]) for row in status_rows
            }
            total = sum(by_status.values())

            avg_row = conn.execute(
                "SELECT AVG(score) AS avg_score FROM tracking_lifecycle WHERE score IS NOT NULL"
            ).fetchone()
            avg_score = (
                round(float(avg_row["avg_score"]), 2)
                if avg_row is not None and avg_row["avg_score"] is not None
                else None
            )

            return {
                "total": total,
                "by_status": by_status,
                "avg_score": avg_score,
            }

    def backup_db(self, backup_dir: Path | None = None) -> Path:
        """
        Create a timestamped online SQLite backup in `workspace/backups/`.
        """
        if backup_dir is None:
            backup_dir = resolve_root() / "workspace" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"career_ops_{timestamp}.db"

        with get_db_connection(self.db_path) as src_conn:
            dest_conn = sqlite3.connect(str(backup_path))
            try:
                src_conn.backup(dest_conn)
            finally:
                dest_conn.close()

        return backup_path


def insert_vaga(
    vaga: VagaInput,
    descricao: str = "",
    description_clean: str | None = None,
    db_path: Path | None = None,
) -> tuple[str, bool]:
    """Module-level convenience wrapper around `CareerOpsRepository.insert_vaga`."""
    return CareerOpsRepository(db_path).insert_vaga(
        vaga, descricao, description_clean=description_clean
    )


def resolve_vaga_id(
    identifier: str | int | None, db_path: Path | None = None
) -> str | None:
    """Module-level convenience wrapper around `CareerOpsRepository.resolve_vaga_id`."""
    return CareerOpsRepository(db_path).resolve_vaga_id(identifier)


def get_vaga(vaga_id: str | int, db_path: Path | None = None) -> dict[str, Any] | None:
    """Module-level convenience wrapper around `CareerOpsRepository.get_vaga`."""
    return CareerOpsRepository(db_path).get_vaga(vaga_id)


def get_vaga_description(vaga_id: str | int, db_path: Path | None = None) -> str | None:
    """Module-level convenience wrapper around `CareerOpsRepository.get_vaga_description`."""
    return CareerOpsRepository(db_path).get_vaga_description(vaga_id)


def list_vagas(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Module-level convenience wrapper around `CareerOpsRepository.list_vagas`."""
    return CareerOpsRepository(db_path).list_vagas(
        status=status, limit=limit, offset=offset
    )


def update_lifecycle(
    vaga_id: str | int,
    status: str,
    score: float | None = None,
    archetype: str | None = None,
    application_date: str | None = None,
    report_path: str | None = None,
    cv_pdf_path: str | None = None,
    notes: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Module-level convenience wrapper around `CareerOpsRepository.update_lifecycle`."""
    return CareerOpsRepository(db_path).update_lifecycle(
        vaga_id=vaga_id,
        status=status,
        score=score,
        archetype=archetype,
        application_date=application_date,
        report_path=report_path,
        cv_pdf_path=cv_pdf_path,
        notes=notes,
    )


def get_pipeline_stats(db_path: Path | None = None) -> dict[str, Any]:
    """Module-level convenience wrapper around `CareerOpsRepository.get_pipeline_stats`."""
    return CareerOpsRepository(db_path).get_pipeline_stats()


def get_canonical_report_path(vaga: dict[str, Any]) -> str:
    """Return root-relative canonical report path e.g. output/reports/062-role-company.md."""
    seq = vaga.get("seq_num") or 1
    role = vaga.get("role") or "role"
    company = vaga.get("company") or "company"
    from .utils import build_report_filename

    filename = build_report_filename(seq, role, company)
    return f"output/reports/{filename}"
