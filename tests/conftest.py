"""
conftest.py — Shared pytest fixtures for career-ops-v2 tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from career_ops.config import get_db_path
from career_ops.models import VagaInput
from career_ops.repository import CareerOpsRepository

SAMPLE_STATES_YML = """\
states:
  - id: evaluated
    label: Evaluated
    aliases: [evaluada]
    description: Offer evaluated with report, pending decision
    dashboard_group: evaluated
  - id: applied
    label: Applied
    aliases: [aplicado, enviada, aplicada, sent]
    description: Application submitted
    dashboard_group: applied
  - id: interview
    label: Interview
    aliases: [entrevista]
    description: Active interview process
    dashboard_group: interview
  - id: offer
    label: Offer
    aliases: [oferta]
    description: Offer received
    dashboard_group: offer
  - id: rejected
    label: Rejected
    aliases: [rechazado, rechazada]
    description: Rejected by company
    dashboard_group: rejected
  - id: discarded
    label: Discarded
    aliases: [descartado, descartada, cerrada, cancelada, duplicado, repost]
    description: Discarded by candidate or offer closed
    dashboard_group: discarded
  - id: skip
    label: SKIP
    aliases: [no_aplicar, no aplicar, skip, monitor, geo blocker]
    description: Doesn't fit, don't apply
    dashboard_group: skip
"""


@pytest.fixture
def career_ops_root(tmp_path: Path) -> Path:
    """
    Create a minimal career-ops project structure in a temp directory.
    Returns the root path.
    """
    root = tmp_path / "career-ops"
    root.mkdir()

    # Create directory structure
    (root / "data").mkdir()
    (root / "templates").mkdir()
    (root / "reports").mkdir()
    (root / "workspace").mkdir()
    (root / "workspace" / "reports").mkdir()
    (root / "workspace" / "output").mkdir()
    (root / "workspace" / "jds").mkdir()
    (root / "config").mkdir()

    # Write states.yml
    (root / "config" / "states.yml").write_text(SAMPLE_STATES_YML, encoding="utf-8")

    return root


@pytest.fixture
def temp_repo(career_ops_root: Path) -> CareerOpsRepository:
    """Initialize and return a temporary CareerOpsRepository in career_ops_root."""
    return CareerOpsRepository(db_path=get_db_path(career_ops_root), auto_init=True)


@pytest.fixture
def root_with_tracker(career_ops_root: Path) -> Path:
    """Career-ops root with a pre-populated SQLite database and deliverable files."""
    repo = CareerOpsRepository(db_path=get_db_path(career_ops_root), auto_init=True)

    seed_records = [
        (
            "https://example.com/jobs/1",
            "Acme Corp",
            "Senior Data Engineer",
            "evaluated",
            4.2,
            "2026-01-15",
            "workspace/reports/001-acme-2026-01-15.md",
            "workspace/output/001-acme.pdf",
            "Good match",
        ),
        (
            "https://example.com/jobs/2",
            "BigTech",
            "Machine Learning Engineer",
            "applied",
            3.8,
            "2026-01-16",
            "workspace/reports/002-bigtech-2026-01-16.md",
            "workspace/output/002-bigtech.pdf",
            "Applied",
        ),
        (
            "https://example.com/jobs/3",
            "StartupXYZ",
            "Data Scientist",
            "rejected",
            2.1,
            "2026-01-17",
            "workspace/reports/003-startupxyz-2026-01-17.md",
            None,
            "Low score",
        ),
        (
            "https://example.com/jobs/4",
            "MegaCorp",
            "Analytics Lead",
            "interview",
            4.5,
            "2026-01-18",
            "workspace/reports/004-megacorp-2026-01-18.md",
            "workspace/output/004-megacorp.pdf",
            "In process",
        ),
    ]

    for idx, (url, company, role, status, score, app_date, rep_path, pdf_path, notes) in enumerate(
        seed_records, start=1
    ):
        if rep_path:
            full_rep = career_ops_root / rep_path
            full_rep.parent.mkdir(parents=True, exist_ok=True)
            full_rep.write_text(f"# Report {idx}", encoding="utf-8")
        if pdf_path:
            full_pdf = career_ops_root / pdf_path
            full_pdf.parent.mkdir(parents=True, exist_ok=True)
            full_pdf.write_bytes(b"%PDF-1.4\n")

        vid, _ = repo.insert_vaga(
            VagaInput(
                original_url=url,
                company=company,
                role=role,
                source_portal="greenhouse",
            ),
            descricao=f"Job description for {role} at {company}.",
        )
        repo.update_lifecycle(
            vaga_id=vid,
            status=status,
            score=score,
            application_date=app_date,
            report_path=rep_path,
            cv_pdf_path=pdf_path,
            notes=notes,
        )

    return career_ops_root
