"""Synthetic training data generator.

Creates labeled (resume, job description, score) tuples from the skill taxonomy.
This is intentionally synthetic — clearly documented — and easy to replace with
real labeled data later (e.g., from a RecSys dataset like Kaggle "Resume & Job
 postings" or a custom-curated set).

The score is computed deterministically from the feature vector so the
ground-truth signal is consistent with the features the model sees.
"""
from __future__ import annotations

import json
import random
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from app.services.skills_taxonomy import SKILL_TAXONOMY


CANONICAL_SKILLS = sorted(SKILL_TAXONOMY.keys())

ROLES = [
    "Senior Machine Learning Engineer",
    "Data Scientist",
    "Backend Engineer",
    "Full Stack Developer",
    "Frontend Engineer",
    "DevOps Engineer",
    "Data Engineer",
    "NLP Engineer",
    "Cloud Architect",
    "Software Engineer",
    "ML Platform Engineer",
    "Computer Vision Engineer",
    "Analytics Engineer",
    "Site Reliability Engineer",
    "Security Engineer",
]

COMPANIES = [
    "Acme Corp",
    "Globex",
    "Initech",
    "Umbrella Labs",
    "Stark Industries",
    "Wayne Enterprises",
    "Hooli",
    "Vandelay Industries",
    "Soylent Corp",
    "Pied Piper",
]

ROLE_TO_SKILLS: Dict[str, List[str]] = {
    "Senior Machine Learning Engineer": ["python", "pytorch", "scikit-learn", "machine learning", "nlp", "docker", "aws", "rest api", "sql", "git"],
    "Data Scientist": ["python", "pandas", "numpy", "scikit-learn", "machine learning", "data analysis", "sql", "tableau", "communication"],
    "Backend Engineer": ["python", "fastapi", "postgresql", "docker", "rest api", "redis", "aws", "git", "kubernetes"],
    "Full Stack Developer": ["javascript", "typescript", "react", "next.js", "node.js", "postgresql", "docker", "tailwind", "git"],
    "Frontend Engineer": ["javascript", "typescript", "react", "tailwind", "css", "html", "figma", "git"],
    "DevOps Engineer": ["docker", "kubernetes", "terraform", "aws", "ansible", "jenkins", "linux", "bash", "git", "python"],
    "Data Engineer": ["python", "sql", "postgresql", "airflow", "spark", "kafka", "docker", "aws", "etl"],
    "NLP Engineer": ["python", "pytorch", "transformers", "nlp", "machine learning", "docker", "llm", "rag", "rest api"],
    "Cloud Architect": ["aws", "gcp", "terraform", "kubernetes", "docker", "linux", "security", "python"],
    "Software Engineer": ["python", "sql", "docker", "git", "rest api", "postgresql", "linux"],
    "ML Platform Engineer": ["python", "pytorch", "docker", "kubernetes", "mlops", "aws", "terraform", "airflow", "sql"],
    "Computer Vision Engineer": ["python", "pytorch", "computer vision", "machine learning", "docker", "aws", "numpy"],
    "Analytics Engineer": ["sql", "python", "pandas", "data analysis", "tableau", "etl", "snowflake", "bigquery"],
    "Site Reliability Engineer": ["linux", "python", "docker", "kubernetes", "terraform", "aws", "prometheus"],
    "Security Engineer": ["security", "python", "linux", "aws", "encryption", "oauth", "jwt", "docker"],
}

EDUCATION_OPTIONS = ["bachelor", "master", "phd", "computer science"]
YEARS_RANGE = (1, 12)


def _sentence(skills: Sequence[str]) -> str:
    """Turn a list of skills into a sentence fragment for the corpus."""
    if not skills:
        return ""
    if len(skills) == 1:
        return f"Strong experience with {skills[0]}."
    head = ", ".join(skills[:-1])
    return f"Strong experience with {head} and {skills[-1]}."


def _responsibilities(skills: Sequence[str]) -> str:
    return (
        "Responsibilities include designing, building and maintaining production "
        f"systems involving {', '.join(skills[:5])}. You will collaborate with cross-functional teams, "
        "participate in code reviews, mentor junior engineers, and contribute to architectural decisions."
    )


