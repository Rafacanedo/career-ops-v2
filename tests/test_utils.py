"""
test_utils.py — Unit tests for shared utilities including slugify_token.
"""

from __future__ import annotations

import pytest

from career_ops.utils import (
    build_cv_filename,
    build_deliverable_slugs,
    build_report_filename,
    slugify_token,
)


class TestSlugifyToken:
    def test_basic_slug(self) -> None:
        assert slugify_token("Senior Data Engineer") == "senior-data-engineer"
        assert slugify_token("Nubank") == "nubank"

    def test_unicode_accents_and_diacritics(self) -> None:
        assert slugify_token("São Paulo Tech") == "sao-paulo-tech"
        assert slugify_token("Líder Técnico & Soluções") == "lider-tecnico-and-solucoes"
        assert slugify_token("Itaú Unibanco") == "itau-unibanco"

    def test_tech_keywords_mapping(self) -> None:
        assert slugify_token("C++ Software Engineer") == "cpp-software-engineer"
        assert slugify_token("Senior C# Developer") == "senior-csharp-developer"
        assert slugify_token(".NET Core Lead") == "dotnet-core-lead"
        assert slugify_token("CI/CD & DevOps") == "ci-cd-and-devops"
        assert slugify_token("Data/Analytics Architect") == "data-analytics-architect"

    def test_special_characters_and_whitespace_collapse(self) -> None:
        assert slugify_token("  Lead @ Architecture (Cloud)  ") == "lead-at-architecture-cloud"
        assert slugify_token("Role---with---dashes") == "role-with-dashes"
        assert slugify_token("Quotes \"and\" 'symbols'! #1") == "quotes-and-symbols-1"

    def test_length_capping(self) -> None:
        long_role = "Senior Staff Principal Distributed Systems & Cloud Infrastructure Data Platform Architect"
        slug = slugify_token(long_role, max_len=40)
        assert len(slug) <= 40
        assert not slug.endswith("-")
        assert not slug.startswith("-")

    def test_empty_and_fallback(self) -> None:
        assert slugify_token("") == "item"
        assert slugify_token(None) == "item"
        assert slugify_token("   ") == "item"
        assert slugify_token("!#$%^*()") == "item"
        assert slugify_token("@") == "at"
        assert slugify_token("&") == "and"


class TestDeliverableFilenames:
    def test_build_deliverable_slugs(self) -> None:
        r_slug, c_slug = build_deliverable_slugs("Senior AI Engineer", "Factored")
        assert r_slug == "senior-ai-engineer"
        assert c_slug == "factored"

    def test_build_report_filename(self) -> None:
        fname = build_report_filename(62, "Senior AI Engineer", "Factored")
        assert fname == "062-senior-ai-engineer-factored.md"

        fname_single = build_report_filename(3, "Data Engineer", "Artefact")
        assert fname_single == "003-data-engineer-artefact.md"

    def test_build_cv_filename(self) -> None:
        cv_name = build_cv_filename(62, "rafael", "Senior AI Engineer", "Factored")
        assert cv_name == "062-rafael-senior-ai-engineer-factored.pdf"
