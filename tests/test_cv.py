from __future__ import annotations

import json
from pathlib import Path
from click.testing import CliRunner
from career_ops.cli import cli

SAMPLE_PAYLOAD = {
    "format": "a4",
    "lang": "en",
    "name": "Jane Doe",
    "headline": "Lead Systems Architect",
    "contact": {
        "email": "jane@example.com",
        "location": "New York, NY",
        "linkedin_url": "https://linkedin.com/in/janedoe",
    },
    "summary": "Experienced architect specialized in resilient backends and distributed data pipelines.",
    "experience": [
        {
            "company": "Acme Corp",
            "role": "Principal Engineer",
            "location": "New York, NY",
            "start_date": "2021",
            "end_date": "Present",
            "bullets": [
                "Architected event-driven microservices serving 10M daily active users.",
                "Decreased API p99 latency by 35% through Redis caching.",
            ],
        }
    ],
    "skills": {
        "languages": ["Python", "Go"],
        "cloud": ["AWS", "Kubernetes"],
    },
    "education": [
        {
            "institution": "Columbia University",
            "degree": "M.S. in Computer Science",
            "year": "2018",
        }
    ],
    "projects": [],
}


def test_cv_render_cli_success(career_ops_root: Path):
    runner = CliRunner()
    payload_file = career_ops_root / "workspace" / "staging" / "cv_valid.json"
    payload_file.parent.mkdir(parents=True, exist_ok=True)
    payload_file.write_text(json.dumps(SAMPLE_PAYLOAD), encoding="utf-8")
    out_pdf = career_ops_root / "workspace" / "output" / "resume.pdf"

    result = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "cv",
            "render",
            "--payload",
            str(payload_file),
            "--out",
            str(out_pdf),
            "--format",
            "a4",
        ],
    )
    assert result.exit_code == 0, result.output
    res_data = json.loads(result.output)
    assert res_data["status"] == "success"
    assert out_pdf.exists()


def test_cv_render_cli_invalid_schema(career_ops_root: Path):
    runner = CliRunner()
    bad_payload_file = career_ops_root / "workspace" / "staging" / "cv_bad.json"
    bad_payload_file.parent.mkdir(parents=True, exist_ok=True)
    bad_payload_file.write_text('{"format": "invalid_format"}', encoding="utf-8")
    out_pdf = career_ops_root / "workspace" / "output" / "bad.pdf"

    result = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "cv",
            "render",
            "--payload",
            str(bad_payload_file),
            "--out",
            str(out_pdf),
        ],
    )
    assert result.exit_code == 1
    assert "Invalid CV payload schema" in result.output


def test_cv_render_cli_tracks_vaga_id(career_ops_root: Path):
    runner = CliRunner()
    # 1. Init and insert job
    runner.invoke(cli, ["--root", str(career_ops_root), "init"])
    intake_res = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "intake-raw",
            "--company",
            "Databricks",
            "--role",
            "Staff Engineer",
            "--url",
            "https://databricks.com/jobs/1",
        ],
    )
    vaga_id = json.loads(intake_res.output)["id"]

    # 2. Render with --vaga-id
    payload_file = career_ops_root / "workspace" / "staging" / f"cv_{vaga_id}.json"
    payload_file.parent.mkdir(parents=True, exist_ok=True)
    payload_file.write_text(json.dumps(SAMPLE_PAYLOAD), encoding="utf-8")
    out_pdf = career_ops_root / "workspace" / "output" / f"{vaga_id}_cv.pdf"

    res = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "cv",
            "render",
            "--payload",
            str(payload_file),
            "--out",
            str(out_pdf),
            "--vaga-id",
            vaga_id,
        ],
    )
    assert res.exit_code == 0, res.output

    # 3. Verify show command reflects PDF path
    show_res = runner.invoke(cli, ["--root", str(career_ops_root), "show", vaga_id])
    assert show_res.exit_code == 0
    show_data = json.loads(show_res.output)
    assert show_data["cv_pdf_path"] in (
        str(out_pdf),
        str(out_pdf.relative_to(career_ops_root)).replace("\\", "/"),
    )


def test_cv_render_cli_auto_derives_human_readable_name(career_ops_root: Path):
    runner = CliRunner()
    runner.invoke(cli, ["--root", str(career_ops_root), "init"])
    intake_res = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "intake-raw",
            "--company",
            "Nubank",
            "--role",
            "Senior Data / Analytics Engineer (C++)",
            "--url",
            "https://nubank.com/jobs/data-eng",
        ],
    )
    vaga_id = json.loads(intake_res.output)["id"]

    payload_file = career_ops_root / "workspace" / "staging" / f"cv_{vaga_id}.json"
    payload_file.parent.mkdir(parents=True, exist_ok=True)
    payload_file.write_text(json.dumps(SAMPLE_PAYLOAD), encoding="utf-8")

    # Render without --out
    res = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "cv",
            "render",
            "--payload",
            str(payload_file),
            "--vaga-id",
            vaga_id,
        ],
    )
    assert res.exit_code == 0, res.output
    res_json = json.loads(res.output)
    assert res_json["status"] == "success"

    # Expected slug: 001-rafael-senior-data-analytics-engineer-cpp-nubank.pdf
    expected_pdf = (
        career_ops_root
        / "output"
        / "cv"
        / "001-rafael-senior-data-analytics-engineer-cpp-nubank.pdf"
    )
    assert expected_pdf.exists()
    assert res_json["pdf_path"] == str(expected_pdf)

    # Database reflection
    show_res = runner.invoke(cli, ["--root", str(career_ops_root), "show", vaga_id])
    assert show_res.exit_code == 0
    show_data = json.loads(show_res.output)
    assert show_data["cv_pdf_path"] in (
        str(expected_pdf),
        "output/cv/001-rafael-senior-data-analytics-engineer-cpp-nubank.pdf",
    )


