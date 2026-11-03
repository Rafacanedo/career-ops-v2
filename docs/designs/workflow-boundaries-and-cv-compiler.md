# Career-Ops Workflow Boundaries, Deterministic Evaluation & Native CV Compiler

* **Author:** Rafa Canedo & Antigravity Swarm Architecture
* **Status:** Approved
* **Date:** 2026-11-01

--------------------------------------------------------------------------------

## Overview

This technical design specifies the architecture for Career-Ops v2 workflow boundaries, deterministic evaluation scoring, relational story bank indexing, and a native Python-driven CV compilation engine (`career_ops.render`). 

The architecture strictly delineates tasks between deterministic Python code (data ingestion, ATS APIs, relational SQLite storage, Pydantic validation, formulaic scoring, and Playwright PDF compilation) and AI agent skills (semantic gap analysis, ATS keyword adaptation, and STAR+R coaching). It eliminates uncommitted Node.js dependencies, replaces brittle HTML string-replacement templating with schema-validated Jinja2 templates, and introduces programmatic DOM overflow telemetry to guarantee ATS-optimized single-page PDF resumes.

--------------------------------------------------------------------------------

## The Problem

The existing Career-Ops architecture exhibits five critical friction points:

1. **Non-Deterministic Score Drift**: When AI agents directly calculate a numerical 1.0–5.0 score for a job posting, the assigned score drifts by 0.5–1.0 points across identical runs due to LLM stochastic variations. Hard blockers (e.g., non-negotiable on-site location requirements) are inconsistently penalized.
2. **Runtime Dependency Friction & Missing Scripts**: CV PDF generation in v1 relied on `node generate-pdf.mjs`, which is not committed to the repository and forces a Python project to maintain a separate Node/npm runtime environment.
3. **Template Fragility & Tag Injection**: Resume generation relied on agents performing raw regex/string replacement on `cv-template.html` (`{{EXPERIENCE}}`, `{{SKILLS}}`). LLMs frequently generate broken HTML tags, unclosed `<div>` elements, and unescaped ampersands (`&`), breaking document styling.
4. **Undetected Page Spillover**: Previous tools lacked pagination checks. If tailored bullet points exceeded printable page dimensions, headless print engines silently produced a 2-page PDF with an orphaned trailing page, ruining recruiter presentation.
5. **Windows Shell Argument Truncation**: Passing complex structured JSON directly via CLI command flags (`--data '{"skills": ...}'`) fails in Windows PowerShell due to argument length limits and quotation escaping rules.
6. **Story Bank Context Bloat**: Storing all behavioral STAR+R stories in a monolithic markdown file (`content/story-bank.md`) wastes thousands of context tokens when an agent only needs 2–3 relevant stories for a specific interview prep or application question.

--------------------------------------------------------------------------------

## Goals

* **Python-Native CV Compiler (`career_ops.render`)**: Replace external Node.js scripts with a pure Python Playwright engine (`playwright`) that compiles Jinja2 HTML templates into ATS-compliant PDFs.
* **Strict Pydantic Schema Validation**: Require all tailored CV data to validate against a Pydantic model (`CVPayload`) before rendering, enforcing character limits and section constraints.
* **Programmatic DOM Overflow Telemetry**: Implement a headless browser DOM measurement script that accounts for print margins and verifies `document.body.scrollHeight <= printableMaxHeight`. If content overflows, halt generation with exit code `2` and emit structured JSON telemetry specifying exact section heights and line-excess estimates.
* **Deterministic Categorical Evaluation**: Agent outputs categorical ratings (`cv_match`, `level_alignment`, `comp_alignment`, `cultural_signals`, `strategic_alignment`) and blocker flags; Python executes a weighted scoring formula and enforces a hard blocker cap (`BLOCKER_SCORE_CAP = 3.2`).
* **Robust File-Based IPC**: Implement structured payload exchange via `workspace/staging/` with ephemeral cleanup upon successful database commit.
* **Story Bank Context Retrieval**: Provide a lightweight markdown parser and lookup engine for `content/story-bank.md`, enabling token-efficient tag-based retrieval via CLI without multi-table sync complexity.
* **Cross-Platform Path Normalization**: Normalize local font and asset paths using standard `pathlib.Path.resolve().as_uri()` to ensure reliable rendering on Windows, macOS, and Linux.

