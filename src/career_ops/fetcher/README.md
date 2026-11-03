# Job Posting Fetcher (`src/career_ops/fetcher`)

## Overview
Deterministic ATS connector engine and job description extraction pipeline supporting direct REST API integration, MCP endpoints, GitHub issue scrapers, Schema.org JSON-LD / OpenGraph HTML fallback extraction, and SQLite ingestion orchestration.

## Interface
- `[models.py:JobPosting]`: Primary data structure storing normalized job records (`id`, `company`, `role`, `url`, `location`, `description`, `ats_type`, `raw_payload`).
- `[models.py:JobPosting.to_csv_row]`: Serializes job posting into legacy CSV dictionary format with processing timestamp.
- `[connectors.py:BaseConnector]`: Abstract base class requiring `fetch_jobs(target: dict) -> list[JobPosting]` and providing resilient `safe_get`.
- `[connectors.py:BaseConnector.safe_get]`: Resilient HTTP GET wrapper with automatic headers, timeout handling, and 404 suppression.
- `[connectors.py:GreenhouseConnector]`: Ingests postings via Greenhouse Board API (`/v1/boards/{company}/jobs?content=true`).
- `[connectors.py:LeverConnector]`: Ingests postings via Lever REST API (`/v0/postings/{company}?mode=json`).
- `[connectors.py:AshbyConnector]`: Ingests postings via Ashby API (`/posting-api/job-board/{company}`).
- `[connectors.py:RecruiteeConnector]`: Ingests postings via Recruitee API (`/api/offers/`).
- `[connectors.py:BreezyConnector]`: Ingests postings via Breezy HR API (`/json/postings`).
- `[connectors.py:GoogleSearchConnector]`: Ingests Google Jobs SERP data via SearchAPI or SerpApi.
- `[connectors.py:InhireConnector]`: Ingests tech jobs from Inhire.io API.
- `[connectors.py:EightfoldConnector]`: Ingests postings from Eightfold and Mercado Libre career portals.
- `[connectors.py:WorkableConnector]`: Ingests postings via Workable API (`/api/v1/widget/accounts/{company}`).
- `[connectors.py:SmartRecruitersConnector]`: Ingests postings via SmartRecruiters REST API (`/v1/companies/{company}/postings`).
- `[connectors.py:BaseMCPConnector]`: Base class for remote MCP JSON-RPC job sources.
- `[connectors.py:GupyMCPConnector]`: Ingests Gupy portal listings via MCP endpoint.
- `[connectors.py:HimalayasMCPConnector]`: Ingests remote tech jobs from Himalayas via MCP.
- `[connectors.py:JobicyMCPConnector]`: Ingests remote postings from Jobicy via MCP.
- `[connectors.py:JobStackMCPConnector]`: Ingests developer listings from JobStack via MCP.
- `[connectors.py:GitHubIssuesConnector]`: Ingests curated remote tech jobs from community GitHub issues repositories (e.g. `backend-br/vagas`, `datascience-br/vagas`).
- `[connectors.py:CONNECTORS]`: Mapping dictionary resolving ATS identifiers to connector classes.
- `[connectors.py:get_connector]`: Factory function performing case-insensitive connector instantiation.
- `[connectors.py:fetch_single_url]`: Deterministically fetches a single job posting from an ATS URL (Greenhouse, Lever, Inhire) or HTML page (Schema.org `JobPosting` JSON-LD / OpenGraph fallback) without LLM calls.
- `[orchestrator.py:FetchOrchestrator]`: Batch orchestrator executing job queries across configured portal targets.
- `[orchestrator.py:FetchOrchestrator.run]`: Main execution loop filtering fetched jobs and inserting new records atomically into SQLite via `CareerOpsRepository.insert_vaga()`.

