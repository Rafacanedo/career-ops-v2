# Career-Ops Unified Sequential Indexing (`seq_num`) & Deliverables Storage (`output/reports/`)

* **Author:** Rafa Canedo & Antigravity Swarm Architecture
* **Date:** 2026-11-01
* **Status:** Approved (Proceeding to Direct Implementation)
* **Components:** `src/career_ops/{db, repository, config, utils, cli, cv, verify, dashboard, export}`, `.agents/skills/*`

---

## 1. Overview & Problem Statement

### The Problem
In Career-Ops v2, job opportunities are identified internally by an opaque, 28-character deterministic timestamp-UUID hash (e.g., `vaga_1a1986e8a5e_76ef95`). While this guarantees URL deduplication and referential integrity across relational tables (`vagas`, `vaga_descricoes`, and `tracking_lifecycle`), it introduces severe human and agent operational friction:

1. **Fragmented Naming & Cognitive Overhead**: Resume PDFs follow the human-readable pattern `output/cv/{seq:03d}-rafael-{role_slug}-{company_slug}.pdf` (e.g. `062-rafael-senior-ai-engineer-factored.pdf`), but evaluation reports reside in `workspace/reports/report_vaga_{hash}.md` (e.g. `report_vaga_1a1986e8a5e_76ef95.md`). A user looking at CV `062` cannot identify the corresponding report without querying SQLite.
2. **Asymmetric Directory Topology**: Candidate-facing resumes are isolated in `./output/cv/`, while candidate-facing evaluation reports (which contain STAR+R interview prep and draft application answers) remain in `workspace/reports/`. In Career-Ops v2, `workspace/` is designed as scratch storage for transient files (`workspace/staging/`), not polished deliverables.
3. **CLI Lookup Usability**: Commands like `career-ops show`, `evaluate`, `cv render`, and `track` require the full hash ID. The `career-ops list` table does not display `seq_num`, forcing operators to inspect raw SQLite tables to find the sequence number.
4. **Agent Token Overhead**: Passing 28-character hashes across multi-turn subagent prompts consumes 7–8 tokens per reference compared to 1 token for `#62`, inflating context overhead and increasing typo risks.
5. **Strict Evaluation Validation Mismatch**: In `cli.py:evaluate_cmd`, `if payload.vaga_id != vaga_id: sys.exit(1)` performs strict string comparison. Invoking `career-ops evaluate 62` fails when `payload.vaga_id` contains the canonical hash.

### Solution Overview
1. **Preserve Relational Idempotency**: Keep `vagas.id` (hash `vaga_...`) as the primary key and foreign key target for `vaga_descricoes` and `tracking_lifecycle`.
2. **Promote `seq_num` as Universal Sequence Key (SK)**: Treat `vagas.seq_num` (`INTEGER UNIQUE`) as the primary human-facing and agent-facing index.
3. **Polymorphic Boundary Resolution**: Implement `CareerOpsRepository.resolve_vaga_id` to normalize integers, zero-padded strings (`"062"`), `#`-prefixed strings (`"#62"`), and hashes (`"vaga_..."`) to the canonical primary key.
4. **Deliverables Topology Elevation**: Move evaluation reports to `output/reports/{seq:03d}-{role_slug}-{company_slug}.md`, cleanly pairing with `output/cv/{seq:03d}-rafael-{role_slug}-{company_slug}.pdf`.
5. **Deterministic Slug Utilities**: Centralize deliverable path generation in `src/career_ops/utils.py` using `slugify_token` to eliminate LLM prompt hallucination.
6. **Two-Phase Atomic Retroactive Migration**: Migrate the 10 existing reports and SQLite tracking records via an idempotent CLI command with dry-run support.

---

## 2. Technical Architecture & Component Design

```
+--------------------------------------------------------------------------+
|                              CLI & Skills Layer                          |
|  career-ops show 62 | evaluate 62 | cv render --vaga-id 62 | track 62     |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                   Polymorphic Boundary Resolver                          |
|         CareerOpsRepository.resolve_vaga_id(identifier) -> str           |
|   Resolves "62", "062", "#62", or "vaga_..." -> canonical vagas.id      |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                            SQLite Relational Core                        |
|                                                                          |
|  vagas:                     vaga_descricoes:       tracking_lifecycle:   |
|  - id TEXT PRIMARY KEY      - vaga_id (FK -> id)   - vaga_id (FK -> id)  |
|  - seq_num INTEGER UNIQUE   - description_raw      - score               |
|  - canonical_url            - content_hash         - report_path (rel)   |
|  - company, role...                                - cv_pdf_path (rel)   |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                       Consolidated Deliverables Tree                     |
|                                                                          |
|  output/                                                                 |
|  +-- cv/                                                                 |
|  |   +-- 062-rafael-senior-ai-engineer-factored.pdf                      |
|  +-- reports/                                                            |
|      +-- 062-senior-ai-engineer-factored.md                              |
|                                                                          |
|  workspace/ (Ephemeral / Scratchpad Only)                               |
|  +-- staging/                                                            |
|      +-- eval_62.json, cv_62.json                                        |
+--------------------------------------------------------------------------+
```

