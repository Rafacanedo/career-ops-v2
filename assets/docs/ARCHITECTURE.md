# Architecture Overview

For the complete technical specification and design document, see [Decoupled SQLite Relational Architecture & Storage Boundary](../../docs/designs/decoupled-sqlite-architecture.md).

## System Overview

Career-Ops v2 coordinates four primary layers across a strict boundary between a deterministic Python CLI core and the AI agent harness:

```text
[Public ATS APIs / MCP Servers / URL Intake]
                     │
                     ▼
           career-ops CLI (Python)
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
  Local SQLite Database     Human Deliverables
  (data/career_ops.db)      (output/ & reports/)
  - vagas                   - output/cv/{seq}-{role}-{company}.pdf
  - vaga_descricoes         - output/reports/{seq}-{role}-{company}.md
  - tracking_lifecycle      - output/dashboard.html
```

## Storage Layers

1. **Embedded Relational State (`data/career_ops.db`)**:
   - `vagas`: Fast metadata indexed by `id`, `seq_num`, and `canonical_url`.
   - `vaga_descricoes`: Isolated full-text JD payloads with SHA-256 content deduplication.
   - `tracking_lifecycle`: Application status, fit scores, archetype, notes, and artifact paths.

2. **Local Deliverables & Artifacts (`output/`)**:
   - `output/cv/`: Tailored, ATS-optimized single-page PDF resumes compiled with Playwright.
   - `output/reports/`: In-depth qualitative evaluation reports and gap analysis.
   - `output/dashboard.html`: Standalone interactive HTML dashboard.

3. **User Identity & Experience (`content/` and `config/`)**:
   - `config/profile.yml`: Single source of truth for candidate identity, contact info, and target roles (git-ignored).
   - `content/cv.md`: Full canonical resume history and experience (git-ignored).
   - `content/story-bank.md`: Structured STAR+R interview story catalog (git-ignored).