## Invariants
- `[models.py:JobPosting.to_csv_row]`: Returns dictionary matching 6-field legacy CSV schema with string ID and given processing date.
- `[connectors.py:BaseConnector.safe_get]`: Catches HTTPError and general exceptions, returning `None` (suppressing 404 when `silent_404=True`).
- `[connectors.py:GreenhouseConnector.fetch_jobs]`: Returns empty list if `company_token` is missing or if content and simple requests fail.
- `[connectors.py:LeverConnector.fetch_jobs]`: Returns empty list if `company_token` is missing or if response payload is not a list.
- `[connectors.py:AshbyConnector.fetch_jobs]`: Returns empty list if `company_token` is missing or if request/parsing fails.
- `[connectors.py:WorkableConnector.fetch_jobs]`: Returns empty list if `company_token` is missing or response status code != 200.
- `[connectors.py:BaseMCPConnector.call_tool]`: Returns `None` if `mcp_url` is empty, status != 200, or stream/content block does not contain text payload.
- `[connectors.py:GupyMCPConnector.fetch_jobs]`: Clamps limit parameter to range `[1, 100]` and deduplicates postings by URL via `seen_urls` set.
- `[connectors.py:JobicyMCPConnector.fetch_jobs]`: Clamps limit parameter to range `[1, 50]` and deduplicates postings by URL via `seen_urls` set.
- `[connectors.py:GitHubIssuesConnector.fetch_jobs]`: Skips issue items containing `pull_request` and halts iteration when issue age exceeds `max_days`.
- `[connectors.py:get_connector]`: Performs case-insensitive lookup in `CONNECTORS` mapping, instantiating matching class or returning `None`.
- `[connectors.py:fetch_single_url]`: Prioritizes direct ATS API endpoints (Greenhouse, Lever, Inhire) before falling back to deterministic JSON, Schema.org `JobPosting` JSON-LD, or OpenGraph HTML extraction; returns `(None, "web")` when extraction fails.
- `[orchestrator.py:FetchOrchestrator.__init__]`: Raises `FileNotFoundError` if `config_path` does not exist; initializes `CareerOpsRepository` targeting `data/career_ops.db` under `root_dir` (unless overridden).
- `[orchestrator.py:FetchOrchestrator.run]`: Filters targets by `source` (`'all'`, `'ats'`, `'mcp'`, `'github'`); streams matching postings into `CareerOpsRepository.insert_vaga()` with database-enforced `canonical_url` deduplication.
- `[orchestrator.py:FetchOrchestrator._passes_filter]`: Rejects posting if any negative title keyword matches `job.role`, or positive title keywords exist and none match `job.role`, or negative location keywords match full text.

## Side Effects
- `[connectors.py:BaseConnector.safe_get]` / `[connectors.py:fetch_single_url]`: Performs outbound HTTP GET network requests via `requests.get`.
- `[connectors.py:GoogleSearchConnector.fetch_jobs]`: Performs outbound HTTP GET network requests to SearchAPI / SerpApi and reads `SEARCHAPI_API_KEY` / `SERPAPI_API_KEY` environment variables.
- `[connectors.py:EightfoldConnector.fetch_jobs]`: Performs outbound HTTP GET network requests to Eightfold and Mercado Libre endpoints.
- `[connectors.py:WorkableConnector.fetch_jobs]`: Performs outbound HTTP POST network request to Workable API endpoint.
- `[connectors.py:BaseMCPConnector.call_tool]`: Performs outbound HTTP POST JSON-RPC network request to `mcp_url`.
- `[connectors.py:GitHubIssuesConnector.fetch_jobs]`: Reads `GITHUB_TOKEN` environment variable and performs outbound HTTP GET requests to GitHub API.
- `[orchestrator.py:FetchOrchestrator.__init__]`: Reads configuration YAML/JSON file from disk at `config_path` and initializes SQLite schema at `db_path`.
- `[orchestrator.py:FetchOrchestrator.run]`: Inserts job metadata and descriptions into SQLite (`vagas` and `vaga_descricoes`) via `CareerOpsRepository` and prints progress logs to stdout.

## Verification
- Run: `uv run pytest tests/test_connectors.py -v`