def _requirements(skills: Sequence[str]) -> str:
    return (
        "Required Qualifications: "
        + ", ".join(skills)
        + ". We value strong fundamentals, a bias for shipping, and excellent communication skills."
    )


def _preferred(skills: Sequence[str]) -> str:
    return "Preferred: " + ", ".join(skills) + "."


@dataclass
class TrainingExample:
    resume_text: str
    job_text: str
    job_title: str
    resume_skills: List[str]
    job_skills: List[str]
    job_preferred: List[str]
    resume_years: float
    required_years: float
    score: float
    education_required: bool
    education_present: bool


def _deterministic_score(
    resume_skills: Sequence[str],
    job_skills: Sequence[str],
    job_preferred: Sequence[str],
    resume_years: float,
    required_years: float,
    education_required: bool,
    education_present: bool,
) -> float:
    """Compute a deterministic ground-truth match score in [0, 1]."""
    req = set(job_skills)
    matched_required = req & set(resume_skills)
    coverage = len(matched_required) / max(len(req), 1)
    preferred_bonus = (
        len(set(resume_skills) & set(job_preferred)) / max(len(set(job_preferred)), 1)
    ) * 0.1
    base = coverage * 0.75 + preferred_bonus

    # Experience bonus — gated on having some skill overlap so a candidate
    # with zero required-skills match can't game the score via years alone.
    if coverage <= 0.0:
        exp_score = -0.05  # small penalty for "wrong domain" resumes
    elif required_years > 0:
        if resume_years + 0.5 >= required_years:
            exp_score = 0.15
        elif resume_years + 1.5 >= required_years:
            exp_score = 0.08
        else:
            exp_score = max(0, 0.05 - 0.02 * (required_years - resume_years))
    else:
        exp_score = 0.07

    edu_score = 0.05 if (not education_required or education_present) else 0.0
    score = base + exp_score + edu_score
    # Noise (deterministic on quantities, not random per-generation)
    noise = (len(resume_skills) % 7) / 1000.0
    return float(max(0.0, min(1.0, score + noise)))


def generate_example(rng: random.Random) -> TrainingExample:
    role = rng.choice(ROLES)
    company = rng.choice(COMPANIES)
    required = list(ROLE_TO_SKILLS[role])
    preferred_pool = [s for s in CANONICAL_SKILLS if s not in required]
    preferred = rng.sample(preferred_pool, k=min(4, len(preferred_pool)))

    # Coverage distribution: realistic spread instead of always 40–100%.
    # Without low-coverage examples the model never learns what a "bad fit"
    # looks like and over-predicts the high range for any non-empty overlap.
    # We split into three buckets with the bulk at 40–100% but include
    # meaningful mass at 0–30% so calibration is honest end-to-end.
    bucket = rng.random()
    if bucket < 0.20:            # ~20% hard-negatives (0–25% coverage)
        coverage_pct = rng.uniform(0.0, 0.25)
    elif bucket < 0.55:          # ~35% weak fits (25–60%)
        coverage_pct = rng.uniform(0.25, 0.6)
    else:                        # ~45% solid fits (60–100%)
        coverage_pct = rng.uniform(0.6, 1.0)

    n_required_have = int(round(len(required) * coverage_pct))
    resume_required = rng.sample(required, k=min(n_required_have, len(required)))
    adjacency_pool = [s for s in CANONICAL_SKILLS if s not in required and s not in preferred]
    n_extras = rng.randint(0, 6)
    resume_extras = rng.sample(adjacency_pool, k=min(n_extras, len(adjacency_pool)))

    # Sometimes include preferred skills
    n_preferred_have = rng.randint(0, len(preferred))
    resume_preferred_have = rng.sample(preferred, k=n_preferred_have) if preferred else []

    resume_skills_list = sorted(set(resume_required + resume_extras + resume_preferred_have))

    # Years
    required_years = float(rng.randint(*YEARS_RANGE))
    if resume_required:
        resume_years = max(0.0, required_years + rng.uniform(-3.5, 5.0))
    else:
        resume_years = rng.uniform(0.0, 4.0)

    edu_required = rng.random() < 0.55
    edu_present = (rng.random() < 0.7) if edu_required else False

    score = _deterministic_score(
        resume_skills_list,
        required,
        preferred,
        resume_years,
        required_years,
        edu_required,
        edu_present,
    )

    resume_text = _build_resume_text(resume_skills_list, resume_years, edu_present)
    job_text = _build_jd_text(role, company, required, preferred, required_years, edu_required)

    return TrainingExample(
        resume_text=resume_text,
        job_text=job_text,
        job_title=role,
        resume_skills=resume_skills_list,
        job_skills=required,
        job_preferred=preferred,
        resume_years=resume_years,
        required_years=required_years,
        score=score,
        education_required=edu_required,
        education_present=edu_present,
    )


