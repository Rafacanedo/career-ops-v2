# Career-Ops Decoupled SQLite Relational Architecture & Storage Boundary

* **Author:** Rafa Canedo
* **Status:** Proposed
* **Date:** 2026-10-30

---

## Overview

This technical design specifies the refactoring of `career-ops` from a file-based pipeline (Markdown tables, CSVs, and loose TSV staging files) to an embedded SQLite relational core (`data/career_ops.db`). The architecture establishes a normalized 3-table relational schema (`vagas`, `vaga_descricoes`, and `tracking_lifecycle`) that separates raw job opportunities from their full-text descriptions and application lifecycle states.

The system is optimized for local-first execution with zero external cloud dependencies, protecting AI agent context windows from token bloat through targeted CLI query commands while preserving deliverable files (evaluation reports and PDF resumes) in filesystem directories.

## Problem Statement

The existing `career-ops-python` implementation suffers from three architectural failure modes:

1. **Token Draining in Agent Workflows**: The system relies on reading entire markdown tables (`workspace/applications.md`) and candidate checklists (`workspace/pipeline.md`) into the LLM context window. As the tracker grows to hundreds of rows, every pipeline inspection or status update consumes 8,000–15,000 tokens per turn, inflating execution cost and latency.
2. **Indexing & Schema Brittleness**: Storing structured pipeline records in pipe-delimited markdown tables causes frequent parsing failures. Unescaped pipe characters (`|`) in job titles, trailing formatting variations, and regex-based table rewrites cause data corruption and lost rows during automated updates.
3. **Unenforceable Deduplication & Split State**: Tracking state is fragmented across `job-tracker.csv` (historically designated single source of truth), `applications.md` (human markdown table), and `tracker-additions/` (staging TSVs). Deduplication across these files relies on linear file scans without atomic uniqueness constraints, resulting in duplicate entries across job boards and reposts.

## Goals & Non-Goals

### Goals

* **Embedded Relational Storage**: Replace runtime CSV and Markdown state files with an embedded SQLite database (`data/career_ops.db`) using Python's standard library `sqlite3` without external database services.
* **Normalized 3-Table Relational Schema**:
  * `vagas`: Metadata catalog and identity keys (`canonical_url`, `company_norm`, `role_norm`).
  * `vaga_descricoes`: Isolated 1:1 text table storing raw and sanitized job descriptions.
  * `tracking_lifecycle`: Application progress, scores, archetypes, and artifact references.
* **Context-Efficient CLI Interface**: Implement targeted CLI commands (`career-ops list`, `career-ops show`, `career-ops track`, `career-ops stats`) that return only the records requested by the agent (under 250 tokens per typical query).
* **Deterministic Core Architecture**: Keep the entire Python codebase deterministic (zero LLM SDK dependencies, zero external model API calls, rule-based parsing and normalization). Delegate all semantic evaluation, scoring, and resume tailoring exclusively to the AI agent harness.
* **Deterministic Deduplication**: Enforce database-level uniqueness on `canonical_url` with composite indexing on `company_norm + role_norm` and an automated collision resolution policy.
* **Deliverable Storage Boundary**: Keep operational state inside SQLite (excluded from Git via `.gitignore`), while maintaining human-readable evaluation reports (`workspace/reports/report_<id>.md`) and resume PDFs (`workspace/output/<id>_resume.pdf`) on the filesystem.

### Non-Goals

* **LLM Calls Inside Python Core**: No OpenAI, Anthropic, or Google GenAI API calls inside the Python CLI or repository modules. The Python library is deterministic ingestion and storage infrastructure; semantic analysis belongs solely to the AI agent.
* **Remote Cloud Synchronization**: Cloud databases (Firebase / Firestore / PostgreSQL) are explicitly excluded from this core refactor; local-first SQLite is the sole runtime engine.
* **Git Versioning of Operational State**: The SQLite database file will not be committed to Git. Git tracks code, configuration, templates, and agent skills—not operational candidate records.
* **Legacy File Backward-Compatibility**: No dual-writing or two-way synchronization back to `applications.md` or `job-tracker.csv`. Legacy files are archived in `workspace/` as historical backups.
* **Direct Browser Automation**: Browser-based HTML-to-PDF rendering continues to use the existing Node.js Playwright script (`generate-pdf.mjs`).

## Open Questions

* **None**: All initial architectural unknowns regarding storage engine choice, text payload isolation, deduplication constraints, and deliverable boundaries were resolved during the brainstorm phase.

## Critical User Journeys (CUJs)

