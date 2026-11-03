"""
test_cli.py — Click CLI runner tests for career-ops database-backed commands.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner

from career_ops.cli import cli
from career_ops.config import get_db_path
from career_ops.repository import CareerOpsRepository


def test_cli_init_creates_sqlite_db(career_ops_root: Path):
    runner = CliRunner()
    db_path = get_db_path(career_ops_root)
    assert not db_path.exists()

    result = runner.invoke(cli, ["--root", str(career_ops_root), "init"])
    assert result.exit_code == 0, result.output
    assert db_path.exists()

    repo = CareerOpsRepository(db_path=db_path, auto_init=False)
    stats = repo.get_pipeline_stats()
    assert stats["total"] == 0


def test_cli_intake_with_mock_ats_response(career_ops_root: Path, monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "title": "Staff Data Engineer",
        "company_name": "Stripe",
        "absolute_url": "https://boards.greenhouse.io/stripe/jobs/998877?utm_source=linkedin",
        "content": "Build scalable distributed payment data pipelines using Spark and Python.",
    }
    mock_resp.raise_for_status.return_value = None
    monkeypatch.setattr("requests.get", lambda *a, **kw: mock_resp)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "intake",
            "https://boards.greenhouse.io/stripe/jobs/998877",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["is_new"] is True
    assert payload["company"] == "Stripe"
    assert payload["role"] == "Staff Data Engineer"
    assert payload["status"] == "queued"
    vaga_id = payload["id"]

    repo = CareerOpsRepository(db_path=get_db_path(career_ops_root), auto_init=False)
    desc = repo.get_vaga_description(vaga_id)
    assert desc == "Build scalable distributed payment data pipelines using Spark and Python."

    # Duplicate intake preserves oldest ID and returns is_new=False
    dup_result = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "intake",
            "https://boards.greenhouse.io/stripe/jobs/998877",
        ],
    )
    assert dup_result.exit_code == 0, dup_result.output
    dup_payload = json.loads(dup_result.output)
    assert dup_payload["is_new"] is False
    assert dup_payload["id"] == vaga_id


def test_cli_intake_html_json_ld_fallback(career_ops_root: Path, monkeypatch):
    html_doc = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "JobPosting",
          "title": "Analytics Engineer",
          "hiringOrganization": {"@type": "Organization", "name": "Nubank"},
          "description": "Design dbt models and analytical warehouses."
        }
        </script>
      </head>
      <body>Job Page</body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("not json")
    mock_resp.text = html_doc
    mock_resp.raise_for_status.return_value = None
    monkeypatch.setattr("requests.get", lambda *a, **kw: mock_resp)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--root", str(career_ops_root), "intake", "https://example.com/careers/analytics-eng"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["company"] == "Nubank"
    assert payload["role"] == "Analytics Engineer"


def test_cli_intake_raw_from_desc_file(career_ops_root: Path):
    desc_file = career_ops_root / "workspace" / "jds" / "sample_jd.txt"
    desc_file.write_text("Full JD text from file for Senior ML Engineer.", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "intake-raw",
            "--company",
            "Databricks",
            "--role",
            "Senior ML Engineer",
            "--url",
            "https://databricks.com/careers/123",
            "--desc-file",
            str(desc_file),
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["is_new"] is True
    assert data["company"] == "Databricks"

    # Verify list --status queued emits valid JSON with required keys
    list_res = runner.invoke(
        cli,
        ["--root", str(career_ops_root), "list", "--status", "queued"],
    )
    assert list_res.exit_code == 0, list_res.output
    items = json.loads(list_res.output)
    assert len(items) == 1
    item = items[0]
    for required_key in ("id", "company", "role", "canonical_url", "status"):
        assert required_key in item
    assert item["id"] == data["id"]
    assert item["status"] == "queued"

    # Verify show <id> --full returns complete job description
    show_res = runner.invoke(
        cli,
        ["--root", str(career_ops_root), "show", data["id"], "--full"],
    )
    assert show_res.exit_code == 0, show_res.output
    shown = json.loads(show_res.output)
    assert shown["id"] == data["id"]
    assert shown["description"] == "Full JD text from file for Senior ML Engineer."

    # Verify track <id> --score 4.5 --status evaluated updates status and score
    track_res = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "track",
            data["id"],
            "--score",
            "4.5",
            "--status",
            "evaluated",
            "--report",
            "workspace/reports/report_databricks.md",
        ],
    )
    assert track_res.exit_code == 0, track_res.output
    tracked = json.loads(track_res.output)
    assert tracked["status"] == "evaluated"
    assert tracked["status_triagem"] == "triaged"
    assert tracked["score"] == 4.5
    assert tracked["report_path"] == "workspace/reports/report_databricks.md"

    # Verify track <id> --pdf updates artifact without requiring --status again
    track_pdf_res = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "track",
            data["id"],
            "--pdf",
            "workspace/output/databricks_cv.pdf",
        ],
    )
    assert track_pdf_res.exit_code == 0, track_pdf_res.output
    tracked_pdf = json.loads(track_pdf_res.output)
    assert tracked_pdf["status"] == "evaluated"
    assert tracked_pdf["cv_pdf_path"] == "workspace/output/databricks_cv.pdf"

    # Verify stats reflects updated status and score
    stats_res = runner.invoke(
        cli,
        ["--root", str(career_ops_root), "stats"],
    )
    assert stats_res.exit_code == 0, stats_res.output
    stats = json.loads(stats_res.output)
    assert stats["total"] == 1
    assert stats["by_status"]["evaluated"] == 1
    assert stats["avg_score"] == 4.5


def test_cli_scan_ingests_configured_portals(career_ops_root: Path, monkeypatch):
    portals_yml = career_ops_root / "config" / "portals.yml"
    portals_yml.write_text(
        """
