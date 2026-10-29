# Architecture

## System Overview

The active implementation is a Python CLI centered on the `workspace/` user-data contract.

```text
content/cv.md + config/profile.yml + workspace/*
                |
                v
          career-ops CLI
                |
    +-----------+-----------+-----------+
    |           |           |           |
 verify    normalize    merge/export  dashboard
                |
                v
     workspace/applications.md
```

## Core Data Flow

- `workspace/pipeline.md` is the pending URL inbox.
- `workspace/job-tracker.csv` is the optional spreadsheet-synced tracker.
- `workspace/applications.md` is the application source of truth.
- `workspace/reports/` stores report markdown.
- `workspace/output/` stores generated artifacts such as PDFs, CSV exports, and dashboard HTML.
- `config/states.yml` is the canonical pipeline state definition.

## Current Commands

- `verify`, `normalize`, `dedup`, and `merge` maintain tracker integrity.
- `scan-csv` queues new opportunities from `workspace/job-tracker.csv`.
- `cv` wraps `generate-pdf.mjs` for PDF generation.
- `export` writes CSV exports from the current workspace tracker files.
- `dashboard build` generates a static HTML dashboard from `workspace/applications.md`.

## Legacy Notes

- The old Node `.mjs` utility naming in earlier docs is obsolete; the supported surface is the Python CLI.
- References to `data/` as the primary tracker location are obsolete; the current contract uses `workspace/`.
- The old Go TUI dashboard is not part of this repository.
