"""Tests for the matching engine using a freshly-loaded model bundle."""
import numpy as np

from app.ml.feature_engineering import TfidfSimilarity
from app.ml.pytorch_model import TorchMatcher
from app.ml.sklearn_baseline import SklearnBaseline
from app.ml.synthetic_data import generate_dataset
from app.ml.train_pipeline import featurize
from app.services.matching_engine import MatchingEngine, ModelBundle, load_models_if_needed


def test_matching_engine_produces_full_result():
    examples = generate_dataset(80)
    bundle = ModelBundle(
        sklearn=SklearnBaseline(),
        pytorch=TorchMatcher(),
        tfidf=TfidfSimilarity(),
    )
    bundle.tfidf.fit([ex.resume_text for ex in examples] + [ex.job_text for ex in examples])
    bundle.sklearn.fit(
        [ex.resume_text for ex in examples],
        [ex.job_text for ex in examples],
        [ex.score for ex in examples],
    )
    X, y, _ = featurize(examples)
    bundle.pytorch.fit(X, y, epochs=10)
    bundle.loaded = True

    engine = MatchingEngine(bundle)
    ex = examples[0]
    result = engine.match(
        resume_text=ex.resume_text,
        resume_skills=ex.resume_skills,
        resume_years=ex.resume_years,
        education_present=ex.education_present,
        jd_text=ex.job_text,
        jd_required_skills=ex.job_skills,
        jd_preferred_skills=ex.job_preferred,
        jd_required_years=ex.required_years,
        jd_education_required=ex.education_required,
    )

    assert 0.0 <= result.sklearn_score <= 100.0
    assert 0.0 <= result.pytorch_score <= 100.0
    assert 0.0 <= result.final_score <= 100.0
    assert isinstance(result.matching_skills, list)
    assert isinstance(result.missing_skills, list)
    assert isinstance(result.recommendations, list)
    assert len(result.explanation) > 20