tracked_companies:
  - name: Brex
    ats: greenhouse
    token: brex
title_filter:
  positive: [data]
  negative: [intern]
""",
        encoding="utf-8",
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "jobs": [
            {
                "title": "Senior Data Scientist",
                "absolute_url": "https://boards.greenhouse.io/brex/jobs/101",
                "content": "Data science role at Brex.",
            }
        ]
    }
    mock_resp.raise_for_status.return_value = None
    monkeypatch.setattr("requests.get", lambda *a, **kw: mock_resp)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--root", str(career_ops_root), "scan", "--source", "ats"],
    )
    assert result.exit_code == 0, result.output

    list_res = runner.invoke(
        cli,
        ["--root", str(career_ops_root), "list", "--status", "queued"],
    )
    items = json.loads(list_res.output)
    assert len(items) == 1
    assert items[0]["company"] == "Brex"
    assert items[0]["role"] == "Senior Data Scientist"


def test_cli_show_and_track_nonexistent_id_returns_error(career_ops_root: Path):
    runner = CliRunner()
    show_res = runner.invoke(
        cli,
        ["--root", str(career_ops_root), "show", "vaga_missing"],
    )
    assert show_res.exit_code == 1

    track_res = runner.invoke(
        cli,
        ["--root", str(career_ops_root), "track", "vaga_missing", "--status", "evaluated"],
    )
    assert track_res.exit_code == 1


def test_cli_evaluate_command(career_ops_root: Path):
    runner = CliRunner()
    # 1. Init DB and insert a job
    runner.invoke(cli, ["--root", str(career_ops_root), "init"])
    intake_res = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "intake-raw",
            "--company",
            "Apple",
            "--role",
            "Staff AI Engineer",
            "--url",
            "https://jobs.apple.com/en-us/details/123",
            "--description",
            "Work on CoreML pipelines and LLM inference.",
        ],
    )
    assert intake_res.exit_code == 0
    vaga_id = json.loads(intake_res.output)["id"]

    # 2. Write staging evaluation file
    eval_payload = {
        "vaga_id": vaga_id,
        "cv_match": "high",
        "level_alignment": "target",
        "comp_alignment": "in_range",
        "cultural_signals": "positive",
        "strategic_alignment": "north_star",
        "blockers": [],
        "archetype": "Staff AI Engineer",
        "report_path": "workspace/reports/report_apple.md",
        "notes": "Excellent match.",
    }
    staging_file = career_ops_root / "workspace" / "staging" / f"eval_{vaga_id}.json"
    staging_file.parent.mkdir(parents=True, exist_ok=True)
    staging_file.write_text(json.dumps(eval_payload), encoding="utf-8")

    # 3. Run career-ops evaluate
    eval_res = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "evaluate",
            vaga_id,
            "--file",
            str(staging_file),
        ],
    )
    assert eval_res.exit_code == 0, eval_res.output
    eval_data = json.loads(eval_res.output)
    assert eval_data["id"] == vaga_id
    assert eval_data["score"] == 4.72
    assert eval_data["status"] == "evaluated"
    assert eval_data["archetype"] == "Staff AI Engineer"
    assert not staging_file.exists()  # Cleaned up by default


def test_cli_stories_list(career_ops_root: Path):
    runner = CliRunner()
    story_bank_file = career_ops_root / "content" / "story-bank.md"
    story_bank_file.parent.mkdir(parents=True, exist_ok=True)
    story_bank_file.write_text(
        """# Stories
## Story: Distributed Consensus Optimization
**Tags:** raft, distributed-systems, storage

### Situation
Raft leader election timeouts caused cluster instability under packet drop.

### Task
Tune heartbeat intervals and prevent split-brain states.

### Action
Implemented pre-vote protocol and randomized election intervals.

