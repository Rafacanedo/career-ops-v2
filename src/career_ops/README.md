# Career Ops Core Package (`src/career_ops`)

## Overview
Deterministic core business logic, SQLite WAL database engine (`db.py`), transactional repository layer (`repository.py`), domain dataclasses (`models.py`), normalization utilities (`utils.py`), and Click CLI command handlers (`cli.py`) powering the `career-ops` relational pipeline.

## Interface
- `[fetcher](./fetcher/README.md)`: Subpackage managing deterministic ATS REST connectors, MCP clients, GitHub issue scrapers, and `FetchOrchestrator`.
- `[cli.py:cli]`: Root Click command group configuring `--root` (`CAREER_OPS_ROOT`) and attaching `CareerOpsContext`.
- `[cli.py:init_cmd]`: CLI command (`career-ops init`) initializing `data/career_ops.db` schema.
- `[cli.py:intake_cmd]`: CLI command (`career-ops intake <url>`) deterministically fetching and ingesting a single URL into SQLite.
- `[cli.py:intake_raw_cmd]`: CLI command (`career-ops intake-raw`) ingesting pre-extracted job fields and description files into SQLite.
- `[cli.py:list_cmd]`: CLI command (`career-ops list`) returning compact metadata rows in JSON (non-TTY default) or table (TTY default) format without loading full-text descriptions.
- `[cli.py:show_cmd]`: CLI command (`career-ops show <vaga_id>`) returning metadata and optionally joining `description_raw` when `--full` is passed.
- `[cli.py:track_cmd]`: CLI command (`career-ops track <vaga_id>`) upserting candidate lifecycle state, score, archetype, and artifact paths.
- `[cli.py:stats_cmd]`: CLI command (`career-ops stats`) outputting pipeline count summaries grouped by status and average score.
- `[config.py:resolve_root]`: Resolves project root with strict precedence (`--root` > `CAREER_OPS_ROOT` > cwd if `data/career_ops.db`, `config/states.yml`, or `pyproject.toml` exists > 3-level package ancestor > cwd fallback).
- `[config.py:get_db_path]`: Returns resolved path to `<root>/data/career_ops.db`.
- `[config.py:get_output_dir]`: Returns resolved path to `<root>/workspace/output/`.
- `[config.py:get_reports_dir]`: Returns resolved path to `<root>/workspace/reports/`.
- `[config.py:get_states_file]`: Returns resolved path to `<root>/config/states.yml`.
- `[config.py:load_states]`: Parses canonical state definitions and alias mappings from `config/states.yml`.
- `[config.py:CANONICAL_STATUSES]`: Canonical status list (`Evaluated`, `Applied`, `Interview`, `Offer`, `Rejected`, `Discarded`, `SKIP`).
- `[config.py:STATUS_RANK]`: Progression hierarchy mapping (`skip`/`discarded`: 0, `rejected`: 1, `evaluated`: 2, `applied`: 3, `interview`: 4, `offer`: 5).
- `[context.py:CareerOpsContext]`: Click context carrier resolving `root`, `db_path`, and lazily initializing `CareerOpsRepository`.
- `[context.py:pass_ctx]`: Click decorator injecting `CareerOpsContext` into command handlers.
- `[cv.py:cv_cmd]`: CLI command (`career-ops cv`) invoking Playwright via `generate-pdf.mjs` to render HTML resumes into A4/Letter PDFs.
- `[dashboard.py:render_dashboard_html]`: Renders a standalone, self-contained HTML dashboard string from SQLite application records.
- `[dashboard.py:dashboard_cmd]`: CLI command group (`career-ops dashboard`) for static dashboard generation.
- `[dashboard.py:dashboard_build_cmd]`: CLI command (`career-ops dashboard build`) compiling SQLite tracker records into `workspace/output/dashboard.html`.
- `[db.py:SCHEMA_VERSION]`: Integer schema version constant (`1`) tracked via `PRAGMA user_version`.
- `[db.py:SCHEMA_DDL]`: Idempotent SQLite DDL defining `vagas`, `vaga_descricoes`, `tracking_lifecycle`, indexes, and `trg_vagas_updated_at`.
- `[db.py:ManagedConnection]`: `sqlite3.Connection` subclass that commits/rolls back and closes the file handle when exiting a `with` block.
- `[db.py:get_db_connection]`: Opens a `ManagedConnection` with `isolation_level=None`, `row_factory=sqlite3.Row`, `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`, and `PRAGMA busy_timeout=5000`.
- `[db.py:init_db]`: Idempotently executes `SCHEMA_DDL` and updates `PRAGMA user_version`.
- `[export.py:EXPORT_FIELDS]`: Ordered 18-column field list for CSV exports from SQLite.
- `[export.py:export_applications]`: Exports SQLite records to semicolon-delimited UTF-8-BOM CSV, JSON, or HTML at `output_path`.
- `[export.py:export_cmd]`: CLI command (`career-ops export`) writing `applications.csv`, `applications.json`, or `dashboard.html` into `workspace/output/`.
- `[fetch_cmd.py:fetch_cmd]`: CLI command (`career-ops scan` / `career-ops fetch`) running `FetchOrchestrator` across ATS, MCP, or GitHub targets.
- `[models.py:VagaInput]`: Input dataclass for job ingestion (`original_url`, `company`, `role`, `source_portal`, optional normalized keys and location/remote metadata).
- `[models.py:Vaga]`: Stored vacancy dataclass extending `VagaInput` with `id`, `status_triagem`, `created_at`, and `updated_at`.
- `[models.py:VagaDescricao]`: Isolated job description payload dataclass (`vaga_id`, `description_raw`, `content_hash`, `description_clean`, `fetched_at`).
- `[models.py:TrackingLifecycle]`: Candidate lifecycle state dataclass (`vaga_id`, `status`, `score`, `archetype`, `application_date`, `status_updated_at`, `report_path`, `cv_pdf_path`, `notes`).
- `[repository.py:generate_vaga_id]`: Generates unique `vaga_<hex_ms>_<uuid6>` identifiers using standard library primitives.
- `[repository.py:CareerOpsRepository]`: Transactional data access layer encapsulating `insert_vaga`, `get_vaga`, `get_vaga_description`, `list_vagas`, `update_lifecycle`, `get_pipeline_stats`, and `backup_db`.
- `[repository.py:insert_vaga]`, `[repository.py:get_vaga]`, `[repository.py:get_vaga_description]`, `[repository.py:list_vagas]`, `[repository.py:update_lifecycle]`, `[repository.py:get_pipeline_stats]`: Module-level convenience wrappers around `CareerOpsRepository`.
- `[sync_check.py:run_sync_check]`: Audits workspace coherence (`content/cv.md`, `config/profile.yml`, `data/career_ops.db` readability, hardcoded metrics, and `article-digest.md` freshness).
- `[sync_check.py:sync_check_cmd]`: CLI command (`career-ops sync-check`) executing setup coherence verification.
- `[utils.py:validate_status]`: Normalizes raw status strings and legacy aliases into canonical status labels.
- `[utils.py:normalize_company]`: Lowercases company names and strips punctuation/whitespace.
- `[utils.py:normalize_role]`: Lowercases role titles and strips parenthetical/punctuation noise.
- `[utils.py:role_fuzzy_match]`: Compares two roles for >= 2 shared words longer than 3 characters.
- `[utils.py:parse_score]`: Parses numeric score floats from strings (`4.2/5`).
- `[utils.py:extract_report_num]`: Extracts numeric report ID from markdown link syntax.
- `[utils.py:normalize_url]`: Resolves platform-specific identifiers (LinkedIn, Gupy, Inhire, Greenhouse, Ashby, HireWithNear, Indeed, Glassdoor, Mercado Libre) and strips query/fragment parameters.
- `[utils.py:days_between]`: Computes absolute calendar days between two ISO date strings.
- `[utils.py:get_status_rank]`: Returns numeric rank for status progression comparison.
- `[utils.py:compute_content_hash]`: Computes SHA-256 hex digest of whitespace-collapsed text (`" ".join(text.split())`).
- `[verify.py:run_verify]`: Verifies `data/career_ops.db` existence, `PRAGMA integrity_check`, presence of all 3 relational tables, and filesystem existence of all referenced `report_path` and `cv_pdf_path` artifacts.
- `[verify.py:verify_cmd]`: CLI command (`career-ops verify`) running pipeline integrity checks.