### 2.1 Database & Schema (`src/career_ops/db.py`)
No DDL breaking changes are required. The schema already defines:
```sql
CREATE TABLE IF NOT EXISTS vagas (
    id TEXT PRIMARY KEY,
    seq_num INTEGER UNIQUE,
    canonical_url TEXT NOT NULL UNIQUE,
    ...
);
CREATE INDEX IF NOT EXISTS idx_vagas_seq_num ON vagas(seq_num);
```
During initialization (`init_db()`), ensure any legacy rows without `seq_num` are backfilled:
```sql
UPDATE vagas SET seq_num = rowid WHERE seq_num IS NULL;
```

### 2.2 Repository Boundary Resolver (`src/career_ops/repository.py`)
Add `resolve_vaga_id`:
```python
def resolve_vaga_id(self, identifier: str | int | None) -> str | None:
    """
    Resolve polymorphic identifier to canonical vagas.id.
    Accepts:
      - Integers: 62
      - Zero-padded strings: '062'
      - Cardinal strings: '#62'
      - Canonical hash: 'vaga_1a1986e8a5e_76ef95'
    """
    if identifier is None:
        return None
    s = str(identifier).strip().lstrip("#")
    if s.isdigit():
        seq = int(s)
        with get_db_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT id FROM vagas WHERE seq_num = ? OR id = ? ORDER BY (CASE WHEN id = ? THEN 0 ELSE 1 END) LIMIT 1;",
                (seq, str(identifier).strip(), str(identifier).strip()),
            ).fetchone()
            if row:
                return str(row["id"])
    with get_db_connection(self.db_path) as conn:
        row = conn.execute("SELECT id FROM vagas WHERE id = ?;", (str(identifier).strip(),)).fetchone()
        return str(row["id"]) if row else None
```
Ensure that `get_vaga`, `get_vaga_description`, and `update_lifecycle` resolve the identifier to canonical `id` before querying or mutating SQLite tables.

### 2.3 Deliverable Slug & Filename Generation (`src/career_ops/utils.py`)
Centralize filename derivation in `src/career_ops/utils.py` reusing `slugify_token`:
```python
def build_deliverable_slugs(role: str, company: str) -> tuple[str, str]:
    role_slug = slugify_token(role or "role", max_len=40)
    company_slug = slugify_token(company or "company", max_len=30)
    return role_slug, company_slug

def build_report_filename(seq_num: int, role: str, company: str) -> str:
    role_slug, company_slug = build_deliverable_slugs(role, company)
    return f"{seq_num:03d}-{role_slug}-{company_slug}.md"

def build_cv_filename(seq_num: int, candidate: str, role: str, company: str) -> str:
    role_slug, company_slug = build_deliverable_slugs(role, company)
    return f"{seq_num:03d}-{candidate}-{role_slug}-{company_slug}.pdf"
```

### 2.4 Directory Configuration (`src/career_ops/config.py`)
Update `config.py` to point reports to `./output/reports/`:
```python
def get_reports_dir(root: Path) -> Path:
    """Return the deliverable path to reports."""
    return root / "output" / "reports"

def get_output_dir(root: Path) -> Path:
    """Return top-level deliverables root."""
    return root / "output"
```

### 2.5 CLI Commands (`src/career_ops/cli.py`)
1. **`list_cmd`**:
   - Add `SEQ` column (formatted as `{seq:03d}`) as the primary column in table mode.
   - Include `"seq_num"` in `--format json` output.
2. **`show_cmd`**:
   - Accept polymorphic ID.
   - Print `Seq:          #{vaga['seq_num']:03d}` alongside `ID:`.
   - Print `Suggested Report: output/reports/{filename}`.
3. **`evaluate_cmd`**:
   - Normalize both `vaga_id` argument and `payload.vaga_id` via `resolve_vaga_id`.
   - Verify `canon_arg == canon_payload`.
   - Auto-derive `output/reports/{filename}` if `payload.report_path` is omitted or points to legacy `workspace/reports/`.
4. **`track_cmd`**:
   - Resolve `vaga_id` to canonical hash before calling `update_lifecycle`.
