# Setup Guide

## Prerequisites

- Python 3.11+
- `uv` (recommended) or standard `pip`
- Node.js 18+ (for Playwright resume rendering)

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/Rafacanedo/career-ops-v2.git
cd career-ops-v2
uv sync
```

### 2. Configure your profile

```bash
cp config/profile.example.yml config/profile.yml
```
Edit `config/profile.yml` with your contact details, target roles, and narrative proof points.

### 3. Add your personal CV

- Create `content/cv.md` with your canonical resume experience.
- (Optional) Create `content/story-bank.md` with STAR+R stories for interview prep.

### 4. Initialize database & verify setup

```bash
# Initialize local SQLite database
uv run career-ops init

# Check setup consistency
uv run career-ops sync-check
uv run career-ops verify
```

### 5. Common commands

```bash
# Scan configured job portals for new openings
uv run career-ops scan

# Ingest a single job posting URL
uv run career-ops intake <url>

# List tracked opportunities
uv run career-ops list

# Generate an ATS-optimized PDF resume
uv run career-ops cv --seq 001

# Build interactive HTML dashboard
uv run career-ops dashboard build
```
