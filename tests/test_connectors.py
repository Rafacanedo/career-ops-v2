from unittest.mock import MagicMock, patch
from career_ops.fetcher.connectors import get_connector, InhireConnector

def test_get_connector_inhire():
    connector = get_connector("inhire")
    assert isinstance(connector, InhireConnector)

@patch("career_ops.fetcher.connectors.InhireConnector.safe_get")
def test_inhire_connector_fetch_jobs_success(mock_safe_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "displayName": "Engenheiro(a) de Dados | Snowflake",
        "tenantName": "VONBZ",
        "description": "<p>Vaga de Teste</p>"
    }
    mock_safe_get.return_value = mock_resp

    connector = InhireConnector()
    jobs = connector.fetch_jobs({"url": "https://vonbz.inhire.app/vagas/c7f46744-ea3e-47c2-8c1b-e76175350a05/engenheiroa-de-dados"})

    assert len(jobs) == 1
    assert jobs[0].role == "Engenheiro(a) de Dados | Snowflake"
    assert jobs[0].company == "VONBZ"
    assert jobs[0].description == "<p>Vaga de Teste</p>"
    mock_safe_get.assert_called_once_with("https://api.inhire.app/job-posts/public/pages/c7f46744-ea3e-47c2-8c1b-e76175350a05", silent_404=True)

def test_fetch_orchestrator_filtering(tmp_path):
    from career_ops.fetcher.orchestrator import FetchOrchestrator
    from career_ops.fetcher.models import JobPosting

    config_file = tmp_path / "portals.yml"
    config_file.write_text("""
title_filter:
  positive:
    - data
    - analytics
  negative:
    - counsel
    - mobile
    - director
location_filter:
  negative:
    - colombia
    - casablanca
""", encoding="utf-8")

    orch = FetchOrchestrator(root_dir=tmp_path, config_path=config_file)

    # Valid Data job -> Pass
    job_valid = JobPosting(url="https://example.com/job1", description="Remote Brazil Data Engineer", company="Test", role="Senior Data Engineer")
    assert orch._passes_filter(job_valid) is True

    # Counsel / Legal -> Filtered out
    job_counsel = JobPosting(url="https://example.com/job2", description="Legal Counsel", company="Test", role="Bill Pay Counsel")
    assert orch._passes_filter(job_counsel) is False

    # Mobile -> Filtered out
    job_mobile = JobPosting(url="https://example.com/job3", description="Mobile App Dev", company="Test", role="Senior Mobile Engineer")
    assert orch._passes_filter(job_mobile) is False

    # Executive Director -> Filtered out
    job_director = JobPosting(url="https://example.com/job4", description="Director of Data", company="Test", role="Director, Data Science")
    assert orch._passes_filter(job_director) is False

    # International location (Colombia) -> Filtered out
    job_colombia = JobPosting(url="https://example.com/job5", description="Job in Colombia", company="Test", role="Data Engineer Colombia")
    assert orch._passes_filter(job_colombia) is False


@patch("career_ops.fetcher.connectors.GupyMCPConnector.call_tool")
def test_gupy_mcp_connector(mock_call_tool):
    from career_ops.fetcher.connectors import GupyMCPConnector
    import json

    mock_call_tool.return_value = json.dumps({
        "data": {
            "data": [
                {
                    "id": 11525461,
                    "title": "Engenheiro de Dados Sênior",
                    "description": "Snowflake e dbt.",
                    "careerPageName": "Eng4tech",
                    "jobUrl": "https://eng4tech.gupy.io/job/11525461",
                    "workplaceType": "remote",
                    "city": "Belo Horizonte",
                    "state": "Minas Gerais",
                    "country": "Brasil",
                }
            ]
        }
    })

    connector = get_connector("gupy")
    assert isinstance(connector, GupyMCPConnector)
    jobs = connector.fetch_jobs({
        "queries": ["Engenheiro de Dados"],
        "workplace_types": "remote",
        "limit": 10,
    })

    assert len(jobs) == 1
    assert jobs[0].company == "Eng4tech"
    assert jobs[0].role == "Engenheiro de Dados Sênior"
    assert jobs[0].url == "https://eng4tech.gupy.io/job/11525461"
    assert "Snowflake e dbt." in jobs[0].description


