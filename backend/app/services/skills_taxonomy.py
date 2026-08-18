"""Skill taxonomy — canonical list used for normalization + extraction."""
from __future__ import annotations

import re
from typing import Iterable, List, Set

# Canonical skills (canonical name -> alias set)
SKILL_TAXONOMY: dict[str, set[str]] = {
    "python": {"python", "python3"},
    "java": {"java"},
    "javascript": {"javascript", "js", "java script"},
    "typescript": {"typescript", "ts"},
    "c++": {"c++", "cpp", "c plus plus"},
    "c#": {"c#", "csharp", "c sharp"},
    "go": {"go", "golang"},
    "rust": {"rust"},
    "ruby": {"ruby"},
    "php": {"php"},
    "scala": {"scala"},
    "kotlin": {"kotlin"},
    "swift": {"swift"},
    "react": {"react", "react.js", "reactjs"},
    "next.js": {"next.js", "nextjs", "next js"},
    "vue": {"vue", "vue.js", "vuejs"},
    "angular": {"angular", "angularjs"},
    "svelte": {"svelte"},
    "node.js": {"node.js", "nodejs", "node js"},
    "express": {"express", "expressjs"},
    "fastapi": {"fastapi", "fast api"},
    "django": {"django"},
    "flask": {"flask"},
    "spring": {"spring", "spring boot"},
    "rails": {"rails", "ruby on rails"},
    "html": {"html", "html5"},
    "css": {"css", "css3"},
    "tailwind": {"tailwind", "tailwind css"},
    "sass": {"sass", "scss"},
    "sql": {"sql"},
    "postgresql": {"postgresql", "postgres", "psql"},
    "mysql": {"mysql"},
    "mongodb": {"mongodb", "mongo"},
    "redis": {"redis"},
    "elasticsearch": {"elasticsearch", "elastic search", "es"},
    "cassandra": {"cassandra"},
    "kafka": {"kafka"},
    "airflow": {"airflow", "apache airflow"},
    "spark": {"spark", "pyspark", "apache spark"},
    "hadoop": {"hadoop"},
    "snowflake": {"snowflake"},
    "bigquery": {"bigquery"},
    "docker": {"docker"},
    "kubernetes": {"kubernetes", "k8s"},
    "terraform": {"terraform"},
    "ansible": {"ansible"},
    "jenkins": {"jenkins"},
    "github actions": {"github actions", "gh actions"},
    "gitlab ci": {"gitlab ci", "gitlab"},
    "circleci": {"circleci"},
    "aws": {"aws", "amazon web services"},
    "gcp": {"gcp", "google cloud", "google cloud platform"},
    "azure": {"azure", "microsoft azure"},
    "linux": {"linux"},
    "bash": {"bash", "shell", "sh"},
    "git": {"git"},
    "machine learning": {"machine learning", "ml"},
    "deep learning": {"deep learning", "dl"},
    "nlp": {"nlp", "natural language processing"},
    "computer vision": {"computer vision", "cv"},
    "reinforcement learning": {"reinforcement learning", "rl"},
    "data science": {"data science"},
    "data analysis": {"data analysis", "data analytics"},
    "data engineering": {"data engineering"},
    "etl": {"etl"},
    "mlops": {"mlops", "ml ops"},
    "pytorch": {"pytorch", "torch"},
    "tensorflow": {"tensorflow", "tf"},
    "scikit-learn": {"scikit-learn", "sklearn", "scikit learn"},
    "pandas": {"pandas"},
    "numpy": {"numpy"},
    "scipy": {"scipy"},
    "matplotlib": {"matplotlib"},
    "seaborn": {"seaborn"},
    "plotly": {"plotly"},
    "transformers": {"transformers", "huggingface"},
    "llm": {"llm", "large language model", "large language models"},
    "rag": {"rag", "retrieval augmented generation"},
    "langchain": {"langchain"},
    "rest api": {"rest", "rest api", "restful"},
    "graphql": {"graphql"},
    "grpc": {"grpc"},
    "microservices": {"microservices", "micro services", "microservice"},
    "design patterns": {"design patterns"},
    "system design": {"system design"},
    "agile": {"agile"},
    "scrum": {"scrum"},
    "tdd": {"tdd", "test driven development"},
    "ci/cd": {"ci/cd", "ci cd", "continuous integration", "continuous deployment"},
    "unit testing": {"unit testing", "unit tests"},
    "pytest": {"pytest"},
    "junit": {"junit"},
    "selenium": {"selenium"},
    "playwright": {"playwright"},
    "security": {"security", "application security", "appsec"},
    "oauth": {"oauth", "oauth2"},
    "jwt": {"jwt"},
    "encryption": {"encryption"},
    "tableau": {"tableau"},
    "power bi": {"power bi", "powerbi"},
    "excel": {"excel", "microsoft excel"},
    "jira": {"jira"},
    "confluence": {"confluence"},
    "figma": {"figma"},
    "communication": {"communication"},
    "leadership": {"leadership"},
    "teamwork": {"teamwork"},
    "problem solving": {"problem solving", "problem-solving"},
}


def _build_index() -> dict[str, str]:
    idx: dict[str, str] = {}
    for canonical, aliases in SKILL_TAXONOMY.items():
        idx[canonical] = canonical
        for alias in aliases:
            idx[alias] = canonical
    return idx


_ALIAS_TO_CANONICAL = _build_index()


def detect_skills(text: str) -> List[str]:
    """Return canonical skills detected in the text (deduped, ordered)."""
    if not text:
        return []
    lower = text.lower()
    seen: Set[str] = set()
    detected: List[str] = []
    # Longest-first so multi-word aliases (e.g. "scikit-learn") match before
    # their sub-tokens (e.g. "scikit").
    for alias, canonical in sorted(_ALIAS_TO_CANONICAL.items(), key=lambda x: -len(x[0])):
        if alias and _search_word(lower, alias):
            if canonical not in seen:
                seen.add(canonical)
                detected.append(canonical)
    return detected


def _search_word(text: str, alias: str) -> bool:
    """Return True if alias appears as a discrete token/phrase."""
    escaped = re.escape(alias)
    pattern = rf"(?<![a-z0-9+#]){escaped}(?![a-z0-9+#])"
    return re.search(pattern, text) is not None


def is_known_skill(term: str) -> bool:
    return term.lower().strip() in _ALIAS_TO_CANONICAL


def canonicalize(term: str) -> str:
    return _ALIAS_TO_CANONICAL.get(term.lower().strip(), term.lower().strip())
