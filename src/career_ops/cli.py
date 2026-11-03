"""
cli.py — Click entry-point for career-ops-python.

All subcommands share the global --root option, which points to
the career-ops project directory (or CAREER_OPS_ROOT env var).
"""

from __future__ import annotations

import io
import json
import re
import shutil
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()

# Enable UTF-8 mode on Windows so emojis render correctly in terminal.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, io.UnsupportedOperation):
        pass

from .context import CareerOpsContext, pass_ctx  # noqa: F401 (re-exported)
from .cv import cv_cmd
from .dashboard import dashboard_cmd
from .db import init_db
from .eval.scoring import calculate_score
from .export import export_cmd
from .fetch_cmd import fetch_cmd
from .fetcher.connectors import fetch_single_url
from .models import VagaInput
from .repository import VALID_LIFECYCLE_STATUSES
from .schemas.eval import EvaluationPayload
from .stories.parser import filter_stories, load_story_bank
from .sync_check import sync_check_cmd
from .verify import verify_cmd

# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.option(
    "--root",
    envvar="CAREER_OPS_ROOT",
    default=None,
    metavar="PATH",
    help="Path to the career-ops project root. Defaults to CAREER_OPS_ROOT env var or cwd.",
)
@click.version_option(package_name="career-ops-python")
@click.pass_context
def cli(ctx: click.Context, root: str | None) -> None:
    """career-ops Python tools — SQLite relational pipeline, ingestion, and tracking."""
    ctx.obj = CareerOpsContext(root)


# ---------------------------------------------------------------------------
# Core SQLite Commands
# ---------------------------------------------------------------------------


@cli.command("init")
@pass_ctx
def init_cmd(ctx: CareerOpsContext) -> None:
    """Initialize the SQLite database at data/career_ops.db."""
    init_db(ctx.db_path)
    click.echo(f"[OK] Initialized SQLite database at {ctx.db_path}")


@cli.command("intake")
@click.argument("url")
@click.option("--company", default=None, help="Override or supply company name.")
@click.option("--role", default=None, help="Override or supply role title.")
@click.option("--source", default=None, help="Override source portal identifier.")
@click.option("--location", default=None, help="Optional job location.")
@click.option("--remote-type", default=None, help="Optional remote type (e.g. remote, hybrid).")
@click.option("--description", default=None, help="Override or supply raw job description.")
@pass_ctx
def intake_cmd(
    ctx: CareerOpsContext,
    url: str,
    company: str | None,
    role: str | None,
    source: str | None,
    location: str | None,
    remote_type: str | None,
    description: str | None,
) -> None:
    """Fetch and ingest a single job posting URL into SQLite deterministically."""
    posting = None
    detected_portal = "web"

    if company is None or role is None or description is None:
        posting, detected_portal = fetch_single_url(url)

    resolved_company = company or (posting.company if posting else "")
    resolved_role = role or (posting.role if posting else "")
    resolved_desc = (
        description
        if description is not None
        else (posting.description if posting else "")
    )
    resolved_source = source or detected_portal
    resolved_url = (posting.url if posting and posting.url else url)

    if not resolved_company or not resolved_role:
        click.secho(
            f"[ERROR] Could not deterministically extract company and role from {url}. "
            "Use 'career-ops intake-raw' or pass --company and --role.",
            fg="red",
        )
        sys.exit(1)

    vaga_input = VagaInput(
        original_url=resolved_url,
        company=resolved_company,
        role=resolved_role,
        source_portal=resolved_source,
        location=location,
        remote_type=remote_type,
    )
    vaga_id, is_new = ctx.repository.insert_vaga(vaga_input, descricao=resolved_desc)
    row = ctx.repository.get_vaga(vaga_id) or {}
    payload = {
        "id": vaga_id,
        "is_new": is_new,
        "company": resolved_company,
        "role": resolved_role,
        "canonical_url": row.get("canonical_url", resolved_url),
        "status": row.get("status", "queued"),
    }
    click.echo(json.dumps(payload, ensure_ascii=False))


