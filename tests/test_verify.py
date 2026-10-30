"""Tests for verify.py — pipeline health checks."""

from __future__ import annotations

from pathlib import Path

from career_ops.scan_csv import FIELDNAMES
from career_ops.verify import run_verify


def _write_tracker(root: Path, rows: list[str]) -> Path:
    tracker = root / "workspace" / "job-tracker.csv"
    tracker.parent.mkdir(parents=True, exist_ok=True)
    header = ";".join(FIELDNAMES)
    tracker.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8-sig")
    return tracker


class TestRunVerify:
    def test_no_file_returns_errors(self, career_ops_root: Path):
        errors, warnings = run_verify(career_ops_root)
        assert errors >= 1

    def test_clean_pipeline_no_errors(self, root_with_tracker: Path):
        _write_tracker(root_with_tracker, [
            "001;https://example.com/1;Acme;Engineer;;Queued;;;2026-07-25;;2026-07-25;;;",
        ])
        errors, warnings = run_verify(root_with_tracker)
        assert errors == 0

    def test_detects_duplicate_ids(self, career_ops_root: Path):
        _write_tracker(career_ops_root, [
            "001;https://example.com/1;Acme;Engineer;;Queued;;;2026-07-25;;2026-07-25;;;",
            "001;https://example.com/2;Beta;Analyst;;Queued;;;2026-07-25;;2026-07-25;;;",
        ])
        errors, _ = run_verify(career_ops_root)
        assert errors >= 1

    def test_detects_missing_report_file(self, career_ops_root: Path):
        _write_tracker(career_ops_root, [
            "001;https://example.com/1;Acme;Engineer;;Screened;4.5;;2026-07-25;;2026-07-25;;workspace/reports/nonexistent.md;",
        ])
        errors, _ = run_verify(career_ops_root)
        assert errors >= 1
