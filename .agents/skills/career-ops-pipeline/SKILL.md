---
name: career-ops-pipeline
description: Process all URLs in your pending inbox.
---

# Career-Ops Pipeline Processor

Use this workflow to batch-evaluate job opportunities currently queued in SQLite (`status = 'queued'`) or to ingest and evaluate a batch of new URLs.

## Pre-flight Check
Run sync check before starting:
```bash
career-ops sync-check
```
If warnings appear, notify the user and ask whether to continue.

## Steps

### 📂 1. Load Queued Opportunities from SQLite
1. If the user provided new raw URLs in the prompt, ingest each one first:
   ```bash
   career-ops intake "<url>"
   ```
2. Query the pending queue from SQLite (using a compact `--limit` to protect context tokens):
   ```bash
   career-ops list --status queued --limit 10
   ```
3. If no queued records exist, inform the user and suggest running `/career-ops-scan` or `career-ops intake <url>`.

### 🔄 2. Process Each Queued Item
For each queued item (`vaga_id`):

1. **Fetch the full Job Description on demand:**
   ```bash
   career-ops show <vaga_id> --full
   ```
2. **Handle missing descriptions:**
   - If `description` is empty, attempt fetching from `canonical_url` / `original_url` via URL reader or browser tools.
   - If inaccessible (login wall, 404, closed role), mark the item as `skip` or `discarded` so it leaves the queue:
     ```bash
     career-ops track <vaga_id> --status discarded --notes "Inaccessible or closed URL"
     ```
3. **Trigger evaluation:**
   - Execute the [career-ops-evaluate](/career-ops-evaluate) workflow for `<vaga_id>`.
   - Save the evaluation report to `output/reports/{seq:03d}-{role_slug}-{company_slug}.md` (suggested by `career-ops show <id>`).
   - Commit evaluation state via `career-ops evaluate`:
     ```bash
     career-ops evaluate <vaga_id> --file "workspace/staging/eval_<vaga_id>.json"
     ```
   - If score `>= 4.0`, generate the tailored CV PDF via [career-ops-cv](/career-ops-cv):
     ```bash
     career-ops cv render --payload "workspace/staging/cv_<vaga_id>.json" --vaga-id <vaga_id>
     ```

### 📊 3. Verify Pipeline Health
After processing the batch, run integrity verification and summary stats:
```bash
career-ops verify
career-ops stats
```

---
## Final Output
Show a results table:
```
| Vaga ID | Company | Role | Score | PDF | Recommendation |
```
Then show overall pipeline stats (`career-ops stats`: total tracked, queued remaining, average score, and high-fit PDFs generated).
