"""
models.py — Dataclasses for career-ops data structures.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VagaInput:
    original_url: str
    company: str
    role: str
    source_portal: str
    canonical_url: str | None = None
    company_norm: str | None = None
    role_norm: str | None = None
    location: str | None = None
    remote_type: str | None = None


@dataclass
class Vaga(VagaInput):
    id: str = ""
    seq_num: int | None = None
    status_triagem: str = "queued"
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class VagaDescricao:
    vaga_id: str
    description_raw: str
    content_hash: str
    description_clean: str | None = None
    fetched_at: str | None = None


@dataclass
class TrackingLifecycle:
    vaga_id: str
    status: str = "evaluated"
    score: float | None = None
    archetype: str | None = None
    application_date: str | None = None
    status_updated_at: str | None = None
    report_path: str | None = None
    cv_pdf_path: str | None = None
    notes: str | None = None
