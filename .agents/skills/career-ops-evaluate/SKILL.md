---
name: career-ops-evaluate
description: Evaluate a Job Description (URL or Text), then generate prep/PDF only for high-fit roles.
---

# Career-Ops Evaluation Workflow

Use this workflow to evaluate a specific job posting against your profile. Generate application prep and a customized PDF resume only when the match is good.

## Pre-flight Check
Before evaluating, run a sync check:
```bash
career-ops sync-check
```
If warnings appear, notify the user before continuing.

## Language Detection
Detect the language of the Job Description:
- **Portuguese (BR):** If JD is in Portuguese → generate the report, CV summary, and all candidate-facing text in **Portuguese (BR)**.
- **English:** Default for any other language.

## Input
Provide an existing `vaga_id` (e.g. sequence number `62` / `#062` or canonical hash `vaga_...`), a job posting URL, or paste the Job Description text directly.

---

## Steps

### 🔍 1. Ingest or Retrieve Job Description (SQLite)
1. **If given an existing `vaga_id` or sequence number:**
   Fetch the metadata and full job description from SQLite:
   ```bash
   career-ops show <vaga_id_or_seq> --full
   ```
   *Note: `career-ops show` outputs `suggested_report_path: output/reports/{seq:03d}-{role}-{company}.md`.*
2. **If given a URL (not yet in SQLite):**
   First attempt deterministic ingestion via the CLI:
   ```bash
   career-ops intake "<url>"
   ```
   Then run `career-ops show <vaga_id> --full` using the returned `id`.
3. **Fallback extraction (if deterministic fetch fails or description is empty, or if raw text was pasted):**
   - Once you have `{company}`, `{role}`, `{url}`, and description text, pass it to `career-ops intake-raw`:
     ```bash
     career-ops intake-raw --company "<company>" --role "<role>" --url "<url>" --description "<text>"
     ```
   - Capture the returned `vaga_id`.

### 📋 2. Load Your Profile & Story Bank
Read sources of truth:
1. `config/profile.yml` — Primary source for identity, targets, and positioning.
2. `content/cv.md` — Canonical comprehensive experience base.
3. Query relevant behavioral stories using the CLI:
   ```bash
   career-ops stories list --limit 5
   ```

### ✨ 3. Detect Archetype
Classify the offer into one of the archetypes defined in `config/profile.yml`.

### 🧠 4. Perform Evaluation & Categorical Fit Scoring
Perform deep qualitative gap analysis across the 5 dimensions:
- **`cv_match`**: `exact` (90%+ direct mapping), `high` (solid match with minor gaps), `medium` (some transferable skills), `low` (weak overlap).
- **`level_alignment`**: `target` (natural level), `stretch` (higher title/scope), `overqualified`.
- **`comp_alignment`**: `above_range`, `in_range`, `below_range`, `unverified` (via `search_web` market research).
- **`cultural_signals`**: `positive`, `neutral`, `red_flags` (warning signs in JD).
- **`strategic_alignment`**: `north_star`, `adjacent`, `distraction`.
- **`blockers`**: list any hard disqualifiers (e.g. mandatory non-remote relocation, visa sponsorship unavailable).

Stage the evaluation JSON payload to `workspace/staging/eval_<vaga_id>.json`:
```json
{
  "vaga_id": "<vaga_id>",
  "cv_match": "high",
  "level_alignment": "target",
  "comp_alignment": "in_range",
  "cultural_signals": "positive",
  "strategic_alignment": "north_star",
  "blockers": [],
  "archetype": "<detected>",
  "report_path": "output/reports/<seq_or_suggested_filename>.md",
  "notes": "Strong alignment with system design goals."
}
```

### 📊 5. Calculate Deterministic Score via CLI
Execute the deterministic formula calculation and atomic database commit:
```bash
career-ops evaluate <vaga_id_or_seq> --file workspace/staging/eval_<vaga_id>.json
```
The CLI computes the weighted score (1.0–5.0), applies the `BLOCKER_SCORE_CAP = 3.2` if blockers or `red_flags` exist, updates `tracking_lifecycle`, and outputs the final score.

Score Thresholds:
| Score | Recommendation | Action |
|---|---|---|
| 4.5+ | Strong match — recommend applying immediately | Generate F/G + Tailor CV |
| 4.0–4.4 | Good match — worth applying | Generate F/G + Tailor CV |
| 3.5–3.9 | Decent — apply only if specific reason | Sections A–E only |
| < 3.5 | Recommend against applying (or blocked) | Sections A–E only |

### 📝 6. Generate Sections F/G (if score ≥ 4.0 or force prep requested)
Generate these sections only when score `>= 4.0` or user explicitly requested force prep:
- **F) Interview Prep** — 6-10 STAR+R stories mapped to JD requirements.
- **G) Draft Application Answers** — Reusable answers using Grounded Confident Fit tone.

### 💾 7. Save Evaluation Report
Write the final markdown report to `output/reports/{seq:03d}-{role_slug}-{company_slug}.md` (as reported by `career-ops show <id>`).

Include traceability metadata in the report header:
```markdown
# Relatório de Avaliação — [Role] ([Company])

- **Sequence Number:** `#[seq:03d]`
- **Vaga ID:** `vaga_...`
- **Empresa:** [Company]
- **Cargo:** [Role]
- **Score Determinístico:** 4.x / 5.0
```

### 🖨️ 8. Generate Tailored PDF (if score ≥ 4.0)
If score `>= 4.0`, trigger the [career-ops-cv](/career-ops-cv) workflow immediately.

---
## Final Output
Show the user:
1. Summary card (`vaga_id`, Company, Role, Score, Archetype, Recommendation).
2. Links to the saved report and PDF if generated.
3. Top 3 recommended actions.
