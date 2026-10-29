"""
conftest.py — Shared pytest fixtures for career-ops-python tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest


SAMPLE_APPLICATIONS_MD = """\
# Applications Tracker

| # | Date | Company | Role | Status | Score/5 | PDF | Report | Notes |
|---|------|---------|------|--------|---------|-----|--------|-------|
| 1 | 2026-01-15 | Acme Corp | Senior Data Engineer | Evaluated | 4.2/5 | ✅ | [1](reports/001-acme-2026-01-15.md) | Good match |
| 2 | 2026-01-16 | BigTech | Machine Learning Engineer | Applied | 3.8/5 | ✅ | [2](reports/002-bigtech-2026-01-16.md) | Applied |
| 3 | 2026-01-17 | StartupXYZ | Data Scientist | Rejected | 2.1/5 | ❌ | [3](reports/003-startupxyz-2026-01-17.md) | Low score |
| 4 | 2026-01-18 | MegaCorp | Analytics Lead | Interview | 4.5/5 | ✅ | [4](reports/004-megacorp-2026-01-18.md) | In process |
"""

SAMPLE_PIPELINE_MD = """\
# Pipeline — Pending Evaluations

## Pending

- [ ] https://example.com/jobs/123 [jd: local:workspace/jds/jd_001.md]

## Processed
"""

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
    (root / "workspace" / "tracker-additions").mkdir(parents=True)
    (root / "batch" / "tracker-additions").mkdir(parents=True)
    (root / "config").mkdir()

    # Write states.yml in both current and legacy locations used by tests.
    (root / "config" / "states.yml").write_text(SAMPLE_STATES_YML, encoding="utf-8")
    (root / "templates" / "states.yml").write_text(SAMPLE_STATES_YML, encoding="utf-8")

    return root


@pytest.fixture
def root_with_tracker(career_ops_root: Path) -> Path:
    """Career-ops root with a pre-populated applications.md."""
    apps_file = career_ops_root / "workspace" / "applications.md"
    apps_file.write_text(SAMPLE_APPLICATIONS_MD, encoding="utf-8")
    (career_ops_root / "data" / "applications.md").write_text(
        SAMPLE_APPLICATIONS_MD, encoding="utf-8"
    )
    (career_ops_root / "workspace" / "pipeline.md").write_text(
        SAMPLE_PIPELINE_MD, encoding="utf-8"
    )
    (career_ops_root / "data" / "pipeline.md").write_text(
        SAMPLE_PIPELINE_MD, encoding="utf-8"
    )
    (career_ops_root / "workspace" / "job-tracker.csv").write_text(
        "ID;URL;Job Description;Company;Position;Processing Date\r\n",
        encoding="utf-8-sig",
    )
    (career_ops_root / "data" / "job-tracker.csv").write_text(
        "ID;URL;Job Description;Company;Position;Processing Date\r\n",
        encoding="utf-8-sig",
    )

    # Create the report files referenced in the tracker
    for num, slug in [
        (1, "001-acme-2026-01-15"),
        (2, "002-bigtech-2026-01-16"),
        (3, "003-startupxyz-2026-01-17"),
        (4, "004-megacorp-2026-01-18"),
    ]:
        (career_ops_root / "workspace" / "reports" / f"{slug}.md").write_text(
            f"# Report {num}", encoding="utf-8"
        )
        (career_ops_root / "reports" / f"{slug}.md").write_text(
            f"# Report {num}", encoding="utf-8"
        )

    return career_ops_root
