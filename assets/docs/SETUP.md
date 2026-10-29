# Setup Guide

## Prerequisites

- Python 3.11+
- `uv`
- Node.js 18+ for `generate-pdf.mjs`

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/Rafacanedo/career-ops-python.git
cd career-ops-python
uv sync
```

### 2. Configure your profile

```bash
cp config/profile.example.yml config/profile.yml
```

### 3. Add your personal content

- `content/cv.md`
- `content/story-bank.md` if you use interview-prep workflows
- `workspace/applications.md` as your application source of truth
- `workspace/pipeline.md` as your pending URL inbox

### 4. Verify the setup

```bash
uv run career-ops sync-check
uv run career-ops verify
```

### 5. Common commands

```bash
uv run career-ops scan-csv
uv run career-ops merge
uv run career-ops export
uv run career-ops dashboard build
```

## Notes

- The active data contract uses `workspace/`, not `data/`.
- The old Go TUI dashboard is not part of this repository.
- `batch_cv.py` is deprecated and unsupported; use the CLI commands instead.
