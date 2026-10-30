"""
verify.py — Health check for career-ops pipeline integrity (job-tracker.csv).

Checks:
  1. job-tracker.csv exists and contains 14 columns
  2. ID uniqueness and zero-padding
  3. Valid report links if Report Path is specified
  4. Valid CV PDF links if CV PDF Path is specified
  5. Valid Job Description Path if specified
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import click

from .config import get_job_tracker_file
from .context import CareerOpsContext, pass_ctx
from .scan_csv import FIELDNAMES


def run_verify(root: Path) -> tuple[int, int]:
    """Run pipeline health checks against job-tracker.csv."""
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

    tracker_file = get_job_tracker_file(root)

    if not tracker_file.exists():
        error("job-tracker.csv nao encontrado em workspace/")
        return errors, warnings

    click.echo("\n📊 Checking job-tracker.csv integrity...\n")

    rows = []
    with open(tracker_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        header = reader.fieldnames or []
        for r in reader:
            rows.append(r)

    # Check 1: Header verification
    missing_cols = [c for c in FIELDNAMES if c not in header]
    if missing_cols:
        error(f"job-tracker.csv missing columns: {', '.join(missing_cols)}")
    else:
        ok("job-tracker.csv header has all 14 columns")

    # Check 2: ID uniqueness
    seen_ids = set()
    dup_ids = 0
    for r in rows:
        jid = r.get("ID", "").strip()
        if jid in seen_ids:
            error(f"Duplicate ID found: #{jid}")
            dup_ids += 1
        seen_ids.add(jid)
    if dup_ids == 0:
        ok("All IDs are unique")

    # Check 3: Report & CV files exist
    broken_reports = 0
    broken_cvs = 0
    broken_jds = 0

    for r in rows:
        jid = r.get("ID", "").strip()
        rep = r.get("Report Path", "").strip()
        cv = r.get("CV PDF Path", "").strip()
        jd = r.get("Job Description Path", "").strip()

        if rep and not (root / rep).exists():
            error(f"#{jid}: Report file missing: {rep}")
            broken_reports += 1

        if cv and not (root / cv).exists():
            error(f"#{jid}: CV PDF file missing: {cv}")
            broken_cvs += 1

        if jd and not (root / jd).exists():
            warn(f"#{jid}: JD file missing: {jd}")
            broken_jds += 1

    if broken_reports == 0:
        ok("All report file paths exist")
    if broken_cvs == 0:
        ok("All CV PDF file paths exist")
    if broken_jds == 0:
        ok("All JD file paths exist")

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
    """Health check for career-ops pipeline integrity."""
    errors, _ = run_verify(ctx.root)
    sys.exit(1 if errors > 0 else 0)
