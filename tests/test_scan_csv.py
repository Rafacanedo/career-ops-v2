from __future__ import annotations

from pathlib import Path

from career_ops.scan_csv import (
    FIELDNAMES,
    add_job_row,
    get_pending_jobs,
    update_tracker_row,
)


def test_scan_csv_handles_14_column_tracker_rows(root_with_tracker: Path):
    tracker = root_with_tracker / "workspace" / "job-tracker.csv"
    header = ";".join(FIELDNAMES)
    tracker.write_text(
        f"{header}\r\n"
        "101;https://example.com/jobs/new-role;Acme Labs;Senior Analyst;workspace/jds/jd_101.md;Queued;;;2026-07-25;;2026-07-25;;;\r\n"
        "102;https://example.com/jobs/already-done;Acme Labs;Senior Analyst;workspace/jds/jd_102.md;Applied;4.8;Full-Stack;2026-07-25;2026-07-26;2026-07-26;Good;workspace/reports/102.md;workspace/cvs/102.pdf\r\n",
        encoding="utf-8-sig",
    )

    pending = get_pending_jobs(root_with_tracker)

    assert len(pending) == 1
    assert pending[0]["id"] == "101"
    assert pending[0]["company"] == "Acme Labs"


def test_update_tracker_row_writes_back_to_14_column_csv(root_with_tracker: Path):
    tracker = root_with_tracker / "workspace" / "job-tracker.csv"
    header = ";".join(FIELDNAMES)
    tracker.write_text(
        f"{header}\r\n"
        "123;https://example.com/jobs/123;Acme Corp;Data Engineer;;Queued;;;2026-07-25;;2026-07-25;;;\r\n",
        encoding="utf-8-sig",
    )

    updated = update_tracker_row(
        root_with_tracker,
        "123",
        company="Acme Corp",
        position="Staff Data Engineer",
        status="Screened",
        score="4.9",
    )

    assert updated is True
    tracker_content = tracker.read_text(encoding="utf-8-sig")
    assert "Staff Data Engineer" in tracker_content
    assert "Screened" in tracker_content
    assert "4.9" in tracker_content


def test_add_job_row_prevents_duplicates(root_with_tracker: Path):
    tracker = root_with_tracker / "workspace" / "job-tracker.csv"
    header = ";".join(FIELDNAMES)
    tracker.write_text(
        f"{header}\r\n"
        "001;https://example.com/jobs/001;Acme Corp;Data Engineer;;Queued;;;2026-07-25;;2026-07-25;;;\r\n",
        encoding="utf-8-sig",
    )

    created, item_id, msg = add_job_row(
        root_with_tracker,
        "https://example.com/jobs/001",
        "Acme Corp",
        "Data Engineer",
    )

    assert created is False
    assert "ja cadastrada" in msg