@cli.command("intake-raw")
@click.option("--company", required=True, help="Company name.")
@click.option("--role", required=True, help="Role title.")
@click.option("--url", required=True, help="Job posting URL.")
@click.option(
    "--desc-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to file containing the raw job description.",
)
@click.option("--description", default="", help="Inline job description text.")
@click.option("--source", default="manual", show_default=True, help="Source portal identifier.")
@click.option("--location", default=None, help="Optional job location.")
@click.option("--remote-type", default=None, help="Optional remote type.")
@pass_ctx
def intake_raw_cmd(
    ctx: CareerOpsContext,
    company: str,
    role: str,
    url: str,
    desc_file: Path | None,
    description: str,
    source: str,
    location: str | None,
    remote_type: str | None,
) -> None:
    """Ingest pre-extracted job details directly into SQLite."""
    desc_text = desc_file.read_text(encoding="utf-8") if desc_file is not None else description
    vaga_input = VagaInput(
        original_url=url,
        company=company,
        role=role,
        source_portal=source,
        location=location,
        remote_type=remote_type,
    )
    vaga_id, is_new = ctx.repository.insert_vaga(vaga_input, descricao=desc_text)
    row = ctx.repository.get_vaga(vaga_id) or {}
    payload = {
        "id": vaga_id,
        "is_new": is_new,
        "company": company,
        "role": role,
        "canonical_url": row.get("canonical_url", url),
        "status": row.get("status", "queued"),
    }
    click.echo(json.dumps(payload, ensure_ascii=False))


@cli.command("list")
@click.option("--status", default=None, help="Filter by status (e.g. queued, evaluated, applied).")
@click.option("--limit", default=50, show_default=True, type=int, help="Max rows to return.")
@click.option("--offset", default=0, show_default=True, type=int, help="Pagination offset.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table"], case_sensitive=False),
    default=None,
    help="Output format (defaults to json for non-TTY, table for interactive terminal).",
)
@pass_ctx
def list_cmd(
    ctx: CareerOpsContext,
    status: str | None,
    limit: int,
    offset: int,
    fmt: str | None,
) -> None:
    """List job opportunities from SQLite without loading full-text descriptions."""
    effective_fmt = (fmt or ("table" if sys.stdout.isatty() else "json")).lower()
    rows = ctx.repository.list_vagas(status=status, limit=limit, offset=offset)

    compact_rows = [
        {
            "seq_num": r.get("seq_num"),
            "id": r["id"],
            "company": r["company"],
            "role": r["role"],
            "canonical_url": r["canonical_url"],
            "status": r["status"],
            "score": r.get("score"),
            "source_portal": r.get("source_portal"),
            "location": r.get("location"),
            "remote_type": r.get("remote_type"),
        }
        for r in rows
    ]

    if effective_fmt == "json":
        click.echo(json.dumps(compact_rows, ensure_ascii=False))
        return

    if not compact_rows:
        click.echo("No matching job records found.")
        return

    click.echo(f"{'SEQ':<5} {'ID':<28} {'STATUS':<12} {'SCORE':<7} {'COMPANY':<22} {'ROLE'}")
    click.echo("-" * 102)
    for item in compact_rows:
        score_str = f"{item['score']:.1f}" if item["score"] is not None else "-"
        seq_str = f"{item['seq_num']:03d}" if item.get("seq_num") is not None else "---"
        click.echo(
            f"{seq_str:<5} {item['id']:<28} {str(item['status']):<12} {score_str:<7} "
            f"{str(item['company'])[:20]:<22} {item['role']}"
        )