## Invariants
- `[db.py:get_db_connection]`: Always sets `isolation_level=None`, `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`, and `PRAGMA busy_timeout=5000`, closing the connection handle on context manager exit via `ManagedConnection`.
- `[repository.py:CareerOpsRepository.insert_vaga]`: Executes within an explicit `BEGIN IMMEDIATE` transaction; on `UNIQUE(canonical_url)` collision, preserves the oldest `id` and `created_at`, updating `vaga_descricoes` and `vagas.updated_at` only when incoming `descricao` is non-empty and its `content_hash` differs from stored hash (or backfilling if empty).
- `[repository.py:CareerOpsRepository.list_vagas]`: Queries `vagas LEFT JOIN tracking_lifecycle` without reading `vaga_descricoes`, filtering by `LOWER(COALESCE(t.status, v.status_triagem))` (or `LOWER(v.status_triagem)` when filtering `"triaged"`).
- `[repository.py:CareerOpsRepository.update_lifecycle]`: Rejects unknown statuses (`ValueError`) and missing `vaga_id` (`KeyError`); prevents downgrading an active lifecycle status to a lower-ranked active status while allowing terminal exit statuses (`rejected`, `discarded`, `skip`) from any active stage; preserves existing non-null fields via `COALESCE` when optional arguments are `None`; sets `vagas.status_triagem = 'triaged'`.
- `[export.py:export_applications]`: CSV output uses `utf-8-sig` encoding, semicolon delimiter (`;`), CRLF (`\r\n`), and `csv.QUOTE_ALL`.
- `[verify.py:run_verify]`: Requires `PRAGMA integrity_check` to return `"ok"`, all 3 tables in `REQUIRED_TABLES` to exist, and all non-empty `report_path` and `cv_pdf_path` entries to resolve to existing files on disk.

## Side Effects
- `[db.py:get_db_connection]` / `[db.py:init_db]`: Creates parent directory `data/` and initializes SQLite file `data/career_ops.db` (plus `-wal` and `-shm` files during active connections).
- `[repository.py:CareerOpsRepository]`: Mutates rows in `vagas`, `vaga_descricoes`, and `tracking_lifecycle`, and writes online backup copies to `workspace/backups/career_ops_<timestamp>.db` via `backup_db()`.
- `[cv.py:cv_cmd]`: Executes Node.js subprocess (`generate-pdf.mjs`) to render PDF files in `workspace/output/`.
- `[dashboard.py:dashboard_build_cmd]`: Writes standalone HTML dashboard to `workspace/output/dashboard.html`.
- `[export.py:export_cmd]`: Writes `applications.csv`, `applications.json`, or `dashboard.html` to `workspace/output/`.
- `[fetch_cmd.py:fetch_cmd]`: Performs outbound HTTP requests via `FetchOrchestrator` and inserts new postings into `data/career_ops.db`.

## Verification
- Run: `uv run pytest tests/ -v`
