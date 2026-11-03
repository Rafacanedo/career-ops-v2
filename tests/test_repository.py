"""
test_repository.py — Unit tests for CareerOpsRepository transactional operations,
collision resolution, lifecycle state transitions, and pipeline statistics.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from career_ops.db import get_db_connection
from career_ops.models import VagaInput
from career_ops.repository import (
    CareerOpsRepository,
    get_pipeline_stats,
    get_vaga,
    get_vaga_description,
    insert_vaga,
    list_vagas,
    update_lifecycle,
)
from career_ops.utils import compute_content_hash


@pytest.fixture()
def repo(tmp_path: Path) -> CareerOpsRepository:
    db_path = tmp_path / "data" / "career_ops.db"
    return CareerOpsRepository(db_path=db_path)


class TestInsertAndGetVaga:
    def test_insert_and_get_vaga_success(self, repo: CareerOpsRepository) -> None:
        vaga_in = VagaInput(
            original_url="https://boards.greenhouse.io/acme/jobs/12345?utm_source=linkedin",
            company="Acme Corp.",
            role="Senior Data Engineer (Remote)",
            source_portal="greenhouse",
            location="Brazil",
            remote_type="remote",
        )
        raw_jd = "We are looking for a Senior Data Engineer proficient in Python and SQL."

        vaga_id, created = repo.insert_vaga(
            vaga_in, raw_jd, description_clean="Clean JD"
        )

        assert created is True
        assert re.match(r"^vaga_[0-9a-f]+_[0-9a-f]{6}$", vaga_id)

        record = repo.get_vaga(vaga_id)
        assert record is not None
        assert record["id"] == vaga_id
        assert record["canonical_url"] == "greenhouse:acme:12345"
        assert record["company"] == "Acme Corp."
        assert record["company_norm"] == "acme corp"
        assert record["role"] == "Senior Data Engineer (Remote)"
        assert record["role_norm"] == "senior data engineer remote"
        assert record["source_portal"] == "greenhouse"
        assert record["location"] == "Brazil"
        assert record["remote_type"] == "remote"
        assert record["status_triagem"] == "queued"
        assert record["status"] == "queued"
        assert "description_raw" not in record

        desc = repo.get_vaga_description(vaga_id)
        assert desc == raw_jd

    def test_get_nonexistent_vaga_returns_none(self, repo: CareerOpsRepository) -> None:
        assert repo.get_vaga("vaga_nonexistent") is None
        assert repo.get_vaga_description("vaga_nonexistent") is None


class TestCollisionHandling:
    def test_collision_preserves_oldest_id_and_ignores_identical_content(
        self, repo: CareerOpsRepository
    ) -> None:
        vaga_1 = VagaInput(
            original_url="https://boards.greenhouse.io/stripe/jobs/999",
            company="Stripe",
            role="Backend Engineer",
            source_portal="greenhouse",
        )
        vaga_2 = VagaInput(
            original_url="https://boards.greenhouse.io/stripe/jobs/999?gh_src=abc",
            company="Stripe Inc",
            role="Backend Engineer [Remote]",
            source_portal="greenhouse",
        )

        first_id, created_1 = repo.insert_vaga(vaga_1, "Build payment systems.")
        second_id, created_2 = repo.insert_vaga(vaga_2, "Build   payment\nsystems.")

        assert created_1 is True
        assert created_2 is False
        assert second_id == first_id

        all_rows = repo.list_vagas()
        assert len(all_rows) == 1
        assert all_rows[0]["id"] == first_id

    def test_collision_backfills_empty_description(
        self, repo: CareerOpsRepository
    ) -> None:
        vaga = VagaInput(
            original_url="https://jobs.ashbyhq.com/linear/abc-123",
            company="Linear",
            role="Product Engineer",
            source_portal="ashby",
        )
        first_id, created_1 = repo.insert_vaga(vaga, "")
        assert created_1 is True
        assert repo.get_vaga_description(first_id) == ""

        second_id, created_2 = repo.insert_vaga(
            vaga, "Full job description backfilled on second pass."
        )
        assert created_2 is False
        assert second_id == first_id
        assert (
            repo.get_vaga_description(first_id)
            == "Full job description backfilled on second pass."
        )

    def test_collision_backfills_missing_vaga_descricoes_row(
        self, repo: CareerOpsRepository
    ) -> None:
        vaga = VagaInput(
            original_url="https://boards.greenhouse.io/datadog/jobs/555",
            company="Datadog",
            role="Distributed Systems Engineer",
            source_portal="greenhouse",
        )
        first_id, _ = repo.insert_vaga(vaga, "Initial text")

        # Simulate missing child row in vaga_descricoes
        with get_db_connection(repo.db_path) as conn:
            conn.execute("DELETE FROM vaga_descricoes WHERE vaga_id = ?", (first_id,))
        assert repo.get_vaga_description(first_id) is None

        second_id, created_2 = repo.insert_vaga(vaga, "Recreated description row")
        assert created_2 is False
        assert second_id == first_id
        assert repo.get_vaga_description(first_id) == "Recreated description row"

    def test_collision_updates_description_when_content_hash_changes_and_ignores_empty(
        self, repo: CareerOpsRepository
    ) -> None:
        vaga = VagaInput(
            original_url="https://boards.greenhouse.io/vercel/jobs/777",
            company="Vercel",
            role="Infrastructure Engineer",
            source_portal="greenhouse",
        )
        first_id, _ = repo.insert_vaga(vaga, "Version 1: Salary $140k")

        with get_db_connection(repo.db_path) as conn:
            conn.execute(
                "UPDATE vagas SET updated_at = '2020-01-01 00:00:00' WHERE id = ?",
                (first_id,),
            )

        # Revise job description content
        revised_jd = "Version 2: Salary $165k + Equity"
        second_id, created_2 = repo.insert_vaga(
            vaga, revised_jd, description_clean="Clean V2"
        )
        assert created_2 is False
        assert second_id == first_id
        assert repo.get_vaga_description(first_id) == revised_jd

        with get_db_connection(repo.db_path) as conn:
            desc_row = conn.execute(
                "SELECT content_hash, description_clean FROM vaga_descricoes WHERE vaga_id = ?",
                (first_id,),
            ).fetchone()
            assert desc_row["content_hash"] == compute_content_hash(revised_jd)
            assert desc_row["description_clean"] == "Clean V2"

            vaga_row = conn.execute(
                "SELECT updated_at FROM vagas WHERE id = ?",
                (first_id,),
            ).fetchone()
            assert vaga_row["updated_at"] != "2020-01-01 00:00:00"

        # Passing an empty description on a subsequent collision must NOT wipe the stored description
        third_id, created_3 = repo.insert_vaga(vaga, "")
        assert created_3 is False
        assert third_id == first_id
        assert repo.get_vaga_description(first_id) == revised_jd


class TestListAndLifecycle:
    def test_list_vagas_filtering_and_pagination(
        self, repo: CareerOpsRepository
    ) -> None:
        ids: list[str] = []
        for idx in range(5):
            v_id, _ = repo.insert_vaga(
                VagaInput(
                    original_url=f"https://boards.greenhouse.io/co/jobs/{idx}",
                    company=f"Company {idx}",
                    role="Data Engineer",
                    source_portal="greenhouse",
                ),
                f"Description {idx}",
            )
            ids.append(v_id)

        repo.update_lifecycle(ids[0], status="evaluated", score=4.2)
        repo.update_lifecycle(ids[1], status="applied", score=4.8)
        repo.update_lifecycle(ids[2], status="discarded", score=2.0)

        queued = repo.list_vagas(status="queued")
        assert [r["id"] for r in queued] == [ids[3], ids[4]]

        evaluated = repo.list_vagas(status="evaluated")
        assert [r["id"] for r in evaluated] == [ids[0]]

        applied = repo.list_vagas(status="applied")
        assert [r["id"] for r in applied] == [ids[1]]

        triaged = repo.list_vagas(status="triaged")
        assert {r["id"] for r in triaged} == {ids[0], ids[1], ids[2]}

        page_1 = repo.list_vagas(limit=2, offset=0)
        page_2 = repo.list_vagas(limit=2, offset=2)
        assert [r["id"] for r in page_1] == [ids[0], ids[1]]
        assert [r["id"] for r in page_2] == [ids[2], ids[3]]

    def test_update_lifecycle_upserts_and_preserves_existing_fields(
        self, repo: CareerOpsRepository
    ) -> None:
        v_id, _ = repo.insert_vaga(
            VagaInput(
                original_url="https://boards.greenhouse.io/anthropic/jobs/42",
                company="Anthropic",
                role="Research Engineer",
                source_portal="greenhouse",
            ),
            "Research JD",
        )

        # Step 1: Evaluate
        eval_state = repo.update_lifecycle(
            v_id,
            status="evaluated",
            score=4.7,
            archetype="AI Platform",
            report_path="workspace/reports/report_042.md",
            notes="Strong match",
        )
        assert eval_state["status_triagem"] == "triaged"
        assert eval_state["status"] == "evaluated"
        assert eval_state["score"] == 4.7
        assert eval_state["archetype"] == "AI Platform"
        assert eval_state["report_path"] == "workspace/reports/report_042.md"
        assert eval_state["cv_pdf_path"] is None

        # Step 2: Apply and attach CV PDF (preserving score, archetype, report_path)
        applied_state = repo.update_lifecycle(
            v_id,
            status="applied",
            application_date="2026-10-30",
            cv_pdf_path="workspace/output/042_resume.pdf",
        )
        assert applied_state["status"] == "applied"
        assert applied_state["score"] == 4.7
        assert applied_state["archetype"] == "AI Platform"
        assert applied_state["report_path"] == "workspace/reports/report_042.md"
        assert applied_state["cv_pdf_path"] == "workspace/output/042_resume.pdf"
        assert applied_state["application_date"] == "2026-10-30"

        # Step 3: Calling with lower active rank ('evaluated') does not downgrade 'applied'
        no_downgrade = repo.update_lifecycle(
            v_id,
            status="evaluated",
            notes="Updated notes without downgrading status",
        )
        assert no_downgrade["status"] == "applied"
        assert no_downgrade["notes"] == "Updated notes without downgrading status"

        # Step 4: Terminal exit states ('rejected', 'discarded') are allowed from any active stage
        rejected_state = repo.update_lifecycle(v_id, status="rejected")
        assert rejected_state["status"] == "rejected"

    def test_update_lifecycle_validation_errors(
        self, repo: CareerOpsRepository
    ) -> None:
        with pytest.raises(KeyError, match="does not exist"):
            repo.update_lifecycle("vaga_missing", status="evaluated")

        v_id, _ = repo.insert_vaga(
            VagaInput(
                original_url="https://boards.greenhouse.io/test/jobs/1",
                company="Test",
                role="Engineer",
                source_portal="greenhouse",
            ),
            "JD",
        )
        with pytest.raises(ValueError, match="Invalid lifecycle status"):
            repo.update_lifecycle(v_id, status="invalid_state")


class TestStatsBackupAndWrappers:
    def test_get_pipeline_stats(self, repo: CareerOpsRepository) -> None:
        empty_stats = repo.get_pipeline_stats()
        assert empty_stats == {"total": 0, "by_status": {}, "avg_score": None}

        v1, _ = repo.insert_vaga(
            VagaInput("https://example.com/1", "Co1", "R1", "gh"), "JD1"
        )
        v2, _ = repo.insert_vaga(
            VagaInput("https://example.com/2", "Co2", "R2", "gh"), "JD2"
        )
        v3, _ = repo.insert_vaga(
            VagaInput("https://example.com/3", "Co3", "R3", "gh"), "JD3"
        )

        repo.update_lifecycle(v1, status="evaluated", score=4.0)
        repo.update_lifecycle(v2, status="applied", score=4.5)

        stats = repo.get_pipeline_stats()
        assert stats["total"] == 3
        assert stats["by_status"] == {
            "evaluated": 1,
            "applied": 1,
            "queued": 1,
        }
        assert stats["avg_score"] == 4.25

    def test_backup_db_and_module_level_wrappers(self, tmp_path: Path) -> None:
        db_path = tmp_path / "data" / "career_ops.db"
        v_id, created = insert_vaga(
            VagaInput("https://example.com/job/10", "ModCo", "Platform Eng", "lever"),
            "Module wrapper JD",
            db_path=db_path,
        )
        assert created is True
        assert get_vaga(v_id, db_path=db_path) is not None
        assert get_vaga_description(v_id, db_path=db_path) == "Module wrapper JD"

        update_lifecycle(v_id, status="interview", score=4.9, db_path=db_path)
        rows = list_vagas(status="interview", db_path=db_path)
        assert len(rows) == 1
        assert rows[0]["id"] == v_id

        stats = get_pipeline_stats(db_path=db_path)
        assert stats["total"] == 1
        assert stats["by_status"] == {"interview": 1}
        assert stats["avg_score"] == 4.9

        repo = CareerOpsRepository(db_path=db_path)
        backup_file = repo.backup_db(backup_dir=tmp_path / "backups")
        assert backup_file.exists()

        backup_repo = CareerOpsRepository(db_path=backup_file, auto_init=False)
        assert backup_repo.get_vaga(v_id) is not None


class TestSequentialIndexing:
    def test_seq_num_incremental_assignment(self, repo: CareerOpsRepository) -> None:
        v1 = VagaInput("https://boards.greenhouse.io/co/1", "Co A", "Role 1", "greenhouse")
        v2 = VagaInput("https://boards.greenhouse.io/co/2", "Co B", "Role 2", "greenhouse")
        v3 = VagaInput("https://boards.greenhouse.io/co/3", "Co C", "Role 3", "greenhouse")

        id1, _ = repo.insert_vaga(v1, "JD 1")
        id2, _ = repo.insert_vaga(v2, "JD 2")
        id3, _ = repo.insert_vaga(v3, "JD 3")

        rec1 = repo.get_vaga(id1)
        rec2 = repo.get_vaga(id2)
        rec3 = repo.get_vaga(id3)

        assert rec1 is not None and rec1["seq_num"] == 1
        assert rec2 is not None and rec2["seq_num"] == 2
        assert rec3 is not None and rec3["seq_num"] == 3

        all_vagas = repo.list_vagas()
        assert [v["seq_num"] for v in all_vagas] == [1, 2, 3]

    def test_duplicate_url_preserves_seq_num(self, repo: CareerOpsRepository) -> None:
        v1 = VagaInput("https://boards.greenhouse.io/co/same", "Co A", "Role 1", "greenhouse")
        id1, created1 = repo.insert_vaga(v1, "Initial JD")
        assert created1 is True

        v2 = VagaInput("https://boards.greenhouse.io/co/same?ref=extra", "Co A", "Role 1 Updated", "greenhouse")
        id2, created2 = repo.insert_vaga(v2, "Updated JD")
        assert created2 is False
        assert id1 == id2

        rec = repo.get_vaga(id1)
        assert rec is not None and rec["seq_num"] == 1

    def test_polymorphic_resolution_and_lookup(self, repo: CareerOpsRepository) -> None:
        v1 = VagaInput("https://boards.greenhouse.io/co/lookup", "Lookup Co", "Platform Lead", "greenhouse")
        id1, _ = repo.insert_vaga(v1, "Platform Description")

        # Resolve via integer
        assert repo.resolve_vaga_id(1) == id1
        # Resolve via zero-padded string
        assert repo.resolve_vaga_id("001") == id1
        # Resolve via cardinal prefix
        assert repo.resolve_vaga_id("#1") == id1
        assert repo.resolve_vaga_id("#001") == id1
        # Resolve via canonical hash
        assert repo.resolve_vaga_id(id1) == id1
        # Non-existent
        assert repo.resolve_vaga_id(999) is None
        assert repo.resolve_vaga_id("non_existent") is None

        # get_vaga by seq_num
        row_by_num = repo.get_vaga(1)
        assert row_by_num is not None
        assert row_by_num["id"] == id1

        row_by_str_num = repo.get_vaga("001")
        assert row_by_str_num is not None
        assert row_by_str_num["id"] == id1

        # get_vaga_description by seq_num
        desc = repo.get_vaga_description(1)
        assert desc == "Platform Description"

        # update_lifecycle using seq_num
        updated = repo.update_lifecycle(1, status="interview", score=4.7)
        assert updated["id"] == id1
        assert updated["status"] == "interview"
        assert updated["score"] == 4.7
