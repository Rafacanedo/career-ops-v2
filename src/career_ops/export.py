"""
export.py — Export SQLite tracker data to CSV, JSON, or HTML in workspace/output/.

CSV format:
  - Separator: semicolon (;)  — required for Excel 365 PT-BR auto-detection
  - Encoding:  UTF-8-BOM      — required for Excel to recognize accented chars
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import click

from .config import get_db_path, get_output_dir
from .context import CareerOpsContext, pass_ctx
from .dashboard import _build_dashboard_data, render_dashboard_html
from .repository import CareerOpsRepository

CODEPAGE = "utf-8-sig"  # UTF-8 with BOM — Excel 365 PT-BR auto-detects this
SEPARATOR = ";"

EXPORT_FIELDS = [
    "seq_num",
    "id",
    "canonical_url",
    "original_url",
    "company",
    "role",
    "source_portal",
    "location",
    "remote_type",
    "status_triagem",
    "status",
    "score",
    "archetype",
    "application_date",
    "report_path",
    "cv_pdf_path",
    "notes",
    "created_at",
    "updated_at",
]


def export_applications(root: Path, output_path: Path, fmt: str | None = None) -> int:
    """Export SQLite records to CSV, JSON, or HTML at output_path."""
    db_path = get_db_path(root)
    repo = CareerOpsRepository(db_path=db_path, auto_init=True)
    rows = repo.list_vagas(limit=100000)

    effective_fmt = (fmt or output_path.suffix.lstrip(".") or "csv").lower()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if effective_fmt == "json":
        output_path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return len(rows)

    if effective_fmt == "html":
        data = _build_dashboard_data(root, output_path)
        output_path.write_text(render_dashboard_html(data), encoding="utf-8")
        return len(rows)

    with open(output_path, mode="w", encoding=CODEPAGE, newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=EXPORT_FIELDS,
            delimiter=SEPARATOR,
            quoting=csv.QUOTE_ALL,
            lineterminator="\r\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for r in rows:
            serialized = {
                k: ("" if r.get(k) is None else str(r.get(k)))
                for k in EXPORT_FIELDS
            }
            writer.writerow(serialized)

    return len(rows)


@click.command()
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["csv", "json", "html"], case_sensitive=False),
    default="csv",
    show_default=True,
    help="Export format: csv, json, or html.",
)
@click.option(
    "--output-dir",
    default=None,
    metavar="DIR",
    help="Directory to write exported files. Defaults to workspace/output/.",
)
@pass_ctx
def export_cmd(ctx: CareerOpsContext, fmt: str, output_dir: str | None) -> None:
    """Export SQLite tracker data to CSV, JSON, or HTML in workspace/output/."""
    root = ctx.root
    out_dir = Path(output_dir) if output_dir else get_output_dir(root)
    fmt_lower = fmt.lower()

    filename_map = {
        "csv": "applications.csv",
        "json": "applications.json",
        "html": "dashboard.html",
    }
    target_path = out_dir / filename_map[fmt_lower]
    count = export_applications(root, target_path, fmt=fmt_lower)
    click.echo(f"[OK] {target_path.name}  ->  {count} rows  ->  {target_path}")
