"""Tests for merge_tracker.py — TSV merging logic."""

from __future__ import annotations

from pathlib import Path

from career_ops.merge_tracker import run_merge


def _write_tracker(root: Path, rows: list[str]) -> Path:
    apps_file = root / "workspace" / "applications.md"
    header = (
        "# Tracker\n\n"
        "| # | Date | Company | Role | Status | Score/5 | PDF | Report | Notes |\n"
        "|---|------|---------|------|--------|---------|-----|--------|-------|\n"
    )
    apps_file.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    return apps_file


def _write_tsv(root: Path, filename: str, content: str) -> Path:
    tsv_path = root / "workspace" / "tracker-additions" / filename
    tsv_path.write_text(content, encoding="utf-8")
    return tsv_path


class TestRunMerge:
    def test_no_tracker_file(self, career_ops_root: Path):
        result = run_merge(career_ops_root, dry_run=True)
        assert result == {"added": 0, "updated": 0, "skipped": 0}

    def test_no_pending_tsvs(self, career_ops_root: Path):
        _write_tracker(career_ops_root, [
            "| 1 | 2026-01-01 | Acme | Engineer | Evaluated | 4.0/5 | ✅ | [1](r.md) | |",
        ])
        result = run_merge(career_ops_root, dry_run=True)
        assert result == {"added": 0, "updated": 0, "skipped": 0}

    def test_adds_new_entry(self, career_ops_root: Path):
        _write_tracker(career_ops_root, [
            "| 1 | 2026-01-01 | Acme | Engineer | Evaluated | 4.0/5 | ✅ | [1](r.md) | |",
        ])
        _write_tsv(
            career_ops_root, "002-bigtech.tsv",
            "2\t2026-01-20\tBigTech\tDev Lead\tEvaluated\t3.9/5\t✅\t[2](reports/002.md)\tNew entry"
        )
        result = run_merge(career_ops_root, dry_run=False)
        assert result["added"] == 1
        content = (career_ops_root / "workspace" / "applications.md").read_text(encoding="utf-8")
        assert "BigTech" in content

    def test_tsv_moved_to_merged_after_processing(self, career_ops_root: Path):
        _write_tracker(career_ops_root, [])
        tsv = _write_tsv(
            career_ops_root, "005-corp.tsv",
            "5\t2026-01-25\tTestCorp\tAnalyst\tEvaluated\t4.1/5\t✅\t[5](reports/005.md)\t"
        )
        run_merge(career_ops_root, dry_run=False)
        assert not tsv.exists()
        merged = career_ops_root / "workspace" / "tracker-additions" / "merged" / "005-corp.tsv"
        assert merged.exists()

    def test_dry_run_does_not_move_tsvs(self, career_ops_root: Path):
        _write_tracker(career_ops_root, [])
        tsv = _write_tsv(
            career_ops_root, "006-firm.tsv",
            "6\t2026-01-26\tFirm\tDev\tEvaluated\t3.7/5\t✅\t[6](reports/006.md)\t"
        )
        run_merge(career_ops_root, dry_run=True)
        assert tsv.exists()  # Not moved in dry-run

    def test_skip_existing_entry_lower_score(self, career_ops_root: Path):
        _write_tracker(career_ops_root, [
            "| 1 | 2026-01-01 | Acme | Senior Engineer | Applied | 4.5/5 | ✅ | [1](reports/001.md) | |",
        ])
        (career_ops_root / "workspace" / "reports" / "001.md").write_text("report", encoding="utf-8")
        _write_tsv(
            career_ops_root, "001-acme-v2.tsv",
            "1\t2026-01-10\tAcme\tSenior Engineer\tEvaluated\t3.0/5\t✅\t[1](reports/001.md)\t"
        )
        result = run_merge(career_ops_root, dry_run=False)
        assert result["skipped"] == 1

    def test_update_existing_entry_higher_score(self, career_ops_root: Path):
        _write_tracker(career_ops_root, [
            "| 1 | 2026-01-01 | Acme | Senior Engineer | Evaluated | 3.0/5 | ✅ | [1](reports/001.md) | |",
        ])
        (career_ops_root / "workspace" / "reports" / "001.md").write_text("report", encoding="utf-8")
        _write_tsv(
            career_ops_root, "001-acme-v2.tsv",
            "1\t2026-01-10\tAcme\tSenior Engineer\tEvaluated\t4.5/5\t✅\t[1](reports/001.md)\t"
        )
        result = run_merge(career_ops_root, dry_run=False)
        assert result["updated"] == 1
        content = (career_ops_root / "workspace" / "applications.md").read_text(encoding="utf-8")
        assert "4.5/5" in content
