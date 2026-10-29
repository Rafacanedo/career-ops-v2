"""
merge_tracker.py — Merge tracker additions into applications.md.

Port of merge-tracker.mjs.

Reads all .tsv files from workspace/tracker-additions/, validates and parses them,
deduplicates against existing applications.md, and either:
  - Inserts new entries (after the table header)
  - Updates existing entries in-place if the new score is higher
  - Skips if the existing entry already has an equal or higher score
  - Moves processed .tsv files to tracker-additions/merged/

Handles three TSV input formats (9-col, 8-col, pipe-delimited markdown).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import click

from .config import get_apps_file, get_additions_dir
from .parser import read_applications, parse_tsv_content
from .utils import normalize_company, role_fuzzy_match, parse_score, extract_report_num
from .context import pass_ctx, CareerOpsContext


def run_merge(root: Path, dry_run: bool = False, verify_after: bool = False) -> dict:
    """
    Run the tracker merge operation.

    Returns a dict with keys: added, updated, skipped.
    """
    apps_file = get_apps_file(root)
    additions_dir = get_additions_dir(root)
    merged_dir = additions_dir / "merged"

    # --- Read current applications.md ---
    if not apps_file.exists():
        click.echo("No applications.md found. Nothing to merge into.")
        return {"added": 0, "updated": 0, "skipped": 0}

    lines, existing_apps = read_applications(apps_file)
    max_num = max((e.num for e in existing_apps), default=0)
    click.echo(f"📊 Existing: {len(existing_apps)} entries, max #{max_num}")

    # --- Read pending TSV additions from workspace/tracker-additions/ ---
    if not additions_dir.exists():
        click.echo("No tracker-additions directory found.")
        return {"added": 0, "updated": 0, "skipped": 0}

    tsv_files = sorted(
        [f for f in additions_dir.iterdir() if f.suffix == ".tsv"],
        key=lambda f: int("".join(c for c in f.stem if c.isdigit()) or "0"),
    )

    if not tsv_files:
        click.echo("✅ No pending additions to merge.")
        return {"added": 0, "updated": 0, "skipped": 0}

    click.echo(f"📥 Found {len(tsv_files)} pending additions")

    added = 0
    updated = 0
    skipped = 0
    new_lines: list[str] = []

    for tsv_file in tsv_files:
        content = tsv_file.read_text(encoding="utf-8").strip()
        addition = parse_tsv_content(content, tsv_file.name)
        if addition is None:
            skipped += 1
            continue

        # --- Dedup detection (3 methods) ---
        report_num = extract_report_num(addition.report)
        duplicate = None

        # Method 1: exact report number match
        if report_num:
            for app in existing_apps:
                if extract_report_num(app.report) == report_num:
                    duplicate = app
                    break

        # Method 2: exact entry number match
        if not duplicate:
            for app in existing_apps:
                if app.num == addition.num:
                    duplicate = app
                    break

        # Method 3: company + role fuzzy match
        if not duplicate:
            norm_company = normalize_company(addition.company)
            for app in existing_apps:
                if normalize_company(app.company) != norm_company:
                    continue
                if role_fuzzy_match(addition.role, app.role):
                    duplicate = app
                    break

        # --- Handle duplicate or new entry ---
        if duplicate:
            new_score = parse_score(addition.score)
            old_score = parse_score(duplicate.score)

            if new_score > old_score:
                click.echo(
                    f"🔄 Update: #{duplicate.num} {addition.company} — {addition.role} "
                    f"({old_score}→{new_score})"
                )
                # Find and update the line in-place
                for i, line in enumerate(lines):
                    if line == duplicate.raw:
                        updated_line = (
                            f"| {duplicate.num} | {addition.date} | {addition.company} | "
                            f"{addition.role} | {duplicate.status} | {addition.score} | "
                            f"{duplicate.pdf} | {addition.report} | "
                            f"Re-eval {addition.date} ({old_score}→{new_score}). {addition.notes} |"
                        )
                        lines[i] = updated_line
                        updated += 1
                        break
            else:
                click.echo(
                    f"⏭️  Skip: {addition.company} — {addition.role} "
                    f"(existing #{duplicate.num} {old_score} >= new {new_score})"
                )
                skipped += 1
        else:
            # New entry
            entry_num = addition.num if addition.num > max_num else max_num + 1
            if addition.num > max_num:
                max_num = addition.num
            else:
                max_num = entry_num

            new_line = (
                f"| {entry_num} | {addition.date} | {addition.company} | "
                f"{addition.role} | {addition.status} | {addition.score} | "
                f"{addition.pdf} | {addition.report} | {addition.notes} |"
            )
            new_lines.append(new_line)
            added += 1
            click.echo(
                f"➕ Add #{entry_num}: {addition.company} — {addition.role} ({addition.score})"
            )

    # --- Insert new lines after table header separator ---
    if new_lines:
        insert_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("|") and ("---" in line or "|-|" in line):
                insert_idx = i + 1
                break
        if insert_idx >= 0:
            lines[insert_idx:insert_idx] = new_lines

    # --- Write back and move processed files ---
    if not dry_run:
        apps_file.write_text("\n".join(lines), encoding="utf-8")
        merged_dir.mkdir(parents=True, exist_ok=True)
        for tsv_file in tsv_files:
            shutil.move(str(tsv_file), str(merged_dir / tsv_file.name))
        click.echo(f"\n✅ Moved {len(tsv_files)} TSVs to merged/")

    click.echo(f"\n📊 Summary: +{added} added, 🔄{updated} updated, ⏭️{skipped} skipped")
    if dry_run:
        click.echo("(dry-run — no changes written)")

    # --- Optional verify ---
    if verify_after and not dry_run:
        click.echo("\n--- Running verification ---")
        from .verify import run_verify
        errors, _ = run_verify(root)
        if errors > 0:
            sys.exit(1)

    return {"added": added, "updated": updated, "skipped": skipped}


# ---------------------------------------------------------------------------
# Click command
# ---------------------------------------------------------------------------

@click.command()
@click.option("--dry-run", is_flag=True, help="Preview changes without writing.")
@click.option("--verify", "verify_after", is_flag=True, help="Run verify after merge.")
@pass_ctx
def merge_cmd(ctx: CareerOpsContext, dry_run: bool, verify_after: bool) -> None:
    """Merge pending tracker TSV additions into applications.md."""
    run_merge(ctx.root, dry_run=dry_run, verify_after=verify_after)
