---
name: career-ops-scan
description: Scan Portals and Companies for New Job Listings.
---

# Career-Ops Portal Scanner

Use this workflow to find new open roles that match your title filters across the portals and companies defined in your configuration.

## Steps

### 🗺️ 1. Load & Verify
1. Run `career-ops sync-check` — notify user if warnings.
2. Read `portals.yml` to get: `search_queries`, `tracked_companies`, `title_filter`.
3. Read these dedup sources:
   - `workspace/applications.md` — company+role already evaluated
   - `workspace/pipeline.md` — URLs already in inbox
   - `workspace/job-tracker.csv` — URLs already queued or processed in the external inbox

### 🏢 2. Level 1 — Direct Company Scans (Most Reliable)
For each enabled company in `tracked_companies` that has a `careers_url`:
1. Use `read_url_content` for a static fetch attempt.
2. If the result is blank or insufficient, use `browser_subagent` to navigate and extract all job listings.
3. For each listing extract: `{title, url, company}`.
4. If the `careers_url` returns a 404 or redirect, fall back to the company's `scan_query` and log for manual update.

### ⚡ 3. Level 2 — Greenhouse API (Fast, Structured)
For each enabled company in `tracked_companies` that has an `api:` field:
1. Use `read_url_content` to fetch the Greenhouse JSON endpoint.
2. Parse `jobs[].title` and `jobs[].absolute_url`.
3. Merge results with Level 1 (deduplicate by URL).

### 🌐 4. Level 3 — Web Search Discovery (Broad)
For each enabled query in `search_queries`:
1. Run `search_web` with the query string.
2. Extract `{title, url, company}` from each result using these patterns:
   - Ashby: `"Senior AI PM @ EverAI"` → title: `Senior AI PM`, company: `EverAI`
   - Greenhouse: `"AI Engineer at Anthropic"` → title: `AI Engineer`, company: `Anthropic`
   - Lever: `"Product Manager - AI @ Temporal"` → title: `Product Manager - AI`, company: `Temporal`
3. Merge results with Level 1+2.

### 🔍 5. Filter All Results
Apply `title_filter` rules (case-insensitive):
1. At least 1 keyword from `title_filter.positive` must match.
2. Zero keywords from `title_filter.negative` may match.
3. `seniority_boost` keywords raise priority but are not required.

### 🔄 6. Deduplicate
Against all 3 sources loaded in Step 1. Mark status for scan history:
- New match → `added`
- Filtered by title → `skipped_title`
- Already seen → `skipped_dup`

### 📥 7. Update Files
1. Append NEW roles to `workspace/pipeline.md` under the "Pending" section:
   ```
   - [ ] {url} | {company} | {title}
   ```
2. If the user wants the findings persisted in the spreadsheet inbox, append new rows to `workspace/job-tracker.csv` with `Processing Date` left blank so `career-ops scan-csv` can queue them through the supported CLI flow.

---
## Final Output
Show a scan summary:
```
Portal Scan — {YYYY-MM-DD}
━━━━━━━━━━━━━━━━━━━━━━━━━━
Queries run: N
Total found: N
Filtered by title: N relevant
Duplicates skipped: N
New added to pipeline: N

  + {company} | {title} | {source}
  ...

→ Run /career-ops-pipeline to evaluate the new offers.
```
