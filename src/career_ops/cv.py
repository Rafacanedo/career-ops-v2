"""
cv.py — Click command group for CV rendering in Career-Ops v2.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from .context import CareerOpsContext, pass_ctx
from .render.compiler import CVOverflowError, compile_cv
from .schemas.cv import CVPayload


@click.group("cv", invoke_without_command=True)
@click.pass_context
def cv_cmd(ctx: click.Context) -> None:
    """Generate clean, ATS-parseable single-page PDF resumes from JSON payloads."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cv_cmd.command("render")
@click.option(
    "--payload",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to structured CVPayload JSON.",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output PDF destination path. Auto-derived if omitted when --vaga-id is provided.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["a4", "letter"], case_sensitive=False),
    default="a4",
    show_default=True,
    help="PDF page size format.",
)
@click.option(
    "--vaga-id",
    default=None,
    help="Optional vaga_id to automatically track generated PDF in SQLite.",
)
@pass_ctx
def render_subcmd(
    ctx: CareerOpsContext,
    payload: Path,
    out_path: Path | None,
    fmt: str,
    vaga_id: str | None,
) -> None:
    """Render a structured JSON resume payload to a verified single-page ATS PDF."""
    if out_path is None:
        if not vaga_id:
            click.secho(
                "[ERROR] Either --out or --vaga-id must be provided to determine the output path.",
                fg="red",
                err=True,
            )
            sys.exit(1)
        vaga = ctx.repository.get_vaga(vaga_id)
        if vaga is None:
            click.secho(f"[ERROR] vaga_id '{vaga_id}' not found in database.", fg="red", err=True)
            sys.exit(1)
        seq = vaga.get("seq_num") or 1
        from .utils import build_cv_filename, slugify_token

        candidate_slug = "rafael"
        profile_path = ctx.root / "config" / "profile.yml"
        if profile_path.exists():
            try:
                import yaml

                p_data = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
                full_name = p_data.get("candidate", {}).get("full_name", "")
                if full_name:
                    first = full_name.strip().split()[0]
                    candidate_slug = slugify_token(first) or "rafael"
            except Exception:
                pass

        filename = build_cv_filename(seq, candidate_slug, vaga.get("role"), vaga.get("company"))
        from .config import get_cv_output_dir

        out_dir = get_cv_output_dir(ctx.root)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename
    else:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        content = payload.read_text(encoding="utf-8")
        cv_data = CVPayload.model_validate_json(content)
    except Exception as exc:
        click.secho(f"[ERROR] Invalid CV payload schema: {exc}", fg="red", err=True)
        sys.exit(1)

    try:
        result = compile_cv(cv_data, out_path, format=fmt)
    except CVOverflowError as exc:
        click.echo(json.dumps(exc.telemetry, ensure_ascii=False), err=True)
        sys.exit(2)
    except Exception as exc:
        click.secho(f"[ERROR] Rendering failed: {exc}", fg="red", err=True)
        sys.exit(1)

    if vaga_id:
        existing = ctx.repository.get_vaga(vaga_id)
        if existing is not None:
            canonical_id = existing["id"]
            curr = str(existing.get("status") or "").strip().lower()
            from .repository import VALID_LIFECYCLE_STATUSES

            effective_status = curr if curr in VALID_LIFECYCLE_STATUSES else "evaluated"

            # Remove previously recorded PDF if its path differs from new out_path
            old_pdf_path = existing.get("cv_pdf_path")
            if old_pdf_path:
                old_p = Path(old_pdf_path)
                if not old_p.is_absolute():
                    old_p = ctx.root / old_p
                try:
                    if old_p.resolve() != out_path.resolve() and old_p.exists():
                        old_p.unlink()
                except OSError:
                    pass

            try:
                rel_path = out_path.relative_to(ctx.root).as_posix()
            except ValueError:
                rel_path = str(out_path).replace("\\", "/")

            ctx.repository.update_lifecycle(
                vaga_id=canonical_id,
                status=effective_status,
                cv_pdf_path=rel_path,
            )

    click.echo(
        json.dumps(
            {
                "status": "success",
                "pdf_path": str(result.pdf_path),
                "format": result.format,
                "page_count": result.page_count,
            },
            ensure_ascii=False,
        )
    )


