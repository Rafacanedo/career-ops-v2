---
name: career-ops
description: Career-Ops Main Menu & Onboarding
---

# Career-Ops Main Menu

Use this workflow to check the status of your Career-Ops setup and see all available commands.

## Step 1 — Setup Check

Before doing ANYTHING else, validate the environment using the CLI:

1. Run the command `career-ops sync-check`.
2. Ensure the following core files exist in their correct locations:
   - `content/cv.md` — Your master resume (required)
   - `config/profile.yml` — Your identity, target roles, and narrative (required)
   - `config/portals.yml` — Portal scanner configuration (recommended)
   - `data/career_ops.db` — Embedded SQLite relational database (auto-initialized via `career-ops init` if missing)

If `data/career_ops.db` is missing, initialize it by running:

```bash
career-ops init
```

### Onboarding Mode

If core files are missing or `sync-check` fails, follow these steps:

- **Missing Database:** Run `career-ops init` to create `data/career_ops.db`.
- **Missing CV:** Ask the user to paste their CV or LinkedIn URL. Create `content/cv.md` with the content.
- **Missing Profile:** Copy `config/profile.example.yml` → `config/profile.yml`. Ask for: **Full Name, Email, Location** and **Target Roles**.
- **Missing Portals:** Copy `assets/templates/portals.example.yml` → `config/portals.yml`. Adjust the `title_filter` to match the target roles.
- **Confirm:** Rerun `career-ops sync-check` to ensure everything is 🟢.

---

## Step 2 — Choose Your Path

After confirming setup, you can interact with the system via **Agent Skills / Workflows** (for semantic reasoning) or **CLI Commands** (for deterministic data operations).

### Agent Skills (Usage: `/<name>`)

#### Discovery & Queue
- `/career-ops-archetypes` — Generate 5 strategic personas from your CV (do this first).
- `/career-ops-scan` — Scan external portals and companies for new roles into SQLite.
- `/career-ops-pipeline` — Process all queued roles (`status = queued`) in SQLite (ideal for batch evaluation).

#### Evaluation & Generation
- `/career-ops-evaluate` — Evaluate a job ID, URL, or description; generate Sections F/G and tailored PDF for scores >= 4.0.
- `/career-ops-cv` — Generate the final customized PDF resume for a specific job.

#### Application
- `/career-ops-apply` — Generate personalized answers for application forms and record `applied` status.
- `/career-ops-interview-prep` — Generate likely recruiter/interview questions and grounded answers from a completed report.

#### Tracking
- `/career-ops-tracker` — View application history and pipeline statistics via `career-ops stats` and `career-ops list`.

---

### CLI Commands (Usage: `career-ops <command>`)

Use the terminal for deterministic ingestion, querying, and lifecycle tracking:
- `career-ops init` — Initialize the SQLite relational database at `data/career_ops.db`.
- `career-ops intake <url>` — Fetch and ingest a single job posting URL into SQLite.
- `career-ops intake-raw --company <c> --role <r> --url <u> --desc-file <path>` — Ingest pre-extracted job details directly into SQLite.
- `career-ops scan` — Run configured ATS, MCP, and GitHub scanners into SQLite with automatic deduplication.
- `career-ops list [--status <status>] [--limit <n>]` — List compact job metadata without loading full-text descriptions into context.
- `career-ops show <id> [--full]` — Retrieve metadata and optionally the full job description (`--full`) for a single record.
- `career-ops track <id> --status <status> [--score <score>] [--archetype <name>] [--report <path>] [--pdf <path>]` — Update candidate lifecycle state and artifact pointers.
- `career-ops stats` — Output pipeline count summaries and average fit score.
- `career-ops export [--format csv|json|html]` — Export tracker records or build the interactive HTML dashboard in `workspace/output/`.
- `career-ops verify` — Deep health check of SQLite database integrity and referenced report/PDF files on disk.
- `career-ops sync-check` — Validate environment setup (`cv.md`, `profile.yml`, `data/career_ops.db`).

---

### Language Support
Language detection is automatic based on the **Job Description**:
- **Portuguese (BR)**: If the JD is in PT-BR, I will output reports, CV summaries, and form answers in Portuguese.
- **English**: Default for all other cases.

### 💡 Pro Tip
You don't always need to call a workflow. Just **paste a job URL or description** here, and I will automatically ingest it into SQLite and trigger the `/career-ops-evaluate` pipeline for you.
