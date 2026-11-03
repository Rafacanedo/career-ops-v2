# career-ops-python 🚀

A comprehensive Python-powered CLI and agentic workflow system for managing your career pipeline. This project automates the tedious parts of job hunting: scanning and ingesting postings into an embedded SQLite relational core, evaluating job descriptions against your profile, and generating tailored ATS-optimized resumes.

> [!NOTE]
> This project uses a decoupled, local-first SQLite relational architecture (`data/career_ops.db`) designed to protect AI agent context windows from token bloat while keeping human deliverables (evaluation reports and PDF resumes) on the filesystem.

## System Overview

The system architecture coordinates four primary layers across a strict boundary between the deterministic Python core and the AI agent harness:
1. **Deterministic Extraction & Ingestion**: The ATS fetcher subsystem (`src/career_ops/fetcher`) interfaces with public ATS REST APIs (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee, Breezy, Inhire, Eightfold), HTTP MCP servers (Gupy, Himalayas, Jobicy, JobStack), GitHub issue repositories, and Schema.org JSON-LD / OpenGraph HTML fallbacks—streaming normalized postings directly into SQLite without LLM API calls.
2. **Embedded Relational State (`data/career_ops.db`)**: The core storage engine (`src/career_ops/db.py` and `src/career_ops/repository.py`) persists opportunities across a normalized 3-table schema (`vagas`, `vaga_descricoes`, and `tracking_lifecycle`) in SQLite WAL mode with atomic `BEGIN IMMEDIATE` transactions.
3. **Context-Efficient Querying & Deduplication**: Database-enforced `UNIQUE(canonical_url)` constraints and content-hash revision tracking prevent duplicates while CLI commands (`list`, `show`, `track`, `stats`) return compact metadata payloads (<250 tokens) unless full descriptions are explicitly requested (`show <id> --full`).
4. **Deliverables, Rendering & Export**: Evaluation reports (`workspace/reports/`) and tailored resume PDFs (`workspace/output/`, rendered via Node.js Playwright `generate-pdf.mjs`) reside on the filesystem, alongside on-demand CSV, JSON, and standalone HTML dashboard exports (`workspace/output/dashboard.html`).

## Subdirectories & System Boundaries

- `[src](./src/README.md)`: Intermediate source root grouping the Python implementation packages.
  - `[src/career_ops](./src/career_ops/README.md)`: Core package providing the Click CLI, SQLite connection manager (`db.py`), transactional repository (`repository.py`), normalization utilities (`utils.py`), and artifact generators.
  - `[src/career_ops/fetcher](./src/career_ops/fetcher/README.md)`: Deterministic ingestion engine implementing ATS/MCP/GitHub connectors and `FetchOrchestrator`.
- `[docs/designs](./docs/designs/SITEMAP.md)`: Technical architecture and design specifications, including `[decoupled-sqlite-architecture.md](./docs/designs/decoupled-sqlite-architecture.md)`.
- `data/`: Local runtime directory holding `data/career_ops.db` (excluded from Git via `.gitignore`).
- `workspace/`: Deliverable storage directory containing evaluation reports (`reports/`), generated resumes and exports (`output/`), and automated SQLite backups (`backups/`).
- `config/`: Pipeline configuration files defining canonical application states (`states.yml`), tracked job portals (`portals.yml`), and user profile parameters (`profile.yml`).
- `assets/`: Templates, fonts, and scripts for HTML-to-PDF resume compilation (`assets/templates/cv-template.html`, `generate-pdf.mjs`).

## Global Invariants

