import csv
import json
import re
from datetime import date
from pathlib import Path

import yaml

from career_ops.scan_csv import FIELDNAMES
from career_ops.utils import normalize_url

from .connectors import GITHUB_ATS_TYPES, MCP_ATS_TYPES, get_connector
from .models import JobPosting


class FetchOrchestrator:
    def __init__(self, root_dir: Path, config_path: Path, source: str = "all"):
        self.root_dir = root_dir
        self.config_path = config_path
        self.source = source
        self.tracker_path = root_dir / "workspace" / "job-tracker.csv"
        self.pipeline_path = root_dir / "workspace" / "pipeline.md"
        self.applications_path = root_dir / "workspace" / "applications.md"
        
        # Load config
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.suffix in [".yaml", ".yml"]:
                self.config = yaml.safe_load(f) or {}
            else:
                self.config = json.load(f)
                
        # Parse targets (support 'targets', 'tracked_companies', 'mcp_targets', 'github_targets')
        self.targets = []
        if "targets" in self.config:
            self.targets.extend(self.config["targets"])
            
        if "tracked_companies" in self.config:
            for comp in self.config["tracked_companies"]:
                # Map tracked_company schema to target dictionary schema
                ats_type = comp.get("ats") or comp.get("ats_type", "greenhouse")
                token = comp.get("token") or comp.get("company_token")
                name = comp.get("name") or token
                self.targets.append({
                    "company_name": name,
                    "company_token": token,
                    "ats_type": ats_type
                })

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
            "errors": 0
        }
        
        print("Loading dedup sources (applications.md, pipeline.md, job-tracker.csv)...")
        existing_urls, max_id, fieldnames = self._load_dedup_sources()
        next_id = max_id + 1
        
        new_postings: list[JobPosting] = []
        new_tracker_rows = []
        
        for target in self.targets:
            ats_type = target.get("ats_type", "greenhouse")
            company_name = target.get("company_name") or target.get("company_token") or target.get("query") or ats_type
            
            is_serp = (ats_type.lower() == "google")
            if is_serp:
                # Discard SERP completely: too noisy, dirty and full of expired jobs
                continue

            is_mcp = (ats_type.lower() in MCP_ATS_TYPES)
            is_github = (ats_type.lower() in GITHUB_ATS_TYPES)
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
                    
                # Deduplication check
                norm_url = normalize_url(job.url)
                if norm_url in existing_urls:
                    continue
                    
                # Keyword & Location Filtering
                if not self._passes_filter(job):
                    stats["filtered"] += 1
                    continue
                
                existing_urls.add(norm_url)
                new_postings.append(job)
                
                # For MCP / GitHub / aggregator targets, job.company carries the real employer name
                resolved_company = (
                    (job.company or target.get("company_name") or "").strip()
                    if (is_mcp or is_github)
                    else (target.get("company_name") or job.company or "").strip()
                )

                formatted_id = f"{next_id:03d}"
                today_iso = date.today().isoformat()
                jd_rel_path = ""
                if job.description:
                    jds_dir = self.root_dir / "workspace" / "jds"
                    try:
                        jds_dir.mkdir(parents=True, exist_ok=True)
                        jd_file = jds_dir / f"jd_{formatted_id}.md"
                        jd_file.write_text(job.description, encoding="utf-8")
                        jd_rel_path = f"workspace/jds/jd_{formatted_id}.md"
                    except Exception:
                        pass
                
                # Format row for job-tracker.csv (supports both 14-col and legacy 6-col schemas)
                tracker_row = {
                    "ID": formatted_id,
                    "URL": job.url,
                    "Company": resolved_company,
                    "Position": job.role,
                    "Job Description": job.description or "",
                    "Job Description Path": jd_rel_path,
                    "Status": "Queued",
                    "Score": "",
                    "Archetype": "",
                    "Added Date": today_iso,
                    "Application Date": "",
                    "Status Date": today_iso,
                    "Notes": "",
                    "Report Path": "",
                    "CV PDF Path": "",
                    "Processing Date": "",
                }
                complete_row = {f: tracker_row.get(f, "") for f in fieldnames}
                new_tracker_rows.append(complete_row)
                
                next_id += 1
                stats["saved"] += 1
                print(f"  + [{job.company or company_name}] [{job.role}]")

        # Save to pipeline.md & job-tracker.csv
        if new_postings:
            self._append_to_pipeline(new_postings)
            self._append_to_tracker(fieldnames, new_tracker_rows)
            print(f"\nSaved {len(new_postings)} new jobs to pipeline.md and job-tracker.csv.")
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
        if self.title_positives and not any(pos in title_text for pos in self.title_positives):
            return False
                
        # Location negatives
        if self.loc_negatives and any(neg in full_text for neg in self.loc_negatives):
            return False
                
        return True

    def _load_dedup_sources(self) -> tuple[set[str], int, list[str]]:
        urls = set()
        max_id = 0
        fieldnames = list(FIELDNAMES)
        
        # 1. job-tracker.csv
        if self.tracker_path.exists():
            with open(self.tracker_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=";")
                if reader.fieldnames:
                    fieldnames = list(reader.fieldnames)
                    
                for row in reader:
                    u = row.get("URL", "").strip()
                    if u:
                        urls.add(normalize_url(u))
                    try:
                        row_id = int(row.get("ID", 0))
                        max_id = max(max_id, row_id)
                    except ValueError:
                        pass
                        
        # 2. pipeline.md
        if self.pipeline_path.exists():
            text = self.pipeline_path.read_text(encoding="utf-8")
            for u in re.findall(r'https?://[^\s\|\]]+', text):
                urls.add(normalize_url(u))
                
        # 3. applications.md
        if self.applications_path.exists():
            text = self.applications_path.read_text(encoding="utf-8")
            for u in re.findall(r'https?://[^\s\|\]]+', text):
                urls.add(normalize_url(u))

        return urls, max_id, fieldnames

    def _append_to_pipeline(self, postings: list[JobPosting]):
        if not self.pipeline_path.exists():
            return
            
        content = self.pipeline_path.read_text(encoding="utf-8")
        pending_marker = "## Pending\n"
        
        # Read existing normalized URLs in pipeline.md to prevent duplicate appends
        existing_urls = set()
        for u in re.findall(r'https?://[^\s\|\]]+', content):
            existing_urls.add(normalize_url(u))

        lines_to_add = []
        for j in postings:
            norm = normalize_url(j.url)
            if norm not in existing_urls:
                existing_urls.add(norm)
                lines_to_add.append(f"- [ ] {j.url} | {j.company} | {j.role}")

        if not lines_to_add:
            return

        if pending_marker in content:
            parts = content.split(pending_marker)
            new_content = parts[0] + pending_marker + "\n".join(lines_to_add) + "\n" + parts[1].lstrip()
        else:
            new_content = content + "\n\n## Pending\n\n" + "\n".join(lines_to_add) + "\n"
            
        self.pipeline_path.write_text(new_content, encoding="utf-8")
        
    def _append_to_tracker(self, fieldnames: list[str], new_rows: list[dict]):
        if not new_rows:
            return

        # Load existing normalized URLs in job-tracker.csv to prevent duplicate row appends
        existing_urls = set()
        if self.tracker_path.exists():
            with open(self.tracker_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    u = row.get("URL", "").strip()
                    if u:
                        existing_urls.add(normalize_url(u))

        filtered_rows = []
        for r in new_rows:
            u = r.get("URL", "").strip()
            if u:
                norm = normalize_url(u)
                if norm not in existing_urls:
                    existing_urls.add(norm)
                    filtered_rows.append(r)

        if not filtered_rows:
            return

        file_exists = self.tracker_path.exists()
        with open(self.tracker_path, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f, 
                fieldnames=fieldnames, 
                delimiter=";", 
                quoting=csv.QUOTE_ALL,
                lineterminator="\r\n",
                extrasaction="ignore"
            )
            if not file_exists:
                writer.writeheader()
            writer.writerows(filtered_rows)
