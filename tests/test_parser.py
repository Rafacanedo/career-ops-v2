"""Tests for parser.py — parsing of applications.md and TSVs."""

from __future__ import annotations

import pytest

from career_ops.parser import parse_app_line, parse_tsv_content, read_applications
from career_ops.models import AppEntry, TrackerAddition


class TestParseAppLine:
    def test_valid_line(self):
        line = "| 1 | 2026-01-15 | Acme Corp | Senior Engineer | Evaluated | 4.2/5 | ✅ | [1](reports/001.md) | Good match |"
        entry = parse_app_line(line)
        assert entry is not None
        assert entry.num == 1
        assert entry.company == "Acme Corp"
        assert entry.role == "Senior Engineer"
        assert entry.status == "Evaluated"
        assert entry.score == "4.2/5"

    def test_legacy_score_status_order_is_detected(self):
        line = "| 1 | 2026-01-15 | Acme Corp | Senior Engineer | 4.2/5 | Evaluated | ✅ | [1](reports/001.md) | Good match |"
        entry = parse_app_line(line)
        assert entry is not None
        assert entry.status == "Evaluated"
        assert entry.score == "4.2/5"

    def test_header_line_returns_none(self):
        line = "| # | Date | Company | Role | Score | Status | PDF | Report | Notes |"
        # num will be non-integer
        assert parse_app_line(line) is None

    def test_separator_line_returns_none(self):
        line = "|---|------|---------|------|-------|--------|-----|--------|-------|"
        assert parse_app_line(line) is None

    def test_non_pipe_line_returns_none(self):
        assert parse_app_line("# Applications Tracker") is None

    def test_zero_num_returns_none(self):
        line = "| 0 | 2026-01-01 | X | Y | Evaluated | 3.0/5 | ✅ | [0](r.md) | |"
        assert parse_app_line(line) is None

    def test_notes_captured(self):
        line = "| 5 | 2026-02-01 | Corp | Dev | Applied | 3.5/5 | ❌ | [5](r.md) | My notes here |"
        entry = parse_app_line(line)
        assert entry is not None
        assert entry.notes == "My notes here"


class TestParseTsvContent:
    def test_9col_tsv(self):
        content = "10\t2026-01-20\tAcme\tEngineer\tEvaluated\t4.0/5\t✅\t[10](reports/010.md)\tNotes"
        result = parse_tsv_content(content, "010-acme.tsv")
        assert result is not None
        assert result.num == 10
        assert result.company == "Acme"
        assert result.status == "Evaluated"
        assert result.score == "4.0/5"

    def test_8col_tsv_no_notes(self):
        content = "11\t2026-01-21\tBigCo\tDev\tApplied\t3.8/5\t✅\t[11](reports/011.md)"
        result = parse_tsv_content(content, "011-bigco.tsv")
        assert result is not None
        assert result.num == 11
        assert result.notes == ""

    def test_pipe_delimited(self):
        content = "| 12 | 2026-01-22 | StartupX | PM | 3.5/5 | Evaluated | ❌ | [12](reports/012.md) | Good |"
        result = parse_tsv_content(content, "012.tsv")
        assert result is not None
        assert result.num == 12
        assert result.company == "StartupX"

    def test_alias_status_normalised(self):
        content = "15\t2026-02-01\tCorp\tEngineer\tevaluada\t4.1/5\t✅\t[15](reports/015.md)\t"
        result = parse_tsv_content(content, "015.tsv")
        assert result is not None
        assert result.status == "Evaluated"

    def test_swapped_score_status_detection(self):
        # score before status (swapped format)
        content = "16\t2026-02-02\tFirm\tDev\t4.3/5\tEvaluated\t✅\t[16](reports/016.md)\t"
        result = parse_tsv_content(content, "016.tsv")
        assert result is not None
        assert result.score == "4.3/5"
        assert result.status == "Evaluated"

    def test_empty_content_returns_none(self):
        assert parse_tsv_content("", "empty.tsv") is None

    def test_too_few_fields_returns_none(self):
        assert parse_tsv_content("1\t2026-01-01\tAcme", "bad.tsv") is None


class TestReadApplications:
    def test_reads_and_parses(self, root_with_tracker):
        apps_file = root_with_tracker / "workspace" / "applications.md"
        lines, entries = read_applications(apps_file)
        assert len(entries) == 4
        assert entries[0].num == 1
        assert entries[0].company == "Acme Corp"
        assert entries[3].num == 4

    def test_skips_header_and_separator(self, root_with_tracker):
        apps_file = root_with_tracker / "workspace" / "applications.md"
        _, entries = read_applications(apps_file)
        nums = [e.num for e in entries]
        assert all(n > 0 for n in nums)
