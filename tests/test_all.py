"""
test_all.py — Integration test suite for career-ops-python.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from career_ops.cli import cli


class TestSyntax:
    """Check all modules import cleanly."""

    MODULES = [
        "career_ops",
        "career_ops.config",
        "career_ops.context",
        "career_ops.models",
        "career_ops.utils",
        "career_ops.db",
        "career_ops.repository",
        "career_ops.cli",
        "career_ops.verify",
        "career_ops.sync_check",
        "career_ops.dashboard",
        "career_ops.export",
        "career_ops.cv",
        "career_ops.fetch_cmd",
        "career_ops.fetcher.connectors",
        "career_ops.fetcher.orchestrator",
    ]

    @pytest.mark.parametrize("module", MODULES)
    def test_module_imports(self, module: str):
        result = subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{module} import failed:\n{result.stderr}"


class TestCliRegistration:
    """All commands must be registered and show help."""

    EXPECTED_COMMANDS = [
        "init",
        "intake",
        "intake-raw",
        "scan",
        "list",
        "show",
        "track",
        "stats",
        "export",
        "verify",
        "sync-check",
        "dashboard",
        "cv",
    ]

    def test_cli_has_all_commands(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        for cmd in self.EXPECTED_COMMANDS:
            assert cmd in result.output, f"Command '{cmd}' not found in --help output"

    @pytest.mark.parametrize("cmd", EXPECTED_COMMANDS)
    def test_command_has_help(self, cmd: str):
        runner = CliRunner()
        result = runner.invoke(cli, [cmd, "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output


class TestGracefulEmptyData:
    """Commands should not crash when no data files exist."""

    COMMANDS_OK_ON_EMPTY = [
        ["init"],
        ["verify"],
        ["sync-check"],
        ["list"],
        ["stats"],
        ["export"],
        ["scan", "--help"],
    ]

    @pytest.mark.parametrize("cmd_args", COMMANDS_OK_ON_EMPTY)
    def test_command_graceful_on_empty(self, career_ops_root: Path, cmd_args: list[str]):
        runner = CliRunner()
        result = runner.invoke(cli, ["--root", str(career_ops_root)] + cmd_args)
        assert result.exit_code in (0, 1), (
            f"Command {cmd_args} crashed with exit code {result.exit_code}:\n{result.output}"
        )
        assert "Traceback" not in result.output, (
            f"Command {cmd_args} raised an exception:\n{result.output}"
        )
