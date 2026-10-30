import re
import os
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from .models import JobPosting

class BaseConnector(ABC):
    @abstractmethod
    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        pass
        
    def safe_get(self, url: str, params: Optional[dict] = None, silent_404: bool = True) -> Optional[requests.Response]:
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp
        except requests.exceptions.HTTPError as http_err:
            if resp.status_code == 404 and silent_404:
                return None
            return None
        except Exception:
            return None


class GreenhouseConnector(BaseConnector):
    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        company = target.get('company_token')
        if not company:
            return []
            
        url_with_content = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
        resp = self.safe_get(url_with_content, silent_404=True)
        
        # Fallback without content=true if content=true is not supported or 404
        if not resp:
            url_simple = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
            resp = self.safe_get(url_simple, silent_404=True)
            
        if not resp:
            return []
            
        try:
            data = resp.json()
            jobs = data.get("jobs", [])
            postings = []
            for job in jobs:
                title = job.get("title", "")
                url = job.get("absolute_url", "")
                content = job.get("content", "")
                if title and url:
                    postings.append(JobPosting(
                        url=url,
                        description=content,
                        company=company,
                        role=title
                    ))
            return postings
        except Exception:
            return []


class LeverConnector(BaseConnector):
    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        company = target.get('company_token')
        if not company:
            return []
            
        url = f"https://api.lever.co/v0/postings/{company}"
        resp = self.safe_get(url, silent_404=True)
        if not resp:
            return []
            
        try:
            jobs = resp.json()
            if not isinstance(jobs, list):
                return []
            postings = []
            for job in jobs:
                title = job.get("text", "")
                url = job.get("hostedUrl", "")
                desc = job.get("descriptionPlain", job.get("description", ""))
                if title and url:
                    postings.append(JobPosting(
                        url=url,
                        description=desc,
                        company=company,
                        role=title
                    ))
            return postings
        except Exception:
            return []


class AshbyConnector(BaseConnector):
    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        company = target.get('company_token')
        if not company:
            return []
            
        url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
        resp = self.safe_get(url, silent_404=True)
        if not resp:
            return []
            
        try:
            data = resp.json()
            jobs = data.get("jobs", [])
            postings = []
            for job in jobs:
                title = job.get("title", "")
                url = job.get("jobUrl", "")
                desc = job.get("descriptionHtml", "")
                if title and url:
                    postings.append(JobPosting(
                        url=url,
                        description=desc,
                        company=company,
                        role=title
                    ))
            return postings
        except Exception:
            return []


class RecruiteeConnector(BaseConnector):
    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        company = target.get('company_token')
        if not company:
            return []
            
        url = f"https://{company}.recruitee.com/api/offers"
        resp = self.safe_get(url, silent_404=True)
        if not resp:
            return []
            
        try:
            data = resp.json()
            offers = data.get("offers", [])
            postings = []
            for offer in offers:
                title = offer.get("title", "")
                url = offer.get("careers_url", "")
                desc = offer.get("description", "")
                if title and url:
                    postings.append(JobPosting(
                        url=url,
                        description=desc,
                        company=company,
                        role=title
                    ))
            return postings
        except Exception:
            return []


class BreezyConnector(BaseConnector):
    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        company = target.get('company_token')
        if not company:
            return []
            
        url = f"https://{company}.breezy.hr/json"
        resp = self.safe_get(url, silent_404=True)
        if not resp:
            return []
            
        try:
            jobs = resp.json()
            if not isinstance(jobs, list):
                return []
            postings = []
            for job in jobs:
                title = job.get("name", "")
                url = job.get("url", "")
                if title and url:
                    postings.append(JobPosting(
                        url=url,
                        description="",
                        company=company,
                        role=title
                    ))
            return postings
        except Exception:
            return []


