"""
tracker.py — Display job application pipeline metrics directly from job-tracker.csv.
"""

from __future__ import annotations

import csv
from collections import Counter

import click

from .config import get_job_tracker_file
from .context import CareerOpsContext, pass_ctx
from .utils import parse_score


@click.command("tracker")
@pass_ctx
def tracker_cmd(ctx: CareerOpsContext) -> None:
    """Display application history and pipeline metrics directly from job-tracker.csv."""
    tracker_file = get_job_tracker_file(ctx.root)
    if not tracker_file.exists():
        click.echo("❌ workspace/job-tracker.csv nao encontrado.")
        return

    rows = []
    with open(tracker_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            rows.append(r)

    total_jobs = len(rows)
    status_counts = Counter()
    scores = []

    for r in rows:
        st = r.get("Status", "").strip() or "Queued"
        status_counts[st] += 1

        sc_val = parse_score(r.get("Score", ""))
        if sc_val > 0:
            scores.append(sc_val)

    avg_score = (sum(scores) / len(scores)) if scores else 0.0

    click.echo("==================================================")
    click.echo("📊 CAREER-OPS PIPELINE SUMMARY (job-tracker.csv)")
    click.echo("==================================================")
    click.echo(f"Total de Vagas Registradas: {total_jobs}")
    click.echo(f"Média de Score das Vagas Avaliadas: {avg_score:.2f} / 5.0")
    click.echo("--------------------------------------------------")
    click.echo("📌 Distribuição por Status:")
    for st, count in status_counts.most_common():
        pct = (count / total_jobs * 100) if total_jobs > 0 else 0
        click.echo(f"  • {st:20s}: {count:3d} ({pct:5.1f}%)")
    click.echo("==================================================")
