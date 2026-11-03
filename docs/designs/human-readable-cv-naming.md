# Career-Ops Human-Readable ATS CV PDF Naming & Sequential Indexing

* **Author:** Rafa Canedo & Antigravity Swarm Architecture
* **Status:** Approved
* **Date:** 2026-11-01

--------------------------------------------------------------------------------

## Overview

This technical design specifies the architecture for human-readable, chronologically sortable single-page ATS resume filenames and persistent sequential indexing across Career-Ops v2.

Generated resumes will follow the deterministic convention:
`workspace/output/{index:03d}-rafael-{role_slug}-{company_slug}.pdf`

Example: `workspace/output/001-rafael-senior-data-engineer-nubank.pdf`

The design introduces a persistent integer sequence stored in SQLite (`vagas.seq_num`), an automated migration strategy for existing databases, an ATS/filesystem-safe slugification engine in `src/career_ops/utils.py`, and automatic output path derivation in `src/career_ops/cv.py`.

--------------------------------------------------------------------------------

## The Problem

The previous Career-Ops CV generation workflow exhibited several operational shortcomings:

1. **Recruiter Friction & Opaque Filenames**: Output files were named after internal unique IDs (e.g. `vaga_1a1986e8a5e_76ef95_resume.pdf`). When sent to recruiters or uploaded to applicant tracking systems (Greenhouse, Lever, Workday), the filenames appeared as uninformative machine hashes rather than candidate-branded documents.
2. **Filesystem Exploration Overhead**: In the `workspace/output/` directory, users could not identify which resume matched which company or role without cross-referencing SQLite database tables or opening each PDF file manually.
3. **Lexical Sorting Drift**: Simple unpadded integers (`1`, `2`, `10`) cause alphabetical sorting failures in Windows File Explorer and Unix shells, grouping `10` before `2`.
4. **Filesystem & ATS Fragility**: Raw job titles and company names routinely contain characters that are illegal or problematic on Windows/Linux filesystems or web ATS upload endpoints (slashes `/`, ampersands `&`, plus signs `+`, quotation marks, and regional Portuguese diacritics like `ã`, `é`, `ç`).
5. **Path Length Ceilings**: Overly long job titles risk exceeding the Windows `MAX_PATH` threshold (260 characters) when combined with deep directory trees.
6. **Orphaned File Accumulation**: If a job's title was updated after an initial resume had been compiled, changing the filename could leave the old PDF abandoned on disk.

--------------------------------------------------------------------------------

## Goals

* **Deterministic Human-Readable Template**: Generate all CV PDFs following `{index:03d}-rafael-{role_slug}-{company_slug}.pdf`.
* **Persistent Sequential Indexing (`seq_num`)**: Add an auto-incrementing integer sequence column to `vagas` starting at `1`, assigned atomically at job ingestion time within `BEGIN IMMEDIATE` transactions.
* **Backward-Compatible SQLite Migration**: Automatically detect missing `seq_num` columns in `init_db()` and backfill existing database rows using `rowid` without data loss or user intervention.
* **Robust Slugification Engine**: Provide `slugify_token()` in `src/career_ops/utils.py` that normalizes Unicode accents (NFKD), translates technical keywords (`c++` -> `cpp`, `.net` -> `dotnet`, `/` -> `-`), collapses hyphens, and enforces length budgets (40 chars for role, 30 chars for company).
* **CLI Automated Path Derivation**: Allow `--out` to be optional in `career-ops cv render` when `--vaga-id` is supplied, automatically deriving the canonical output path while preserving explicit `--out` overrides.
* **Idempotent Overwrite & Orphan Cleanup**: Re-rendering a CV for an existing job overwrites the PDF in place. If the job title mutated since the last compilation, remove the old PDF recorded in `tracking_lifecycle.cv_pdf_path` to keep `workspace/output/` clean.
* **Payload Decoupling**: Keep internal staging files (`workspace/staging/cv_<vaga_id>.json`) and evaluation reports (`workspace/reports/report_<vaga_id>.md`) keyed by `<vaga_id>` to prevent breaking other pipeline components.

--------------------------------------------------------------------------------

## Non-Goals

