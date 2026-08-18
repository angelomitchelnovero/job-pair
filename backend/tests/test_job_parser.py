"""Tests for the job description parser."""
from app.services.job_parser import JobParser


SAMPLE_JD = """
Senior Machine Learning Engineer

About the role
You will design and ship ML systems. Responsibilities include building NLP pipelines,
shipping model serving infrastructure, and partnering with product.

Requirements
- 5+ years of experience in machine learning
- Strong Python and PyTorch skills
- Experience with AWS, Docker, and Kubernetes
- Bachelor's degree in Computer Science or related field

Nice to have
- Experience with LLM and RAG systems
- Open-source contributions
"""


def test_parse_extracts_title():
    parser = JobParser()
    data = parser.parse(SAMPLE_JD, title="Senior ML Engineer")
    assert data.title == "Senior ML Engineer"


def test_parse_extracts_required_skills():
    parser = JobParser()
    data = parser.parse(SAMPLE_JD, title="Senior ML Engineer")
    required = {s.lower() for s in data.skills_required}
    assert "python" in required
    assert "pytorch" in required
    assert "machine learning" in required
    assert "docker" in required
    assert "aws" in required


def test_parse_extracts_preferred_skills():
    parser = JobParser()
    data = parser.parse(SAMPLE_JD, title="Senior ML Engineer")
    preferred = {s.lower() for s in data.skills_preferred}
    assert any(s in preferred for s in ("llm", "rag"))


def test_parse_extracts_years():
    parser = JobParser()
    data = parser.parse(SAMPLE_JD, title="Senior ML Engineer")
    assert data.experience_years == 5


def test_parse_extracts_education():
    parser = JobParser()
    data = parser.parse(SAMPLE_JD, title="Senior ML Engineer")
    assert data.education_required is not None


def test_parse_extracts_responsibilities():
    parser = JobParser()
    data = parser.parse(SAMPLE_JD, title="Senior ML Engineer")
    assert len(data.responsibilities) >= 1
