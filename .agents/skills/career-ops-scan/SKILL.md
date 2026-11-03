---
name: career-ops-scan
description: Scan Portals and Companies for New Job Listings.
---

# Career-Ops Portal Scanner

Use this workflow to find new open roles across configured ATS portals, MCP job servers, GitHub repositories, and web searches, ingesting them directly into SQLite (`data/career_ops.db`) with automatic deduplication.

## Steps

### 🗺️ 1. Pre-flight & Automated Scanner
1. Run `career-ops sync-check` — notify user if warnings appear.
2. Execute the deterministic multi-source scanner configured in `config/portals.yml`:
   ```bash
   career-ops scan
   ```
   *(Optional: pass `--source ats`, `--source mcp`, or `--source github` to scan a specific subset.)*
   This automatically fetches postings, applies `title_filter` rules from `config/portals.yml`, normalizes URLs, and inserts new postings into SQLite with `status_triagem = 'queued'` while deduplicating against existing `canonical_url` records.

### 🌐 2. Supplementary Web / Career Page Discovery (Optional)
If the user requests additional web search discovery or direct career page scraping beyond the automated connectors:
1. Read `config/portals.yml` to get `search_queries`, `tracked_companies`, and `title_filter`.
2. For each enabled query or custom career page:
   - Run `search_web` or fetch the page to extract `{title, url, company}`.
   - Apply `title_filter` rules (case-insensitive):
     1. At least 1 keyword from `title_filter.positive` must match.
     2. Zero keywords from `title_filter.negative` may match.
3. For each matching role found via web search, ingest it into SQLite using `career-ops intake`:
   ```bash
   career-ops intake "<url>" --company "<company>" --role "<title>"
   ```
   SQLite automatically handles `canonical_url` deduplication (`"is_new": false` if already tracked).

### 📊 3. Verify Queued Results
Run a quick check on the newly queued items:
```bash
career-ops list --status queued --limit 20
career-ops stats
```

---
## Final Output
Show a scan summary:
```
Portal Scan — {YYYY-MM-DD}
━━━━━━━━━━━━━━━━━━━━━━━━━━
Total fetched: N
Filtered out:  N
New jobs saved to SQLite (queued): N

  + [{vaga_id}] {company} | {role} | {source_portal}
  ...

→ Run /career-ops-pipeline to evaluate the queued offers.
```
