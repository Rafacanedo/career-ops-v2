"""
unapplied.py — List evaluated jobs from job-tracker.csv that meet application threshold and are not yet applied.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import click

from .config import get_job_tracker_file
from .context import CareerOpsContext, pass_ctx
from .utils import parse_score


def clean_url(url_str: str) -> str:
    """Clean markdown formatting and asterisks from extracted URL."""
    cleaned = re.sub(r"^\**|\**$", "", url_str.strip())
    m = re.search(r"https?://[^\s\)\>]+", cleaned)
    return m.group(0) if m else cleaned


def get_salary_expectation(report_path_str: str, root: Path) -> str:
    """Extract salary expectation/compensation range from a report markdown file if it exists."""
    if not report_path_str:
        return "N/A"

    report_path = root / report_path_str
    if not report_path.exists():
        return "N/A"

    content = report_path.read_text(encoding="utf-8", errors="ignore")
    m_sec = re.search(r"## D\)[^\n]*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    text = m_sec.group(1) if m_sec else content

    candidates = []
    for line in text.splitlines():
        line_s = line.strip("- *")
        if not line_s or line_s.startswith("|"):
            continue
        if re.search(r"(R\$|BRL|\$|\bUSD\b|\bEUR\b)", line_s, re.IGNORECASE) and re.search(r"\d", line_s):
            clean = re.sub(r"^\**[^*:]+:\**\s*", "", line_s)
            clean = re.sub(r"\*\*", "", clean).strip()
            if clean:
                candidates.append(clean)

    if candidates:
        first = candidates[0]
        if "+" in first:
            first = first.split("+")[0].strip()
        if "(" in first and ")" in first and len(first) > 60:
            first = re.sub(r"\([^)]*\)", "", first).strip()
        return first[:55]

    return "N/A"


@click.command("unapplied")
@click.option("--min-score", default=4.0, type=float, help="Minimum score threshold (default 4.0).")
@click.option("--format", "out_fmt", type=click.Choice(["markdown", "json", "csv"]), default="markdown", help="Output format.")
@pass_ctx
def unapplied_cmd(ctx: CareerOpsContext, min_score: float, out_fmt: str) -> None:
    """List unapplied high-fit job positions directly from job-tracker.csv."""
    tracker_file = get_job_tracker_file(ctx.root)
    if not tracker_file.exists():
        click.echo("❌ workspace/job-tracker.csv nao encontrado.")
        return

    unapplied_jobs = []
    with open(tracker_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            status = row.get("Status", "").strip()
            app_date = row.get("Application Date", "").strip()

            # Skip applied, interview, rejected, closed, or discarded jobs
            if app_date or status.lower() in ("applied", "interview", "rejected", "closed", "discarded", "descartada"):
                continue

            score_str = row.get("Score", "").strip()
            score_val = parse_score(score_str)

            if score_val >= min_score:
                item_id = row.get("ID", "").strip()
                company = row.get("Company", "").strip()
                position = row.get("Position", "").strip()
                url = clean_url(row.get("URL", "").strip())
                report_path = row.get("Report Path", "").strip()
                salary = get_salary_expectation(report_path, ctx.root)

                title = f"{position} - {company}" if company else position
                unapplied_jobs.append({
                    "id": item_id,
                    "title": title,
                    "score": score_str or f"{score_val:.1f}",
                    "salary": salary,
                    "url": url,
                })

    # Sort by score desc, then ID desc
    unapplied_jobs.sort(key=lambda x: (parse_score(x["score"]), x["id"]), reverse=True)

    if out_fmt == "markdown":
        click.echo("| ID da vaga | Titulo da vaga | Nota | Expectativa de Salário | URL |")
        click.echo("|------------|----------------|------|------------------------|-----|")
        for job in unapplied_jobs:
            click.echo(f"| {job['id']} | {job['title']} | {job['score']} | {job['salary']} | {job['url']} |")
    elif out_fmt == "json":
        click.echo(json.dumps(unapplied_jobs, indent=2, ensure_ascii=False))
    elif out_fmt == "csv":
        click.echo("ID da vaga;Titulo da vaga;Nota;Expectativa de Salário;URL")
        for job in unapplied_jobs:
            click.echo(f"{job['id']};{job['title']};{job['score']};{job['salary']};{job['url']}")
