"""
test_db.py — Unit tests for SQLite engine, schema DDL, models, and content hashing.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from career_ops.config import get_db_path, resolve_root
from career_ops.db import SCHEMA_VERSION, get_db_connection, init_db
from career_ops.models import TrackingLifecycle, Vaga, VagaDescricao, VagaInput
from career_ops.utils import compute_content_hash


class TestModelsAndUtils:
    def test_vaga_dataclasses(self) -> None:
        v_in = VagaInput(
            original_url="https://boards.greenhouse.io/acme/jobs/123",
            company="Acme Corp",
            role="Senior Data Engineer",
            source_portal="greenhouse",
            canonical_url="greenhouse:acme:123",
            company_norm="acme corp",
            role_norm="senior data engineer",
            location="Remote",
            remote_type="remote",
        )
        assert v_in.company == "Acme Corp"
        assert v_in.canonical_url == "greenhouse:acme:123"

        vaga = Vaga(
            original_url=v_in.original_url,
            company=v_in.company,
            role=v_in.role,
            source_portal=v_in.source_portal,
            id="vaga_001",
        )
        assert vaga.id == "vaga_001"
        assert vaga.status_triagem == "queued"

        desc = VagaDescricao(
            vaga_id="vaga_001",
            description_raw="Full job description",
            content_hash=compute_content_hash("Full job description"),
        )
        assert desc.vaga_id == "vaga_001"
        assert desc.description_clean is None

        lifecycle = TrackingLifecycle(
            vaga_id="vaga_001",
            status="evaluated",
            score=4.5,
            archetype="Data Platform",
            report_path="workspace/reports/report_001.md",
        )
        assert lifecycle.score == 4.5
        assert lifecycle.status == "evaluated"

    def test_compute_content_hash_collapses_whitespace(self) -> None:
        text_a = "Senior   Data Engineer\n\nBuild pipelines\twith Python."
        text_b = "Senior Data Engineer Build pipelines with Python."
        expected = hashlib.sha256(text_b.encode("utf-8")).hexdigest()

        assert compute_content_hash(text_a) == expected
        assert compute_content_hash(text_b) == expected
        assert compute_content_hash("Different description") != expected

    def test_config_db_path_and_resolve_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db_file = tmp_path / "data" / "career_ops.db"
        db_file.parent.mkdir(parents=True)
        db_file.touch()

        monkeypatch.delenv("CAREER_OPS_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)

        resolved = resolve_root()
        assert resolved == tmp_path.resolve()
        assert get_db_path(tmp_path) == db_file
        assert get_db_path() == db_file.resolve()


class TestDatabaseEngine:
    def test_connection_pragmas(self, tmp_path: Path) -> None:
        db_path = tmp_path / "data" / "career_ops.db"
        with get_db_connection(db_path) as conn:
            assert isinstance(conn, sqlite3.Connection)
            assert conn.row_factory is sqlite3.Row
            assert conn.isolation_level is None

            journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            foreign_keys = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
            busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]

            assert journal_mode.lower() == "wal"
            assert foreign_keys == 1
            assert busy_timeout == 5000

    def test_init_db_creates_tables_indexes_and_triggers_idempotently(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "data" / "career_ops.db"
        init_db(db_path)
        # Second call should succeed without errors (idempotent DDL)
        init_db(db_path)

        with get_db_connection(db_path) as conn:
            tables = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table';"
                ).fetchall()
            }
            assert {"vagas", "vaga_descricoes", "tracking_lifecycle"}.issubset(tables)

            indexes = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index';"
                ).fetchall()
            }
            assert {
                "idx_vagas_triagem",
                "idx_vagas_company_role",
                "idx_tracking_status",
            }.issubset(indexes)

            triggers = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'trigger';"
                ).fetchall()
            }
            assert "trg_vagas_updated_at" in triggers

            user_version = conn.execute("PRAGMA user_version;").fetchone()[0]
            assert user_version == SCHEMA_VERSION

    def test_canonical_url_unique_constraint(self, tmp_path: Path) -> None:
        db_path = tmp_path / "data" / "career_ops.db"
        init_db(db_path)

        with get_db_connection(db_path) as conn:
            conn.execute(
                """
                INSERT INTO vagas (
                    id, canonical_url, original_url, company, company_norm,
                    role, role_norm, source_portal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "vaga_1",
                    "greenhouse:acme:123",
                    "https://boards.greenhouse.io/acme/jobs/123",
                    "Acme",
                    "acme",
                    "Engineer",
                    "engineer",
                    "greenhouse",
                ),
            )

            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO vagas (
                        id, canonical_url, original_url, company, company_norm,
                        role, role_norm, source_portal
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "vaga_2",
                        "greenhouse:acme:123",
                        "https://boards.greenhouse.io/acme/jobs/123?utm_source=test",
                        "Acme",
                        "acme",
                        "Engineer",
                        "engineer",
                        "greenhouse",
                    ),
                )

    def test_foreign_key_enforcement_and_cascade_delete(self, tmp_path: Path) -> None:
        db_path = tmp_path / "data" / "career_ops.db"
        init_db(db_path)

        with get_db_connection(db_path) as conn:
            # Inserting child record for non-existent vaga_id must fail
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO vaga_descricoes (vaga_id, description_raw, content_hash)
                    VALUES (?, ?, ?)
                    """,
                    ("missing_vaga", "raw text", "hash123"),
                )

            conn.execute(
                """
                INSERT INTO vagas (
                    id, canonical_url, original_url, company, company_norm,
                    role, role_norm, source_portal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "vaga_cascade",
                    "lever:beta:456",
                    "https://jobs.lever.co/beta/456",
                    "Beta",
                    "beta",
                    "Data Scientist",
                    "data scientist",
                    "lever",
                ),
            )
            conn.execute(
                """
                INSERT INTO vaga_descricoes (vaga_id, description_raw, content_hash)
                VALUES (?, ?, ?)
                """,
                ("vaga_cascade", "Description payload", "hash_456"),
            )
            conn.execute(
                """
                INSERT INTO tracking_lifecycle (vaga_id, status, score)
                VALUES (?, ?, ?)
                """,
                ("vaga_cascade", "evaluated", 4.2),
            )

            # Deleting parent row must cascade to both child tables
            conn.execute("DELETE FROM vagas WHERE id = ?", ("vaga_cascade",))

            desc_count = conn.execute(
                "SELECT COUNT(*) FROM vaga_descricoes WHERE vaga_id = ?",
                ("vaga_cascade",),
            ).fetchone()[0]
            tracking_count = conn.execute(
                "SELECT COUNT(*) FROM tracking_lifecycle WHERE vaga_id = ?",
                ("vaga_cascade",),
            ).fetchone()[0]

            assert desc_count == 0
            assert tracking_count == 0

    def test_updated_at_trigger_fires_on_vaga_update(self, tmp_path: Path) -> None:
        db_path = tmp_path / "data" / "career_ops.db"
        init_db(db_path)

        with get_db_connection(db_path) as conn:
            conn.execute(
                """
                INSERT INTO vagas (
                    id, canonical_url, original_url, company, company_norm,
                    role, role_norm, source_portal, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "vaga_trig",
                    "ashby:gamma:789",
                    "https://jobs.ashbyhq.com/gamma/789",
                    "Gamma",
                    "gamma",
                    "ML Engineer",
                    "ml engineer",
                    "ashby",
                    "2020-01-01 00:00:00",
                    "2020-01-01 00:00:00",
                ),
            )

            conn.execute(
                "UPDATE vagas SET status_triagem = 'triaged' WHERE id = ?",
                ("vaga_trig",),
            )

            row = conn.execute(
                "SELECT created_at, updated_at, status_triagem FROM vagas WHERE id = ?",
                ("vaga_trig",),
            ).fetchone()

            assert row["status_triagem"] == "triaged"
            assert row["created_at"] == "2020-01-01 00:00:00"
            assert row["updated_at"] != "2020-01-01 00:00:00"

    def test_legacy_schema_migration_backfills_seq_num(self, tmp_path: Path) -> None:
        db_path = tmp_path / "data" / "career_ops.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Create legacy v1 schema lacking seq_num
        with get_db_connection(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE vagas (
                    id TEXT PRIMARY KEY,
                    canonical_url TEXT NOT NULL UNIQUE,
                    original_url TEXT NOT NULL,
                    company TEXT NOT NULL,
                    company_norm TEXT NOT NULL,
                    role TEXT NOT NULL,
                    role_norm TEXT NOT NULL,
                    source_portal TEXT NOT NULL,
                    location TEXT,
                    remote_type TEXT,
                    status_triagem TEXT NOT NULL DEFAULT 'queued',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute("PRAGMA user_version = 1;")
            conn.execute(
                """
                INSERT INTO vagas (id, canonical_url, original_url, company, company_norm, role, role_norm, source_portal)
                VALUES ('v1', 'url1', 'http://a', 'Co A', 'co a', 'Role A', 'role a', 'p1'),
                       ('v2', 'url2', 'http://b', 'Co B', 'co b', 'Role B', 'role b', 'p2');
                """
            )

        # Run init_db to trigger migration
        init_db(db_path)

        with get_db_connection(db_path) as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(vagas)").fetchall()]
            assert "seq_num" in cols
            rows = conn.execute("SELECT id, seq_num FROM vagas ORDER BY rowid").fetchall()
            assert rows[0]["seq_num"] == 1
            assert rows[1]["seq_num"] == 2
            assert conn.execute("PRAGMA user_version;").fetchone()[0] == 2