* **Non-PDF Naming Changes**: Staging JSON files, database keys, and evaluation markdown reports will not adopt the human-readable slug. They remain keyed by `<vaga_id>` for referential integrity.
* **Dynamic Sparse/Dense Re-Indexing**: Sequence numbers are immutable once assigned to a job. If a job is skipped or deleted, its sequence number is not recycled, preventing race conditions and index drift.
* **Arbitrary Candidate Name Slugging**: The candidate token is standardized to `rafael` (derived from `profile.yml` with a fallback), satisfying the user requirement.

--------------------------------------------------------------------------------

## Critical User Journeys (CUJs)

### CUJ 1: Job Ingestion & Sequential Index Assignment
* **Given**: A new job URL or scraped posting.
* **When**: The system executes `repository.insert_vaga(vaga_input)`.
* **Then**: Inside the transactional block, the repository queries `SELECT COALESCE(MAX(seq_num), 0) + 1 FROM vagas;`, assigns the integer to `vagas.seq_num`, and commits the row. If the URL is already present, the existing record's `seq_num` and `id` are preserved.

### CUJ 2: Automated Resume Rendering
* **Given**: Job posting `vaga_123` with `seq_num = 1`, `role = "Senior Data / Analytics Engineer (C++)"`, `company = "Nubank & Co."`.
* **When**: The agent or user runs:
  ```bash
  career-ops cv render --payload workspace/staging/cv_vaga_123.json --vaga-id vaga_123
  ```
* **Then**: The CLI checks that `--out` was omitted, loads `vaga_123` metadata, normalizes the role to `senior-data-analytics-engineer-cpp` and company to `nubank-co`, constructs destination path `workspace/output/001-rafael-senior-data-analytics-engineer-cpp-nubank-co.pdf`, compiles the single-page PDF, records the path in `tracking_lifecycle.cv_pdf_path`, and exits `0`.

### CUJ 3: Re-Generation & Title Mutation Handling
* **Given**: An existing PDF `workspace/output/001-rafael-data-engineer-nubank.pdf` is recorded for `vaga_123`.
* **When**: The job title is updated to "Senior Data Engineer" and `career-ops cv render` is executed again for `vaga_123`.
* **Then**: The CLI derives the new path `workspace/output/001-rafael-senior-data-engineer-nubank.pdf`. Upon successful compilation, the CLI removes the previous file from disk, updates `tracking_lifecycle.cv_pdf_path` to the new path, and leaves no orphaned artifacts in `workspace/output/`.

--------------------------------------------------------------------------------

## Technical Plan & Architecture

### 1. Data Model & Migration (`src/career_ops/db.py`)

Update `SCHEMA_DDL` to include `seq_num`:
```sql
CREATE TABLE IF NOT EXISTS vagas (
    id TEXT PRIMARY KEY,
    seq_num INTEGER UNIQUE,
    original_url TEXT NOT NULL,
    canonical_url TEXT UNIQUE,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    source_portal TEXT NOT NULL,
    company_norm TEXT,
    role_norm TEXT,
    location TEXT,
    remote_type TEXT,
    status_triagem TEXT NOT NULL DEFAULT 'queued',
    created_at TEXT NOT NULL DEFAULT (DATETIME('now')),
    updated_at TEXT NOT NULL DEFAULT (DATETIME('now'))
);

CREATE INDEX IF NOT EXISTS idx_vagas_seq_num ON vagas(seq_num);
```

In `init_db()`:
```python
def init_db(db_path: Path | None = None) -> None:
    ...
    # Run schema migration if seq_num column does not exist
    cols = [r[1] for r in conn.execute("PRAGMA table_info(vagas)").fetchall()]
    if "seq_num" not in cols:
        conn.execute("ALTER TABLE vagas ADD COLUMN seq_num INTEGER")
        conn.execute("UPDATE vagas SET seq_num = rowid WHERE seq_num IS NULL")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_vagas_seq_num ON vagas(seq_num)")
```

### 2. Repository Atomicity (`src/career_ops/repository.py`)

* In `insert_vaga()`:
```python
cur.execute("SELECT COALESCE(MAX(seq_num), 0) + 1 FROM vagas")
next_seq = cur.fetchone()[0]
```
* In `get_vaga()`, `list_vagas()`, and `get_vagas_by_status()`: Include `seq_num` in the returned dictionary and dataclasses.

### 3. Slugification Engine (`src/career_ops/utils.py`)

