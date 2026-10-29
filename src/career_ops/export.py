"""
export.py — Export workspace/job-tracker.csv data to CSV for Excel 365 (PT-BR).

Exports:
  - workspace/job-tracker.csv  →  workspace/output/applications.csv

CSV format:
  - Separator: semicolon (;)  — required for Excel 365 PT-BR auto-detection
  - Encoding:  UTF-8-BOM      — required for Excel to recognize accented chars
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import click

from .config import get_job_tracker_file, get_output_dir
from .context import CareerOpsContext, pass_ctx

CODEPAGE = "utf-8-sig"  # UTF-8 with BOM — Excel 365 PT-BR auto-detects this
SEPARATOR = ";"


def export_applications(root: Path, output_path: Path) -> int:
    """Export job-tracker.csv rows to workspace/output/applications.csv."""
    tracker_file = get_job_tracker_file(root)
    if not tracker_file.exists():
        raise FileNotFoundError(f"Not found: {tracker_file}")

    rows = []
    with open(tracker_file, "r", encoding=CODEPAGE) as f:
        reader = csv.DictReader(f, delimiter=SEPARATOR)
        for r in reader:
            rows.append(r)

    if not rows:
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with io.open(output_path, mode="w", encoding=CODEPAGE, newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
            delimiter=SEPARATOR,
            quoting=csv.QUOTE_ALL,
            lineterminator="\r\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


@click.command()
@click.option(
    "--output-dir",
    default=None,
    metavar="DIR",
    help="Directory to write CSV files. Defaults to workspace/output/.",
)
@pass_ctx
def export_cmd(ctx: CareerOpsContext, output_dir: str | None) -> None:
    """Export workspace tracker data to semicolon-separated CSV (Excel 365 PT-BR format)."""
    root = ctx.root
    out_dir = Path(output_dir) if output_dir else get_output_dir(root)

    apps_out = out_dir / "applications.csv"
    try:
        count = export_applications(root, apps_out)
        click.echo(f"[OK] applications.csv  ->  {count} linhas  ->  {apps_out}")
    except FileNotFoundError as e:
        click.secho(f"[ERRO] {e}", fg="red")
