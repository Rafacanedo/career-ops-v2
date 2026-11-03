from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from career_ops.cli import cli
from career_ops.export import export_applications


def test_export_applications_reads_sqlite_repository(root_with_tracker: Path):
    output_path = root_with_tracker / "workspace" / "output" / "applications.csv"
    count = export_applications(root_with_tracker, output_path)

    assert count == 4
    content = output_path.read_text(encoding="utf-8-sig")
    assert '"Acme Corp"' in content
    assert '"4.2"' in content


def test_export_command_defaults_to_workspace_output(root_with_tracker: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["--root", str(root_with_tracker), "export"])

    assert result.exit_code == 0, result.output
    assert (root_with_tracker / "workspace" / "output" / "applications.csv").exists()


def test_export_command_json_format(root_with_tracker: Path):
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--root", str(root_with_tracker), "export", "--format", "json"]
    )

    assert result.exit_code == 0, result.output
    json_out = root_with_tracker / "workspace" / "output" / "applications.json"
    assert json_out.exists()
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert len(payload) == 4
    assert any(item["company"] == "Acme Corp" for item in payload)
