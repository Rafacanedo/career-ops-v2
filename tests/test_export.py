from __future__ import annotations

from pathlib import Path
from click.testing import CliRunner

from career_ops.cli import cli
from career_ops.export import export_applications
from career_ops.scan_csv import FIELDNAMES


def test_export_applications_reads_workspace_tracker(root_with_tracker: Path):
    tracker = root_with_tracker / "workspace" / "job-tracker.csv"
    header = ";".join(FIELDNAMES)
    tracker.write_text(
        f"{header}\r\n"
        "001;https://example.com/1;Acme Corp;Data Engineer;;Screened;4.2;;2026-07-25;;2026-07-25;;;\r\n",
        encoding="utf-8-sig",
    )

    output_path = root_with_tracker / "workspace" / "output" / "applications.csv"
    count = export_applications(root_with_tracker, output_path)

    assert count == 1
    content = output_path.read_text(encoding="utf-8-sig")
    assert '"Acme Corp"' in content
    assert '"4.2"' in content


def test_export_command_defaults_to_workspace_output(root_with_tracker: Path):
    tracker = root_with_tracker / "workspace" / "job-tracker.csv"
    header = ";".join(FIELDNAMES)
    tracker.write_text(
        f"{header}\r\n"
        "001;https://example.com/1;Acme Corp;Data Engineer;;Screened;4.2;;2026-07-25;;2026-07-25;;;\r\n",
        encoding="utf-8-sig",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["--root", str(root_with_tracker), "export"])

    assert result.exit_code == 0, result.output
    assert (root_with_tracker / "workspace" / "output" / "applications.csv").exists()
