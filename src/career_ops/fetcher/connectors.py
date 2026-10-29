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


CONNECTORS = {
    "greenhouse": GreenhouseConnector,
    "lever": LeverConnector,
    "ashby": AshbyConnector,
    "recruitee": RecruiteeConnector,
    "breezy": BreezyConnector,
    "google": GoogleSearchConnector,
    "inhire": InhireConnector,
    "eightfold": EightfoldConnector,
}

def get_connector(ats_type: str) -> Optional[BaseConnector]:
    connector_class = CONNECTORS.get(ats_type.lower())
    if connector_class:
        return connector_class()
    return None