5. **`cv render` (`src/career_ops/cv.py`)**:
   - Accept polymorphic ID and resolve before updating lifecycle.

### 2.6 Retroactive Migration Command (`career-ops migrate-reports`)
Implement an idempotent two-phase migration command:
1. Scan `tracking_lifecycle` for all rows with non-empty `report_path`.
2. For each row:
   - Resolve `vaga = repo.get_vaga(row["vaga_id"])`.
   - Compute target filename `build_report_filename(vaga["seq_num"], vaga["role"], vaga["company"])`.
   - Compute target relative path `output/reports/{filename}`.
   - If old file exists under `workspace/reports/` or referenced path:
     - Copy to `output/reports/{filename}`.
     - Update SQLite `tracking_lifecycle.report_path = ?`.
     - Unlink old file upon transaction commit.
3. Provide `--dry-run` flag for plan preview.

---

## 3. Goals vs. Non-Goals

### In-Scope Goals
* Add canonical identifier resolution (`resolve_vaga_id`) in `src/career_ops/repository.py`.
* Support `seq_num` (`62`, `062`, `#62`) across all CLI commands (`show`, `evaluate`, `cv render`, `track`).
* Add `SEQ` column to `career-ops list` table and include `seq_num` in JSON output.
* Update default report directory to `output/reports/` and file naming to `{seq:03d}-{role_slug}-{company_slug}.md`.
* Centralize deliverable filename generation helpers in `src/career_ops/utils.py`.
* Implement and execute an idempotent migration script to migrate existing reports and update `tracking_lifecycle.report_path`.
* Update `verify.py`, `dashboard.py`, and `config.py` to recognize `output/reports/`.
* Update agent skills documentation to reflect sequential lookup and report destination.
* Maintain 100% test pass rate across `tests/`.

### Out-of-Scope Non-Goals
* Modifying SQLite table schemas or altering foreign keys from `vagas.id` to `seq_num`.
* Changing staging JSON payload paths (`workspace/staging/eval_*.json` and `workspace/staging/cv_*.json`).
* Altering CV PDF placement (`output/cv/`) or CV naming convention.
* Moving candidate profile configuration (`config/profile.yml`) or story database files.

---

## 4. Alternatives Considered

* **Alternative 1: Altering SQLite Schema to use `seq_num` as `PRIMARY KEY`**:
  * *Rejected because:* URL deduplication relies on immutable hashes derived from URLs and content. Replacing string primary keys with an auto-increment integer complicates deduplication, makes cascade deletion hazardous, and risks database lock contention.
* **Alternative 2: Leaving Reports in `workspace/reports/`**:
  * *Rejected because:* `workspace/` is scratch space for intermediate artifacts. Evaluation reports contain interview STAR+R stories and application answers used during submission. Grouping them under `output/reports/` provides symmetry with `output/cv/`.
* **Alternative 3: Prompt-Based Slug Generation in LLM Agent Skills**:
  * *Rejected because:* Prompt-generated slugs introduce variations in punctuation, accents, and character limits, causing broken file references and failing `career-ops verify`. Filename derivation must be deterministic in Python.

---

## 5. Implementation Phases & Verification Plan

1. **Phase 1: DAL Primitives & DB Safety**:
   - Add `resolve_vaga_id` and ensure `get_vaga`, `get_vaga_description`, and `update_lifecycle` resolve IDs.
   - Add `build_deliverable_slugs`, `build_report_filename`, and `build_cv_filename` in `utils.py`.
2. **Phase 2: Configuration, Verify & Dashboard**:
   - Update `config.py` (`get_reports_dir` -> `root / "output" / "reports"`).
   - Update `verify.py` (`_resolve_artifact_path` checks `output/reports/`).
   - Update `dashboard.py` and `export.py`.
3. **Phase 3: CLI Commands & Resolution**:
   - Update `cli.py` (`list`, `show`, `evaluate`, `track`) and `cv.py`.
4. **Phase 4: Migration Command & Execution**:
   - Implement `migrate_reports_cmd` and run migration on `data/career_ops.db` and disk.
5. **Phase 5: Agent Skills Updates**:
   - Update `.agents/skills/career-ops-evaluate/SKILL.md`, `career-ops-cv/SKILL.md`, `career-ops-pipeline/SKILL.md`, `career-ops-apply/SKILL.md`.
6. **Phase 6: Automated Test Suite & Final Verification**:
   - Update `test_repository.py`, `test_cli.py`, `test_verify.py`, `conftest.py`.
   - Run `pytest` and `career-ops verify`.
