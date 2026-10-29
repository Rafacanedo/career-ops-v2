---
name: career-ops-pipeline
description: Process all URLs in your pending inbox.
---

# Career-Ops Pipeline Processor

Use this workflow to evaluate all job URLs currently in your `workspace/job-tracker.csv` with 'Processing Date' empty.

## Pre-flight Check
Run sync check and scan the tracker before starting:
```bash
career-ops sync-check
career-ops scan-csv
```
If warnings appear, notify user and ask whether to continue.

## Steps

### 📂 1. Load Pipeline
1. Read `workspace/pipeline.md`.
2. Extract all items marked as `- [ ]` from the "Pending" section.
3. For each item, check if it contains a `[jd: local:...]` reference.
4. List all files in `workspace/reports/` to determine the starting sequential report number.

### 🔄 2. Process Each Item
For each pending item:

1. **Determine report number** — max existing report number + 1 (zero-padded, e.g. `007`).
2. **Extract the URL** — strip any extra metadata from the pipeline line (e.g., `| Company | Title`).
3. **Check for Local JD** — If the line contains `[jd: local:path/to/jd.md]`, use this file as the source of truth for the Job Description.
4. **Trigger evaluation** — invoke the [career-ops-evaluate](/career-ops-evaluate) workflow for this URL. If a local JD was found, pass its content (or path) to the evaluator.
5. **Handle errors:**
   - If URL is inaccessible (login wall, 404, private) → mark as `- [!] {url} — Error: {reason}` and continue to next item.
   - If extraction fails after all methods → mark as `- [!]` and ask the user to paste the JD manually.
6. On success → Move the item from "Pending" to "Processed" in `workspace/pipeline.md`:
   ```
   - [x] #{NNN} | {url} | {company} | {role} | {score}/5 | PDF {✅|❌}
   ```
   PDF is ✅ only when score `>= 4.0` and the tailored PDF was generated. For score `< 4.0`, use PDF ❌ by policy.

### 📊 3. Sync Tracker
After processing all items, run:
```bash
career-ops merge
```
Then run a health check:
```bash
career-ops verify
```

---
## Final Output
Show a results table:
```
| # | Company | Role | Score | PDF | Recommendation |
```
Then show overall pipeline stats (total processed, avg score, high-fit PDFs generated).