--------------------------------------------------------------------------------

## Non-Goals

* **Multi-Page Resumes**: Career-Ops explicitly targets dense, high-impact 1-page resumes. Multi-page document layout is out of scope.
* **Automated Web Form Submission**: The system will not attempt browser automation to fill and submit job applications on third-party ATS platforms. The agent acts purely in an advisory capacity.
* **Direct Reverse PDF Parsing (OCR)**: The CLI will not implement in-band OCR or PDF reverse-parsing. ATS parseability is guaranteed structurally via single-column semantic HTML and vector text layer output.

--------------------------------------------------------------------------------

## Critical User Journeys (CUJs)

### CUJ 1: Feed Triage & Deterministic Ingestion
* **Given**: A configured list of companies in `registry/companies.yml`.
* **When**: The user or agent executes `career-ops fetch`.
* **Then**: The Python core queries ATS REST endpoints, deduplicates entries in SQLite, and `career-ops list --status queued --limit 10` returns compact JSON/tabular rows under 250 tokens for the agent to review.

### CUJ 2: Agentic Categorical Evaluation & Formula Scoring
* **Given**: A queued job opportunity with ID `vaga_042`.
* **When**: The agent retrieves the full description via `career-ops show vaga_042`, performs gap analysis, writes `workspace/staging/eval_vaga_042.json`, and invokes `career-ops evaluate vaga_042 --file workspace/staging/eval_vaga_042.json`.
* **Then**: The CLI validates the payload, applies the deterministic weighting formula, caps the score at `3.2` if blockers or `cultural_signals: "red_flags"` exist, commits the result (including `archetype` and `report_path`) to `tracking_lifecycle`, and cleans up the staging file.

### CUJ 3: Tailored CV Compilation with DOM Overflow Diagnostics
* **Given**: A high-fit job (`score >= 4.0`) requiring a tailored resume.
* **When**: The agent selects and reformulates bullets, stages `workspace/staging/cv_vaga_042.json`, and invokes `career-ops cv render --payload workspace/staging/cv_vaga_042.json --out workspace/output/vaga_042_resume.pdf --format a4`.
* **Case A (Within Budget)**: Playwright emulates print media, confirms `scrollHeight <= printableHeight` (1064.9px for A4 with 0.3in margins), writes the vector PDF with standard text layer, registers the path in SQLite, and exits 0.
* **Case B (Overflow)**: Content exceeds printableHeight. Compiler raises `CVOverflowError`, and CLI halts compilation, exits with code `2`, and returns telemetry JSON (`{"status": "overflow", "overflow_px": 38, "sections": {"summary": 120, "experience": 750, ...}, "estimated_line_excess": 2}`). The agent reads the telemetry, trims the flagged bullet, and re-invokes the command successfully.

### CUJ 4: Story Bank Lookup & Targeted Context Retrieval
* **Given**: The user maintains `content/story-bank.md` with STAR+R stories tagged with competencies.
* **When**: The agent runs `career-ops stories list --tag distributed-systems --limit 2`.
* **Then**: The CLI reads the markdown file, filters matching stories by tag, and returns only the 2 relevant stories in compact JSON format (< 300 tokens).

--------------------------------------------------------------------------------

## Technical Plan (Architecture)

### Architectural Diagram

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   AI AGENT HARNESS (Skills Layer)                     │
│  • /career-ops-evaluate: Semantic gap analysis & categorical rating    │
│  • /career-ops-cv: Bullet prioritization & ATS keyword rephrasing      │
│  • /career-ops-interview-prep: STAR+R behavioral simulation            │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │ Writes Staged JSON             │ Queries Compact Rows
                    ▼                                ▼