@cv_cmd.command("migrate")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Inspect planned migrations without mutating disk or database.",
)
@pass_ctx
def migrate_subcmd(ctx: CareerOpsContext, dry_run: bool) -> None:
    """Migrate legacy CV PDFs from workspace/output/ to output/cv/ and normalize database paths."""
    import shutil
    from .config import get_cv_output_dir
    from .utils import slugify_token

    cv_dir = get_cv_output_dir(ctx.root)
    if not dry_run:
        cv_dir.mkdir(parents=True, exist_ok=True)

    candidate_slug = "rafael"
    profile_path = ctx.root / "config" / "profile.yml"
    if profile_path.exists():
        try:
            import yaml

            p_data = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
            full_name = p_data.get("candidate", {}).get("full_name", "")
            if full_name:
                first = full_name.strip().split()[0]
                candidate_slug = slugify_token(first) or "rafael"
        except Exception:
            pass

    vagas = ctx.repository.list_vagas(limit=100000)
    migrated = []
    skipped = []
    errors = []
    processed_sources: set[Path] = set()

    from .repository import VALID_LIFECYCLE_STATUSES

    for v in vagas:
        vid = v.get("id")
        cv_path_raw = v.get("cv_pdf_path")
        if not cv_path_raw:
            continue

        seq = v.get("seq_num") or 1
        role_slug = slugify_token(v.get("role") or "role", max_len=40)
        company_slug = slugify_token(v.get("company") or "company", max_len=30)
        canonical_name = f"{seq:03d}-{candidate_slug}-{role_slug}-{company_slug}.pdf"
        canonical_dest = cv_dir / canonical_name
        canonical_rel = f"output/cv/{canonical_name}"

        # Resolve current physical path
        curr_p = Path(cv_path_raw)
        if not curr_p.is_absolute():
            curr_p = ctx.root / curr_p

        # Check if already canonical on disk and in database
        if curr_p.resolve() == canonical_dest.resolve() and cv_path_raw == canonical_rel:
            skipped.append({"vaga_id": vid, "reason": "already_canonical"})
            processed_sources.add(curr_p.resolve())
            continue

        curr = str(v.get("status") or "").strip().lower()
        curr_status = curr if curr in VALID_LIFECYCLE_STATUSES else "evaluated"
        if not curr_p.exists():
            # Check fallbacks: in workspace/output or already placed at canonical_dest
            fallback_legacy = ctx.root / "workspace" / "output" / Path(cv_path_raw).name
            if fallback_legacy.exists():
                curr_p = fallback_legacy
            elif canonical_dest.exists():
                if not dry_run:
                    ctx.repository.update_lifecycle(vaga_id=vid, status=curr_status, cv_pdf_path=canonical_rel)
                migrated.append(
                    {
                        "vaga_id": vid,
                        "from": str(cv_path_raw),
                        "to": canonical_rel,
                        "action": "db_pointer_repaired",
                    }
                )
                continue
            else:
                errors.append({"vaga_id": vid, "path": cv_path_raw, "error": "file_not_found"})
                continue

        processed_sources.add(curr_p.resolve())
        try:
            if not dry_run:
                shutil.copy2(curr_p, canonical_dest)
                ctx.repository.update_lifecycle(vaga_id=vid, status=curr_status, cv_pdf_path=canonical_rel)
                try:
                    if curr_p.resolve() != canonical_dest.resolve():
                        curr_p.unlink()
                except OSError:
                    pass

            migrated.append(
                {
                    "vaga_id": vid,
                    "from": str(
                        curr_p.relative_to(ctx.root)
                        if curr_p.is_relative_to(ctx.root)
                        else curr_p
                    ),
                    "to": canonical_rel,
                    "action": "migrated" if not dry_run else "planned",
                }
            )
        except Exception as exc:
            errors.append({"vaga_id": vid, "error": str(exc)})

    # Also scan workspace/output for unreferenced legacy PDFs matching vaga_<id>
    legacy_dir = ctx.root / "workspace" / "output"
    if legacy_dir.exists():
        for p in legacy_dir.glob("*.pdf"):
            if p.resolve() in processed_sources:
                continue
            name = p.stem
            matched_vaga = None
            for v in vagas:
                vid = v.get("id")
                if vid and vid in name:
                    matched_vaga = v
                    break
            if matched_vaga:
                vid = matched_vaga.get("id")
                curr_v = str(matched_vaga.get("status") or "").strip().lower()
                v_status = curr_v if curr_v in VALID_LIFECYCLE_STATUSES else "evaluated"
                seq = matched_vaga.get("seq_num") or 1
                role_slug = slugify_token(matched_vaga.get("role") or "role", max_len=40)
                company_slug = slugify_token(matched_vaga.get("company") or "company", max_len=30)
                canonical_name = f"{seq:03d}-{candidate_slug}-{role_slug}-{company_slug}.pdf"
                canonical_dest = cv_dir / canonical_name
                canonical_rel = f"output/cv/{canonical_name}"
                try:
                    if not dry_run:
                        shutil.copy2(p, canonical_dest)
                        ctx.repository.update_lifecycle(vaga_id=vid, status=v_status, cv_pdf_path=canonical_rel)
                        try:
                            p.unlink()
                        except OSError:
                            pass
                        migrated.append(
                            {
                                "vaga_id": vid,
                                "from": str(p.relative_to(ctx.root)),
                                "to": canonical_rel,
                                "action": "orphan_recovered",
                            }
                        )
                    else:
                        migrated.append(
                            {
                                "vaga_id": vid,
                                "from": str(p.relative_to(ctx.root)),
                                "to": canonical_rel,
                                "action": "orphan_planned",
                            }
                        )
                except Exception as exc:
                    errors.append({"vaga_id": vid, "error": str(exc)})

    click.echo(
        json.dumps(
            {
                "status": "success",
                "dry_run": dry_run,
                "migrated_count": len(migrated),
                "migrated": migrated,
                "skipped_count": len(skipped),
                "errors_count": len(errors),
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