@cli.command("show")
@click.argument("vaga_id")
@click.option("--full", is_flag=True, default=False, help="Include full job description.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "text"], case_sensitive=False),
    default=None,
    help="Output format (defaults to json for non-TTY, text for interactive terminal).",
)
@pass_ctx
def show_cmd(
    ctx: CareerOpsContext,
    vaga_id: str,
    full: bool,
    fmt: str | None,
) -> None:
    """Display metadata and optionally the full job description for a single vaga."""
    vaga = ctx.repository.get_vaga(vaga_id)
    if vaga is None:
        click.secho(f"[ERROR] Vaga not found: {vaga_id}", fg="red")
        sys.exit(1)

    from .repository import get_canonical_report_path
    canonical_report = get_canonical_report_path(vaga)
    vaga["suggested_report_path"] = canonical_report

    if full:
        desc = ctx.repository.get_vaga_description(vaga["id"]) or ""
        vaga["description"] = desc
        vaga["description_raw"] = desc

    effective_fmt = (fmt or ("text" if sys.stdout.isatty() else "json")).lower()
    if effective_fmt == "json":
        click.echo(json.dumps(vaga, ensure_ascii=False))
        return

    seq_display = f"#{vaga['seq_num']:03d}" if vaga.get("seq_num") is not None else "---"
    click.echo(f"Seq:           {seq_display}")
    click.echo(f"ID:            {vaga['id']}")
    click.echo(f"Company:       {vaga['company']}")
    click.echo(f"Role:          {vaga['role']}")
    click.echo(f"Status:        {vaga['status']}")
    click.echo(f"Canonical URL: {vaga['canonical_url']}")
    if vaga.get("score") is not None:
        click.echo(f"Score:         {vaga['score']}")
    if vaga.get("report_path"):
        click.echo(f"Report:        {vaga['report_path']}")
    else:
        click.echo(f"Report:        (pending) -> {canonical_report}")
    if vaga.get("cv_pdf_path"):
        click.echo(f"CV PDF:        {vaga['cv_pdf_path']}")
    if full:
        click.echo("\n--- Job Description ---")
        click.echo(vaga.get("description", ""))


@cli.command("track")
@click.argument("vaga_id")
@click.option("--status", default=None, help="Lifecycle status (evaluated, applied, interview, offer, rejected, discarded, skip).")
@click.option("--score", default=None, type=float, help="Numeric fit score (0.0 - 5.0).")
@click.option("--archetype", default=None, help="Matched candidate archetype.")
@click.option("--application-date", default=None, help="Application date (YYYY-MM-DD).")
@click.option("--report", "report_path", default=None, help="Path to markdown evaluation report.")
@click.option("--pdf", "cv_pdf_path", default=None, help="Path to generated CV PDF.")
@click.option("--notes", default=None, help="Candidate or recruiter notes.")
@pass_ctx
def track_cmd(
    ctx: CareerOpsContext,
    vaga_id: str,
    status: str | None,
    score: float | None,
    archetype: str | None,
    application_date: str | None,
    report_path: str | None,
    cv_pdf_path: str | None,
    notes: str | None,
) -> None:
    """Update candidate application lifecycle state and artifact pointers."""
    effective_status = status
    canon_id = ctx.repository.resolve_vaga_id(vaga_id)
    if canon_id is None:
        click.secho(f"[ERROR] Vaga '{vaga_id}' does not exist.", fg="red")
        sys.exit(1)

    if effective_status is None:
        existing = ctx.repository.get_vaga(canon_id)
        curr = str(existing.get("status") or "").strip().lower() if existing else ""
        effective_status = curr if curr in VALID_LIFECYCLE_STATUSES else "evaluated"

    try:
        updated = ctx.repository.update_lifecycle(
            vaga_id=canon_id,
            status=effective_status,
            score=score,
            archetype=archetype,
            application_date=application_date,
            report_path=report_path,
            cv_pdf_path=cv_pdf_path,
            notes=notes,
        )
    except (KeyError, ValueError) as exc:
        click.secho(f"[ERROR] {exc}", fg="red")
        sys.exit(1)

    click.echo(json.dumps(updated, ensure_ascii=False))