class GoogleSearchConnector(BaseConnector):
    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        api_key = target.get("api_key") or os.environ.get("SEARCHAPI_API_KEY") or os.environ.get("SERPAPI_API_KEY")
        if not api_key:
            return []

        query = target.get("query", "Data Analyst")
        location = target.get("location", "Brazil")
        chips = target.get("chips")
        max_pages = int(target.get("max_pages", 3))

        url = "https://www.searchapi.io/api/v1/search"
        params = {
            "engine": "google_jobs",
            "q": query,
            "location": location,
            "gl": "br",
            "hl": "pt",
            "api_key": api_key
        }
        
        if chips:
            params["chips"] = chips

        postings = []
        page_count = 0
        
        while page_count < max_pages:
            page_count += 1
            try:
                response = requests.get(url, params=params, timeout=10)
                results = response.json()
            except Exception:
                break

            if "error" in results:
                break

            jobs_results = results.get("jobs", [])
            if not jobs_results:
                break
                
            for job in jobs_results:
                title = job.get("title", "")
                company = job.get("company_name", "")
                link = job.get("apply_link", "")
                
                if not link and job.get("apply_links"):
                    link = job.get("apply_links")[0].get("link", "")
                    
                description = job.get("description", "")
                
                if link and title:
                    postings.append(
                        JobPosting(
                            url=link,
                            description=description,
                            company=company,
                            role=title
                        )
                    )
            
            next_page_token = results.get("pagination", {}).get("next_page_token") or results.get("next_page_token")
            if next_page_token:
                params["next_page_token"] = next_page_token
            else:
                break

        return postings


class InhireConnector(BaseConnector):
    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        target_val = target.get('job_id') or target.get('url') or target.get('company_token') or ""
        match = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', target_val, re.IGNORECASE)
        job_id = match.group(0) if match else target_val
        if not job_id:
            return []
            
        url = f"https://api.inhire.app/job-posts/public/pages/{job_id}"
        resp = self.safe_get(url, silent_404=True)
        if not resp:
            return []
            
        try:
            data = resp.json()
            title = data.get("displayName") or data.get("title") or ""
            company = data.get("tenantName") or ""
            desc = data.get("description") or ""
            job_url = target.get('url') or f"https://api.inhire.app/job-posts/public/pages/{job_id}"
            
            if title:
                return [JobPosting(
                    url=job_url,
                    description=desc,
                    company=company,
                    role=title
                )]
            return []
        except Exception:
            return []


