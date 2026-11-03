"""
db.py — SQLite connection lifecycle management and schema initialization.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import get_db_path

SCHEMA_VERSION = 2

SCHEMA_DDL = """
PRAGMA foreign_keys = ON;

-- Table 1: Ingested Opportunities (Metadata)
CREATE TABLE IF NOT EXISTS vagas (
    id TEXT PRIMARY KEY,
    seq_num INTEGER UNIQUE,
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

CREATE INDEX IF NOT EXISTS idx_vagas_triagem ON vagas(status_triagem);
CREATE INDEX IF NOT EXISTS idx_vagas_company_role ON vagas(company_norm, role_norm);
CREATE INDEX IF NOT EXISTS idx_vagas_seq_num ON vagas(seq_num);

-- Trigger: Automatically touch updated_at timestamp on vacancy updates
CREATE TRIGGER IF NOT EXISTS trg_vagas_updated_at
AFTER UPDATE ON vagas
BEGIN
    UPDATE vagas SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Table 2: Job Description Content (Isolated Payload)
CREATE TABLE IF NOT EXISTS vaga_descricoes (
    vaga_id TEXT PRIMARY KEY,
    description_raw TEXT NOT NULL,
    description_clean TEXT,
    content_hash TEXT NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vaga_id) REFERENCES vagas(id) ON DELETE CASCADE
);

-- Table 3: Candidate Application Lifecycle & Artifact Pointers
CREATE TABLE IF NOT EXISTS tracking_lifecycle (
    vaga_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'evaluated',
    score REAL,
    archetype TEXT,
    application_date DATE,
    status_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    report_path TEXT,
    cv_pdf_path TEXT,
    notes TEXT,
    FOREIGN KEY (vaga_id) REFERENCES vagas(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tracking_status ON tracking_lifecycle(status);
"""


class ManagedConnection(sqlite3.Connection):
    """
    SQLite connection subclass that closes the connection when exiting a `with` block,
    preventing file lock leaks on Windows NTFS while remaining a `sqlite3.Connection`.
    """

    def __enter__(self) -> ManagedConnection:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        try:
            if self.in_transaction:
                if exc_type is None:
                    self.commit()
                else:
                    self.rollback()
        except sqlite3.ProgrammingError:
            pass
        finally:
            self.close()
        return False


def get_db_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """
    Open and configure a SQLite connection with WAL mode, foreign keys, and busy timeout.
    Defaults to `<root>/data/career_ops.db` when `db_path` is omitted.
    """
    target_path = Path(db_path) if db_path is not None else get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(target_path),
        isolation_level=None,
        factory=ManagedConnection,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def init_db(db_path: Path | None = None) -> None:
    """
    Idempotently initialize the SQLite schema, indexes, and triggers.
    """
    with get_db_connection(db_path) as conn:
        # Backward-compatible schema migration: check legacy table before running DDL
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'vagas';"
        ).fetchone()
        if table_exists:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(vagas);").fetchall()]
            if "seq_num" not in cols:
                conn.execute("ALTER TABLE vagas ADD COLUMN seq_num INTEGER;")
            conn.execute("UPDATE vagas SET seq_num = rowid WHERE seq_num IS NULL;")

        conn.executescript(SCHEMA_DDL)
        conn.execute("PRAGMA foreign_keys=ON;")

        current_version = conn.execute("PRAGMA user_version;").fetchone()[0]
        if current_version < SCHEMA_VERSION:
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")