┌───────────────────────────────────────┐  ┌─────────────────────────────┐
│  workspace/staging/                   │  │  career-ops CLI             │
│  • eval_<id>.json                     │  │  • list / show              │
│  • cv_<id>.json                       │  │  • stories list --tag <tag> │
└───────────────────┬───────────────────┘  └──────────────┬──────────────┘
                    │ Consumes Payload                    │ Reads/Writes
                    ▼                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   PYTHON CORE (career_ops)                             │
│                                                                        │
│  ┌──────────────────────┐  ┌─────────────────┐  ┌───────────────────┐  │
│  │ Pydantic Schemas     │  │ Formula Scoring │  │ SQLite Database   │  │
│  │ • CVPayload          │  │ • eval/scoring  │  │ • vagas           │  │
│  │ • EvaluationPayload  │  │ • Cap = 3.2     │  │ • tracking_life.. │  │
│  └──────────┬───────────┘  └─────────────────┘  └───────────────────┘  │
│             │                                                          │
│             ▼                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ CV Compiler (career_ops.render)                                  │  │
│  │ 1. Jinja2 Templating: assets/templates/ats_clean.html            │  │
│  │ 2. Playwright Headless Chromium Engine (sync_playwright)         │  │
│  │ 3. Print Media Emulation & DOM Height Telemetry                  │  │
│  │ 4. Exit Code 2 & CVOverflowError on Page Overflow                │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
└─────────────────────────────────────┼──────────────────────────────────┘
                                      │ Emits Single-Page PDF
                                      ▼
                      ┌───────────────────────────────┐
                      │ workspace/output/<id>_cv.pdf  │
                      └───────────────────────────────┘
