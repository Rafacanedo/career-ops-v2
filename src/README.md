# Source Directory (`src`)

## Overview
Root source tree containing the deterministic Python implementation of the `career-ops` SQLite relational pipeline, CLI commands, and ATS ingestion utilities.

## Subdirectories & Boundaries
- `[career_ops](./career_ops/README.md)`: Core package providing the Click CLI (`cli.py`), SQLite connection & schema manager (`db.py`), transactional repository (`repository.py`), domain models (`models.py`), normalization utilities (`utils.py`), report/artifact verification (`verify.py`), and the `[fetcher](./career_ops/fetcher/README.md)` ingestion subpackage.