### CUJ 1: Automated Deterministic Scraper Job Ingestion
* **Given**: A configured ATS target in `config/portals.yml` and an initialized SQLite database.
* **When**: The user or agent executes `career-ops scan` (or runs `career-ops intake <url>`).
* **Then**: The scraper fetches structured JSON directly from the ATS REST API (or parses JSON-LD / HTML DOM deterministically without LLM calls), normalizes the URL, company, and role, and performs an atomic insert into SQLite. If duplicate, it preserves the oldest record and continues without human intervention.

### CUJ 2: Agentic Candidate Triaging & Listing
* **Given**: 50 job postings exist in `vagas` with `status_triagem = 'queued'`.
* **When**: An Antigravity agent runs `career-ops list --status queued --limit 5`.
* **Then**: The CLI executes a lightweight indexed query and returns exactly 5 rows in compact JSON or tabular format (~150 tokens), leaving the full-text job description unread in `vaga_descricoes`.

### CUJ 3: Agentic Evaluation & Deliverable Generation
* **Given**: A candidate job with ID `vaga_042` is selected for evaluation.
* **When**: The agent runs `career-ops show vaga_042` to retrieve the full description, performs semantic evaluation against user archetypes within its own LLM context, writes `workspace/reports/report_042.md`, and runs `career-ops track vaga_042 --score 4.5 --status evaluated --report workspace/reports/report_042.md`.
* **Then**: `tracking_lifecycle` is populated with `status = 'evaluated'`, the score, and the report path, `vagas.status_triagem` updates to `'triaged'`, and the detailed evaluation report is available on the filesystem for the user to review.

---

## Proposed Architecture

### 1. System Boundary: Deterministic Python Core vs. Agentic Harness

A strict architectural boundary separates the deterministic Python package from the AI agent harness:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   AGENTIC HARNESS (Antigravity Skills)                 │
│  • Semantic Inference (Job fit evaluation, archetype matching)         │
│  • Qualitative Scoring (0.0 – 5.0 fit rating & gap analysis)           │
│  • Content Generation (Interview prep questions, tailored CV content)  │
│  • Tool Calls via CLI (Runs deterministic commands, passes arguments)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ CLI Commands (stdin/stdout)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   DETERMINISTIC PYTHON CORE (career_ops)               │
│  • Deterministic Execution (Zero LLM API calls, zero model deps)       │
│  • Public ATS REST APIs (JSON extraction: Greenhouse, Lever, Ashby)    │
│  • Schema.org / DOM Fallback (Deterministic BeautifulSoup parsing)      │
│  • String Normalization (Leverages src/career_ops/utils.py)            │
│  • Relational Transactions (SQLite WAL engine, ACID constraints)       │
└────────────────────────────────────────────────────────────────────────┘
```

### 2. Subsystem Components & Responsibilities

#### A. Database Connection & Schema Manager (`src/career_ops/db.py`)
* **Connection Lifecycle**: Provides a contextual `get_db_connection(db_path: Path)` manager.
* **Pragmas**: Automatically configures write-ahead logging (`PRAGMA journal_mode=WAL;`), foreign key constraint enforcement (`PRAGMA foreign_keys=ON;`), and busy timeout (`PRAGMA busy_timeout=5000;`) on every connection.
* **Locking & Concurrency Protection**: Sets `isolation_level=None` (autocommit mode) and wraps all write operations in explicit `BEGIN IMMEDIATE` transaction blocks to prevent lock-upgrade deadlocks on Windows NTFS file systems.
* **Idempotent DDL Initializer**: Runs schema creation on startup, ensuring tables and indexes exist without requiring external migration tooling.
* **Storage Location**: Defaults to `<root>/data/career_ops.db`, protected from version control via `.gitignore`. Automated timestamped backups are mirrored to `workspace/backups/` upon batch mutations.

#### B. Deterministic Ingestion & Parsing Engine (`src/career_ops/fetcher/`)
All job parsing is deterministic rule-based code without AI model invocation:
1. **Direct Public ATS APIs (Priority 1)**:
   - **Greenhouse**: Queries `https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{id}?content=true` to parse title, location, and HTML content directly from structured JSON.
   - **Lever**: Queries `https://api.lever.co/v0/postings/{company}/{id}` to extract role attributes and plain-text requirements directly from JSON.
   - **Ashby**: Queries Ashby public posting API endpoint to extract job attributes from JSON.
   - **Gupy / Workable / SmartRecruiters**: Extract job details directly from public REST endpoints.
2. **Deterministic HTML / Schema.org Extractor (Priority 2 Fallback)**:
   - Inspects page for `schema.org/JobPosting` JSON-LD script blocks (`<script type="application/ld+json">`), parsing `title`, `hiringOrganization.name`, `jobLocation`, and `description` via standard JSON decoding.
   - If JSON-LD is absent, extracts metadata deterministically via OpenGraph tags (`og:title`, `og:site_name`) and standard CSS selectors (`article`, `main`, `.job-description`).
