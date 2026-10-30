"""
scan_csv.py — Sync workspace/job-tracker.csv for job pipeline management.

Flow:
  1. Read workspace/job-tracker.csv (semicolon-separated, UTF-8-BOM).
  2. Maintain 14-column Single Source of Truth schema:
     ID;URL;Company;Position;Job Description Path;Status;Score;Archetype;Added Date;Application Date;Status Date;Notes;Report Path;CV PDF Path
  3. Validate deduplication by URL or Company+Position.
  4. Provide helper functions to read pending jobs and update tracker rows.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

import click

from .config import get_job_tracker_file
from .context import CareerOpsContext, pass_ctx
from .utils import normalize_company, normalize_url

CODEPAGE = "utf-8-sig"       # UTF-8-BOM so Excel 365 PT-BR opens cleanly
SEPARATOR = ";"

FIELDNAMES = [
    "ID",
    "URL",
    "Company",
    "Position",
    "Job Description Path",
    "Status",
    "Score",
    "Archetype",
    "Added Date",
    "Application Date",
    "Status Date",
    "Notes",
    "Report Path",
    "CV PDF Path",
]


def _read_tracker(tracker_path: Path) -> tuple[list[str], list[dict]]:
    """Read job-tracker.csv. Returns (fieldnames, rows)."""
    if not tracker_path.exists():
        return FIELDNAMES, []
    content = tracker_path.read_text(encoding=CODEPAGE)
    reader = csv.DictReader(io.StringIO(content), delimiter=SEPARATOR)
    fieldnames = list(reader.fieldnames or FIELDNAMES)
    rows = []
    for row in reader:
        rows.append({k.strip(): (v or "").strip() for k, v in row.items() if k is not None})
    return fieldnames, rows


def _write_tracker(tracker_path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Write rows back to job-tracker.csv preserving format."""
    tracker_path.parent.mkdir(parents=True, exist_ok=True)
    # Ensure all required fieldnames exist
    out_fields = list(fieldnames)
    for fn in FIELDNAMES:
        if fn not in out_fields:
            out_fields.append(fn)

    with open(tracker_path, "w", encoding=CODEPAGE, newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=out_fields,
            delimiter=SEPARATOR,
            lineterminator="\r\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def get_pending_jobs(root: Path) -> list[dict]:
    """Get all rows with Status empty or 'Queued' from job-tracker.csv."""
    tracker_path = get_job_tracker_file(root)
    if not tracker_path.exists():
        return []

    _, rows = _read_tracker(tracker_path)
    pending = []

    for row in rows:
        status = row.get("Status", "").strip()
        url = row.get("URL", "").strip()

        if status not in ("", "Queued"):
            continue

        if not url:
            continue

        pending.append({
            "id": row.get("ID", "").strip(),
            "url": url,
            "company": row.get("Company", "").strip(),
            "position": row.get("Position", "").strip(),
            "jd_path": row.get("Job Description Path", "").strip(),
            "added_date": row.get("Added Date", "").strip(),
        })

    return pending


def update_tracker_row(
    root: Path,
    row_id: str,
    company: str | None = None,
    position: str | None = None,
    jd_path: str | None = None,
    status: str | None = None,
    score: str | None = None,
    archetype: str | None = None,
    app_date: str | None = None,
    status_date: str | None = None,
    notes: str | None = None,
    report_path: str | None = None,
    cv_pdf_path: str | None = None,
) -> bool:
    """Update a specific row in job-tracker.csv by ID or URL."""
    tracker_path = get_job_tracker_file(root)
    if not tracker_path.exists():
        return False

    fieldnames, rows = _read_tracker(tracker_path)
    updated = False
    today_iso = date.today().isoformat()
    norm_id = row_id.strip()

    for row in rows:
        if row.get("ID", "").strip() == norm_id or (row_id.startswith("http") and normalize_url(row.get("URL", "")) == normalize_url(row_id)):
            if company is not None:
                row["Company"] = company
            if position is not None:
                row["Position"] = position
            if jd_path is not None:
                row["Job Description Path"] = jd_path
            if status is not None:
                row["Status"] = status
            if score is not None:
                row["Score"] = score
            if archetype is not None:
                row["Archetype"] = archetype
            if app_date is not None:
                row["Application Date"] = app_date
            if status_date is not None:
                row["Status Date"] = status_date
            else:
                row["Status Date"] = today_iso
            if notes is not None:
                row["Notes"] = notes
            if report_path is not None:
                row["Report Path"] = report_path
            if cv_pdf_path is not None:
                row["CV PDF Path"] = cv_pdf_path
            updated = True
            break

    if updated:
        _write_tracker(tracker_path, fieldnames, rows)

    return updated


def add_job_row(
    root: Path,
    url: str,
    company: str = "",
    position: str = "",
    jd_path: str = "",
) -> tuple[bool, str, str]:
    """
    Add a new job to job-tracker.csv if it doesn't already exist.
    Returns (created, item_id, message).
    """
    tracker_path = get_job_tracker_file(root)
    fieldnames, rows = _read_tracker(tracker_path)
    norm_target_url = normalize_url(url)
    norm_target_company = normalize_company(company)
    norm_target_position = position.lower().strip()

    # Check for duplicates
    for row in rows:
        r_url = normalize_url(row.get("URL", ""))
        r_comp = normalize_company(row.get("Company", ""))
        r_pos = row.get("Position", "").lower().strip()

        if r_url and r_url == norm_target_url:
            return False, row.get("ID", ""), f"URL ja cadastrada no ID {row.get('ID')}"
        if norm_target_company and norm_target_position and r_comp == norm_target_company and r_pos == norm_target_position:
            return False, row.get("ID", ""), f"Vaga ({company} - {position}) ja cadastrada no ID {row.get('ID')}"

    # Generate next sequential 3-digit ID
    max_id = 0
    for r in rows:
        rid = r.get("ID", "").strip()
        if rid.isdigit():
            max_id = max(max_id, int(rid))

    next_id = f"{max_id + 1:03d}"
    today_iso = date.today().isoformat()

    new_row = {
        "ID": next_id,
        "URL": url,
        "Company": company,
        "Position": position,
        "Job Description Path": jd_path,
        "Status": "Queued",
        "Score": "",
        "Archetype": "",
        "Added Date": today_iso,
        "Application Date": "",
        "Status Date": today_iso,
        "Notes": "",
        "Report Path": "",
        "CV PDF Path": "",
    }

    rows.append(new_row)
    _write_tracker(tracker_path, fieldnames or FIELDNAMES, rows)
    return True, next_id, f"Vaga cadastrada com sucesso como ID #{next_id}"


@click.command()
@click.option("--init", is_flag=True, default=False, help="Initialize empty job-tracker.csv with 14 columns.")
@pass_ctx
def scan_csv_cmd(ctx: CareerOpsContext, init: bool) -> None:
    """Scan workspace/job-tracker.csv for pending job evaluations."""
    root = ctx.root
    tracker_path = get_job_tracker_file(root)

    if init:
        if tracker_path.exists():
            click.echo(f"[INFO] {tracker_path} ja existe.")
            return
        _write_tracker(tracker_path, FIELDNAMES, [])
        click.echo(f"[OK] Criado {tracker_path} com 14 colunas.")
        return

    pending = get_pending_jobs(root)
    click.echo(f"[OK] {len(pending)} vagas pendentes para triagem em job-tracker.csv")
    for p in pending[:10]:
        click.echo(f"  + ID #{p['id']}: {p['company']} - {p['position']} ({p['url']})")
    if len(pending) > 10:
        click.echo(f"  ... (+{len(pending) - 10} mais)")