@patch("career_ops.fetcher.connectors.HimalayasMCPConnector.call_tool")
def test_himalayas_mcp_connector(mock_call_tool):
    from career_ops.fetcher.connectors import HimalayasMCPConnector

    mock_call_tool.return_value = (
        "Found 1 jobs (showing 1):\n\n"
        "**Senior Data Engineer**\n"
        "🏢 Acme Global · 📍 Remote (Brazil)\n"
        "💰 95k - 120k USD · 📊 Senior\n"
        "Build modern data pipelines with Python and dbt.\n"
        "🔗 [Apply](https://himalayas.app/companies/acme-global/jobs/senior-data-engineer)\n\n---\n"
    )

    connector = get_connector("himalayas")
    assert isinstance(connector, HimalayasMCPConnector)
    jobs = connector.fetch_jobs({"query": "Data Engineer", "country": "Brazil"})

    assert len(jobs) == 1
    assert jobs[0].role == "Senior Data Engineer"
    assert jobs[0].company == "Acme Global"
    assert jobs[0].url == "https://himalayas.app/companies/acme-global/jobs/senior-data-engineer"


@patch("career_ops.fetcher.connectors.JobicyMCPConnector.call_tool")
def test_jobicy_mcp_connector(mock_call_tool):
    from career_ops.fetcher.connectors import JobicyMCPConnector
    import json

    mock_call_tool.return_value = json.dumps({
        "count": 1,
        "jobs": [
            {
                "id": 141990,
                "url": "https://jobicy.com/jobs/141990-analytics-engineer",
                "jobTitle": "Analytics Engineer",
                "companyName": "DataFlow Inc",
                "jobGeo": "LATAM",
                "jobLevel": "Senior",
                "jobExcerpt": "Lead dbt modeling.",
            }
        ]
    })

    connector = get_connector("jobicy")
    assert isinstance(connector, JobicyMCPConnector)
    jobs = connector.fetch_jobs({"query": "analytics engineer"})

    assert len(jobs) == 1
    assert jobs[0].role == "Analytics Engineer"
    assert jobs[0].company == "DataFlow Inc"
    assert jobs[0].url == "https://jobicy.com/jobs/141990-analytics-engineer"


@patch("career_ops.fetcher.connectors.JobStackMCPConnector.call_tool")
def test_jobstack_mcp_connector(mock_call_tool):
    from career_ops.fetcher.connectors import JobStackMCPConnector
    import json

    mock_call_tool.return_value = json.dumps({
        "results": [
            {
                "id": "gh-123",
                "title": "AI Engineer",
                "company": "NeuralOps",
                "location": "Remote",
                "url": "https://boards.greenhouse.io/neuralops/jobs/123",
                "description": "Build LLM agents.",
            }
        ]
    })

    connector = get_connector("jobstack")
    assert isinstance(connector, JobStackMCPConnector)
    jobs = connector.fetch_jobs({"query": "AI Engineer", "remote": True})

    assert len(jobs) == 1
    assert jobs[0].role == "AI Engineer"
    assert jobs[0].company == "NeuralOps"
    assert jobs[0].url == "https://boards.greenhouse.io/neuralops/jobs/123"


@patch("career_ops.fetcher.connectors.requests.post")
def test_workable_connector(mock_post):
    from career_ops.fetcher.connectors import WorkableConnector

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "shortcode": "ABC1234",
                "title": "Data Scientist",
                "department": ["Data"],
                "workplace": "remote",
                "location": {"city": "São Paulo", "country": "Brazil"},
            }
        ]
    }
    mock_post.return_value = mock_resp

    connector = get_connector("workable")
    assert isinstance(connector, WorkableConnector)
    jobs = connector.fetch_jobs({"company_token": "omie", "company_name": "Omie"})

    assert len(jobs) == 1
    assert jobs[0].role == "Data Scientist"
    assert jobs[0].company == "Omie"
    assert jobs[0].url == "https://apply.workable.com/omie/j/ABC1234/"


