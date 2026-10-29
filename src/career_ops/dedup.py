"""
dedup.py — Remove duplicate entries from applications.md.

Port of dedup-tracker.mjs.

Groups entries by normalised company + fuzzy role match.
Keeps the entry with the highest score. If a removed entry had
a more advanced pipeline status, that status is preserved on the kept entry.
Merges notes (future enhancement).
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import click

from .config import get_apps_file
from .parser import read_applications
from .utils import normalize_company, normalize_role, parse_score, get_status_rank
from .context import pass_ctx, CareerOpsContext


def run_dedup(root: Path, dry_run: bool = False) -> int:
    """
    Run deduplication on applications.md.

    Returns the number of duplicates removed.
    """
    apps_file = get_apps_file(root)

    if not apps_file.exists():
        click.echo("No applications.md found. Nothing to dedup.")
        return 0

    lines, entries = read_applications(apps_file)
    click.echo(f"📊 {len(entries)} entries loaded")

    # Build line-index map: entry num → index in `lines`
    entry_line_map: dict[int, int] = {}
    for i, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        try:
            num = int(parts[1])
            if num > 0:
                entry_line_map[num] = i
        except ValueError:
            continue

    # Group entries by normalised company name
    company_groups: dict[str, list] = {}
    for entry in entries:
        key = normalize_company(entry.company)
        company_groups.setdefault(key, []).append(entry)

    removed = 0
    lines_to_remove: set[int] = set()

    for company_entries in company_groups.values():
        if len(company_entries) < 2:
            continue

        # Within same company, cluster by fuzzy role match
        processed: set[int] = set()
        for i, entry_a in enumerate(company_entries):
            if i in processed:
                continue
            cluster = [entry_a]
            processed.add(i)
            for j, entry_b in enumerate(company_entries):
                if j in processed:
                    continue
                # Match if exact same normalized role title or pointing to the same report
                same_role = normalize_role(entry_a.role) == normalize_role(entry_b.role)
                same_report = (
                    entry_a.report.strip() == entry_b.report.strip()
                    and entry_a.report.strip() not in ("", "❌", "none")
                )
                if same_role or same_report:
                    cluster.append(entry_b)
                    processed.add(j)

            if len(cluster) < 2:
                continue

            # Keep the one with the highest score
            cluster.sort(key=lambda e: parse_score(e.score), reverse=True)
            keeper = cluster[0]

            # Check if any removed entry has more advanced status
            best_rank = get_status_rank(keeper.status)
            best_status = keeper.status
            for dup in cluster[1:]:
                rank = get_status_rank(dup.status)
                if rank > best_rank:
                    best_rank = rank
                    best_status = dup.status

            # Promote keeper's status if needed
            if best_status != keeper.status:
                line_idx = entry_line_map.get(keeper.num)
                if line_idx is not None:
                    parts = lines[line_idx].split("|")
                    parts = [p.strip() for p in parts]
                    parts[5] = best_status  # Status is col 5 in real applications.md
                    lines[line_idx] = "| " + " | ".join(parts[1:-1]) + " |"
                    click.echo(
                        f'  📝 #{keeper.num}: status promoted to "{best_status}"'
                    )

            # Mark duplicates for removal
            for dup in cluster[1:]:
                line_idx = entry_line_map.get(dup.num)
                if line_idx is not None:
                    lines_to_remove.add(line_idx)
                    removed += 1
                    click.echo(
                        f"🗑️  Remove #{dup.num} ({dup.company} — {dup.role}, "
                        f"{dup.score}) → kept #{keeper.num} ({keeper.score})"
                    )

    # Remove duplicate lines (in reverse order to preserve indices)
    for idx in sorted(lines_to_remove, reverse=True):
        lines.pop(idx)

    click.echo(f"\n📊 {removed} duplicates removed")

    if not dry_run and removed > 0:
        shutil.copy2(apps_file, str(apps_file) + ".bak")
        apps_file.write_text("\n".join(lines), encoding="utf-8")
        click.echo("✅ Written to applications.md (backup: applications.md.bak)")
    elif dry_run:
        click.echo("(dry-run — no changes written)")
    else:
        click.echo("✅ No duplicates found")

    return removed


# ---------------------------------------------------------------------------
# Click command
# ---------------------------------------------------------------------------

@click.command()
@click.option("--dry-run", is_flag=True, help="Preview changes without writing.")
@pass_ctx
def dedup_cmd(ctx: CareerOpsContext, dry_run: bool) -> None:
    """Remove duplicate entries from applications.md."""
    run_dedup(ctx.root, dry_run=dry_run)
