# career-ops-python 🚀

A comprehensive Python-powered CLI and agentic workflow system for managing your career pipeline. This project automates the tedious parts of job hunting: tracking applications, evaluating job descriptions against your profile, and generating tailored ATS-optimized resumes.

> [!NOTE]
> This project is the Python successor to the original Node.js utilities, providing a unified CLI and deep integration with AI agents.

## 🌟 Key Features

- **Automated Scanning**: Extract job details from URLs or CSV files using direct APIs (Greenhouse, Lever, etc.) or smart scraping.
- **AI Evaluation**: Grade job opportunities against your professional archetypes.
- **Resume Tailoring**: Generate custom PDF resumes for high-fit roles that strictly follow project layout rules.
- **Pipeline Integrity**: Maintain a clean, de-duplicated, and normalized `applications.md` tracker.
- **Agent-Ready**: Pre-configured markdown workflows for use with coding assistants.

## 🛠 Requirements

- **Python 3.11+**
- [**`uv`**](https://docs.astral.sh/uv/) (highly recommended for dependency management)
- **Node.js** (required only for `generate-pdf.mjs` which handles Playwright rendering)

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/Rafacanedo/career-ops-python.git
cd career-ops-python

# Install dependencies and the CLI
uv sync
```

## ⚙️ Configuration

The tools need to know where your career data (like `applications.md` and `profile.yml`) lives. By default, the CLI looks in the **current working directory**.

If you are running the tools from outside the project folder, you can set the `CAREER_OPS_ROOT` environment variable:

```powershell
# Windows (PowerShell)
$env:CAREER_OPS_ROOT = "C:\Users\Rafael.Canedo\Projects\career-ops-python"
```

Alternatively, pass the `--root` flag to any command:
`career-ops --root . verify`

## ⌨️ CLI Commands

| Command | Description |
|:---|:---|
| `career-ops scan-csv` | Queues new rows from `workspace/job-tracker.csv` into `workspace/pipeline.md`, saving local JDs when present. |
| `career-ops verify` | Checks `workspace/applications.md` and pending tracker additions for broken links, bad statuses, and format issues. |
| `career-ops normalize` | Rewrites non-canonical statuses in `workspace/applications.md` to the supported state set. |
| `career-ops dedup` | Removes or flags duplicate application rows in `workspace/applications.md`. |
| `career-ops merge` | Merges TSV files from `workspace/tracker-additions/` into `workspace/applications.md`. |
| `career-ops cv` | Calls the PDF generator to turn tailored HTML into a final resume PDF under `workspace/output/`. |
| `career-ops export` | Writes Excel-friendly CSV exports for `applications.md` and `pipeline.md` into `workspace/output/`. |
| `career-ops dashboard build` | Builds `workspace/output/dashboard.html` from the current application tracker. |
| `career-ops sync-check` | Validates that required setup files like `content/cv.md` and `config/profile.yml` are present and coherent. |
| `career-ops pipeline-clean` | Removes already-processed or reposted pending items from `workspace/pipeline.md`. |

## 🤖 Agentic Workflows

This repository includes a set of `.agents/workflows` that turn an AI assistant into a career coach. These are accessible via slash commands in supported environments:

- `/career-ops`: Checks setup and routes you to the right workflow or CLI command.
- `/career-ops-apply`: Drafts tailored answers for application forms using an existing evaluation report.
- `/career-ops-archetypes`: Derives your target role personas and strategic positioning from your base profile.
- `/career-ops-cv`: Produces the final tailored resume PDF for a specific evaluated role.
- `/career-ops-evaluate`: Scores a job against your profile and writes a report to `workspace/reports/`.
- `/career-ops-gupy`: Handles Gupy-specific application flow and portal interaction.
- `/career-ops-interview-prep`: Generates likely interview questions and grounded answer material from a report.
- `/career-ops-pipeline`: Processes all pending items in `workspace/pipeline.md` through the evaluation flow.
- `/career-ops-scan`: Finds new matching roles and adds them to the supported workspace queue flow.
- `/career-ops-tracker`: Summarizes application history, coverage, and current pipeline counts.

## 📂 Project Structure

```text
career-ops-python/
├── .agents/workflows/ # AI Agent instruction sets
├── src/career_ops/    # Core Python CLI logic
│   ├── scan_csv.py    # CSV ingestion and API extraction
│   ├── cv.py          # CV generation wrapper (PDF)
│   ├── cli.py         # Command entry points
│   └── ...            # Business logic (verify, dedup, merge, etc.)
├── workspace/         # Your personal tracker, reports, JDs, and outputs
├── tests/             # Comprehensive test suite
└── pyproject.toml     # Dependency definitions (uv-ready)
```

Important workspace files:
- `workspace/applications.md`
- `workspace/pipeline.md`
- `workspace/job-tracker.csv`
- `workspace/reports/`
- `workspace/output/`

## 🧪 Development

```bash
# Run all tests
uv run pytest tests/ -v

# Run a specific test file
uv run pytest tests/test_normalize.py -v
```

---
*Based on the original [career-ops](https://github.com/santifer/career-ops) project.*
