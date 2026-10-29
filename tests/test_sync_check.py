"""Tests for sync_check.py — setup consistency validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_ops.sync_check import run_sync_check


class TestRunSyncCheck:
    def test_missing_cv_is_error(self, career_ops_root: Path):
        errors, _ = run_sync_check(career_ops_root)
        assert any("cv.md" in e for e in errors)

    def test_missing_profile_is_error(self, career_ops_root: Path):
        (career_ops_root / "cv.md").write_text("# My CV\n" + "x" * 200, encoding="utf-8")
        errors, _ = run_sync_check(career_ops_root)
        assert any("profile.yml" in e for e in errors)

    def test_short_cv_is_warning(self, career_ops_root: Path):
        (career_ops_root / "cv.md").write_text("short", encoding="utf-8")
        _, warnings = run_sync_check(career_ops_root)
        assert any("too short" in w for w in warnings)

    def test_clean_setup_no_errors(self, career_ops_root: Path):
        (career_ops_root / "cv.md").write_text("# My CV\n" + "x" * 300, encoding="utf-8")
        profile = career_ops_root / "config" / "profile.yml"
        profile.write_text(
            "full_name: Rafael Canedo\nemail: test@test.com\nlocation: BR\n",
            encoding="utf-8",
        )
        errors, warnings = run_sync_check(career_ops_root)
        assert not any("cv.md" in e for e in errors)
        assert not any("profile.yml" in e for e in errors)

    def test_example_data_in_profile_is_warning(self, career_ops_root: Path):
        (career_ops_root / "cv.md").write_text("# My CV\n" + "x" * 300, encoding="utf-8")
        profile = career_ops_root / "config" / "profile.yml"
        profile.write_text(
            'full_name: "Jane Smith"\nemail: test@test.com\nlocation: BR\n',
            encoding="utf-8",
        )
        _, warnings = run_sync_check(career_ops_root)
        assert any("example data" in w for w in warnings)
