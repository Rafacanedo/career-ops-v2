"""
normalize.py — Normalize non-canonical statuses in applications.md.

Port of normalize-statuses.mjs.

Maps all non-canonical statuses to canonical ones per states.yml:
  Evaluated, Applied, Responded, Interview, Offer, Rejected, Discarded, SKIP

Also strips markdown bold (**) and dates from the status field,
moving DUPLICADO info to the notes column.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Optional

import click

from .config import get_apps_file
from .context import pass_ctx, CareerOpsContext


# ---------------------------------------------------------------------------
# Normalisation logic
# ---------------------------------------------------------------------------

def _normalize_status(raw: str) -> dict:
    """
    Map a raw status string to a canonical one.

    Returns a dict with keys:
      status       — canonical status string (or None if unknown)
      unknown      — True if we couldn't map it
      move_to_notes — original raw string to move to notes column (optional)
    """
    # Strip markdown bold
    s = re.sub(r"\*\*", "", raw).strip()
    lower = s.lower()

    # DUPLICADO variants → Discarded (move original to notes)
    if re.match(r"^(duplicado|dup\b)", s, re.IGNORECASE):
        return {"status": "Discarded", "move_to_notes": raw.strip()}

    # Repost → Discarded (move original to notes)
    if re.match(r"^repost", s, re.IGNORECASE):
        return {"status": "Discarded", "move_to_notes": raw.strip()}

    # CERRADA → Discarded
    if re.fullmatch(r"cerrada", lower):
        return {"status": "Discarded"}

    # Cancelada / Canceled → Discarded
    if re.match(r"^(cancelada|canceled)", lower):
        return {"status": "Discarded"}

    # Descartada / Discarded
    if re.fullmatch(r"(descartada|discarded)", lower):
        return {"status": "Discarded"}

    # Rechazada / Rejected
    if re.fullmatch(r"(rechazada|rejected)", lower):
        return {"status": "Rejected"}

    # Rechazado/Rejected with date → strip date
    if re.match(r"^(rechazado|rejected)\s+\d{4}", lower):
        return {"status": "Rejected"}

    # Aplicado/Applied with date → strip date
    if re.match(r"^(aplicado|applied)\s+\d{4}", lower):
        return {"status": "Applied"}

    # CONDICIONAL → Evaluated
    if re.fullmatch(r"condicional", lower):
        return {"status": "Evaluated"}

    # HOLD → Evaluated
    if re.fullmatch(r"hold", lower):
        return {"status": "Evaluated"}

    # MONITOR → Evaluated
    if re.fullmatch(r"monitor", lower):
        return {"status": "Evaluated"}

    # EVALUAR → Evaluated
    if re.fullmatch(r"evaluar", lower):
        return {"status": "Evaluated"}

    # Verificar → Evaluated
    if re.fullmatch(r"verificar", lower):
        return {"status": "Evaluated"}

    # GEO BLOCKER → SKIP
    if re.search(r"geo.?blocker", lower):
        return {"status": "SKIP"}

    # Em dash, dash, or empty → Discarded
    if s in ("—", "-", ""):
        return {"status": "Discarded"}

    # Already canonical (exact case-insensitive match)
    canonical = [
        "Evaluated", "Applied", "Interview",
        "Offer", "Rejected", "Discarded", "SKIP",
    ]
    for c in canonical:
        if lower == c.lower():
            return {"status": c}

    # Alias mapping
    aliases: dict[str, str] = {
        "evaluada": "Evaluated",
        "aplicado": "Applied", "enviada": "Applied",
        "aplicada": "Applied", "sent": "Applied",
        "entrevista": "Interview",
        "oferta": "Offer",
        "rechazado": "Rejected",
        "descartado": "Discarded", "cerrada": "Discarded",
        "no aplicar": "SKIP", "no_aplicar": "SKIP",
    }
    if lower in aliases:
        return {"status": aliases[lower]}

    # Unknown
    return {"status": None, "unknown": True}


def run_normalize(root: Path, dry_run: bool = False) -> int:
    """
    Run status normalisation against applications.md.

    Returns the number of changes made (0 if nothing to do).
    """
    apps_file = get_apps_file(root)

    if not apps_file.exists():
        click.echo("No applications.md found. Nothing to normalize.")
        return 0

    content = apps_file.read_text(encoding="utf-8")
    lines = content.split("\n")

    changes = 0
    unknowns = []

    for i, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        # | # | date | company | role | STATUS | score | pdf | report | notes |
        # idx: 0(empty) 1  2      3       4      5       6    7        8       9  10(empty)
        if len(parts) < 10:
            continue
        if parts[1] in ("#", "---", ""):
            continue

        try:
            num = int(parts[1])
        except ValueError:
            continue

        raw_status = parts[5]  # Status is col 5 in real applications.md
        result = _normalize_status(raw_status)

        if result.get("unknown"):
            unknowns.append({"num": num, "raw": raw_status, "line": i + 1})
            continue

        if result["status"] == raw_status:
            continue  # already canonical

        old_status = raw_status
        parts[5] = result["status"]  # Status is col 5

        # Move DUPLICADO/Repost info to notes column
        move_to = result.get("move_to_notes")
        if move_to and len(parts) > 9:
            existing = parts[9] or ""
            if move_to not in existing:
                parts[9] = move_to + (". " + existing if existing else "")
        elif move_to:
            parts[9] = move_to

        # Strip bold from score field too (score is col 6)
        if parts[6]:
            parts[6] = re.sub(r"\*\*", "", parts[6])

        # Reconstruct line (| col1 | col2 | ... |)
        lines[i] = "| " + " | ".join(parts[1:-1]) + " |"
        changes += 1
        click.echo(f'#{num}: "{old_status}" -> "{result["status"]}"')

    if unknowns:
        click.echo(f"\n⚠️  {len(unknowns)} unknown statuses:")
        for u in unknowns:
            click.echo(f'  #{u["num"]} (line {u["line"]}): "{u["raw"]}"')

    click.echo(f"\n📊 {changes} statuses normalized")

    if not dry_run and changes > 0:
        shutil.copy2(apps_file, str(apps_file) + ".bak")
        apps_file.write_text("\n".join(lines), encoding="utf-8")
        click.echo("✅ Written to applications.md (backup: applications.md.bak)")
    elif dry_run:
        click.echo("(dry-run — no changes written)")
    else:
        click.echo("✅ No changes needed")

    return changes


# ---------------------------------------------------------------------------
# Click command
# ---------------------------------------------------------------------------

@click.command()
@click.option("--dry-run", is_flag=True, help="Preview changes without writing.")
@pass_ctx
def normalize_cmd(ctx: CareerOpsContext, dry_run: bool) -> None:
    """Normalize non-canonical statuses in applications.md."""
    run_normalize(ctx.root, dry_run=dry_run)
