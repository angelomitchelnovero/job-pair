"""Feature engineering for resume-JD matching.

Produces a numeric feature vector used by both the scikit-learn baseline
(classification head) and the PyTorch neural network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from sklearn.feature_extraction.text import TfidfVectorizer

from app.services.skills_taxonomy import detect_skills
from app.services.text_processing import preprocess


@dataclass
class MatchFeatures:
    """Numeric feature vector for a (resume, job) pair."""

    # Similarity-based (text overlap)
    tfidf_cosine: float
    jaccard_skills: float
    jd_coverage: float  # how much of required JD skills the resume covers

    # Quantities
    resume_skill_count: int
    jd_required_skill_count: int
    matching_skill_count: int
    missing_skill_count: int
    extra_skill_count: int

    # Experience
    years_required: float
    years_estimated: float
    years_gap: float  # estimated - required (positive is surplus)

    # Education
    education_required: int  # 0/1
    education_present: int  # 0/1

    # Length / shape features
    resume_length: int
    jd_length: int

    def to_vector(self) -> List[float]:
        return [
            self.tfidf_cosine,
            self.jaccard_skills,
            self.jd_coverage,
            float(self.resume_skill_count),
            float(self.jd_required_skill_count),
            float(self.matching_skill_count),
            float(self.missing_skill_count),
            float(self.extra_skill_count),
            self.years_required,
            self.years_estimated,
            self.years_gap,
            float(self.education_required),
            float(self.education_present),
            float(self.resume_length),
            float(self.jd_length),
        ]

    FEATURE_NAMES: Sequence[str] = (
        "tfidf_cosine",
        "jaccard_skills",
        "jd_coverage",
        "resume_skill_count",
        "jd_required_skill_count",
        "matching_skill_count",
        "missing_skill_count",
        "extra_skill_count",
        "years_required",
        "years_estimated",
        "years_gap",
        "education_required",
        "education_present",
        "resume_length",
        "jd_length",
    )

    @classmethod
    def feature_names(cls) -> List[str]:
        return list(cls.FEATURE_NAMES)


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    inter = sa & sb
    union = sa | sb
    return len(inter) / len(union) if union else 0.0


def coverage(resume_skills: Iterable[str], required: Iterable[str]) -> float:
    req = set(required)
    if not req:
        return 0.0
    matched = req & set(resume_skills)
    return len(matched) / len(req)


class TfidfSimilarity:
    """Lazy TF-IDF vectorizer shared across calls. Trained on first use."""

    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
            sublinear_tf=True,
            strip_accents="unicode",
        )
        self._fitted = False

    def fit(self, documents: Sequence[str]) -> None:
        if not documents:
            documents = ["placeholder text for fitting tfidf"]
        cleaned = [preprocess(doc) for doc in documents]
        self.vectorizer.fit(cleaned)
        self._fitted = True

    def similarity(self, text_a: str, text_b: str) -> float:
        if not self._fitted:
            self.fit([text_a, text_b])
        vec_a = self.vectorizer.transform([preprocess(text_a)])
        vec_b = self.vectorizer.transform([preprocess(text_b)])
        # sparse cosine similarity
        denom = (vec_a.multiply(vec_a).sum() ** 0.5) * (
            vec_b.multiply(vec_b).sum() ** 0.5
        )
        if denom == 0:
            return 0.0
        return float((vec_a @ vec_b.T).toarray()[0][0] / denom)


def compute_features(
    *,
    resume_text: str,
    jd_text: str,
    resume_skills: Sequence[str],
    jd_required_skills: Sequence[str],
    jd_preferred_skills: Sequence[str],
    years_required: float,
    years_estimated: float,
    education_required: bool,
    education_present: bool,
    tfidf: TfidfSimilarity,
) -> MatchFeatures:
    """Compute the full feature vector for a single pair."""
    jd_required_set = list(jd_required_skills)
    jd_preferred_set = list(jd_preferred_skills)
    resume_set = list(resume_skills)

    matching = sorted(set(resume_set) & (set(jd_required_set) | set(jd_preferred_set)))
    missing = sorted(set(jd_required_set) - set(resume_set))
    extras = sorted(set(resume_set) - (set(jd_required_set) | set(jd_preferred_set)))

    cos = tfidf.similarity(resume_text, jd_text)
    jac = jaccard(resume_set, jd_required_set)
    cov = coverage(resume_set, jd_required_set)

    return MatchFeatures(
        tfidf_cosine=cos,
        jaccard_skills=jac,
        jd_coverage=cov,
        resume_skill_count=len(resume_set),
        jd_required_skill_count=len(jd_required_set),
        matching_skill_count=len(matching),
        missing_skill_count=len(missing),
        extra_skill_count=len(extras),
        years_required=float(years_required or 0.0),
        years_estimated=float(years_estimated or 0.0),
        years_gap=float((years_estimated or 0.0) - (years_required or 0.0)),
        education_required=1 if education_required else 0,
        education_present=1 if education_present else 0,
        resume_length=len(resume_text),
        jd_length=len(jd_text),
    )
