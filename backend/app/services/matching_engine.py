"""Matching engine that combines the sklearn baseline and PyTorch model.

For each (resume, JD) pair we:
  1. Compute engineered features.
  2. Run both models for raw scores (0..1).
  3. Combine into a weighted final score.
  4. Produce explainability — what matched, what's missing, why the score is X.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from app.ml.feature_engineering import TfidfSimilarity, compute_features
from app.ml.pytorch_model import TorchMatcher
from app.ml.sklearn_baseline import SklearnBaseline

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    sklearn_score: float
    pytorch_score: float
    final_score: float
    matching_skills: List[Dict[str, str]]
    missing_skills: List[Dict[str, str]]
    extra_skills: List[str]
    experience_alignment: Dict[str, object]
    education_alignment: Dict[str, object]
    recommendations: List[str]
    feature_breakdown: Dict[str, float]
    explanation: str


@dataclass
class ModelBundle:
    """Holds loaded model references. Lives in app.state."""

    sklearn: SklearnBaseline
    pytorch: TorchMatcher
    tfidf: TfidfSimilarity
    loaded: bool = False


def load_models_if_needed(bundle: ModelBundle) -> ModelBundle:
    """Try to load persisted models; the bundle is updated in-place."""
    if bundle.sklearn.fitted:
        bundle.loaded = True
        return bundle
    ok1 = bundle.sklearn.load()
    ok2 = bundle.pytorch.load()
    if ok1 and ok2:
        # Reuse the sklearn tfidf to avoid re-fitting for inference
        bundle.tfidf = bundle.sklearn.tfidf
        bundle.loaded = True
        logger.info("Loaded persisted models from disk.")
    else:
        # Lazy train on synthetic data if no saved models exist.
        logger.info("No persisted models found; training on synthetic data...")
        from app.ml.synthetic_data import generate_dataset
        from app.ml.train_pipeline import featurize

        examples = generate_dataset(400)
        bundle.tfidf.fit([ex.resume_text for ex in examples] + [ex.job_text for ex in examples])
        bundle.sklearn.fit(
            [ex.resume_text for ex in examples],
            [ex.job_text for ex in examples],
            [ex.score for ex in examples],
        )
        X, y, _ = featurize(examples)
        bundle.pytorch.fit(X, y, epochs=60)
        bundle.loaded = True
    return bundle


def _gap_to_score(gap: float) -> float:
    """Convert years gap to a 0..1 contribution."""
    if gap >= 1:
        return 1.0
    if gap >= 0:
        return 0.7 + 0.3 * gap
    if gap >= -2:
        return max(0.0, 0.5 + 0.1 * gap)
    return 0.1


class MatchingEngine:
    """Stateless service that scores resume vs JD given a model bundle."""

    def __init__(self, bundle: ModelBundle) -> None:
        self.bundle = bundle
        self.tfidf = bundle.tfidf

    def match(
        self,
        *,
        resume_text: str,
        resume_skills: Sequence[str],
        resume_years: float,
        education_present: bool,
        jd_text: str,
        jd_required_skills: Sequence[str],
        jd_preferred_skills: Sequence[str],
        jd_required_years: float,
        jd_education_required: bool,
    ) -> MatchResult:
        features = compute_features(
            resume_text=resume_text,
            jd_text=jd_text,
            resume_skills=resume_skills,
            jd_required_skills=jd_required_skills,
            jd_preferred_skills=jd_preferred_skills,
            years_required=jd_required_years,
            years_estimated=resume_years,
            education_required=jd_education_required,
            education_present=education_present,
            tfidf=self.tfidf,
        )
        vector = features.to_vector()

        sklearn_raw = self.bundle.sklearn.predict_score(vector)
        pytorch_raw = self.bundle.pytorch.predict(vector)
        # Prefer calibrated outputs (fitted on validation slice) so each model
        # speaks in true match-probability space; fall back to raw if a model
        # was loaded from a pre-calibration checkpoint.
        sklearn_score = float(
            getattr(self.bundle.sklearn, "predict_score_calibrated", None)
            and self.bundle.sklearn.predict_score_calibrated(vector)
            or sklearn_raw
        )
        pytorch_score = float(
            getattr(self.bundle.pytorch, "predict_calibrated", None)
            and self.bundle.pytorch.predict_calibrated(vector)
            or pytorch_raw
        )

        # Rule-of-thumb heuristic: mirror the synthetic scoring function so we
        # have an independent third signal. Capped in [0.05, 0.95] to avoid
        # multiplications by zero in the geometric mean below.
        edu_ok = (not jd_education_required) or education_present
        heuristic = (
            features.jd_coverage * 0.75
            + max(0.0, features.years_gap) * 0.04
            + (0.05 if edu_ok else 0.0)
        )
        heuristic = max(0.05, min(0.95, heuristic))

        # Geometric mean of three calibrated probabilities. This is the
        # job-hunter-friendly blend: a single model outputting 1.0 cannot
        # dominate the score (it gets clipped by the lower signal), and a
        # single model outputting 0.1 cannot sink the score either.
        # Result is also floored at 5% so very weak fits still register.
        eps = 0.05
        s_clip = max(eps, min(1 - eps, sklearn_score))
        p_clip = max(eps, min(1 - eps, pytorch_score))
        h_clip = max(eps, min(1 - eps, heuristic))
        geo = (s_clip * p_clip * h_clip) ** (1 / 3)
        final_score = round(geo * 100, 1)
        sklearn_pct = round(sklearn_score * 100, 1)
        pytorch_pct = round(pytorch_score * 100, 1)

        # Skill alignment
        resume_skill_set = set(resume_skills)
        req_set = set(jd_required_skills)
        pref_set = set(jd_preferred_skills)
        matching = sorted(resume_skill_set & req_set)
        matching_with_preferred = resume_skill_set & (req_set | pref_set)
        missing = sorted(req_set - resume_skill_set)
        extras = sorted(resume_skill_set - (req_set | pref_set))

        matching_skills = [{"name": s, "matched": "required"} for s in matching]
        for s in sorted(matching_with_preferred - set(matching)):
            matching_skills.append({"name": s, "matched": "preferred"})
        missing_skills = [{"name": s, "matched": False} for s in missing]

        # Experience alignment
        gap = (resume_years or 0) - (jd_required_years or 0)
        if jd_required_years and jd_required_years > 0:
            if gap >= 0:
                notes = (
                    f"Resume shows about {resume_years:.1f} years vs {jd_required_years:.0f}+ required — meets bar."
                )
            else:
                notes = (
                    f"Resume shows about {resume_years:.1f} years vs {jd_required_years:.0f}+ required — short by {abs(gap):.1f}."
                )
        else:
            notes = "No specific years required; experience not weighted heavily."
        experience_alignment = {
            "required_years": jd_required_years or None,
            "estimated_years": resume_years or None,
            "matched": (jd_required_years or 0) <= (resume_years or 0),
            "notes": notes,
        }

        # Education alignment
        # Note: schema's EducationAlignment.required is Optional[str], so emit a
        # human-readable label rather than a bool. None when there's no requirement.
        education_alignment = {
            "required": ("required" if jd_education_required else None),
            "candidates": ["Bachelor", "Master", "PhD"] if education_present else [],
            "matched": (not jd_education_required) or education_present,
            "notes": (
                "Required degree found in resume."
                if jd_education_required and education_present
                else "No degree requirement, or no degree section detected."
            ),
        }

        # Feature breakdown (directionality)
        breakdown = {
            "tfidf_cosine": round(features.tfidf_cosine, 4),
            "jaccard_skills": round(features.jaccard_skills, 4),
            "jd_coverage": round(features.jd_coverage, 4),
            "matching_skill_count": float(features.matching_skill_count),
            "missing_skill_count": float(features.missing_skill_count),
            "years_gap": round(features.years_gap, 4),
            "education_alignment": float(1.0 if education_alignment["matched"] else 0.0),
        }

        recommendations = self._recommendations(
            missing_skills=missing_skills,  # the dict list, not the bare str list
            extras=extras,
            experience_gap=gap,
            education_required=jd_education_required,
            education_present=education_present,
            final_score=final_score,
        )

        heuristic_pct = round(heuristic * 100, 1)
        explanation = self._explain(
            sklearn_pct=sklearn_pct,
            pytorch_pct=pytorch_pct,
            heuristic_pct=heuristic_pct,
            final_score=final_score,
            matching=matching,
            missing=missing,  # here the str list is correct (used for prose)
            experience_alignment=experience_alignment,
            education_alignment=education_alignment,
            feature_breakdown=breakdown,
        )

        return MatchResult(
            sklearn_score=sklearn_pct,
            pytorch_score=pytorch_pct,
            final_score=final_score,
            matching_skills=matching_skills,
            missing_skills=missing_skills,
            extra_skills=extras,
            experience_alignment=experience_alignment,
            education_alignment=education_alignment,
            recommendations=recommendations,
            feature_breakdown=breakdown,
            explanation=explanation,
        )

    # ----------------------------------------------------------- helpers
    def _recommendations(
        self,
        *,
        missing_skills: List[Dict[str, str]],
        extras: List[str],
        experience_gap: float,
        education_required: bool,
        education_present: bool,
        final_score: float,
    ) -> List[str]:
        recs: List[str] = []
        if missing_skills:
            top_missing = [m["name"] for m in missing_skills[:3]]
            recs.append(
                f"Build a small project demonstrating: {', '.join(top_missing)}."
            )
        if extras:
            recs.append(
                "Tailor your resume summary toward the JD's primary stack "
                f"({ ', '.join(extras[:2]) } are extra noise for this role)."
            )
        if experience_gap < -1:
            recs.append(
                "Highlight internships, open-source contributions, or personal projects "
                "to compensate for the experience gap."
            )
        if education_required and not education_present:
            recs.append(
                "Add a clear Education section (degree, institution, graduation year)."
            )
        if final_score >= 80:
            recs.append("Strong fit — focus on quantified achievements in your cover letter.")
        elif final_score >= 60:
            recs.append("Moderate fit — emphasize transferable projects and impact.")
        else:
            recs.append("Lower fit — consider targeting roles more aligned with your core stack.")
        return recs

    def _explain(
        self,
        *,
        sklearn_pct: float,
        pytorch_pct: float,
        heuristic_pct: float,
        final_score: float,
        matching: List[str],
        missing: List[str],
        experience_alignment: Dict[str, object],
        education_alignment: Dict[str, object],
        feature_breakdown: Dict[str, float],
    ) -> str:
        lines = []
        lines.append(
            f"Final score {final_score}% — geometric mean of three calibrated signals: "
            f"scikit-learn {sklearn_pct}%, PyTorch {pytorch_pct}%, "
            f"coverage heuristic {heuristic_pct}%."
        )
        if matching:
            matched_preview = ", ".join(matching[:6]) + ("…" if len(matching) > 6 else "")
            lines.append(f"Coverage of required skills: {len(matching)} matched (incl. {matched_preview}).")
        if missing:
            missing_preview = ", ".join(missing[:6]) + ("…" if len(missing) > 6 else "")
            lines.append(f"Missing required skills: {missing_preview}.")
        if experience_alignment.get("notes"):
            lines.append(f"Experience: {experience_alignment['notes']}")
        if education_alignment.get("notes"):
            lines.append(f"Education: {education_alignment['notes']}")
        lines.append(
            f"Top features: TF-IDF cosine={feature_breakdown['tfidf_cosine']:.3f}, "
            f"skill coverage={feature_breakdown['jd_coverage']:.3f}, "
            f"years gap={feature_breakdown['years_gap']:.1f}."
        )
        return " ".join(lines)