```

---

### Component Breakdown

#### 1. Schemas (`src/career_ops/schemas/`)

* **`src/career_ops/schemas/cv.py`**:
  ```python
  from pydantic import BaseModel, Field
  from typing import Literal, Optional, Dict, List

  class ContactInfo(BaseModel):
      email: str
      phone: Optional[str] = None
      location: str
      linkedin_url: str
      portfolio_url: Optional[str] = None

  class WorkRole(BaseModel):
      company: str
      role: str
      location: str
      start_date: str
      end_date: str
      bullets: List[str] = Field(..., max_length=8)

  class EducationEntry(BaseModel):
      institution: str
      degree: str
      year: str
      location: Optional[str] = None
      details: Optional[str] = None

  class ProjectEntry(BaseModel):
      name: str
      description: str
      technologies: List[str] = Field(default_factory=list)
      url: Optional[str] = None

  class CVPayload(BaseModel):
      format: Literal["a4", "letter"] = "a4"
      lang: Literal["en", "pt-br"] = "en"
      name: str = Field(..., max_length=100)
      headline: str = Field(..., max_length=120)
      contact: ContactInfo
      summary: str = Field(..., max_length=650)
      experience: List[WorkRole] = Field(..., max_length=4)
      skills: Dict[str, List[str]]
      education: List[EducationEntry] = Field(default_factory=list)
      projects: List[ProjectEntry] = Field(default_factory=list)
  ```

* **`src/career_ops/schemas/eval.py`**:
  ```python
  from pydantic import BaseModel, Field
  from typing import Literal, List, Optional

  class EvaluationPayload(BaseModel):
      vaga_id: str
      cv_match: Literal["exact", "high", "medium", "low"]
      level_alignment: Literal["stretch", "target", "overqualified"]
      comp_alignment: Literal["above_range", "in_range", "below_range", "unverified"]
      cultural_signals: Literal["positive", "neutral", "red_flags"]
      strategic_alignment: Literal["north_star", "adjacent", "distraction"]
      blockers: List[str] = Field(default_factory=list)
      archetype: Optional[str] = None
      report_path: Optional[str] = None
      notes: Optional[str] = None
  ```

#### 2. Deterministic Scoring Engine (`src/career_ops/eval/scoring.py`)
* **Blocker Cap Constant**: `BLOCKER_SCORE_CAP = 3.2`
* **Dimension Scores**:
  * `cv_match`: `exact`=5.0, `high`=4.5, `medium`=3.0, `low`=1.5
  * `strategic_alignment`: `north_star`=5.0, `adjacent`=3.5, `distraction`=1.0
  * `level_alignment`: `target`=5.0, `stretch`=4.0, `overqualified`=3.0
  * `comp_alignment`: `above_range`=5.0, `in_range`=4.5, `unverified`=3.5, `below_range`=1.0
* **Weights**: CV Match (40%), Strategic Alignment (25%), Level Alignment (20%), Comp Alignment (15%).
* **Cultural Signals & Blocker Rule**:
  * If `payload.cultural_signals == "red_flags"`, a blocker `"Cultural red flags detected"` is automatically appended.
  * If `len(payload.blockers) > 0`, the final score is capped: `min(weighted_score, BLOCKER_SCORE_CAP)`.
  * Score is rounded to 2 decimal places: `round(score, 2)`.

#### 3. Native CV Compiler (`src/career_ops/render/compiler.py`)
* Coordinates Jinja2 template loading, path normalization, and Playwright execution using `sync_playwright`.
* **Print Area Calculation**:
  * Margin: `0.3in` top, bottom, left, right.
  * Vertical Margins Total: `0.6in = 15.24mm`.
  * A4 paper height: `297mm`. Printable height: `281.76mm`.
  * Letter paper height: `279.4mm`. Printable height: `264.16mm`.
  * `max_printable_px = printable_height_mm * 3.7795275591`.
* **Execution Flow**:
  1. Ensures Playwright Chromium is provisioned.
  2. Resolves template from `assets/templates/ats_clean.html`.
  3. Prepares HTML with asset URIs using `pathlib.Path(p).resolve().as_uri()`.
  4. Launches browser, sets viewport to printable width (`794px`), loads HTML.
  5. Emulates print media: `page.emulate_media(media="print")`.
  6. Awaits font readiness: `page.evaluate("() => document.fonts.ready")`.
  7. Evaluates DOM height:
     ```javascript
     (maxHeightPx) => {
       const bodyHeight = document.body.scrollHeight;
       const sections = {};
       document.querySelectorAll('[data-section]').forEach(el => {
         sections[el.getAttribute('data-section')] = Math.round(el.offsetHeight);
       });
       return {
         body_height_px: Math.round(bodyHeight),
         max_height_px: Math.round(maxHeightPx),
         is_overflow: bodyHeight > maxHeightPx,
         overflow_px: Math.max(0, Math.round(bodyHeight - maxHeightPx)),
         section_heights: sections
       };
     }
     ```
  8. If `is_overflow` is `True`:
     * Computes `estimated_line_excess = math.ceil(overflow_px / 18.0)`.
     * Raises `CVOverflowError(telemetry)`.
  9. If within budget:
     * Generates PDF with `page.pdf(path=str(out_path), format=format, print_background=True, prefer_css_page_size=True, margin={"top": "0.3in", "bottom": "0.3in", "left": "0.3in", "right": "0.3in"})`.
     * Returns `RenderResult(pdf_path=out_path, format=format, page_count=1)`.

#### 4. Semantic Jinja2 Template (`assets/templates/ats_clean.html`)
* Single-column, linear reading order.
* Standard typography with system fallbacks (`Arial, Helvetica, sans-serif`).
* Explicit print styling:
  ```css
  @page {
    size: {{ format }};
    margin: 0.3in;
  }
  body {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 9.5pt;
    line-height: 1.35;
    color: #111;
  }
  ```
* Mandatory tagged sections: `header`, `summary`, `experience`, `skills`, `education`, `projects`.

#### 5. Streamlined Story Bank (`src/career_ops/stories/`)
* Reads `content/story-bank.md` containing STAR+R stories structured with markdown headers:
  ```markdown
  ## Story: Migrating Distributed Event Bus
  **Tags:** distributed-systems, kafka, incident-response
  
  ### Situation
  ...
  ### Task
  ...
  ### Action
  ...
  ### Result
  ...
  ```
* Parser extracts stories into dataclass `Story(title, tags, situation, task, action, result, reflection)`.
* CLI command `career-ops stories list --tag <tag> [--limit 3]` returns matching stories in compact JSON.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

### Target Files to Create/Modify

#### 1. `pyproject.toml` (Modify)
* **Scope**: Build Configuration & Dependencies
* **Proposed Changes**: Add `pydantic>=2.0`, `jinja2>=3.1`, and `playwright>=1.40` to project dependencies.

#### 2. `src/career_ops/schemas/cv.py` (Create)
* **Scope**: Pydantic Domain Schema
* **Proposed Changes**: Implement `CVPayload`, `WorkRole`, `EducationEntry`, `ProjectEntry`, `ContactInfo`.

#### 3. `src/career_ops/schemas/eval.py` (Create)
* **Scope**: Pydantic Domain Schema
* **Proposed Changes**: Implement `EvaluationPayload` with `vaga_id`, categorical ratings, `archetype`, and `report_path`.

#### 4. `src/career_ops/eval/scoring.py` (Create)
* **Scope**: Evaluation Business Logic
* **Proposed Changes**: Implement `calculate_score(payload: EvaluationPayload) -> tuple[float, list[str]]` with `BLOCKER_SCORE_CAP = 3.2` and `"red_flags"` handling.

#### 5. `src/career_ops/render/compiler.py` (Create)
* **Scope**: PDF Rendering Core
* **Proposed Changes**: Implement `compile_cv(payload: CVPayload, out_path: Path, format: str = "a4") -> RenderResult` with `CVOverflowError`, print media emulation, and DOM measurement.

#### 6. `assets/templates/ats_clean.html` (Create)
* **Scope**: Jinja2 HTML/CSS Template
* **Proposed Changes**: Implement semantic, single-column print template with `data-section` attributes and system typography.

#### 7. `src/career_ops/stories/parser.py` (Create)
* **Scope**: Story Bank Markdown Reader
* **Proposed Changes**: Implement markdown parser and tag filter for `content/story-bank.md`.

#### 8. `src/career_ops/cli.py` (Modify)
* **Scope**: CLI Interface Layer
* **Proposed Changes**: Register commands:
  * `career-ops cv render --payload <path> --out <path> [--format a4]`
  * `career-ops evaluate <vaga_id> --file <eval_file>`
  * `career-ops stories list [--tag <tag>] [--limit 3]`

#### 9. `tests/test_scoring.py` (Create)
* **Scope**: Unit Tests
* **Proposed Changes**: Test formula weighting, category values, and blocker capping rules.

#### 10. `tests/test_stories.py` (Create)
* **Scope**: Unit Tests
* **Proposed Changes**: Test markdown parsing and tag filtering.

#### 11. `tests/test_cv_compiler.py` (Create)
* **Scope**: Unit & Integration Tests
* **Proposed Changes**: Test schema validation, Jinja2 rendering, overflow detection (`CVOverflowError`), and successful PDF compilation.

--------------------------------------------------------------------------------

## Verification Plan

* **Unit Tests**:
  * Execute `pytest tests/test_scoring.py` to verify deterministic score calculation and blocker caps.
  * Execute `pytest tests/test_stories.py` to verify markdown parsing and tag filtering.
* **Compiler Integration Tests**:
  * Execute `pytest tests/test_cv_compiler.py`:
    1. Validate Pydantic rejection on invalid schema.
    2. Validate `CVOverflowError` and telemetry payload when content exceeds page height.
    3. Validate valid single-page PDF generation on compliant payload.
* **Full CLI Verification**:
  * Run `career-ops evaluate vaga_042 --file workspace/staging/eval_sample.json` and verify DB status update.
  * Run `pytest` across all project tests to ensure zero regressions.

--------------------------------------------------------------------------------

*Drafted with EGM*