- **Root Precedence**: Project root directory resolution (`resolve_root`) strictly follows: explicit `--root` CLI argument > `CAREER_OPS_ROOT` environment variable > current working directory if `data/career_ops.db`, `config/states.yml`, or `pyproject.toml` exists > 3-level package ancestor > cwd fallback.
- **Deterministic Core**: The Python package executes deterministically with zero external LLM SDK dependencies or model API calls; all qualitative scoring and resume tailoring occur inside the AI agent harness.
- **Normalized 3-Table Schema**:
  - `vagas`: Stores lightweight opportunity metadata (`id`, `canonical_url`, `original_url`, `company`, `company_norm`, `role`, `role_norm`, `source_portal`, `location`, `remote_type`, `status_triagem`, `created_at`, `updated_at`).
  - `vaga_descricoes`: Isolates full-text payloads (`vaga_id`, `description_raw`, `description_clean`, `content_hash`, `fetched_at`) with `ON DELETE CASCADE`.
  - `tracking_lifecycle`: Tracks candidate lifecycle state (`vaga_id`, `status`, `score`, `archetype`, `application_date`, `status_updated_at`, `report_path`, `cv_pdf_path`, `notes`) with `ON DELETE CASCADE`.
- **Canonical URL Deduplication & Revision Tracking**: `vagas.canonical_url` enforces `UNIQUE` integrity. Collisions preserve the oldest `id` and `created_at`, backfilling or updating `vaga_descricoes` only when incoming text is non-empty and its SHA-256 `content_hash` changes.
- **Status Progression Hierarchy**: Active lifecycle stages (`evaluated`: 2 < `applied`: 3 < `interview`: 4 < `offer`: 5) never downgrade to a lower-ranked active stage during `update_lifecycle`, while terminal exit states (`rejected`: 1, `discarded`: 0, `skip`: 0) are permitted from any prior active stage.
- **Referential & Deliverable Integrity**: All non-empty `report_path` and `cv_pdf_path` pointers in `tracking_lifecycle` are verified against physical files on disk via `career-ops verify`.

## Global Side Effects

- **Local SQLite Mutations**: Creates and updates `data/career_ops.db` using `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`, `PRAGMA busy_timeout=5000`, and `BEGIN IMMEDIATE` transactions.
- **Database Backups**: `CareerOpsRepository.backup_db()` writes timestamped online SQLite backups to `workspace/backups/career_ops_<timestamp>.db`.
- **Outbound HTTP / API Queries**: Ingestion connectors query external job boards, ATS APIs, MCP JSON-RPC endpoints, and GitHub Issues APIs.
- **Subprocess Execution**: Invokes Node.js Playwright runtime (`generate-pdf.mjs`) to render PDF resumes into `workspace/output/`.
- **Export Compilation**: Builds self-contained HTML dashboards (`workspace/output/dashboard.html`), JSON dumps (`workspace/output/applications.json`), and semicolon-delimited UTF-8-BOM CSV exports (`workspace/output/applications.csv`).

## 🛠 Requirements

