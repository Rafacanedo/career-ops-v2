"""Tests for verify.py — SQLite pipeline health checks."""

from __future__ import annotations

from pathlib import Path

from career_ops.config import get_db_path
from career_ops.models import VagaInput
from career_ops.repository import CareerOpsRepository
from career_ops.verify import run_verify


class TestRunVerify:
    def test_no_database_returns_errors(self, career_ops_root: Path):
        errors, _ = run_verify(career_ops_root)
        assert errors >= 1

    def test_clean_pipeline_no_errors(self, root_with_tracker: Path):
        errors, warnings = run_verify(root_with_tracker)
        assert errors == 0
        assert warnings == 0

    def test_detects_missing_report_file(self, career_ops_root: Path):
        repo = CareerOpsRepository(db_path=get_db_path(career_ops_root), auto_init=True)
        vid, _ = repo.insert_vaga(
            VagaInput(
                original_url="https://example.com/1",
                company="Acme",
                role="Engineer",
                source_portal="greenhouse",
            ),
            descricao="JD text",
        )
        repo.update_lifecycle(
            vaga_id=vid,
            status="evaluated",
            score=4.5,
            report_path="workspace/reports/nonexistent.md",
        )

        errors, _ = run_verify(career_ops_root)
        assert errors >= 1

    def test_detects_missing_cv_pdf_file(self, career_ops_root: Path):
        repo = CareerOpsRepository(db_path=get_db_path(career_ops_root), auto_init=True)
        vid, _ = repo.insert_vaga(
            VagaInput(
                original_url="https://example.com/2",
                company="Beta",
                role="Analyst",
                source_portal="lever",
            ),
            descricao="JD text",
        )
        repo.update_lifecycle(
            vaga_id=vid,
            status="applied",
            score=4.0,
            cv_pdf_path="workspace/output/missing_cv.pdf",
        )

        errors, _ = run_verify(career_ops_root)
        assert errors >= 1
