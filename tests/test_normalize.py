"""Tests for normalize.py — status normalisation."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_ops.normalize import run_normalize, _normalize_status


class TestNormalizeStatus:
    """Unit tests for the _normalize_status function."""

    def test_canonical_evaluated(self):
        assert _normalize_status("Evaluated")["status"] == "Evaluated"

    def test_canonical_applied(self):
        assert _normalize_status("Applied")["status"] == "Applied"

    def test_canonical_skip(self):
        assert _normalize_status("SKIP")["status"] == "SKIP"

    def test_alias_evaluada(self):
        assert _normalize_status("evaluada")["status"] == "Evaluated"

    def test_alias_aplicado(self):
        assert _normalize_status("aplicado")["status"] == "Applied"

    def test_alias_entrevista(self):
        assert _normalize_status("entrevista")["status"] == "Interview"

    def test_alias_oferta(self):
        assert _normalize_status("oferta")["status"] == "Offer"

    def test_alias_rechazado(self):
        assert _normalize_status("rechazado")["status"] == "Rejected"

    def test_alias_descartado(self):
        assert _normalize_status("descartado")["status"] == "Discarded"

    def test_duplicado_to_discarded(self):
        result = _normalize_status("DUPLICADO #42")
        assert result["status"] == "Discarded"
        assert result.get("move_to_notes") == "DUPLICADO #42"

    def test_repost_to_discarded(self):
        result = _normalize_status("Repost #123")
        assert result["status"] == "Discarded"
        assert result.get("move_to_notes") == "Repost #123"

    def test_strip_bold(self):
        assert _normalize_status("**Applied**")["status"] == "Applied"

    def test_strip_date_from_applied(self):
        assert _normalize_status("Applied 2026-01-15")["status"] == "Applied"

    def test_strip_date_from_rejected(self):
        assert _normalize_status("Rechazado 2026-02-01")["status"] == "Rejected"

    def test_hold_to_evaluated(self):
        assert _normalize_status("hold")["status"] == "Evaluated"

    def test_monitor_to_evaluated(self):
        assert _normalize_status("monitor")["status"] == "Evaluated"

    def test_condicional_to_evaluated(self):
        assert _normalize_status("condicional")["status"] == "Evaluated"

    def test_cerrada_to_discarded(self):
        assert _normalize_status("cerrada")["status"] == "Discarded"

    def test_cancelada_to_discarded(self):
        assert _normalize_status("cancelada")["status"] == "Discarded"

    def test_geo_blocker_to_skip(self):
        assert _normalize_status("geo blocker")["status"] == "SKIP"

    def test_em_dash_to_discarded(self):
        assert _normalize_status("—")["status"] == "Discarded"

    def test_empty_to_discarded(self):
        assert _normalize_status("")["status"] == "Discarded"

    def test_unknown_returns_none(self):
        result = _normalize_status("WHATEVER_UNKNOWN_XYZ")
        assert result.get("unknown") is True


class TestRunNormalize:
    """Integration tests for run_normalize()."""

    def test_no_file_exits_gracefully(self, career_ops_root: Path):
        result = run_normalize(career_ops_root, dry_run=True)
        assert result == 0

    def test_dry_run_makes_no_changes(self, career_ops_root: Path):
        apps_file = career_ops_root / "workspace" / "applications.md"
        apps_file.write_text(
            "# Tracker\n\n"
            "| # | Date | Company | Role | Status | Score/5 | PDF | Report | Notes |\n"
            "|---|------|---------|------|--------|---------|-----|--------|-------|\n"
            "| 1 | 2026-01-01 | Acme | Engineer | evaluada | 4.0/5 | ✅ | [1](reports/001.md) | |\n",
            encoding="utf-8",
        )
        original = apps_file.read_text(encoding="utf-8")
        run_normalize(career_ops_root, dry_run=True)
        assert apps_file.read_text(encoding="utf-8") == original

    def test_normalizes_evaluada_to_evaluated(self, career_ops_root: Path):
        apps_file = career_ops_root / "workspace" / "applications.md"
        apps_file.write_text(
            "# Tracker\n\n"
            "| # | Date | Company | Role | Status | Score/5 | PDF | Report | Notes |\n"
            "|---|------|---------|------|--------|---------|-----|--------|-------|\n"
            "| 1 | 2026-01-01 | Acme | Engineer | evaluada | 4.0/5 | ✅ | [1](reports/001.md) | |\n",
            encoding="utf-8",
        )
        changes = run_normalize(career_ops_root, dry_run=False)
        assert changes == 1
        content = apps_file.read_text(encoding="utf-8")
        assert "Evaluated" in content
        assert "evaluada" not in content

    def test_creates_backup(self, career_ops_root: Path):
        apps_file = career_ops_root / "workspace" / "applications.md"
        apps_file.write_text(
            "# Tracker\n\n"
            "| # | Date | Company | Role | Status | Score/5 | PDF | Report | Notes |\n"
            "|---|------|---------|------|--------|---------|-----|--------|-------|\n"
            "| 1 | 2026-01-01 | Acme | Engineer | evaluada | 4.0/5 | ✅ | [1](reports/001.md) | |\n",
            encoding="utf-8",
        )
        run_normalize(career_ops_root, dry_run=False)
        assert (career_ops_root / "workspace" / "applications.md.bak").exists()