class EightfoldConnector(BaseConnector):
    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        company_token = target.get('company_token') or "mercadolibre"
        domain = target.get('domain') or f"{company_token}.com"
        company_name = target.get('company_name') or company_token

        # 1. Try Eightfold general list endpoint: https://{company_token}.eightfold.ai/api/apply/v2/jobs
        list_url = f"https://{company_token}.eightfold.ai/api/apply/v2/jobs?domain={domain}&start=0&num=200"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        try:
            r = requests.get(list_url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                positions = data.get("positions", []) or data.get("jobs", [])
                postings = []
                for pos in positions:
                    pos_id = pos.get("id")
                    title = pos.get("name") or pos.get("title", "")
                    desc = pos.get("job_description", "")
                    canonical_url = pos.get("canonicalPositionUrl")
                    if not canonical_url and pos_id:
                        canonical_url = f"https://{company_token}.eightfold.ai/careers/job/{pos_id}"
                    if title and canonical_url:
                        postings.append(JobPosting(
                            url=canonical_url,
                            description=desc,
                            company=company_name,
                            role=title
                        ))
                if postings:
                    return postings
        except Exception:
            pass

        # 2. Try Mercado Libre careers API as special fallback
        if company_token.lower() in ("mercadolibre", "mercado-livre", "mercado_livre"):
            positions_url = "https://careers-meli.mercadolibre.com/api/positions?start=0&limit=200"
            resp = self.safe_get(positions_url, silent_404=True)
            if resp and resp.status_code == 200:
                try:
                    data = resp.json()
                    positions = data.get("positions", [])
                    postings = []
                    for pos in positions:
                        pos_id = pos.get("id")
                        title = pos.get("name") or pos.get("title", "")
                        dept = pos.get("department", "")
                        if pos_id and title:
                            url = f"https://careers-meli.mercadolibre.com/pt/positions?id={pos_id}"
                            postings.append(JobPosting(
                                url=url,
                                description=f"Department: {dept}",
                                company="Mercado Livre",
                                role=title
                            ))
                    if postings:
                        return postings
                except Exception:
                    pass

        # 3. Fallback to direct job_ids if provided in target
        job_ids = target.get("job_ids", [])
        postings = []

        for jid in job_ids:
            url = f"https://{company_token}.eightfold.ai/api/apply/v2/jobs/{jid}?domain={domain}"
            try:
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    title = data.get("name") or data.get("title", "")
                    company = company_name
                    desc = data.get("job_description", "")
                    job_url = f"https://careers-meli.mercadolibre.com/pt/positions?id={jid}"
                    if title:
                        postings.append(JobPosting(
                            url=job_url,
                            description=desc,
                            company=company,
                            role=title
                        ))
            except Exception:
                continue

        return postings


class WorkableConnector(BaseConnector):
    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        company = target.get("company_token")
        company_name = target.get("company_name") or company
        if not company:
            return []

        url = f"https://apply.workable.com/api/v3/accounts/{company}/jobs"
        try:
            resp = requests.post(
                url,
                json={"query": "", "location": [], "department": [], "worktype": [], "remote": []},
                timeout=10,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            results = data.get("results", [])
            postings = []
            for job in results:
                shortcode = job.get("shortcode", "")
                title = job.get("title", "")
                if shortcode and title:
                    job_url = f"https://apply.workable.com/{company}/j/{shortcode}/"
                    loc = job.get("location", {}) or {}
                    city = loc.get("city", "")
                    country = loc.get("country", "")
                    workplace = job.get("workplace", "")
                    desc = f"Location: {city}, {country} ({workplace})"
                    postings.append(
                        JobPosting(
                            url=job_url,
                            description=desc,
                            company=company_name,
                            role=title,
                        )
                    )
            return postings
        except Exception:
            return []


class SmartRecruitersConnector(BaseConnector):
    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        company = target.get("company_token")
        company_name = target.get("company_name") or company
        if not company:
            return []

        url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings?limit=100"
        resp = self.safe_get(url, silent_404=True)
        if not resp:
            return []

        try:
            data = resp.json()
            content = data.get("content", [])
            postings = []
            for job in content:
                job_id = job.get("id", "")
                title = job.get("name", "")
                ref_url = f"https://jobs.smartrecruiters.com/{company}/{job_id}" if job_id else ""
                loc = job.get("location", {}) or {}
                city = loc.get("city", "")
                country = loc.get("country", "")
                remote = loc.get("remote", False)
                desc = f"Location: {city}, {country} | Remote: {remote}"
                if title and ref_url:
                    postings.append(
                        JobPosting(
                            url=ref_url,
                            description=desc,
                            company=company.get("name") if isinstance(company, dict) else company_name,
                            role=title,
                        )
                    )
            return postings
        except Exception:
            return []


class BaseMCPConnector(BaseConnector):
    """Base connector for public Streamable HTTP MCP servers (JSON-RPC 2.0)."""

    mcp_url: str = ""

    def call_tool(self, tool_name: str, arguments: dict, timeout: int = 15) -> Optional[str]:
        import json as _json

        if not self.mcp_url:
            return None
        try:
            resp = requests.post(
                self.mcp_url,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "User-Agent": "CareerOps/2.0 (compatible; Mozilla/5.0)",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                },
                timeout=timeout,
            )
            if resp.status_code != 200:
                return None

            for line in resp.text.splitlines():
                raw = (
                    line[6:].strip()
                    if line.startswith("data: ")
                    else (line.strip() if line.strip().startswith("{") else None)
                )
                if not raw:
                    continue
                try:
                    payload = _json.loads(raw)
                    content = payload.get("result", {}).get("content", [])
                    if content and isinstance(content, list):
                        return content[0].get("text")
                except Exception:
                    continue
            return None
        except Exception:
            return None


class GupyMCPConnector(BaseMCPConnector):
    """Official Gupy Candidates MCP Server (https://candidates.mcp.api.gupy.io/mcp)."""

    mcp_url = "https://candidates.mcp.api.gupy.io/mcp"

    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        import json as _json

        queries = target.get("queries")
        if not queries:
            single_q = target.get("query") or target.get("term") or "Dados"
            queries = [single_q]

        workplace_types = target.get("workplace_types") or target.get("workplaceTypes")
        city = target.get("city")
        state = target.get("state")
        company_id = target.get("company_id") or target.get("companyId")
        career_page_name = target.get("career_page_name") or target.get("careerPageName")
        limit = int(target.get("limit", 50))
        sort_by = target.get("sort_by") or target.get("sortBy") or "publishedDate"

        postings: List[JobPosting] = []
        seen_urls = set()

        for q in queries:
            args: Dict[str, Any] = {
                "term": q,
                "limit": min(max(limit, 1), 100),
                "sortBy": sort_by,
                "sortOrder": "desc",
            }
            if workplace_types:
                args["workplaceTypes"] = workplace_types
            if city:
                args["city"] = city
            if state:
                args["state"] = state
            if company_id:
                args["companyId"] = int(company_id)
            if career_page_name:
                args["careerPageName"] = career_page_name

            text = self.call_tool("search_jobs", args)
            if not text:
                continue

            try:
                parsed = _json.loads(text)
                jobs_list = parsed.get("data", {}).get("data", [])
                if not isinstance(jobs_list, list):
                    jobs_list = parsed.get("jobs", [])
                for item in jobs_list:
                    job_url = item.get("jobUrl") or ""
                    title = item.get("name") or item.get("title") or ""
                    comp_name = (
                        item.get("careerPageName")
                        or target.get("company_name")
                        or "Gupy Company"
                    )
                    desc = item.get("description") or ""
                    workplace = item.get("workplaceType") or ""
                    job_city = item.get("city") or ""
                    job_state = item.get("state") or ""
                    salary_info = item.get("salary", {}) or {}
                    salary_label = salary_info.get("label") or ""

                    meta_prefix = f"Workplace: {workplace} | Location: {job_city}, {job_state}"
                    if salary_label:
                        meta_prefix += f" | Salary: {salary_label}"
                    full_desc = f"{meta_prefix}\n\n{desc}".strip()

                    if job_url and title and job_url not in seen_urls:
                        seen_urls.add(job_url)
                        postings.append(
                            JobPosting(
                                url=job_url,
                                description=full_desc,
                                company=comp_name,
                                role=title,
                            )
                        )
            except Exception:
                continue

        return postings


class HimalayasMCPConnector(BaseMCPConnector):
    """Official Himalayas Remote Jobs MCP Server (https://mcp.himalayas.app/mcp)."""

    mcp_url = "https://mcp.himalayas.app/mcp"

    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        queries = target.get("queries")
        if not queries:
            queries = [target.get("query") or target.get("keyword") or "data engineer"]

        country = target.get("country")
        worldwide = target.get("worldwide")
        experience = target.get("experience")
        sort = target.get("sort", "recent")

        postings: List[JobPosting] = []
        seen_urls = set()

        for q in queries:
            args: Dict[str, Any] = {"keyword": q, "sort": sort}
            if country:
                args["country"] = country
            if worldwide is not None:
                args["worldwide"] = bool(worldwide)
            if experience:
                args["experience"] = experience

            text = self.call_tool("search_jobs", args)
            if not text:
                continue

            blocks = re.split(r"\n(?=🚀 \*\*|\*\*)", text)
            for block in blocks:
                title_match = re.search(r"\*\*(.+?)\*\*", block)
                comp_match = re.search(r"🏢\s*([^·\n]+)", block)
                url_match = re.search(
                    r"https://himalayas\.app/companies/[^\s\)]+", block
                )
                if title_match and url_match:
                    title = title_match.group(1).strip()
                    raw_url = url_match.group(0).split("?")[0]
                    if "/jobs/" not in raw_url:
                        continue
                    company = (
                        comp_match.group(1).strip()
                        if comp_match
                        else (target.get("company_name") or "Himalayas Remote")
                    )
                    if raw_url not in seen_urls:
                        seen_urls.add(raw_url)
                        postings.append(
                            JobPosting(
                                url=raw_url,
                                description=block.strip(),
                                company=company,
                                role=title,
                            )
                        )

        return postings


class JobicyMCPConnector(BaseMCPConnector):
    """Official Jobicy Remote Jobs MCP Server (https://jobicy.com/mcp)."""

    mcp_url = "https://jobicy.com/mcp"

    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        import json as _json

        queries = target.get("queries")
        if not queries:
            queries = [target.get("query") or "data engineer"]

        geo = target.get("geo")
        industry = target.get("industry")
        limit = int(target.get("limit", 25))

        postings: List[JobPosting] = []
        seen_urls = set()

        for q in queries:
            args: Dict[str, Any] = {
                "query": q,
                "limit": min(max(limit, 1), 50),
            }
            if geo:
                args["geo"] = geo
            if industry:
                args["industry"] = industry

            text = self.call_tool("search_jobs", args)
            if not text:
                continue

            try:
                parsed = _json.loads(text)
                jobs_list = parsed.get("jobs", [])
                for item in jobs_list:
                    job_url = item.get("url") or ""
                    title = item.get("jobTitle") or item.get("title") or ""
                    company = item.get("companyName") or "Jobicy Remote"
                    excerpt = item.get("jobExcerpt") or item.get("jobDescription") or ""
                    job_geo = item.get("jobGeo") or "Remote"
                    full_desc = f"Geo: {job_geo}\n\n{excerpt}".strip()

                    if job_url and title and job_url not in seen_urls:
                        seen_urls.add(job_url)
                        postings.append(
                            JobPosting(
                                url=job_url,
                                description=full_desc,
                                company=company,
                                role=title,
                            )
                        )
            except Exception:
                continue

        return postings


class JobStackMCPConnector(BaseMCPConnector):
    """JobStack Multi-ATS Aggregator MCP Server (https://jobstack-mcp.vercel.app/mcp)."""

    mcp_url = "https://jobstack-mcp.vercel.app/mcp"

    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        import json as _json

        queries = target.get("queries")
        if not queries:
            queries = [target.get("query") or target.get("keywords") or "data engineer"]

        location = target.get("location")
        remote = target.get("remote", True)
        sources = target.get("sources", "ats,themuse")
        limit = int(target.get("limit", 25))

        postings: List[JobPosting] = []
        seen_urls = set()

        for q in queries:
            args: Dict[str, Any] = {
                "keywords": q,
                "remote": bool(remote),
                "sources": sources,
                "limit": min(max(limit, 1), 100),
            }
            if location:
                args["location"] = location

            text = self.call_tool("search_jobs", args)
            if not text:
                continue

            try:
                parsed = _json.loads(text)
                results = parsed.get("results", [])
                for item in results:
                    job_url = item.get("url") or ""
                    title = item.get("title") or ""
                    company = item.get("company") or "JobStack"
                    desc = item.get("description") or ""
                    loc = item.get("location") or ""
                    full_desc = f"Location: {loc}\n\n{desc}".strip()

                    if job_url and title and job_url not in seen_urls:
                        seen_urls.add(job_url)
                        postings.append(
                            JobPosting(
                                url=job_url,
                                description=full_desc,
                                company=company,
                                role=title,
                            )
                        )
            except Exception:
                continue

        return postings


class GitHubIssuesConnector(BaseConnector):
    """Fetches job postings from community GitHub Issues repositories (e.g., backend-br/vagas, datascience-br/vagas)."""

    def fetch_jobs(self, target: dict) -> List[JobPosting]:
        import os
        from datetime import datetime, timezone

        repo = target.get("repo") or target.get("company_token")
        if not repo:
            return []

        max_days = int(target.get("max_days", 30))
        now = datetime.now(timezone.utc)
        postings: List[JobPosting] = []

        url = f"https://api.github.com/repos/{repo}/issues?state=open&sort=created&direction=desc&per_page=50"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CareerOps/2.0 (compatible; Mozilla/5.0)",
        }
        gh_token = os.environ.get("GITHUB_TOKEN")
        if gh_token:
            headers["Authorization"] = f"Bearer {gh_token}"

        resp = self.safe_get(url, silent_404=True)
        if not resp:
            return []

        try:
            issues = resp.json()
            if not isinstance(issues, list):
                return []

            for issue in issues:
                if "pull_request" in issue:
                    continue

                created_at_str = issue.get("created_at")
                if created_at_str:
                    created_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    days_ago = (now - created_dt).days
                    if days_ago > max_days:
                        # Repositories are sorted by created descending; older issues can be stopped early
                        break

                raw_title = issue.get("title", "").strip()
                html_url = issue.get("html_url", "")
                body = issue.get("body", "") or ""

                if not raw_title or not html_url:
                    continue

                # Detect company name from title if formatted like "... na Empresa", "... @Empresa", etc.
                company = target.get("company_name") or target.get("name") or repo
                comp_match = re.search(r'(?:na|no|@|at)\s+([A-Za-z0-9\.\-\_\s]+?)(?:\||\[|\(|$)', raw_title, re.IGNORECASE)
                if comp_match:
                    detected_company = comp_match.group(1).strip()
                    if 1 < len(detected_company) < 40:
                        company = detected_company

                # Clean role from bracketed tags
                cleaned_role = re.sub(r'\[.*?\]', '', raw_title).strip()
                role = cleaned_role if cleaned_role else raw_title

                postings.append(
                    JobPosting(
                        url=html_url,
                        description=body.strip(),
                        company=company,
                        role=role,
                    )
                )

            return postings
        except Exception:
            return []


