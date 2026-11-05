import pytest
from pathlib import Path
from pydantic import ValidationError
from career_ops.schemas.cv import CVPayload, ContactInfo, WorkRole, EducationEntry, ProjectEntry
from career_ops.render.compiler import compile_cv, render_html, CVOverflowError


@pytest.fixture
def valid_payload():
    return CVPayload(
        format="a4",
        lang="en",
        name="Alex Chen",
        headline="Staff Software Engineer & AI Systems Architect",
        contact=ContactInfo(
            email="alex@example.com",
            phone="+55 11 99999-9999",
            location="São Paulo, Brazil",
            linkedin_url="https://linkedin.com/in/alexchen",
            portfolio_url="https://github.com/alexchen",
        ),
        summary=(
            "Staff Engineer with 10+ years architecting distributed systems, RAG pipelines, "
            "and event-driven backends. Proven track record leading multi-team migrations, "
            "optimizing database latency, and deploying production LLM agent harnesses."
        ),
        experience=[
            WorkRole(
                company="TechCorp Solutions",
                role="Principal Solutions Architect",
                location="São Paulo, Brazil",
                start_date="2022",
                end_date="Present",
                bullets=[
                    "Spearheaded enterprise modernization of real estate pipeline, decreasing lead time by 40%.",
                    "Architected hybrid retrieval systems supporting 10k daily autonomous agent queries.",
                    "Mentored 8 senior engineers and established company-wide RFC and code review standards.",
                ],
            ),
            WorkRole(
                company="FinTech Global",
                role="Senior Distributed Systems Engineer",
                location="Remote",
                start_date="2019",
                end_date="2022",
                bullets=[
                    "Designed high-throughput Kafka event streaming ingestion handling 50k events/sec.",
                    "Replaced legacy SQL batch sync with real-time change data capture, reducing lag by 95%.",
                ],
            ),
        ],
        skills={
            "languages": ["Python", "TypeScript", "SQL", "Go"],
            "technologies": ["FastAPI", "Playwright", "Docker", "PostgreSQL", "Kafka"],
            "practices": ["System Design", "Event-Driven Architecture", "Domain-Driven Design"],
        },
        education=[
            EducationEntry(
                institution="University of São Paulo",
                degree="B.S. in Computer Science",
                year="2014",
            )
        ],
        projects=[
            ProjectEntry(
                name="Career-Ops",
                description="Autonomous job discovery and ATS resume tailoring CLI pipeline.",
                technologies=["Python", "SQLite", "Playwright"],
                url="https://github.com/example/career-ops",
            )
        ],
    )


def test_schema_validation_rejection():
    # Exceeding 8 bullets per role should fail validation
    with pytest.raises(ValidationError):
        WorkRole(
            company="Test Corp",
            role="Engineer",
            location="Remote",
            start_date="2020",
            end_date="2021",
            bullets=[f"Bullet {i}" for i in range(12)],  # Max is 8
        )


def test_render_html(valid_payload):
    html = render_html(valid_payload)
    assert "Alex Chen" in html
    assert "TechCorp Solutions" in html
    assert "Professional Summary" in html
    assert "data-section=\"header\"" in html
    assert "data-section=\"experience\"" in html


def test_compile_cv_success(valid_payload, tmp_path):
    out_pdf = tmp_path / "test_resume.pdf"
    result = compile_cv(valid_payload, out_pdf, format="a4")
    assert out_pdf.exists()
    assert out_pdf.stat().st_size > 1000
    assert result.page_count == 1
    assert result.telemetry["is_overflow"] is False


def test_compile_cv_overflow_detection(valid_payload, tmp_path):
    # Create an excessively long payload that definitely overflows 1 page
    long_roles = []
    for i in range(4):
        long_roles.append(
            WorkRole(
                company=f"Mega Enterprise Corp {i}",
                role="Senior Staff Distributed Architect & Systems Optimization Specialist",
                location="São Paulo, Brazil & Global Remote Headquarters",
                start_date="2015",
                end_date="2018",
                bullets=[
                    "Spearheaded multi-region data replication across 12 availability zones with zero loss during peak transactional bursts, reducing global tail latency from 850ms down to 42ms.",
                    "Designed and led implementation of an enterprise event orchestration backbone managing 100,000 asynchronous workflows per minute with custom idempotent retry queues.",
                    "Led comprehensive architecture refactoring across 14 cross-functional squad initiatives, introducing domain-driven boundaries and declarative gRPC contracts.",
                    "Engineered real-time telemetry pipelines aggregating multi-tenant observability metrics across 400 microservices into partitioned columnar storage pools.",
                    "Delivered internal developer platform reducing deployment lead time from 4 days to 12 minutes through automated canary verification and zero-downtime rollouts.",
                    "Championed automated database migration safety harnesses, eliminating production lock contention and verifying schema compatibility prior to deployment.",
                    "Built machine learning inference deployment pipelines serving high-availability low-latency models behind circuit-breaking reverse proxies.",
                    "Authored company-wide technical design review guidelines and mentored 15 junior and mid-level engineers in distributed consistency models.",
                ],
            )
        )
    valid_payload.experience = long_roles
    valid_payload.summary = valid_payload.summary * 3  # Long summary

    out_pdf = tmp_path / "overflow_resume.pdf"
    with pytest.raises(CVOverflowError) as exc_info:
        compile_cv(valid_payload, out_pdf, format="a4")

    telemetry = exc_info.value.telemetry
    assert telemetry["is_overflow"] is True
    assert telemetry["overflow_px"] > 0
    assert telemetry["estimated_line_excess"] > 0
    assert "experience" in telemetry["section_heights"]
