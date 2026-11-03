from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from career_ops.cli import cli
from career_ops.dashboard import _build_dashboard_data, render_dashboard_html


def test_build_dashboard_data_uses_sqlite_repository(root_with_tracker: Path):
    output_path = root_with_tracker / "workspace" / "output" / "dashboard.html"
    data = _build_dashboard_data(root_with_tracker, output_path)

    assert data["source_file"].replace("\\", "/").endswith("data/career_ops.db")
    assert data["summary"]["total_applications"] == 4
    assert data["summary"]["counts_by_status"]["Applied"] == 1
    assert data["summary"]["counts_by_group"]["interview"] == 1

    acme = next(item for item in data["applications"] if item["company"] == "Acme Corp")
    assert acme["status"] == "Evaluated"
    assert acme["score_value"] == 4.2
    assert acme["pdf_ready"] is True
    assert acme["report_available"] is True
    assert acme["report_path"] == "../reports/001-acme-2026-01-15.md"


def test_render_dashboard_html_contains_filters_and_report_link(root_with_tracker: Path):
    output_path = root_with_tracker / "workspace" / "output" / "dashboard.html"
    html = render_dashboard_html(_build_dashboard_data(root_with_tracker, output_path))

    assert "Applications Dashboard" in html
    assert "Status Group" in html
    assert "Min Score" in html
    assert "../reports/001-acme-2026-01-15.md" in html


def test_dashboard_build_command_writes_html(root_with_tracker: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["--root", str(root_with_tracker), "dashboard", "build"])

    assert result.exit_code == 0, result.output

    dashboard_path = root_with_tracker / "workspace" / "output" / "dashboard.html"
    assert dashboard_path.exists()
    content = dashboard_path.read_text(encoding="utf-8")
    assert "No applications match the current filters." in content
