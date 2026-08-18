"""Tests for the resume parser."""
from app.services.resume_parser import ResumeParser


SAMPLE_RESUME = """
Alex Parker
alex.parker@example.com | +1 (555) 123-4567

Summary
Software engineer with 6 years of experience building production systems.

Skills
Python, FastAPI, PostgreSQL, Docker, AWS, scikit-learn, PyTorch, NLP

Experience
Senior Engineer, ExampleCo (2020 - Present)
- Led migration of ML pipeline to AWS
- Built NLP features with PyTorch

Backend Engineer, FooBar (2017 - 2020)
- Built REST APIs with FastAPI

Education
Bachelor of Science in Computer Science, University of Example

Projects
- Resume matcher using PyTorch and FastAPI

Certifications
AWS Certified Solutions Architect
"""


def test_parse_text_extracts_basics():
    parser = ResumeParser()
    data = parser.parse_text(SAMPLE_RESUME)

    assert data.full_name == "Alex Parker"
    assert data.email == "alex.parker@example.com"
    assert data.phone is not None
    assert "python" in [s.lower() for s in data.skills]
    assert "pytorch" in [s.lower() for s in data.skills]
    assert "aws" in [s.lower() for s in data.skills]


def test_parse_text_extracts_sections():
    parser = ResumeParser()
    data = parser.parse_text(SAMPLE_RESUME)

    assert "skills" in data.sections
    assert "experience" in data.sections
    assert "education" in data.sections
    assert "projects" in data.sections
    assert "certifications" in data.sections


def test_parse_text_estimates_years():
    parser = ResumeParser()
    data = parser.parse_text(SAMPLE_RESUME)

    assert data.years_experience_estimate is not None
    assert data.years_experience_estimate >= 5


def test_parse_text_handles_empty_text():
    parser = ResumeParser()
    data = parser.parse_text("")
    assert data.skills == []
    assert data.full_name is None
