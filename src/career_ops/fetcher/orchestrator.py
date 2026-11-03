from __future__ import annotations

import json
from pathlib import Path

import yaml

from career_ops.config import get_db_path
from career_ops.models import VagaInput
from career_ops.repository import CareerOpsRepository

from .connectors import GITHUB_ATS_TYPES, MCP_ATS_TYPES, get_connector
from .models import JobPosting


class FetchOrchestrator:
    def __init__(
        self,
        root_dir: Path,
        config_path: Path,
        source: str = "all",
        repository: CareerOpsRepository | None = None,
        db_path: Path | None = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.config_path = Path(config_path)
        self.source = source
        resolved_db_path = (
            Path(db_path) if db_path is not None else get_db_path(self.root_dir)
        )
        self.repository = repository or CareerOpsRepository(db_path=resolved_db_path)

        # Load config
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            if self.config_path.suffix in [".yaml", ".yml"]:
                self.config = yaml.safe_load(f) or {}
            else:
                self.config = json.load(f)

        # Parse targets (support 'targets', 'tracked_companies', 'mcp_targets', 'github_targets')
        self.targets: list[dict] = []
        if "targets" in self.config:
            self.targets.extend(self.config["targets"])

        if "tracked_companies" in self.config:
            for comp in self.config["tracked_companies"]:
                # Map tracked_company schema to target dictionary schema
                ats_type = comp.get("ats") or comp.get("ats_type", "greenhouse")
                token = comp.get("token") or comp.get("company_token")
                name = comp.get("name") or token
                self.targets.append(
                    {
                        "company_name": name,
                        "company_token": token,
                        "ats_type": ats_type,
                    }
                )

        if "mcp_targets" in self.config:
            for mcp_target in self.config["mcp_targets"]:
                target_copy = dict(mcp_target)
                if "ats_type" not in target_copy and "mcp" in target_copy:
                    target_copy["ats_type"] = target_copy["mcp"]
                elif "ats_type" not in target_copy and "ats" in target_copy:
                    target_copy["ats_type"] = target_copy["ats"]
                if "company_name" not in target_copy and "name" in target_copy:
                    target_copy["company_name"] = target_copy["name"]
                self.targets.append(target_copy)

        if "github_targets" in self.config:
            for gh_target in self.config["github_targets"]:
                target_copy = dict(gh_target)
                if "ats_type" not in target_copy:
                    target_copy["ats_type"] = "github_issues"
                if "company_name" not in target_copy and "name" in target_copy:
                    target_copy["company_name"] = target_copy["name"]
                self.targets.append(target_copy)

        # Parse title filters
        title_cfg = self.config.get("title_filter", {})
        if isinstance(title_cfg, dict):
            self.title_positives = [k.lower() for k in title_cfg.get("positive", [])]
            self.title_negatives = [k.lower() for k in title_cfg.get("negative", [])]
        else:
            self.title_positives = [k.lower() for k in self.config.get("keywords", [])]
            self.title_negatives = []

        # Parse location filters
        loc_cfg = self.config.get("location_filter", {})
        if isinstance(loc_cfg, dict):
            self.loc_positives = [k.lower() for k in loc_cfg.get("positive", [])]
            self.loc_negatives = [k.lower() for k in loc_cfg.get("negative", [])]
        else:
            self.loc_positives = []
            self.loc_negatives = []

    def run(self) -> dict:
        stats = {
            "fetched": 0,
            "filtered": 0,
            "saved": 0,
            "errors": 0,
        }

        for target in self.targets:
            ats_type = target.get("ats_type", "greenhouse")
            company_name = (
                target.get("company_name")
                or target.get("company_token")
                or target.get("query")
                or ats_type
            )

            is_serp = str(ats_type).lower() == "google"
            if is_serp:
                # Discard SERP completely: too noisy, dirty and full of expired jobs
                continue

            is_mcp = str(ats_type).lower() in MCP_ATS_TYPES
            is_github = str(ats_type).lower() in GITHUB_ATS_TYPES
            is_ats = not is_mcp and not is_github

            if self.source == "ats" and not is_ats:
                continue
            if self.source == "mcp" and not is_mcp:
                continue
            if self.source == "github" and not is_github:
                continue

            print(f"Processing target: {company_name} ({ats_type})")

            connector = get_connector(ats_type)
            if not connector:
                print(f"  [!] Unknown ATS type: {ats_type}")
                stats["errors"] += 1
                continue

            try:
                jobs = connector.fetch_jobs(target)
            except Exception as e:
                print(f"  [!] Error fetching jobs for {company_name}: {e}")
                stats["errors"] += 1
                continue

            stats["fetched"] += len(jobs)

            for job in jobs:
                if not job.url:
                    continue

                # Keyword & Location Filtering
                if not self._passes_filter(job):
                    stats["filtered"] += 1
                    continue

                # For MCP / GitHub / aggregator targets, job.company carries the real employer name
                resolved_company = (
                    (job.company or target.get("company_name") or "").strip()
                    if (is_mcp or is_github)
                    else (target.get("company_name") or job.company or "").strip()
                ) or str(company_name)

                vaga_input = VagaInput(
                    original_url=job.url,
                    company=resolved_company,
                    role=job.role,
                    source_portal=str(ats_type).lower(),
                    location=getattr(job, "location", None),
                    remote_type=getattr(job, "remote_type", None),
                )

                try:
                    vaga_id, is_new = self.repository.insert_vaga(
                        vaga_input,
                        descricao=job.description or "",
                    )
                except Exception as e:
                    print(f"  [!] Error inserting job {job.url}: {e}")
                    stats["errors"] += 1
                    continue

                if is_new:
                    stats["saved"] += 1
                    print(f"  + [{vaga_id}] [{resolved_company}] [{job.role}]")

        if stats["saved"] > 0:
            print(
                f"\nSaved {stats['saved']} new jobs to SQLite database ({self.repository.db_path})."
            )
        else:
            print("\nNo new jobs found after filtering and deduplication.")

        return stats

    def _passes_filter(self, job: JobPosting) -> bool:
        title_text = job.role.lower()
        full_text = f"{job.role} {job.description}".lower()

        # Title negatives
        if any(neg in title_text for neg in self.title_negatives):
            return False

        # Title positives (if specified)
        if self.title_positives and not any(
            pos in title_text for pos in self.title_positives
        ):
            return False

        # Location negatives
        if self.loc_negatives and any(neg in full_text for neg in self.loc_negatives):
            return False

        return True
