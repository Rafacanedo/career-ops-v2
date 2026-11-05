# Career-Ops v2 🚀

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Architecture: SQLite WAL](https://img.shields.io/badge/architecture-local--first%20SQLite-green.svg)](docs/designs/decoupled-sqlite-architecture.md)

A local-first, AI-assisted job hunting co-pilot and pipeline management system. Career-Ops v2 pairs a fast, deterministic Python/SQLite core with agentic AI workflows to automate the tedious parts of your job hunt: discovering opportunities, evaluating real profile fit, generating tailored single-page ATS resumes, and preparing for interviews—all while keeping your personal data completely private on your machine.

---

## 💡 Why Career-Ops?

Searching for tech roles (Engineering, Data, AI/ML, Product) is often fragmented and time-consuming:
- Tracking dozens of openings across disjointed platforms (Greenhouse, Lever, Ashby, Workable, Gupy, etc.).
- Manually rewriting resumes for ATS algorithms without accidentally hallucinating qualifications.
- Spending hours applying to roles that turn out to be poor fits in seniority or tech stack.
- Overloading AI context windows with massive spreadsheet dumps and markdown tables.

**Career-Ops v2 solves this with a clean, decoupled architecture:**
- 📥 **Automated Ingestion**: Fetch postings directly from public ATS REST APIs and Model Context Protocol (MCP) servers straight into a local SQLite database—zero brittle web scrapers and zero token costs.
- 🎯 **Objective Fit Evaluation**: Evaluates job descriptions against your real resume, calculates an objective 1–5 fit score, and detects requirements gaps before you spend time applying.
- 📄 **ATS-Optimized 1-Page PDF Resumes**: Generates clean, single-page, ATS-parseable PDF resumes tailored to the job description's keywords using Playwright and HTML/CSS templates.
- 🎤 **STAR+R Interview Prep**: Surfaces targeted behavioral and technical questions, matching them with stories from your personal career story bank.
- 🔒 **100% Private & Local-First**: Your CV, target salaries, applications, and confidential notes live in a local SQLite database (`data/career_ops.db`) and are strictly git-ignored.
- ⚡ **Context-Window Efficient**: Built specifically for AI coding assistants (Google Antigravity, Claude Code, Gemini CLI, Cursor). The CLI returns compact metadata payloads (<250 tokens), preventing context bloat.

---

## 🔄 The 4-Step Workflow

```text
  1. INGEST               2. EVALUATE              3. DELIVER               4. TRACK
┌──────────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│  career-ops  │ ────►  │ /career-ops- │ ────►  │ /career-ops- │ ────►  │  career-ops  │
│ intake <url> │        │   evaluate   │        │      cv      │        │  dashboard   │
└──────────────┘        └──────────────┘        └──────────────┘        └──────────────┘
  Fetches ATS             Scores match             Compiles 1-page         Visualizes
  data to SQLite          & gap report             tailored PDF            pipeline state
```

1. **Ingest / Scan**: Provide a job posting URL or run `career-ops scan` to discover new openings from your tracked companies.
2. **Evaluate**: The AI agent reads the job requirements, compares them against your experience (`content/cv.md`), and generates a structured fit report.
3. **Generate Deliverables**: Compile a customized, ATS-friendly PDF resume (`output/cv/`) and generate STAR+R interview preparation notes.
4. **Track & Apply**: Track application status progression (`Applied` → `Interview` → `Offer`) and view your interactive pipeline dashboard (`output/dashboard.html`).

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.11+**
- [**`uv`**](https://docs.astral.sh/uv/) (recommended) or standard `pip`
- **Node.js 18+** (for Playwright resume rendering)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/Rafacanedo/career-ops-v2.git
cd career-ops-v2

# Install dependencies
uv sync
# Or with pip: pip install -e .
```

### 3. Setup Your Profile & Content

```bash
# Create your local profile configuration
cp config/profile.example.yml config/profile.yml

# Initialize the local SQLite database
career-ops init

# Verify setup consistency
career-ops sync-check
```

- Edit `config/profile.yml` with your contact info, target roles, and narrative proof points.
- Place your canonical resume experience in `content/cv.md` (git-ignored).
- (Optional) Add your STAR+R interview stories to `content/story-bank.md`.

---

## ⌨️ CLI Reference

The deterministic Python CLI handles all database operations, ATS network ingestion, and PDF rendering:

| Command | Description |
|:---|:---|
| `career-ops init` | Initializes the SQLite database and 3-table schema at `data/career_ops.db`. |
| `career-ops intake <url>` | Deterministically fetches and ingests a single job posting URL into SQLite. |
| `career-ops intake-raw` | Ingests pre-extracted job details (`--company`, `--role`, `--url`, `--desc-file`) directly into SQLite. |
| `career-ops scan` | Runs configured ATS, MCP, and GitHub scanners (`config/portals.yml`) and streams new postings into SQLite (alias: `fetch`). |
| `career-ops list` | Lists compact job metadata (`--status`, `--limit`, `--offset`, `--format json\|table`) without loading full descriptions. |
| `career-ops show <id>` | Displays metadata for a single `vaga_id` or sequence number, optionally with the full JD (`--full`). |
| `career-ops track <id>` | Updates candidate lifecycle state (`--status`, `--score`, `--archetype`, `--application-date`, `--report`, `--pdf`, `--notes`). |
| `career-ops stats` | Outputs pipeline count summaries grouped by status and average fit score. |
| `career-ops export` | Exports SQLite tracker records to `csv`, `json`, or `html` in `workspace/output/`. |
| `career-ops dashboard build` | Builds the self-contained interactive HTML dashboard at `workspace/output/dashboard.html`. |
| `career-ops cv` | Invokes Playwright to compile tailored HTML into an ATS-optimized PDF in `output/cv/`. |
| `career-ops verify` | Audits SQLite `PRAGMA integrity_check`, required tables, and disk existence of referenced report/PDF files. |
| `career-ops sync-check` | Validates setup consistency (`content/cv.md`, `config/profile.yml`, `data/career_ops.db`). |

---

## 🤖 Agentic Workflows & Skills

Career-Ops includes pre-configured agent workflows (`.agents/skills/`) compatible with Google Antigravity, Claude Code, and other agent harnesses:

- **`/career-ops`**: Main entrypoint; checks setup integrity and routes to workflows or CLI commands.
- **`/career-ops-scan`**: Scans tracked company portals and queues matching opportunities in SQLite.
- **`/career-ops-pipeline`**: Evaluates queued opportunities in batches using lightweight metadata queries.
- **`/career-ops-evaluate`**: Deep qualitative assessment of a job against your profile; writes report to `output/reports/`.
- **`/career-ops-cv`**: Renders a keyword-aligned, 1-page ATS resume (`output/cv/`) and links it to the database.
- **`/career-ops-apply`**: Formulates concise, personalized responses for application forms and updates status to `Applied`.
- **`/career-ops-interview-prep`**: Generates recruiter interview questions and grounded STAR+R answers from your story bank.
- **`/career-ops-archetypes`**: Synthesizes 5 strategic target personas from your master CV.
- **`/career-ops-gupy`**: Generates optimized summaries and selects skill tags for Gupy ATS applications.
- **`/career-ops-tracker`**: Summarizes pipeline metrics and recent applications.

---

## 🏗️ Technical Architecture & System Invariants

### Decoupled SQLite Relational Engine (`data/career_ops.db`)

The architecture strictly isolates deterministic CLI plumbing from qualitative AI agent inference:

```text
[External ATS APIs / MCP Servers]
              │
              ▼
    Deterministic Fetcher (Python)
              │
              ▼
  Embedded SQLite Storage (WAL Mode)
  ├── vagas (Lightweight Metadata & Deduplication)
  ├── vaga_descricoes (Isolated Full-Text Payloads & Hashing)
  └── tracking_lifecycle (Candidate State, Scores, Deliverable Paths)
              │
       ┌──────┴──────┐
       ▼             ▼
   AI Harness   Deliverables (Filesystem)
   (Skills)     ├── output/cv/ (Tailored 1-Page PDFs)
                ├── output/reports/ (Evaluation Markdown)
                └── workspace/output/ (HTML Dashboard & Exports)
```

### Core Invariants:
1. **Zero LLM Dependencies in Python Core**: The CLI and Python packages execute with zero external LLM API calls or AI SDK dependencies. All LLM reasoning occurs inside the agent harness.
2. **Context-Window Protection**: Database queries return compact records (<250 tokens per typical query). Full job descriptions are isolated in `vaga_descricoes` and only loaded when explicitly requested (`career-ops show <id> --full`).
3. **Atomic Deduplication & Content Hashing**: `vagas.canonical_url` enforces `UNIQUE` database integrity. Duplicate URLs preserve the original ID while updating descriptions only if the SHA-256 `content_hash` changes.
4. **Status Progression Hierarchy**: Lifecycle stages (`evaluated`: 2 < `applied`: 3 < `interview`: 4 < `offer`: 5) cannot be downgraded to a lower active stage, while terminal states (`rejected`: 1, `discarded`: 0, `skip`: 0) can be set from any stage.
5. **Referential & Deliverable Integrity**: `career-ops verify` audits database integrity and confirms that all deliverable paths (`report_path`, `cv_pdf_path`) exist on the physical filesystem.

### Environment Configuration

The CLI automatically resolves the project root from the current working directory. If executing from outside the repository root, set `CAREER_OPS_ROOT`:

```powershell
# Windows (PowerShell)
$env:CAREER_OPS_ROOT = "C:\path\to\career-ops-v2"
career-ops verify
```

```bash
# macOS / Linux (bash/zsh)
export CAREER_OPS_ROOT="/path/to/career-ops-v2"
career-ops verify
```

---

## 📂 Project Structure

```text
career-ops-v2/
├── .agents/skills/          # Agent workflows and skill definitions (SKILL.md)
├── assets/                  # HTML resume templates and self-hosted fonts
│   ├── docs/                # Setup and architecture documentation
│   └── templates/           # ATS resume HTML templates (ats_clean.html, cv-template.html)
├── config/                  # Configuration files
│   ├── portals.yml          # Tracked companies, ATS connectors, and portal targets
│   ├── profile.example.yml  # Template for user profile configuration
│   └── states.yml           # Canonical pipeline state definitions
├── data/                    # Local SQLite database (career_ops.db, git-ignored)
├── docs/                    # Architecture RFCs, guides, and technical design documents
│   └── designs/             # Technical specifications & design docs
├── output/                  # Deliverables: generated resumes (cv/) and reports (reports/)
├── src/career_ops/          # Core Python package
│   ├── fetcher/             # Deterministic ATS, MCP, and GitHub ingestion connectors
│   ├── render/              # Playwright ATS CV compiler with DOM overflow telemetry
│   ├── schemas/             # Pydantic data schemas for evaluations and CV payloads
│   ├── stories/             # STAR+R story bank parser and matcher
│   ├── cli.py               # Click CLI entrypoint
│   ├── config.py            # Path resolution and state management
│   ├── db.py                # SQLite WAL connection manager and schema DDL
│   ├── repository.py        # Transactional SQLite repository layer
│   └── verify.py            # Integrity and deliverable verifier
├── tests/                   # Pytest unit and integration test suites
├── workspace/               # Exports, static dashboard, and database backups
└── pyproject.toml           # Package configuration and dependencies
```

---

## 🧪 Verification & Testing

Run the full automated test suite (126 unit and integration tests):

```bash
# Run all tests
python -m pytest

# Or with uv
uv run pytest tests/ -v
```

---

## 📄 License & Attribution

This project is licensed under the [MIT License](LICENSE).

Based on the original [career-ops](https://github.com/santifer/career-ops) concept by Santi Fer.
