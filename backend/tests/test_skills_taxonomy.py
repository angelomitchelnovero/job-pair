"""Tests for the skills taxonomy."""
from app.services.skills_taxonomy import (
    SKILL_TAXONOMY,
    canonicalize,
    detect_skills,
    is_known_skill,
)


def test_taxonomy_has_python_and_pytorch():
    assert "python" in SKILL_TAXONOMY
    assert "pytorch" in SKILL_TAXONOMY


def test_canonicalize_alias():
    assert canonicalize("React.js") == "react"
    assert canonicalize("Postgres") == "postgresql"


def test_canonicalize_unknown():
    assert canonicalize("Crystal Lang") == "crystal lang"


def test_detect_skills_finds_canonical():
    text = "Strong Python and PyTorch experience with AWS and Kubernetes."
    found = detect_skills(text)
    for s in ("python", "pytorch", "aws", "kubernetes"):
        assert s in found, f"{s} should be detected"


def test_detect_skills_no_duplicates():
    text = "Python Python Python"
    assert detect_skills(text).count("python") == 1


def test_detect_skills_empty():
    assert detect_skills("") == []


def test_is_known_skill_true_and_false():
    assert is_known_skill("Python")
    assert not is_known_skill("Underwater Basket Weaving")
