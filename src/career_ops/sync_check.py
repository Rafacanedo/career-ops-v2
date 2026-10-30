"""
sync_check.py — Validate that the career-ops setup is consistent.

Port of cv-sync-check.mjs.

Checks:
  1. cv.md exists and is not empty
  2. config/profile.yml exists and has required fields filled in
  3. No hardcoded metrics in _shared.md or batch/batch-prompt.md
  4. article-digest.md freshness (if it exists, <30 days)
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import click

from .context import CareerOpsContext, pass_ctx

# Pattern for hardcoded metrics (numbers followed by units)
_METRIC_PATTERN = re.compile(
    r"\b\d{2,4}\+?\s*(hours?|%|evals?|layers?|tests?|fields?|bases?)\b",
    re.IGNORECASE,
)

# Lines to skip when looking for hardcoded metrics
_METRIC_SKIP = ("NEVER hardcode", "NUNCA hardcode")


def run_sync_check(root: Path) -> tuple[list[str], list[str]]:
    """
    Run all sync-consistency checks.

    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    def pick_existing(*paths: Path) -> Path:
        for path in paths:
            if path.exists():
                return path
        return paths[0]

    # --- Check 1: cv.md ---
    cv_path = pick_existing(root / "content" / "cv.md", root / "cv.md")
    if not cv_path.exists():
        errors.append(
            "cv.md not found. "
            "Create it with your CV in markdown format."
        )
    else:
        content = cv_path.read_text(encoding="utf-8-sig")
        if len(content.strip()) < 100:
            warnings.append(
                "cv.md seems too short. Make sure it contains your full CV."
            )

    # --- Check 2: config/profile.yml ---
    profile_path = root / "config" / "profile.yml"
    if not profile_path.exists():
        errors.append(
            "config/profile.yml not found. "
            "Copy from config/profile.example.yml and fill in your details."
        )
    else:
        profile_content = profile_path.read_text(encoding="utf-8-sig")
        required_fields = ["full_name", "email", "location"]
        for field in required_fields:
            if field not in profile_content or '"Jane Smith"' in profile_content:
                warnings.append(
                    f"config/profile.yml may still have example data. Check field: {field}"
                )
                break

    # --- Check 3: Hardcoded metrics ---
    files_to_check = [
        (root / "content" / "modes" / "_shared.md", "_shared.md"),
        (root / "workspace" / "tracker-additions" / "batch-prompt.md", "batch-prompt.md"),
    ]
    for path, name in files_to_check:
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if any(skip in line for skip in _METRIC_SKIP):
                continue
            if line.startswith("#") or line.startswith("<!--"):
                continue
            matches = _METRIC_PATTERN.findall(line)
            if matches:
                warnings.append(
                    f"{name}:{lineno} — Possible hardcoded metric: \"{matches[0]}\". "
                    "Should this be read from cv.md/article-digest.md?"
                )

    # --- Check 4: article-digest.md freshness ---
    digest_path = pick_existing(root / "content" / "article-digest.md", root / "article-digest.md")
    if digest_path.exists():
        mtime = datetime.fromtimestamp(digest_path.stat().st_mtime, tz=UTC)
        now = datetime.now(tz=UTC)
        days_old = (now - mtime).days
        if days_old > 30:
            warnings.append(
                f"article-digest.md is {days_old} days old. "
                "Consider updating if your projects have new metrics."
            )

    return errors, warnings


# ---------------------------------------------------------------------------
# Click command
# ---------------------------------------------------------------------------

@click.command()
@pass_ctx
def sync_check_cmd(ctx: CareerOpsContext) -> None:
    """Validate career-ops setup consistency (cv.md, profile, metrics)."""
    click.echo("\n=== career-ops sync check ===\n")

    errors, warnings = run_sync_check(ctx.root)

    if not errors and not warnings:
        click.echo("All checks passed.")
    else:
        if errors:
            click.echo(f"ERRORS ({len(errors)}):")
            for e in errors:
                click.echo(f"  ERROR: {e}")
        if warnings:
            click.echo(f"\nWARNINGS ({len(warnings)}):")
            for w in warnings:
                click.echo(f"  WARN: {w}")

    click.echo("")
    sys.exit(1 if errors else 0)
