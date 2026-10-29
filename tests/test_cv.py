from __future__ import annotations

import subprocess
from pathlib import Path

from click.testing import CliRunner

from career_ops.cli import cli


def test_cv_fails_cleanly_when_generate_pdf_script_is_missing(career_ops_root: Path):
    input_html = career_ops_root / "workspace" / "output" / "resume.html"
    input_html.write_text("<html><body>resume</body></html>", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "cv",
            str(input_html),
            str(career_ops_root / "workspace" / "output" / "resume.pdf"),
        ],
    )

    assert result.exit_code == 1
    assert "Could not find" in result.output
    assert "generate-pdf.mjs" in result.output
    assert "Traceback" not in result.output


def test_cv_fails_cleanly_when_node_is_missing(career_ops_root: Path, monkeypatch):
    script = career_ops_root / "generate-pdf.mjs"
    script.write_text("console.log('ok')\n", encoding="utf-8")
    input_html = career_ops_root / "workspace" / "output" / "resume.html"
    input_html.write_text("<html><body>resume</body></html>", encoding="utf-8")

    def raise_missing_node(*args, **kwargs):
        raise FileNotFoundError("node")

    monkeypatch.setattr(subprocess, "run", raise_missing_node)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--root",
            str(career_ops_root),
            "cv",
            str(input_html),
            str(career_ops_root / "workspace" / "output" / "resume.pdf"),
        ],
    )

    assert result.exit_code == 1
    assert "'node' command not found" in result.output
    assert "Traceback" not in result.output
