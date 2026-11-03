---
name: career-ops-tracker
description: View application history and pipeline statistics.
---

# Career-Ops Tracker

Use this workflow to see the status of all your job applications and key pipeline metrics directly from SQLite (`data/career_ops.db`) without loading full job descriptions into context.

## Steps

### 📊 1. Load Pipeline Statistics
Run the stats command to retrieve aggregate counts by status and average fit score:
```bash
career-ops stats
```

### 📋 2. List Recent & Active Opportunities
Query compact metadata rows from SQLite:
```bash
career-ops list --limit 50
```
*(You can also filter by a specific status using `career-ops list --status queued`, `--status evaluated`, `--status applied`, `--status interview`, or `--status offer`.)*

### 📈 3. Summarize Metrics
From the returned JSON/table rows and `career-ops stats`, report:
- **Total Opportunities**
- **By Status** — `queued`, `evaluated`, `applied`, `interview`, `offer`, `rejected`, `discarded`, `skip`
- **Average Score** — Across all evaluated offers
- **High-fit Count** — Offers scored `>= 4.0`
- **Pending in Queue** — Count of `queued` records awaiting evaluation

---
## Final Output
Show a formatted table of the most recent tracked applications, followed by the pipeline summary:

```
📊 Pipeline Summary — {YYYY-MM-DD}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total tracked:    N
Queued (inbox):   N
Evaluated:        N
Applied:          N
In interview:     N
Offers received:  N

Avg score:        X.X/5

Top scores:
  • [#{seq_num:03d} | {id}] {Company} — {Role}: {Score}/5 ({Status})
  • ...
```

If the user asks to update a job's status, score, or notes, run:
```bash
career-ops track <vaga_id_or_seq> --status <new_status> [--score <score>] [--notes "<notes>"]
```