@cli.command("evaluate")
@click.argument("vaga_id")
@click.option(
    "--file",
    "eval_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to structured EvaluationPayload JSON.",
)
@click.option(
    "--keep-staging",
    is_flag=True,
    default=False,
    help="Do not delete staging payload after processing.",
)
@pass_ctx
def evaluate_cmd(
    ctx: CareerOpsContext,
    vaga_id: str,
    eval_file: Path,
    keep_staging: bool,
) -> None:
    """Evaluate a candidate opportunity using structured categorical criteria."""
    try:
        content = eval_file.read_text(encoding="utf-8")
        payload = EvaluationPayload.model_validate_json(content)
    except Exception as exc:
        click.secho(f"[ERROR] Invalid evaluation payload: {exc}", fg="red", err=True)
        sys.exit(1)

    canon_arg = ctx.repository.resolve_vaga_id(vaga_id)
    if not canon_arg:
        click.secho(f"[ERROR] Vaga not found: '{vaga_id}'", fg="red", err=True)
        sys.exit(1)

    canon_payload = ctx.repository.resolve_vaga_id(payload.vaga_id)
    if not canon_payload or canon_arg != canon_payload:
        click.secho(
            f"[ERROR] Payload vaga_id '{payload.vaga_id}' does not match command argument '{vaga_id}'.",
            fg="red",
            err=True,
        )
        sys.exit(1)

    vaga_data = ctx.repository.get_vaga(canon_arg)
    assert vaga_data is not None

    from .repository import get_canonical_report_path

    canonical_report = get_canonical_report_path(vaga_data)
    effective_report_path = payload.report_path
    if not effective_report_path:
        effective_report_path = canonical_report
    elif effective_report_path.startswith("workspace/reports/"):
        target_path = ctx.root / canonical_report
        legacy_path = ctx.root / effective_report_path
        if target_path.exists() or not legacy_path.exists():
            effective_report_path = canonical_report

    final_score, effective_blockers = calculate_score(payload)

    # Atomic lifecycle update
    try:
        ctx.repository.update_lifecycle(
            vaga_id=canon_arg,
            status="evaluated",
            score=final_score,
            archetype=payload.archetype,
            report_path=effective_report_path,
            notes=payload.notes,
        )
    except (KeyError, ValueError) as exc:
        click.secho(f"[ERROR] {exc}", fg="red", err=True)
        sys.exit(1)

    if not keep_staging:
        try:
            eval_file.unlink()
        except OSError:
            pass

    result = {
        "id": canon_arg,
        "score": final_score,
        "status": "evaluated",
        "blockers": effective_blockers,
        "archetype": payload.archetype,
        "report_path": effective_report_path,
        "notes": payload.notes,
    }
    click.echo(json.dumps(result, ensure_ascii=False))


