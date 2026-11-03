# Career-Ops Standardized ATS Resume Output Directory (`output/cv/`)

* **Author:** Rafa Canedo & Antigravity Swarm Architecture
* **Status:** Approved
* **Date:** 2026-11-01

--------------------------------------------------------------------------------

## Overview

This technical design specifies the isolation of all generated ATS resume PDFs into a dedicated top-level `./output/cv/` directory in Career-Ops v2. It complements the human-readable sequential naming convention (`{seq:03d}-rafael-{role_slug}-{company_slug}.pdf`), updates pipeline agent skills to eliminate hardcoded path overrides, establishes project-relative paths in SQLite, and provides an idempotent migration strategy for legacy artifacts.

--------------------------------------------------------------------------------

## Architectural Decisions

1. **Dedicated Deliverables Partition (`output/cv/`)**:
   - `workspace/` remains internal scratch space for staging JSON payloads (`workspace/staging/`) and evaluation markdown reports (`workspace/reports/`).
   - Final ATS resume deliverables are generated in `./output/cv/` at the repository root.
   - `.gitignore` already ignores `output/` and `*.pdf`, guaranteeing safety from accidental Git commits.

2. **Centralized Directory Resolution**:
   - `src/career_ops/config.py` provides `get_cv_output_dir(root: Path) -> Path`, ensuring directory existence on demand (`root / "output" / "cv"`).
   - `src/career_ops/cv.py` automatically routes PDF compilation to `get_cv_output_dir(ctx.root)` when `--out` is omitted and `--vaga-id` is provided.

3. **Relative Database Artifact Paths**:
   - SQLite table `tracking_lifecycle.cv_pdf_path` records project-relative POSIX strings (e.g., `output/cv/062-rafael-senior-ai-engineer-factored.pdf`).
   - `career-ops verify` resolves paths against `ctx.root`, ensuring portability across machines, OS platforms, and CI runners.

4. **Agent Skill Modernization**:
   - `.agents/skills/career-ops-pipeline/SKILL.md` and `.agents/skills/career-ops-cv/SKILL.md` delegate destination derivation entirely to the CLI, omitting `--out`.

5. **Legacy File & Database Migration**:
   - Existing disk artifacts such as `workspace/output/vaga_1a1986e8a5e_76ef95_resume.pdf` are migrated to `output/cv/062-rafael-senior-ai-engineer-factored.pdf`.
   - `tracking_lifecycle.cv_pdf_path` is updated to match.