def test_cv_render_cli_missing_out_and_vaga_id(career_ops_root: Path):
    runner = CliRunner()
    payload_file = career_ops_root / "workspace" / "staging" / "cv_temp.json"
    payload_file.parent.mkdir(parents=True, exist_ok=True)
    payload_file.write_text(json.dumps(SAMPLE_PAYLOAD), encoding="utf-8")

    res = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "cv",
            "render",
            "--payload",
            str(payload_file),
        ],
    )
    assert res.exit_code == 1
    assert "Either --out or --vaga-id must be provided" in res.output


def test_cv_render_cli_title_mutation_cleans_up_old_pdf(career_ops_root: Path):
    runner = CliRunner()
    runner.invoke(cli, ["--root", str(career_ops_root), "init"])
    intake_res = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "intake-raw",
            "--company",
            "Stripe",
            "--role",
            "Data Engineer",
            "--url",
            "https://stripe.com/jobs/de-1",
        ],
    )
    vaga_id = json.loads(intake_res.output)["id"]

    payload_file = career_ops_root / "workspace" / "staging" / f"cv_{vaga_id}.json"
    payload_file.parent.mkdir(parents=True, exist_ok=True)
    payload_file.write_text(json.dumps(SAMPLE_PAYLOAD), encoding="utf-8")

    # 1. First render
    res1 = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "cv",
            "render",
            "--payload",
            str(payload_file),
            "--vaga-id",
            vaga_id,
        ],
    )
    assert res1.exit_code == 0
    old_pdf = career_ops_root / "output" / "cv" / "001-rafael-data-engineer-stripe.pdf"
    assert old_pdf.exists()

    # 2. Mutate role title in SQLite
    from career_ops.db import get_db_connection

    with get_db_connection(career_ops_root / "data" / "career_ops.db") as conn:
        conn.execute("UPDATE vagas SET role = 'Staff Data Architect' WHERE id = ?", (vaga_id,))

    # 3. Second render
    res2 = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "cv",
            "render",
            "--payload",
            str(payload_file),
            "--vaga-id",
            vaga_id,
        ],
    )
    assert res2.exit_code == 0
    new_pdf = (
        career_ops_root
        / "output"
        / "cv"
        / "001-rafael-staff-data-architect-stripe.pdf"
    )
    assert new_pdf.exists()
    # Old PDF should be unlinked
    assert not old_pdf.exists()


def test_cv_migrate_legacy_files(career_ops_root: Path):
    runner = CliRunner()
    runner.invoke(cli, ["--root", str(career_ops_root), "init"])
    intake_res = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "intake-raw",
            "--company",
            "Factored",
            "--role",
            "Senior AI Engineer",
            "--url",
            "https://factored.ai/jobs/senior-ai",
        ],
    )
    vaga_id = json.loads(intake_res.output)["id"]

    # Create dummy legacy PDF in workspace/output
    legacy_dir = career_ops_root / "workspace" / "output"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    legacy_pdf = legacy_dir / f"{vaga_id}_resume.pdf"
    legacy_pdf.write_bytes(b"%PDF-1.4 dummy content")

    # Seed in tracking_lifecycle
    from career_ops.db import get_db_connection
    with get_db_connection(career_ops_root / "data" / "career_ops.db") as conn:
        conn.execute(
            "UPDATE tracking_lifecycle SET cv_pdf_path = ? WHERE vaga_id = ?",
            (f"workspace/output/{vaga_id}_resume.pdf", vaga_id),
        )

    # Run cv migrate dry-run
    dry_res = runner.invoke(cli, ["--root", str(career_ops_root), "cv", "migrate", "--dry-run"])
    assert dry_res.exit_code == 0
    dry_json = json.loads(dry_res.output)
    assert dry_json["dry_run"] is True
    assert dry_json["migrated_count"] == 1
    assert legacy_pdf.exists()

    # Run cv migrate actual
    mig_res = runner.invoke(cli, ["--root", str(career_ops_root), "cv", "migrate"])
    assert mig_res.exit_code == 0
    mig_json = json.loads(mig_res.output)
    assert mig_json["status"] == "success"
    assert mig_json["migrated_count"] == 1

    expected_cv = career_ops_root / "output" / "cv" / "001-rafael-senior-ai-engineer-factored.pdf"
    assert expected_cv.exists()
    assert not legacy_pdf.exists()

    # Verify DB pointer
    show_res = runner.invoke(cli, ["--root", str(career_ops_root), "show", vaga_id])
    assert show_res.exit_code == 0
    show_data = json.loads(show_res.output)
    assert show_data["cv_pdf_path"] == "output/cv/001-rafael-senior-ai-engineer-factored.pdf"
