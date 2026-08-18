"""Tests for ML components."""
import numpy as np
import pytest

from app.ml.feature_engineering import (
    MatchFeatures,
    TfidfSimilarity,
    compute_features,
    coverage,
    jaccard,
)
from app.ml.pytorch_model import MatchNet, TorchMatcher
from app.ml.sklearn_baseline import SklearnBaseline
from app.ml.synthetic_data import generate_dataset, save_dataset
from app.ml.train_pipeline import featurize


def test_jaccard_basic():
    assert jaccard({"a", "b", "c"}, {"b", "c", "d"}) == pytest.approx(2 / 4)


def test_jaccard_empty():
    assert jaccard(set(), set()) == 0.0
    assert jaccard({"a"}, set()) == 0.0


def test_coverage_basic():
    assert coverage({"a", "b"}, {"a", "b", "c"}) == pytest.approx(2 / 3)


def test_tfidf_similarity_identical():
    tfidf = TfidfSimilarity()
    text = "Python developer with FastAPI and PostgreSQL experience"
    s = tfidf.similarity(text, text)
    assert s > 0.95


def test_tfidf_similarity_different():
    tfidf = TfidfSimilarity()
    a = "Python FastAPI PostgreSQL"
    b = "Graphic design and photography"
    s = tfidf.similarity(a, b)
    assert 0.0 <= s < 0.5


def test_compute_features_vector_dim():
    tfidf = TfidfSimilarity()
    tfidf.fit(["python resume", "ml job"])
    ff = compute_features(
        resume_text="python developer",
        jd_text="python job",
        resume_skills=["python"],
        jd_required_skills=["python"],
        jd_preferred_skills=[],
        years_required=2.0,
        years_estimated=3.0,
        education_required=True,
        education_present=True,
        tfidf=tfidf,
    )
    vec = ff.to_vector()
    assert len(vec) == len(MatchFeatures.feature_names())
    assert ff.years_gap == 1.0


def test_synthetic_dataset_generation():
    examples = generate_dataset(20)
    assert len(examples) == 20
    assert all(0.0 <= ex.score <= 1.0 for ex in examples)
    assert all(ex.job_skills for ex in examples)


def test_sklearn_baseline_fit_predict(tmp_path):
    from app.core.config import settings

    examples = generate_dataset(60)
    save_dataset(examples, tmp_path / "training_data.json")

    old_sklearn_path = settings.sklearn_model_path
    settings.sklearn_model_path = str(tmp_path / "baseline.joblib")
    try:
        baseline = SklearnBaseline()
        report = baseline.fit(
            resume_texts=[ex.resume_text for ex in examples],
            jd_texts=[ex.job_text for ex in examples],
            scores=[ex.score for ex in examples],
        )
        assert report.training_samples == len(examples)
        assert "mse" in report.metrics
        assert baseline.fitted

        # Predict
        ff = compute_features(
            resume_text=examples[0].resume_text,
            jd_text=examples[0].job_text,
            resume_skills=examples[0].resume_skills,
            jd_required_skills=examples[0].job_skills,
            jd_preferred_skills=examples[0].job_preferred,
            years_required=examples[0].required_years,
            years_estimated=examples[0].resume_years,
            education_required=examples[0].education_required,
            education_present=examples[0].education_present,
            tfidf=baseline.tfidf,
        )
        pred = baseline.predict_score(ff.to_vector())
        assert 0.0 <= pred <= 1.0
    finally:
        settings.sklearn_model_path = old_sklearn_path


def test_torch_matcher_fit_predict(tmp_path):
    from app.core.config import settings

    examples = generate_dataset(80)
    X, y, _ = featurize(examples)
    assert X.shape[1] == 15

    old_torch_path = settings.pytorch_model_path
    settings.pytorch_model_path = str(tmp_path / "matcher.pt")
    try:
        matcher = TorchMatcher()
        report = matcher.fit(X, y, epochs=10)
        assert report.training_samples == len(examples)
        assert matcher.fitted
        score = matcher.predict(X[0].tolist())
        assert 0.0 <= score <= 1.0
    finally:
        settings.pytorch_model_path = old_torch_path


def test_matchnet_forward_shape():
    import torch

    model = MatchNet(input_dim=15, hidden=16)
    x = torch.randn(4, 15)
    out = model(x)
    assert out.shape == (4,)
    assert ((out >= 0) & (out <= 1)).all()