- **Python 3.11+**
- [**`uv`**](https://docs.astral.sh/uv/) (recommended for dependency management)
- **Node.js** (required for `generate-pdf.mjs` Playwright PDF rendering)

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/Rafacanedo/career-ops-python.git
cd career-ops-python

# Install dependencies and the CLI
uv sync

# Initialize the SQLite database
uv run career-ops init
```

## ⚙️ Configuration

By default, the CLI resolves the project root from the current working directory. If running from outside the project folder, set `CAREER_OPS_ROOT` or pass `--root`:

```powershell
# Windows (PowerShell)
$env:CAREER_OPS_ROOT = "C:\Users\rafac\Projects\career-ops-v2"
career-ops --root . verify
```

## ⌨️ CLI Commands

| Command | Description |
|:---|:---|
| `career-ops init` | Initializes the SQLite database and 3-table schema at `data/career_ops.db`. |
| `career-ops intake <url>` | Deterministically fetches and ingests a single job posting URL into SQLite. |
| `career-ops intake-raw` | Ingests pre-extracted job details (`--company`, `--role`, `--url`, `--desc-file`) directly into SQLite. |
| `career-ops scan` | Runs configured ATS, MCP, and GitHub scanners (`config/portals.yml`) and streams new postings into SQLite (alias: `fetch`). |
| `career-ops list` | Lists compact job metadata (`--status`, `--limit`, `--offset`, `--format json\|table`) without loading full descriptions. |
| `career-ops show <id>` | Displays metadata for a single `vaga_id` and optionally includes the full job description (`--full`). |
| `career-ops track <id>` | Updates candidate lifecycle state (`--status`, `--score`, `--archetype`, `--application-date`, `--report`, `--pdf`, `--notes`). |
| `career-ops stats` | Outputs pipeline count summaries grouped by status and average fit score. |
| `career-ops export` | Exports SQLite tracker records to `csv`, `json`, or `html` in `workspace/output/`. |
| `career-ops dashboard build` | Builds the self-contained interactive HTML dashboard at `workspace/output/dashboard.html`. |
| `career-ops cv` | Invokes Playwright (`generate-pdf.mjs`) to render tailored HTML into an ATS-optimized PDF in `workspace/output/`. |
| `career-ops verify` | Audits SQLite `PRAGMA integrity_check`, required tables, and disk existence of referenced report/PDF files. |
| `career-ops sync-check` | Validates setup consistency (`content/cv.md`, `config/profile.yml`, `data/career_ops.db`, and digest freshness). |

## 🤖 Agentic Workflows

This repository includes `.agents/skills` that turn an AI assistant into a context-efficient career coach:

- `/career-ops`: Checks setup (`career-ops sync-check` / `career-ops init`) and routes to workflows or CLI commands.
- `/career-ops-archetypes`: Derives 5 strategic target role personas from `content/cv.md` and `config/profile.yml`.
- `/career-ops-scan`: Runs `career-ops scan` and supplementary discovery to populate queued opportunities in SQLite.
- `/career-ops-pipeline`: Batch-evaluates queued opportunities (`career-ops list --status queued`) using on-demand description loading (`career-ops show <id> --full`).
- `/career-ops-evaluate`: Evaluates a job against your profile, writes `workspace/reports/report_<id>.md`, and updates SQLite via `career-ops track`.
- `/career-ops-cv`: Renders a keyword-optimized PDF resume (`career-ops cv`) and links it via `career-ops track <id> --pdf`.
- `/career-ops-apply`: Drafts tailored answers for application forms from Section G and updates status to `applied`.
- `/career-ops-interview-prep`: Generates 9 grounded recruiter/interview questions and STAR+R answers from an evaluation report.
- `/career-ops-gupy`: Generates a 1450-character PT-BR summary and top 3 matching skills for Gupy profiles.
- `/career-ops-tracker`: Displays pipeline metrics and recent applications via `career-ops stats` and `career-ops list`.

## 📂 Project Structure

```text
career-ops-v2/
├── .agents/skills/          # AI Agent skill workflows (SKILL.md)
├── assets/                  # HTML resume templates and fonts
├── config/                  # Profile, portal targets, and state definitions
├── data/                    # Local SQLite database (career_ops.db, git-ignored)
├── docs/designs/            # Architecture and technical design documents
├── src/career_ops/          # Core Python package
│   ├── fetcher/             # Deterministic ATS, MCP, GitHub, and HTML connectors
│   ├── cli.py               # Click CLI entrypoint (init, intake, list, show, track, stats, ...)
│   ├── config.py            # Root & database path resolution
│   ├── context.py           # Click context and repository injection
│   ├── cv.py                # Playwright PDF generator wrapper
│   ├── dashboard.py         # Static HTML dashboard compiler
│   ├── db.py                # SQLite WAL connection manager and schema DDL
│   ├── export.py            # CSV, JSON, and HTML exporter
│   ├── fetch_cmd.py         # CLI wrapper for FetchOrchestrator
│   ├── models.py            # Dataclasses (VagaInput, Vaga, VagaDescricao, TrackingLifecycle)
│   ├── repository.py        # Transactional SQLite repository layer
│   ├── sync_check.py        # Environment and setup coherence checks
│   ├── utils.py             # URL, company, role normalization & SHA-256 content hashing
│   └── verify.py            # SQLite integrity and artifact file verifier
├── tests/                   # Pytest unit and CLI integration test suites
├── workspace/               # Reports (reports/), PDFs & exports (output/), DB backups (backups/)
└── pyproject.toml           # Package configuration and dependencies
```

## System Verification

```bash
# Run the full test suite
uv run pytest tests/ -v

# Run database, repository, and CLI test suites
uv run pytest tests/test_db.py tests/test_repository.py tests/test_cli.py -v
```

---
*Based on the original [career-ops](https://github.com/santifer/career-ops) project.*