3. **Manual CLI Raw Input**:
   - For unstructured text pasted by the user, the agent harness extracts structured parameters (`--company`, `--role`, `--url`, `--description`) in the agent turn before passing them to `career-ops intake`. The Python CLI performs no heuristic inference.

#### C. Normalization Utilities (`src/career_ops/utils.py`)
* **Consolidates Normalization Algorithms**: Reuses existing canonicalization utilities in [`src/career_ops/utils.py`](file:///c:/Users/rafac/Projects/career-ops-v2/src/career_ops/utils.py) and adds content digest hashing:
  * **`normalize_url(url: str) -> str`**: Strips tracking parameters (`utm_*`, `ref`, `source`, `fbclid`), normalizes HTTP schemes and lowercase hostnames, and resolves platform-specific canonical paths (Greenhouse board job tokens, Lever posting IDs, Ashby board routes, Gupy portal IDs).
  * **`normalize_company(name: str) -> str`**: Lowercases, strips punctuation, and removes legal entity suffixes (`inc`, `llc`, `ltd`, `ltda`, `sa`, `s.a.`, `gmbh`, `corp`).
  * **`normalize_role(title: str) -> str`**: Lowercases, strips punctuation, and strips bracketed/parenthetical metadata tags (e.g., `[Remote]`, `(100% Remoto)`, `[CLT]`, `(Brasil)`).
  * **`compute_content_hash(text: str) -> str`**: Computes SHA-256 digest of whitespace-collapsed text (`hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()`) to track JD revisions.

#### D. Repository Layer (`src/career_ops/repository.py`)
* **`insert_vaga(vaga: VagaInput, descricao: str) -> tuple[str, bool]`**:
  * Executes within an atomic `BEGIN IMMEDIATE` transaction.
  * Generates a deterministic standard-library identifier: `f"vaga_{int(time.time()*1000):x}_{uuid.uuid4().hex[:6]}"`.
  * Attempts insertion into `vagas`.
  * If a `sqlite3.IntegrityError` is raised due to `UNIQUE(canonical_url)`:
    1. Queries the existing record's `id`, `created_at`, and stored `content_hash`.
    2. If incoming `content_hash` differs from stored hash, updates `vaga_descricoes.description_raw`, updates `content_hash`, and touches `vagas.updated_at` to capture job description revisions.
    3. If `vaga_descricoes` is missing, backfills it.
    4. Returns `(existing_id, False)` indicating an existing record was reconciled.
  * If unique, inserts into `vagas` and `vaga_descricoes`, returning `(new_id, True)`.
* **`get_vaga(vaga_id: str) -> dict | None`**: Reads metadata row from `vagas` joined with `tracking_lifecycle`.
* **`get_vaga_description(vaga_id: str) -> str | None`**: Reads `description_raw` from `vaga_descricoes` on demand.
* **`list_vagas(status: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]`**: Queries `vagas LEFT JOIN tracking_lifecycle ON vagas.id = tracking_lifecycle.vaga_id` without reading full-text description payloads. When `status` is specified, filters via `WHERE COALESCE(tracking_lifecycle.status, vagas.status_triagem) = :status`.
* **`update_lifecycle(vaga_id: str, status: str, score: float | None = None, archetype: str | None = None, application_date: str | None = None, report_path: str | None = None, cv_pdf_path: str | None = None, notes: str | None = None) -> dict`**:
  * Manages active lifecycle states (`evaluated`, `applied`, `interview`, `offer`, `rejected`, `discarded`). Application state transitions permit terminal exit states (`rejected`, `discarded`) from any prior active stage. Raises `KeyError` if `vaga_id` does not exist.
  * Upserts `tracking_lifecycle` and sets `vagas.status_triagem = 'triaged'`.
* **`get_pipeline_stats() -> dict`**: Computes fast aggregates (`{"total": int, "by_status": dict[str, int], "avg_score": float | None}`) grouped by `COALESCE(tracking_lifecycle.status, vagas.status_triagem)`.

#### E. CLI Interface (`src/career_ops/cli.py`)
* `career-ops init`: Initializes the database at `data/career_ops.db`.
* `career-ops intake <url>`: Fetches and ingests a single job description into SQLite using deterministic connectors.
* `career-ops intake-raw --company <c> --role <r> --url <u> --desc-file <path>`: Direct deterministic ingestion of pre-extracted job details.
* `career-ops scan`: Executes configured ATS fetchers (`config/portals.yml`), streaming new jobs into SQLite with automated deduplication.
* `career-ops list [--status <name>] [--limit <n>] [--format json|table]`: Returns compact metadata rows (defaults to JSON when `sys.stdout.isatty()` is False for agent calls, table when in interactive terminal).
* `career-ops show <id> [--full]`: Returns metadata and optionally the full job description.
* `career-ops track <id> --status <status> [--score <score>] [--archetype <name>] [--application-date <date>] [--report <path>] [--pdf <path>] [--notes <text>]`: Updates candidate lifecycle state.
* `career-ops stats`: Outputs pipeline count summaries.
* `career-ops export [--format html|csv|json]`: Generates reports or data exports on demand into `workspace/output/`.

### 3. Database Schema & Indexing DDL

```sql
PRAGMA foreign_keys = ON;

-- Table 1: Ingested Opportunities (Metadata)
CREATE TABLE IF NOT EXISTS vagas (
    id TEXT PRIMARY KEY,
    canonical_url TEXT NOT NULL UNIQUE,
    original_url TEXT NOT NULL,
    company TEXT NOT NULL,
    company_norm TEXT NOT NULL,
    role TEXT NOT NULL,
    role_norm TEXT NOT NULL,
    source_portal TEXT NOT NULL,
    location TEXT,
    remote_type TEXT,
    status_triagem TEXT NOT NULL DEFAULT 'queued',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vagas_triagem ON vagas(status_triagem);
CREATE INDEX IF NOT EXISTS idx_vagas_company_role ON vagas(company_norm, role_norm);

-- Trigger: Automatically touch updated_at timestamp on vacancy updates
CREATE TRIGGER IF NOT EXISTS trg_vagas_updated_at
AFTER UPDATE ON vagas
BEGIN
    UPDATE vagas SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Table 2: Job Description Content (Isolated Payload)
CREATE TABLE IF NOT EXISTS vaga_descricoes (
    vaga_id TEXT PRIMARY KEY,
    description_raw TEXT NOT NULL,
    description_clean TEXT,
    content_hash TEXT NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vaga_id) REFERENCES vagas(id) ON DELETE CASCADE
);

-- Table 3: Candidate Application Lifecycle & Artifact Pointers
CREATE TABLE IF NOT EXISTS tracking_lifecycle (
    vaga_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'evaluated',
    score REAL,
    archetype TEXT,
    application_date DATE,
    status_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    report_path TEXT,
    cv_pdf_path TEXT,
    notes TEXT,
    FOREIGN KEY (vaga_id) REFERENCES vagas(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tracking_status ON tracking_lifecycle(status);
```

### 4. Data Flow Sequence

```mermaid
sequenceDiagram
    autonumber
    actor UserOrAgent as Antigravity Agent / User
    participant CLI as Click CLI
    participant Ingest as Deterministic Ingestion Engine
    participant Dedup as DeduplicationService
    participant Repo as CareerOpsRepository
    participant DB as SQLite (career_ops.db)
    participant FS as Filesystem (workspace/)

    Note over UserOrAgent,DB: 1. Deterministic Intake (Zero LLMs)
    UserOrAgent->>CLI: career-ops intake &lt;url&gt;
    CLI->>Ingest: Fetch via ATS API or Schema.org JSON-LD
    Ingest-->>CLI: Structured JobPosting (JSON)
    CLI->>Dedup: normalize_url(), normalize_company(), normalize_role()
    Dedup-->>CLI: normalized keys
    CLI->>Repo: insert_vaga(vaga, description)
    Repo->>DB: INSERT INTO vagas ...
    alt Unique Record
        DB-->>Repo: Success
        Repo->>DB: INSERT INTO vaga_descricoes ...
        Repo-->>CLI: (vaga_id, True)
    else Collision Detected
        DB-->>Repo: UNIQUE Constraint Violation
        Repo->>DB: SELECT id FROM vagas WHERE keys match
        DB-->>Repo: existing oldest id
        Repo-->>CLI: (oldest_id, False)
    end
    CLI-->>UserOrAgent: Intake status & ID

    Note over UserOrAgent,FS: 2. Agentic Evaluation (LLM in Harness)
    UserOrAgent->>CLI: career-ops list --status queued --limit 5
    CLI->>Repo: list_vagas(status="queued", limit=5)
    Repo->>DB: SELECT id, company, role, canonical_url FROM vagas WHERE status_triagem='queued'
    DB-->>Repo: 5 lightweight rows
    Repo-->>CLI: Compact JSON (~150 tokens)
    CLI-->>UserOrAgent: Returns 5 items

    UserOrAgent->>CLI: career-ops show vaga_001 --full
    CLI->>Repo: get_vaga_description("vaga_001")
    Repo->>DB: SELECT description_raw FROM vaga_descricoes WHERE vaga_id='vaga_001'
    DB-->>Repo: Full text description
    Repo-->>CLI: Description text
    CLI-->>UserOrAgent: Description payload

    Note over UserOrAgent: Agent runs LLM inference for fit analysis
    UserOrAgent->>FS: Writes workspace/reports/report_001.md
    UserOrAgent->>CLI: career-ops track vaga_001 --score 4.5 --status evaluated --report workspace/reports/report_001.md
    CLI->>Repo: update_lifecycle(...)
    Repo->>DB: INSERT/UPDATE tracking_lifecycle & UPDATE vagas.status_triagem
    DB-->>Repo: OK
    CLI-->>UserOrAgent: Lifecycle updated
```

---

## Alternatives Considered

### Alternative A: Cloud-Native Database (Google Cloud Firestore / Firebase)

* **Pros**: Native multi-device synchronization and out-of-the-box web UI integration.
* **Cons**: Imposes high onboarding friction for open-source users by requiring Google Cloud project creation, IAM permissions, service account JSON key management, and billing risks. Batch ingestion risks write-rate throttling and exhausts the 20k writes/day free-tier quota.
* **Reason for Rejection**: The project is intended for open-source adoption where anyone can clone the repository and run it locally without third-party cloud accounts or network dependencies.

### Alternative B: File-Based NoSQL / Markdown Frontmatter as Operational State

* **Pros**: Preserves direct human readability in text editors and native `git diff` tracking.
* **Cons**: Incurs high token consumption in AI agent workflows (loading hundreds of rows consumes 8,000–15,000 tokens per turn). Lacks atomic uniqueness constraints, leading to duplicate entries and indexing corruption during automated concurrent updates.
* **Reason for Rejection**: Directly responsible for the indexing bugs, duplicate collisions, and token costs that prompted this refactor.

### Alternative C: Monolithic Single Database Table (Embedding Raw Descriptions)

* **Pros**: Eliminates the 1:1 foreign key relationship between `vagas` and `vaga_descricoes`.
* **Cons**: Storing 5KB–50KB text bodies directly in the primary vacancies table bloats the B-tree page size. A simple query listing 50 job titles and companies would force SQLite to load megabytes of text into memory, slowing down pipeline queries.
* **Reason for Rejection**: Isolating `vaga_descricoes` ensures the primary `vagas` index remains compact in memory and achieves sub-millisecond query execution.

### Alternative D: LLM-Powered Fuzzy Ingestion in Python Core

* **Pros**: Could attempt fuzzy parameter extraction on poorly structured web pages.
* **Cons**: Requires users to configure and pay for external LLM API keys (OpenAI / Anthropic / Gemini) just to run CLI scraping commands. Introduces nondeterministic output, extraction hallucinations, and network latency into core ingestion infrastructure.
* **Reason for Rejection**: The core codebase must remain deterministic, free, and repeatable. Semantic reasoning belongs exclusively to the agent harness.

---

## Non-Functional Requirements

### 1. Security & Privacy
* **Local Storage Isolation**: All opportunity metadata and candidate status data are persisted locally in `data/career_ops.db`.
* **Private Data Isolation**: `data/career_ops.db` is strictly ignored via `.gitignore` to prevent committing personal job search history to public repositories.
* **Zero Telemetry**: The Python core emits no outbound telemetry or external API pings.

### 2. Performance & Latency
* **Agent Context Protection**: CLI list queries return compact JSON or tables limited to <250 tokens per typical invocation, reducing LLM context consumption by over 90%.
* **Low-Latency Local Queries (<5ms)**: SQLite write-ahead logging (WAL) mode enables concurrent reads without locking writes, providing <5ms query response times for local operations.
* **Storage Footprint**: An SQLite database containing 5,000 job postings with full descriptions occupies less than 35 MB of local disk space.

### 3. Rollout & Rollback
* **Clean-Slate Initialization**: `career-ops init` creates the database without modifying existing files in `workspace/`.
* **Disaster Recovery Backups**: Automated timestamped copies (`workspace/backups/career_ops_<timestamp>.db`) created during mutations ensure immediate point-in-time recovery without committing state to Git.
* **Legacy Archival**: Existing files (`workspace/job-tracker.csv`, `workspace/applications.md`) remain in place as read-only historical archives.
* **Rollback Safety**: Reverting to the previous version requires only running `git checkout main`—the historical CSV and markdown trackers remain intact and functional.

---

## Risks & Limits / Mitigations

### 1. SQLite Concurrency & File Locking on Windows
* **Risk**: Concurrent file access between agent CLI invocations and background scrapers can trigger `sqlite3.OperationalError: database is locked` on Windows NTFS file systems when default `DEFERRED` transactions escalate locks.
* **Mitigation**:
  * Enable SQLite WAL mode (`PRAGMA journal_mode=WAL;`), permitting concurrent readers alongside an active writer.
  * Configure `PRAGMA busy_timeout=5000;` on all connections.
  * Use `isolation_level=None` and wrap all write transactions in explicit `BEGIN IMMEDIATE` blocks to acquire write locks at the start of transactions.

### 2. Disaster Recovery & Single Point of Failure (SPOF)
* **Risk**: Excluding `data/career_ops.db` from version control means a disk failure or database file deletion causes unrecoverable pipeline history loss.
* **Mitigation**:
  * Implement automated SQLite online backup copies (`workspace/backups/career_ops_<timestamp>.db`) triggered on mutations.
  * Provide `career-ops export --format json|csv` to generate portable, human-readable backups on demand.

### 3. Scalability Limits of Embedded Local Storage
* **Risk**: Storing thousands of full-text job descriptions could degrade index search performance and exhaust memory during pipeline scans.
* **Mitigation**:
  * Normalizing full text into `vaga_descricoes` keeps the primary `vagas` B-tree compact (<5 MB for 5,000 vacancies).
  * CLI list commands query exclusively against `vagas`, fetching description payloads only when explicitly requested via `career-ops show <id> --full`.

### 4. Schema Evolution Without Heavyweight ORM Migrations
* **Risk**: Schema changes in future releases could require complex data migrations.
* **Mitigation**:
  * Schema initialization uses idempotent DDL statements (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`).
  * Structural migrations are managed via lightweight `PRAGMA user_version` checks in `src/career_ops/db.py` without external migration dependencies.

---

## Detailed Implementation Plan

### 1. Target Files to Create, Modify, and Deprecate

#### A. Files to Create

1. `src/career_ops/db.py` (Create)
   * **Type**: Python Module (Database Engine)
   * **Rationale**: Implements SQLite connection lifecycle management (`get_db_connection(db_path: Path | None = None) -> sqlite3.Connection` with `row_factory = sqlite3.Row` and `isolation_level = None`), WAL mode pragma configuration, foreign key enforcement, and idempotent DDL schema initialization (`init_db(db_path: Path | None = None) -> None`).
2. `src/career_ops/repository.py` (Create)
   * **Type**: Python Module (Data Access Layer)
   * **Rationale**: Encapsulates transactional SQL operations (`insert_vaga`, `get_vaga`, `get_vaga_description`, `list_vagas`, `update_lifecycle`, `get_pipeline_stats`), enforcing atomic multi-table inserts and resolving `canonical_url` unique constraint collisions.
3. `tests/test_db.py` (Create)
   * **Type**: Python Test Suite
   * **Rationale**: Unit tests verifying SQLite connection pragmas (WAL mode, foreign key enforcement) and schema constraints (foreign key cascades, table/index creation, `updated_at` trigger).
4. `tests/test_repository.py` (Create)
   * **Type**: Python Test Suite
   * **Rationale**: Unit tests verifying atomic transactions, `canonical_url` unique constraint collision handling (preserving oldest ID, updating descriptions on content hash changes, backfilling empty descriptions), and lifecycle updates.
5. `tests/test_cli.py` (Create)
   * **Type**: Python Test Suite
   * **Rationale**: Click CLI runner tests for `init`, `intake`, `intake-raw`, `scan`, `list`, `show`, `track`, `stats`, and `export`.

#### B. Files to Modify

6. `src/career_ops/models.py` (Modify)
   * **Type**: Python Module (Domain Dataclasses)
   * **Rationale**: Add `VagaInput`, `Vaga`, `VagaDescricao`, and `TrackingLifecycle` dataclasses (retaining legacy `AppEntry` and `TrackerAddition` during interim phases until Phase 4 cleanup):
     ```python
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
     ```
7. `src/career_ops/utils.py` (Modify)
   * **Type**: Python Module (Shared Normalization Utilities)
   * **Rationale**: Add `compute_content_hash(text: str) -> str` alongside existing `normalize_url`, `normalize_company`, and `normalize_role` functions.
8. `src/career_ops/config.py` (Modify)
   * **Type**: Python Module (Path & Configuration)
   * **Rationale**: Add `get_db_path()` resolving to `data/career_ops.db`; update `resolve_root()` to anchor on `data/career_ops.db`, `config/states.yml`, or `pyproject.toml`; remove deprecated CSV/TSV path helpers (`get_apps_file`, `get_pipeline_file`, `get_job_tracker_file`, `get_additions_dir`) in Phase 4 cleanup.
9. `src/career_ops/context.py` (Modify)
   * **Type**: Python Module (Click Context)
   * **Rationale**: Update `CareerOpsContext` to initialize and expose the `CareerOpsRepository` instance to CLI command handlers.
10. `src/career_ops/cli.py` (Modify)
    * **Type**: Python Module (Click CLI Entrypoint)
    * **Rationale**: Replace legacy commands (`scan-csv`, `dedup`, `normalize`, `tracker`, `unapplied`) with database-backed commands: `init`, `intake`, `intake-raw`, `scan`, `list`, `show`, `track`, `stats`, `export`.
11. `src/career_ops/fetcher/orchestrator.py` (Modify)
    * **Type**: Python Module (Ingestion Orchestrator)
    * **Rationale**: Refactor `FetchOrchestrator` to stream parsed `JobPosting` instances directly into `repository.insert_vaga()` instead of writing semicolon-delimited CSV rows to `job-tracker.csv`.
12. `src/career_ops/dashboard.py` (Modify)
    * **Type**: Python Module (Dashboard Compilation)
    * **Rationale**: Refactor `generate_dashboard` to load pipeline statistics and applications directly from `CareerOpsRepository` instead of parsing markdown tables.
13. `src/career_ops/export.py` (Modify)
    * **Type**: Python Module (Data Export)
    * **Rationale**: Refactor export handlers to read records from SQLite and export CSV or JSON dumps into `workspace/output/`.
14. `src/career_ops/verify.py` (Modify)
    * **Type**: Python Module (Integrity Verification)
    * **Rationale**: Refactor `run_verify` to check SQLite database schema integrity and verify that referenced report markdown and PDF files in `tracking_lifecycle` exist on disk.
15. `src/career_ops/sync_check.py` (Modify)
    * **Type**: Python Module (Coherence Auditing)
    * **Rationale**: Update verification checks to confirm `data/career_ops.db` exists and is readable, while retaining checks for `cv.md` and `config/profile.yml`.
16. `.gitignore` (Modify)
    * **Type**: Configuration
    * **Rationale**: Add `*.db-shm` (alongside existing `data/`, `*.db`, `*.db-wal`, and `*.db-journal` rules) to prevent committing SQLite shared-memory files to Git.
17. `.agents/skills/career-ops/SKILL.md` (Modify)
    * **Type**: Antigravity Skill Definition
    * **Rationale**: Update main router prompt instructions to route through new CLI commands (`career-ops list`, `career-ops show`, `career-ops track`).
18. `.agents/skills/career-ops-evaluate/SKILL.md` (Modify)
    * **Type**: Antigravity Skill Definition
    * **Rationale**: Update evaluation flow: fetch JD via `career-ops show <id> --full`, write `workspace/reports/report_<id>.md`, and call `career-ops track <id> --status evaluated --score <score> --report <path>`.
19. `.agents/skills/career-ops-scan/SKILL.md` (Modify)
    * **Type**: Antigravity Skill Definition
    * **Rationale**: Update scanning instructions to invoke `career-ops scan` or `career-ops intake`.
20. `.agents/skills/career-ops-tracker/SKILL.md` (Modify)
    * **Type**: Antigravity Skill Definition
    * **Rationale**: Update summary instructions to invoke `career-ops stats` and `career-ops list`.
21. `.agents/skills/career-ops-pipeline/SKILL.md` (Modify)
    * **Type**: Antigravity Skill Definition
    * **Rationale**: Replace deprecated `scan-csv` and `merge` references with `career-ops intake` and `career-ops list --status queued`.
22. `.agents/skills/career-ops-apply/SKILL.md` (Modify)
    * **Type**: Antigravity Skill Definition
    * **Rationale**: Replace manual `workspace/applications.md` edits with `career-ops track <id> --status applied`.
23. `.agents/skills/career-ops-cv/SKILL.md` (Modify)
    * **Type**: Antigravity Skill Definition
    * **Rationale**: Replace manual markdown table updates with `career-ops track <id> --pdf <path>`.
24. `README.md` (Modify)
    * **Type**: Documentation (Repository README)
    * **Rationale**: Update architecture description, CLI commands table, and storage layout reflecting the SQLite relational core.
25. `src/career_ops/README.md` (Modify)
    * **Type**: Documentation (Package Contract)
    * **Rationale**: Update package interfaces, invariants, and side effects.
26. `tests/conftest.py` (Modify)
    * **Type**: Test Fixture
    * **Rationale**: Add pytest fixtures for initializing temporary SQLite databases for testing.
27. `tests/test_export.py`, `tests/test_verify.py`, `tests/test_dashboard.py` (Modify)
    * **Type**: Test Suites
    * **Rationale**: Refactor existing tests to seed temporary SQLite databases via `CareerOpsRepository` rather than writing mock `job-tracker.csv` and `applications.md` fixtures.

#### C. Files to Deprecate / Remove from Runtime Flow

28. `src/career_ops/scan_csv.py`, `src/career_ops/parser.py`, `src/career_ops/normalize.py`, `src/career_ops/merge_tracker.py`, `src/career_ops/dedup.py`, `src/career_ops/tracker.py`, `src/career_ops/unapplied.py` (Delete/Archive)
    * **Type**: Python Modules (Legacy File-Based Pipeline)
    * **Rationale**: Obsolete CSV, TSV, and Markdown table parsing, deduplication, and in-place row rewriting modules replaced by `CareerOpsRepository` and `utils.py`.
29. `tests/test_parser.py`, `tests/test_merge.py`, `tests/test_normalize.py`, `tests/test_scan_csv.py`, `tests/test_dedup.py` (Delete/Archive)
    * **Type**: Test Suites
    * **Rationale**: Test suites covering deprecated file-parsing modules.

---

### 2. Implementation Execution Sequence

Phases 1 through 3 are strictly additive, retaining legacy symbols until Phase 4 so that the codebase remains importable and testable at every checkpoint:

```text
Phase 1: Database Engine, Domain Models & Normalization Utilities
  ├── Step 1.1: Add VagaInput, Vaga, VagaDescricao, and TrackingLifecycle to src/career_ops/models.py
  ├── Step 1.2: Add compute_content_hash() to src/career_ops/utils.py
  ├── Step 1.3: Implement src/career_ops/db.py (connection manager, WAL mode, schema DDL)
  ├── Step 1.4: Add get_db_path() and update resolve_root() in src/career_ops/config.py; update .gitignore
  └── Step 1.5: Write and run tests/test_db.py

Phase 2: Repository Layer
  ├── Step 2.1: Implement src/career_ops/repository.py (insert_vaga, get_vaga, list_vagas, update_lifecycle, get_pipeline_stats)
  ├── Step 2.2: Implement atomic collision handling on UNIQUE(canonical_url) (preserve oldest ID, update JD revisions)
  └── Step 2.3: Write and run tests/test_repository.py

Phase 3: Fetcher Ingestion Integration
  ├── Step 3.1: Refactor fetcher/orchestrator.py to write to CareerOpsRepository
  └── Step 3.2: Verify tests/test_connectors.py

Phase 4: Database-Backed CLI Commands & Coordinated Deprecation Cleanup
  ├── Step 4.1: Implement CLI commands in src/career_ops/cli.py (init, intake, intake-raw, scan, list, show, track, stats, export)
  ├── Step 4.2: Refactor dashboard.py, export.py, verify.py, and sync_check.py to use CareerOpsRepository
  ├── Step 4.3: Remove obsolete source modules (parser.py, merge_tracker.py, normalize.py, scan_csv.py, dedup.py, tracker.py, unapplied.py), legacy models/config helpers, and obsolete test suites (test_parser.py, test_merge.py, test_normalize.py, test_scan_csv.py, test_dedup.py)
  └── Step 4.4: Create tests/test_cli.py, update test_export.py / test_verify.py / test_dashboard.py, and run full test suite (pytest tests/)

Phase 5: Agent Skills & Contracts Alignment
  ├── Step 5.1: Update .agents/skills/* (career-ops, evaluate, scan, tracker, pipeline, apply, cv) to use new CLI commands
  └── Step 5.2: Update README.md and src/career_ops/README.md contracts
```

---

### 3. Verification Plan

* **Unit Tests**:
  * Execute `pytest tests/test_db.py tests/test_repository.py -v`.
  * Validate that the `canonical_url` `UNIQUE` constraint raises `IntegrityError` and `CareerOpsRepository` resolves collisions by preserving the oldest record and updating descriptions when `content_hash` changes.
  * Validate that `vaga_descricoes` and `tracking_lifecycle` cascade on `vagas` deletion.
* **CLI & Integration Tests**:
  * Execute `pytest tests/test_cli.py -v`.
  * Test `career-ops init` initializes an empty database at `data/career_ops.db`.
  * Test `career-ops intake` with mock ATS responses inserts into `vagas` and `vaga_descricoes`.
  * Test `career-ops list --status queued` emits valid JSON containing `id`, `company`, `role`, `canonical_url`, and `status`.
  * Test `career-ops show <id> --full` returns complete job description.
  * Test `career-ops track <id> --score 4.5 --status evaluated` updates status and records score.
* **Test Coverage Target**:
  * Maintain >= 85% branch coverage across `db.py` and `repository.py`.
* **Full Test Suite Execution**:
  * Execute `pytest tests/ -v` to ensure zero regressions across all active modules.
