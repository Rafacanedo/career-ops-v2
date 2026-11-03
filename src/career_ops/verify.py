"""
verify.py — Health check for career-ops SQLite database and deliverable artifacts.

Checks:
  1. data/career_ops.db exists and passes SQLite integrity_check
  2. Required relational tables (vagas, vaga_descricoes, tracking_lifecycle) exist
  3. Referenced report markdown files in tracking_lifecycle exist on disk
  4. Referenced CV PDF files in tracking_lifecycle exist on disk
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click

from .config import get_db_path
from .context import CareerOpsContext, pass_ctx
from .db import get_db_connection
from .repository import CareerOpsRepository

REQUIRED_TABLES = {"vagas", "vaga_descricoes", "tracking_lifecycle"}


def _resolve_artifact_path(root: Path, raw_ref: str) -> Path:
    ref = raw_ref.strip()
    md_match = re.match(r"\[([^\]]+)\]\(([^)]+)\)", ref)
    if md_match:
        ref = md_match.group(2).strip()
    elif ref.startswith("local:"):
        ref = ref.split(":", 1)[1].strip()

    p = Path(ref)
    if p.is_absolute():
        return p

    candidates = [
        root / ref,
        root / "output" / "cv" / Path(ref).name,
        root / "output" / "reports" / Path(ref).name,
        root / "workspace" / ref,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def run_verify(root: Path) -> tuple[int, int]:
    """Run pipeline health checks against data/career_ops.db and artifact files."""
    errors = 0
    warnings = 0

    def error(msg: str) -> None:
        nonlocal errors
        click.echo(f"❌ {msg}")
        errors += 1

    def warn(msg: str) -> None:
        nonlocal warnings
        click.echo(f"⚠️  {msg}")
        warnings += 1

    def ok(msg: str) -> None:
        click.echo(f"✅ {msg}")

    db_path = get_db_path(root)
    if not db_path.exists():
        error(f"Database file not found: {db_path}")
        return errors, warnings

    click.echo("\n📊 Checking SQLite database integrity...\n")

    try:
        with get_db_connection(db_path) as conn:
            integrity = conn.execute("PRAGMA integrity_check;").fetchone()
            if not integrity or str(integrity[0]).lower() != "ok":
                error(f"SQLite integrity check failed: {integrity[0] if integrity else 'unknown'}")
                return errors, warnings
            ok("SQLite PRAGMA integrity_check passed")

            table_rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            present_tables = {r["name"] for r in table_rows}
            missing_tables = REQUIRED_TABLES - present_tables
            if missing_tables:
                error(f"Missing required database tables: {', '.join(sorted(missing_tables))}")
                return errors, warnings
            ok("All 3 relational tables (vagas, vaga_descricoes, tracking_lifecycle) exist")
    except Exception as exc:
        error(f"Failed to read SQLite database: {exc}")
        return errors, warnings

    repo = CareerOpsRepository(db_path=db_path, auto_init=False)
    rows = repo.list_vagas(limit=100000)

    broken_reports = 0
    broken_cvs = 0

    for r in rows:
        vid = r.get("id", "")
        rep = (r.get("report_path") or "").strip()
        cv = (r.get("cv_pdf_path") or "").strip()

        if rep and not _resolve_artifact_path(root, rep).exists():
            error(f"{vid}: Report file missing: {rep}")
            broken_reports += 1

        if cv and not _resolve_artifact_path(root, cv).exists():
            error(f"{vid}: CV PDF file missing: {cv}")
            broken_cvs += 1

    if broken_reports == 0:
        ok("All report file paths exist")
    if broken_cvs == 0:
        ok("All CV PDF file paths exist")

    click.echo("\n" + "=" * 50)
    click.echo(f"📊 Pipeline Health: {errors} errors, {warnings} warnings")
    if errors == 0 and warnings == 0:
        click.echo("🟢 Pipeline is clean!")
    elif errors == 0:
        click.echo("🟡 Pipeline OK with warnings")
    else:
        click.echo("🔴 Pipeline has errors — fix before proceeding")

    return errors, warnings


@click.command()
@pass_ctx
def verify_cmd(ctx: CareerOpsContext) -> None:
    """Health check for career-ops SQLite pipeline integrity."""
    errors, _ = run_verify(ctx.root)
    sys.exit(1 if errors > 0 else 0)
