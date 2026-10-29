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

