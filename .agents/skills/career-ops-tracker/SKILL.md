---
name: career-ops-tracker
description: View application history and pipeline statistics.
---

# Career-Ops Tracker

Use this workflow to see the status of all your job applications and key metrics.

## Steps

### 📊 1. Load Data
1. Read `workspace/applications.md`.
2. Parse the full markdown table.

### 📈 2. Calculate Statistics
Compute the following:
- **Total Applications**
- **By Status** — Evaluated, Applied, Responded, Interview, Offer, Rejected, Discarded, SKIP
- **Average Score** — Across all evaluated offers
- **High-fit Count** — Offers scored >= 4.0
- **High-fit PDF Coverage** — % of entries scored >= 4.0 with PDF ✅
- **Report Coverage** — % of entries with a linked report
- **Conversion Rate** — Applied → Interview, Interview → Offer

### 🔍 3. Check Pipeline Status
Read `workspace/pipeline.md` and report:
- Number of URLs pending evaluation

---
## Final Output
Show a formatted table of the most recent applications (sorted by date desc), then the stats summary:

```
📊 Pipeline Summary — {YYYY-MM-DD}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total tracked:    N
Applied:          N
In interview:     N
Offers received:  N

Avg score:        X.X/5
High-fit PDFs:    N (X%)
Pending in inbox: N

Top scores this week:
  • {Company} — {Role}: {Score}/5 ✅
  • ...
```

If the user asks to update a status, edit the corresponding row in `workspace/applications.md` directly.
