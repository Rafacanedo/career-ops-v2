"""Tests for dedup.py — duplicate detection and removal."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_ops.dedup import run_dedup


def _write_tracker(root: Path, rows: list[str]) -> Path:
    apps_file = root / "workspace" / "applications.md"
    header = (
        "# Tracker\n\n"
        "| # | Date | Company | Role | Status | Score/5 | PDF | Report | Notes |\n"
        "|---|------|---------|------|--------|---------|-----|--------|-------|\n"
    )
    apps_file.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    return apps_file


class TestRunDedup:
    def test_no_file_exits_gracefully(self, career_ops_root: Path):
        result = run_dedup(career_ops_root, dry_run=True)
        assert result == 0

    def test_no_duplicates_returns_zero(self, career_ops_root: Path):
        _write_tracker(career_ops_root, [
            "| 1 | 2026-01-01 | Acme Corp | Senior Engineer | Evaluated | 4.0/5 | ✅ | [1](r.md) | |",
            "| 2 | 2026-01-02 | BigTech | Product Manager | Applied | 3.5/5 | ✅ | [2](r.md) | |",
        ])
        result = run_dedup(career_ops_root, dry_run=True)
        assert result == 0

    def test_exact_duplicate_removed(self, career_ops_root: Path):
        _write_tracker(career_ops_root, [
            "| 1 | 2026-01-01 | Acme Corp | Senior Data Engineer | Evaluated | 4.0/5 | ✅ | [1](r.md) | |",
            "| 2 | 2026-01-05 | Acme Corp | Senior Data Engineer | Applied | 3.5/5 | ✅ | [2](r.md) | |",
        ])
        result = run_dedup(career_ops_root, dry_run=False)
        assert result == 1
        content = (career_ops_root / "workspace" / "applications.md").read_text(encoding="utf-8")
        # Higher score (4.0) kept, lower score (3.5) removed
        assert "4.0/5" in content
        assert "3.5/5" not in content

    def test_status_promoted_when_dup_had_higher_status(self, career_ops_root: Path):
        _write_tracker(career_ops_root, [
            "| 1 | 2026-01-01 | Acme Corp | Senior Data Engineer | Evaluated | 4.5/5 | ✅ | [1](r.md) | |",
            "| 2 | 2026-01-05 | Acme Corp | Senior Data Engineer | Interview | 3.0/5 | ✅ | [2](r.md) | |",
        ])
        run_dedup(career_ops_root, dry_run=False)
        content = (career_ops_root / "workspace" / "applications.md").read_text(encoding="utf-8")
        # Score 4.5 is kept, but status Interview should be promoted
        assert "Interview" in content

    def test_dry_run_makes_no_changes(self, career_ops_root: Path):
        apps_file = _write_tracker(career_ops_root, [
            "| 1 | 2026-01-01 | Acme Corp | Senior Data Engineer | Evaluated | 4.0/5 | ✅ | [1](r.md) | |",
            "| 2 | 2026-01-05 | Acme Corp | Senior Data Engineer | Applied | 3.5/5 | ✅ | [2](r.md) | |",
        ])
        original = apps_file.read_text(encoding="utf-8")
        run_dedup(career_ops_root, dry_run=True)
        assert apps_file.read_text(encoding="utf-8") == original

    def test_different_companies_not_deduped(self, career_ops_root: Path):
        _write_tracker(career_ops_root, [
            "| 1 | 2026-01-01 | Acme Corp | Senior Data Engineer | Evaluated | 4.0/5 | ✅ | [1](r.md) | |",
            "| 2 | 2026-01-02 | BigTech Inc | Senior Data Engineer | Evaluated | 3.5/5 | ✅ | [2](r.md) | |",
        ])
        result = run_dedup(career_ops_root, dry_run=True)
        assert result == 0