def _build_resume_text(skills: Sequence[str], years: float, edu_present: bool) -> str:
    """Construct a synthetic resume with sections so the parser detects them."""
    random_name_first = random.choice(["Alex", "Jordan", "Sam", "Casey", "Riley", "Taylor"])
    random_name_last = random.choice(["Parker", "Nguyen", "Patel", "Garcia", "Kim", "Smith", "Brown"])
    name = f"{random_name_first} {random_name_last}"
    skills_block = _sentence(skills)
    projects_block = " - " + "\n - ".join([f"Project using {s}" for s in skills[:4]])
    edu_block = "Bachelor of Science in Computer Science" if edu_present else ""
    return (
        f"{name}\n"
        "Summary\n"
        "Software engineer with hands-on experience shipping production systems.\n\n"
        "Skills\n"
        f"{skills_block}\n\n"
        "Experience\n"
        f"Senior Engineer, ExampleCo ({int(years)} years)\n"
        + "\n".join([f" - Built features using {s}" for s in skills[:5]])
        + "\n\n"
        "Education\n"
        f"{edu_block}\n\n"
        "Projects\n"
        f"{projects_block}\n"
    )


def _build_jd_text(role: str, company: str, required: Sequence[str], preferred: Sequence[str], years: float, edu_required: bool) -> str:
    edu_line = "Bachelor's degree in Computer Science or related field." if edu_required else ""
    return (
        f"Role: {role}\n"
        f"Company: {company}\n\n"
        f"About the role\n"
        f"{_responsibilities(required)}\n\n"
        f"Requirements\n"
        f"{_requirements(required)} {int(years)} years of relevant experience. {edu_line}\n\n"
        f"Nice to have\n"
        f"{_preferred(preferred)}\n"
    )


def generate_dataset(n: int, seed: int = 7) -> List[TrainingExample]:
    rng = random.Random(seed)
    return [generate_example(rng) for _ in range(n)]


def save_dataset(examples: Sequence[TrainingExample], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "resume_text": ex.resume_text,
            "job_text": ex.job_text,
            "job_title": ex.job_title,
            "resume_skills": ex.resume_skills,
            "job_skills": ex.job_skills,
            "job_preferred": ex.job_preferred,
            "resume_years": ex.resume_years,
            "required_years": ex.required_years,
            "score": ex.score,
            "education_required": ex.education_required,
            "education_present": ex.education_present,
        }
        for ex in examples
    ]
    path.write_text(json.dumps(payload, indent=2))


def load_dataset(path: Path) -> List[TrainingExample]:
    raw = json.loads(path.read_text())
    return [
        TrainingExample(
            resume_text=ex["resume_text"],
            job_text=ex["job_text"],
            job_title=ex.get("job_title", ""),
            resume_skills=ex.get("resume_skills", []),
            job_skills=ex.get("job_skills", []),
            job_preferred=ex.get("job_preferred", []),
            resume_years=ex.get("resume_years", 0.0),
            required_years=ex.get("required_years", 0.0),
            score=ex.get("score", 0.0),
            education_required=ex.get("education_required", False),
            education_present=ex.get("education_present", False),
        )
        for ex in raw
    ]