```python
import re
import unicodedata

def slugify_token(text: str, max_len: int = 40) -> str:
    """
    Convert a string into an ATS-safe, filesystem-compliant kebab-case slug.
    Translates technical tokens, removes diacritics, strips punctuation,
    and enforces maximum length bounds.
    """
    if not text:
        return ""
    
    # 1. Lowercase
    s = text.lower().strip()
    
    # 2. Pre-translate common tech tokens and delimiters
    replacements = {
        "c++": "cpp",
        "c#": "csharp",
        ".net": "dotnet",
        "/": "-",
        "\\": "-",
        "&": "and",
        "+": "plus",
        "@": "at",
    }
    for k, v in replacements.items():
        s = s.replace(k, f" {v} ")
    
    # 3. Unicode NFKD normalization to strip diacritics
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    
    # 4. Replace non-alphanumeric with hyphens
    s = re.sub(r"[^a-z0-9]+", "-", s)
    
    # 5. Collapse duplicate hyphens and trim
    s = re.sub(r"-+", "-", s).strip("-")
    
    # 6. Apply character length ceiling without breaking mid-token if possible
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
        
    return s or "item"
```

### 4. CLI Auto-Derivation & Orphan Cleanup (`src/career_ops/cv.py`)

* Make `--out` optional.
* If `--out` is not specified:
  * Require `--vaga-id`.
  * Fetch vaga from repository.
  * Extract `seq_num`, `role`, and `company`.
  * Compute `target_filename = f"{seq_num:03d}-rafael-{slugify_token(role, 40)}-{slugify_token(company, 30)}.pdf"`.
  * Set `out_path = ctx.root / "workspace" / "output" / target_filename`.
* In `update_lifecycle`:
  * If previous `cv_pdf_path` exists on disk and differs from `out_path`, remove the old file from disk.
  * Save the new relative or canonical path in `tracking_lifecycle`.

### 5. Skill Guidance Update (`.agents/skills/career-ops-cv/SKILL.md`)

Update Step 5 command from:
```bash
career-ops cv render --payload workspace/staging/cv_<vaga_id>.json --out workspace/output/<vaga_id>_resume.pdf --format <a4|letter> --vaga-id <vaga_id>
```
To:
```bash
career-ops cv render --payload workspace/staging/cv_<vaga_id>.json --vaga-id <vaga_id> --format <a4|letter>
```

--------------------------------------------------------------------------------

## Alternatives Considered

1. **Minting Sequence at Render Time**: Rejected. Causes numbering gaps when jobs are skipped, makes index unpredictable in tracker, and creates race conditions if multiple CVs are re-rendered.
2. **Dynamic Unpadded Index (`1`, `2`)**: Rejected. Breaks OS lexical sorting (`10` appears before `2`).
3. **Snake_Case or Raw Spaces**: Rejected. Spaces break shell command quoting and web ATS file upload endpoints. Kebab-case is standard across cross-platform tooling.
4. **Altering Staging & Report Filenames**: Rejected. Staging files are ephemeral internal IPC artifacts. Changing their names would introduce cascading churn into evaluation and application skills with zero recruiter benefit.

--------------------------------------------------------------------------------

## Testing & Verification Plan

1. **Database Schema & Migration**:
   * Test `init_db()` creates `seq_num` column on fresh databases.
   * Test `init_db()` migrates legacy databases without `seq_num` and backfills with `rowid`.
   * Test `insert_vaga()` assigns `1`, `2`, `3` incrementally.
   * Test URL deduplication preserves existing `seq_num`.
2. **Slugification Tests (`tests/test_utils.py`)**:
   * Accents: `"São Paulo"` -> `"sao-paulo"`.
   * Tech symbols: `"C++ Developer"` -> `"cpp-developer"`, `".NET Architect"` -> `"dotnet-architect"`.
   * Slashes: `"Data / BI Lead"` -> `"data-bi-lead"`.
   * Truncation: Long titles capped to 40 characters without trailing hyphens.
3. **CV Rendering CLI Tests (`tests/test_cv.py`)**:
   * Invoking `career-ops cv render` without `--out` successfully derives `{seq:03d}-rafael-{role}-{company}.pdf`.
   * Passing explicit `--out` overrides auto-derivation.
   * Modifying role updates the path and cleans up the prior file.
   * Full test suite verification with `pytest`.