CONNECTORS = {
    "greenhouse": GreenhouseConnector,
    "lever": LeverConnector,
    "ashby": AshbyConnector,
    "recruitee": RecruiteeConnector,
    "breezy": BreezyConnector,
    "workable": WorkableConnector,
    "smartrecruiters": SmartRecruitersConnector,
    "google": GoogleSearchConnector,
    "inhire": InhireConnector,
    "eightfold": EightfoldConnector,
    "gupy": GupyMCPConnector,
    "gupy_mcp": GupyMCPConnector,
    "himalayas": HimalayasMCPConnector,
    "himalayas_mcp": HimalayasMCPConnector,
    "jobicy": JobicyMCPConnector,
    "jobicy_mcp": JobicyMCPConnector,
    "jobstack": JobStackMCPConnector,
    "jobstack_mcp": JobStackMCPConnector,
    "github": GitHubIssuesConnector,
    "github_issues": GitHubIssuesConnector,
}

MCP_ATS_TYPES = {
    "gupy",
    "gupy_mcp",
    "himalayas",
    "himalayas_mcp",
    "jobicy",
    "jobicy_mcp",
    "jobstack",
    "jobstack_mcp",
}

GITHUB_ATS_TYPES = {
    "github",
    "github_issues",
}


def get_connector(ats_type: str) -> Optional[BaseConnector]:
    connector_class = CONNECTORS.get(ats_type.lower())
    if connector_class:
        return connector_class()
    return None