### Result
Zero split-brain occurrences across 10,000 synthetic network partition tests.
""",
        encoding="utf-8",
    )

    result = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "stories",
            "list",
            "--tag",
            "raft",
        ],
    )
    assert result.exit_code == 0, result.output
    stories = json.loads(result.output)
    assert len(stories) == 1
    assert stories[0]["title"] == "Distributed Consensus Optimization"
    assert "raft" in stories[0]["tags"]


def test_cli_show_and_list_by_seq_num(career_ops_root: Path):
    runner = CliRunner()
    # Ingest a vacancy
    runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "intake-raw",
            "--company",
            "Anthropic",
            "--role",
            "Research Engineer",
            "--url",
            "https://jobs.anthropic.com/1",
            "--description",
            "LLM safety and alignment research in Python.",
        ],
    )

    # Show via sequence number 1
    res_num = runner.invoke(cli, ["--root", str(career_ops_root), "show", "1"])
    assert res_num.exit_code == 0, res_num.output
    data = json.loads(res_num.output)
    assert data["company"] == "Anthropic"
    assert data["seq_num"] == 1
    assert data["suggested_report_path"] == "output/reports/001-research-engineer-anthropic.md"

    # Show via zero-padded #001 text format
    res_text = runner.invoke(cli, ["--root", str(career_ops_root), "show", "#001", "--format", "text"])
    assert res_text.exit_code == 0, res_text.output
    assert "Seq:           #001" in res_text.output
    assert "Company:       Anthropic" in res_text.output

    # List shows SEQ column
    res_list = runner.invoke(cli, ["--root", str(career_ops_root), "list", "--format", "table"])
    assert res_list.exit_code == 0, res_list.output
    assert "SEQ" in res_list.output
    assert "001" in res_list.output


def test_cli_evaluate_polymorphic_id_resolution(career_ops_root: Path):
    runner = CliRunner()
    res = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "intake-raw",
            "--company",
            "DeepMind",
            "--role",
            "AI Scientist",
            "--url",
            "https://deepmind.google/jobs/1",
            "--description",
            "Reinforcement learning and frontier models.",
        ],
    )
    vaga_id = json.loads(res.output)["id"]

    eval_payload = {
        "vaga_id": vaga_id,  # canonical hash in payload
        "cv_match": "high",
        "level_alignment": "target",
        "comp_alignment": "in_range",
        "cultural_signals": "positive",
        "strategic_alignment": "north_star",
        "blockers": [],
        "archetype": "AI Scientist",
        "notes": "Excellent alignment.",
    }
    staging_file = career_ops_root / "workspace" / "staging" / f"eval_1.json"
    staging_file.parent.mkdir(parents=True, exist_ok=True)
    staging_file.write_text(json.dumps(eval_payload), encoding="utf-8")

    # Call evaluate with integer 1 as command argument
    eval_res = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "evaluate",
            "1",
            "--file",
            str(staging_file),
        ],
    )
    assert eval_res.exit_code == 0, eval_res.output
    eval_data = json.loads(eval_res.output)
    assert eval_data["id"] == vaga_id
    assert eval_data["report_path"] == "output/reports/001-ai-scientist-deepmind.md"


def test_cli_migrate_reports_command(career_ops_root: Path):
    runner = CliRunner()
    # 1. Ingest
    res = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "intake-raw",
            "--company",
            "OpenAI",
            "--role",
            "Systems Engineer",
            "--url",
            "https://openai.com/careers/sys1",
            "--description",
            "High performance GPU clustering.",
        ],
    )
    vaga_id = json.loads(res.output)["id"]

    # 2. Create legacy report in workspace/reports
    legacy_dir = career_ops_root / "workspace" / "reports"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    legacy_file = legacy_dir / f"report_{vaga_id}.md"
    legacy_file.write_text("# Legacy Report Content", encoding="utf-8")

    # Track with legacy path
    runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "track",
            vaga_id,
            "--report",
            f"workspace/reports/report_{vaga_id}.md",
        ],
    )

    # 3. Dry-run migrate-reports
    res_dry = runner.invoke(cli, ["--root", str(career_ops_root), "migrate-reports", "--dry-run"])
    assert res_dry.exit_code == 0, res_dry.output
    dry_data = json.loads(res_dry.output)
    assert dry_data["dry_run"] is True
    assert dry_data["migrated"] == 1
    assert legacy_file.exists()  # Not deleted in dry run

    # 4. Live migrate-reports
    res_live = runner.invoke(cli, ["--root", str(career_ops_root), "migrate-reports"])
    assert res_live.exit_code == 0, res_live.output
    live_data = json.loads(res_live.output)
    assert live_data["dry_run"] is False
    assert live_data["migrated"] == 1

    target_file = career_ops_root / "output" / "reports" / "001-systems-engineer-openai.md"
    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == "# Legacy Report Content"
    assert not legacy_file.exists()

