---
name: career-ops
description: Career-Ops Main Menu & Onboarding
---

# Career-Ops Main Menu

Use this workflow to check the status of your Career-Ops setup and see all available commands.

## Step 1 — Setup Check

Before doing ANYTHING else, validate the environment using the CLI:

1. Run the **Comando** `career-ops sync-check`.
2. Ensure the following core files exist in their correct locations:
   - `content/cv.md` — Your master resume (required)
   - `config/profile.yml` — Your identity, target roles, and narrative (required)
   - `config/portals.yml` — Portal scanner configuration (recommended)
   - `workspace/applications.md` — Application tracker (auto-created if missing)

If `workspace/applications.md` is missing, create it with this header:

```markdown

# Applications Tracker
| ID | Date | Company | Role | Score | Status | PDF | Report | Notes |
|----|------|---------|------|-------|--------|-----|--------|-------|

```

### Onboarding Mode

If core files are missing or `sync-check` fails, follow these steps:

- **Missing CV:** Ask the user to paste their CV or LinkedIn URL. Create `content/cv.md` with the content.
- **Missing Profile:** Copy `config/profile.example.yml` → `config/profile.yml`. Ask for: **Full Name, Email, Location** and **Target Roles**.
- **Missing Portals:** Copy `assets/templates/portals.example.yml` → `config/portals.yml`. Adjust the `title_filter` to match the target roles.
- **Confirm:** Rerun `career-ops sync-check` to ensure everything is 🟢.

---

## Step 2 — Choose Your Path

After confirming setup, you can interact with the system via **Agent Skills / Workflows** (for reasoning) or **CLI Commands** (for data operations).

### Agent Skills (Usage: `/<name>`)

#### Discovery & Queue
- `/career-ops-archetypes` — Generate 5 strategic personas from your CV (do this first).
- `/career-ops-scan` — Scan external portals and companies for new roles.
- `/career-ops-pipeline` — Process all URLs in your `pipeline.md` (ideal for batch processing).

#### Evaluation & Generation
- `/career-ops-evaluate` — Evaluate a job URL/description; generate F/G and tailored PDF for scores >= 4.0.
- `/career-ops-cv` — Generate the final customized PDF resume for a specific job.

#### Application
- `/career-ops-apply` — Generate personalized answers for application forms.
- `/career-ops-interview-prep` — Generate likely recruiter/interview questions and grounded answers from a completed report.

#### Tracking
- `/career-ops-tracker` — View application history and pipeline statistics.

---

### CLI Commands (Usage: `career-ops <command>`)

Use the terminal for batch data management and integrity:
- `career-ops scan-csv` — Sync new jobs from `job-tracker.csv` into the pipeline.
- `career-ops export` — Export your applications and pipeline to Excel-friendly CSVs.
- `career-ops verify` — Deep health check of the entire pipeline integrity.
- `career-ops normalize` — Fix and canonicalize statuses in your tracker.

---

### Language Support
Language detection is automatic based on the **Job Description**:
- **Portuguese (BR)**: If the JD is in PT-BR, I will output reports, CV summaries, and form answers in Portuguese.
- **English**: Default for all other cases.

### 💡 Pro Tip
You don't always need to call a workflow. Just **paste a job URL or description** here, and I will automatically trigger the `/career-ops-evaluate` pipeline for you.