@cli.command("migrate-reports")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview migration plan without modifying filesystem or database.",
)
@pass_ctx
def migrate_reports_cmd(ctx: CareerOpsContext, dry_run: bool) -> None:
    """Migrate legacy workspace/reports/ to canonical output/reports/{seq:03d}-{role}-{company}.md."""
    import shutil
    from .repository import get_canonical_report_path
    from .db import get_db_connection

    with get_db_connection(ctx.db_path) as conn:
        rows = conn.execute(
            """
            SELECT v.id, v.seq_num, v.role, v.company, t.report_path
            FROM vagas v
            JOIN tracking_lifecycle t ON v.id = t.vaga_id
            WHERE t.report_path IS NOT NULL AND TRIM(t.report_path) != ''
            ORDER BY v.seq_num ASC
            """
        ).fetchall()

    plan = []
    migrated_count = 0
    repaired_count = 0

    target_dir = ctx.root / "output" / "reports"
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    for r in rows:
        v_dict = dict(r)
        v_id = v_dict["id"]
        canonical_rel = get_canonical_report_path(v_dict)
        current_ref = v_dict.get("report_path") or ""

        candidates = [
            ctx.root / current_ref,
            ctx.root / "workspace" / "reports" / f"report_{v_id}.md",
            ctx.root / "workspace" / current_ref,
        ]
        source_path = next((c for c in candidates if c.exists()), None)
        target_path = ctx.root / canonical_rel

        item_status = "unchanged"
        if source_path is not None and source_path.resolve() != target_path.resolve():
            item_status = "migrate_file_and_pointer"
            if not dry_run:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
                with get_db_connection(ctx.db_path) as conn:
                    conn.execute(
                        "UPDATE tracking_lifecycle SET report_path = ? WHERE vaga_id = ?",
                        (canonical_rel, v_id),
                    )
                try:
                    source_path.unlink()
                except OSError:
                    pass
            migrated_count += 1
        elif target_path.exists() and current_ref != canonical_rel:
            item_status = "repair_pointer_only"
            if not dry_run:
                with get_db_connection(ctx.db_path) as conn:
                    conn.execute(
                        "UPDATE tracking_lifecycle SET report_path = ? WHERE vaga_id = ?",
                        (canonical_rel, v_id),
                    )
            repaired_count += 1

        plan.append(
            {
                "vaga_id": v_id,
                "seq_num": v_dict["seq_num"],
                "company": v_dict["company"],
                "role": v_dict["role"],
                "current_report_path": current_ref,
                "target_report_path": canonical_rel,
                "action": item_status,
            }
        )

    # Check for unreferenced files in workspace/reports
    migrated_vaga_ids = {r["id"] for r in rows}
    workspace_reports_dir = ctx.root / "workspace" / "reports"
    orphans = []
    if workspace_reports_dir.exists():
        for orphan in workspace_reports_dir.glob("*.md"):
            m = re.search(r"(vaga_[0-9a-f]+_[0-9a-f]{6})", orphan.name)
            if m:
                matched_id = m.group(1)
                if matched_id in migrated_vaga_ids:
                    continue
                v = ctx.repository.get_vaga(matched_id)
                if v:
                    target_rel = get_canonical_report_path(v)
                    target_file = ctx.root / target_rel
                    orphans.append(
                        {
                            "orphan_file": str(orphan.relative_to(ctx.root)).replace("\\", "/"),
                            "matched_vaga": v["id"],
                            "target": target_rel,
                        }
                    )
                    if not dry_run:
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(orphan, target_file)
                        with get_db_connection(ctx.db_path) as conn:
                            conn.execute(
                                "UPDATE tracking_lifecycle SET report_path = ? WHERE vaga_id = ?",
                                (target_rel, v["id"]),
                            )
                        try:
                            orphan.unlink()
                        except OSError:
                            pass
                        migrated_count += 1

    result = {
        "status": "success",
        "dry_run": dry_run,
        "migrated": migrated_count,
        "repaired": repaired_count,
        "items": plan,
        "orphans_migrated": orphans,
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Stories Group
# ---------------------------------------------------------------------------


@click.group("stories")
def stories_group() -> None:
    """Query and manage behavioral STAR+R stories."""
    pass


@stories_group.command("list")
@click.option("--tag", default=None, help="Filter stories by competency tag.")
@click.option("--limit", default=None, type=int, help="Limit number of returned stories.")
@click.option(
    "--file",
    "story_file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Custom path to story-bank.md.",
)
@pass_ctx
def stories_list_subcmd(
    ctx: CareerOpsContext,
    tag: str | None,
    limit: int | None,
    story_file: Path | None,
) -> None:
    """List and query behavioral stories from the story bank."""
    resolved_path = story_file or (ctx.root / "content" / "story-bank.md")
    stories = load_story_bank(resolved_path)
    matched = filter_stories(stories, tag=tag, limit=limit)
    output = [s.to_dict() for s in matched]
    click.echo(json.dumps(output, ensure_ascii=False))


@cli.command("stats")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "table"], case_sensitive=False),
    default=None,
    help="Output format (defaults to json for non-TTY, table for interactive terminal).",
)
@pass_ctx
def stats_cmd(ctx: CareerOpsContext, fmt: str | None) -> None:
    """Output pipeline count summaries and average score."""
    stats = ctx.repository.get_pipeline_stats()
    effective_fmt = (fmt or ("table" if sys.stdout.isatty() else "json")).lower()

    if effective_fmt == "json":
        click.echo(json.dumps(stats, ensure_ascii=False))
        return

    click.echo("=== Career-Ops Pipeline Statistics ===")
    click.echo(f"Total opportunities: {stats['total']}")
    avg = f"{stats['avg_score']:.2f}" if stats["avg_score"] is not None else "N/A"
    click.echo(f"Average fit score:   {avg}")
    if stats["by_status"]:
        click.echo("\nBy Status:")
        for st, cnt in sorted(stats["by_status"].items()):
            click.echo(f"  {st:<15} {cnt}")


# ---------------------------------------------------------------------------
# Subcommand registrations
# ---------------------------------------------------------------------------

cli.add_command(fetch_cmd, name="scan")
cli.add_command(fetch_cmd, name="fetch")
cli.add_command(export_cmd, name="export")
cli.add_command(verify_cmd, name="verify")
cli.add_command(sync_check_cmd, name="sync-check")
cli.add_command(dashboard_cmd, name="dashboard")
cli.add_command(cv_cmd, name="cv")
cli.add_command(stories_group, name="stories")


if __name__ == "__main__":
    cli()
