"""End-to-end training pipeline.

Generates synthetic labeled data, fits the scikit-learn baseline and the
PyTorch model, persists both, and prints a human-readable summary.

Run via:
    python -m app.ml.train_pipeline
or:
    python -m app.ml.train_pipeline --skip-baseline
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np

from app.core.config import settings
from app.core.logging import configure_logging
from app.ml.feature_engineering import TfidfSimilarity, compute_features
from app.ml.pytorch_model import MatchNet, TorchMatcher
from app.ml.sklearn_baseline import SklearnBaseline
from app.ml.synthetic_data import generate_dataset, save_dataset, load_dataset, TrainingExample
from app.services.skills_taxonomy import detect_skills

configure_logging()
logger = logging.getLogger(__name__)


def featurize(examples: list[TrainingExample]) -> tuple[np.ndarray, np.ndarray, TfidfSimilarity]:
    tfidf = TfidfSimilarity()
    corpus = [ex.resume_text for ex in examples] + [ex.job_text for ex in examples]
    tfidf.fit(corpus)
    feats = []
    targets = []
    for ex in examples:
        ff = compute_features(
            resume_text=ex.resume_text,
            jd_text=ex.job_text,
            resume_skills=ex.resume_skills,
            jd_required_skills=ex.job_skills,
            jd_preferred_skills=ex.job_preferred,
            years_required=ex.required_years,
            years_estimated=ex.resume_years,
            education_required=ex.education_required,
            education_present=ex.education_present,
            tfidf=tfidf,
        )
        feats.append(ff.to_vector())
        targets.append(ex.score)
    return np.array(feats, dtype=np.float32), np.array(targets, dtype=np.float32), tfidf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-samples", type=int, default=600)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--skip-baseline", action="store_true")
    parser.add_argument("--skip-torch", action="store_true")
    parser.add_argument("--data-path", type=str, default=None)
    args = parser.parse_args(argv)

    start = time.time()
    data_path = Path(args.data_path or settings.training_data_path)

    if data_path.exists() and data_path.stat().st_size > 0:
        logger.info("Loading existing dataset from %s", data_path)
        examples = load_dataset(data_path)
    else:
        logger.info("Generating %d synthetic examples...", args.n_samples)
        examples = generate_dataset(args.n_samples)
        save_dataset(examples, data_path)
        logger.info("Saved synthetic dataset to %s", data_path)

    if not examples:
        logger.error("Empty training set. Aborting.")
        return 1

    X, y, tfidf = featurize(examples)
    logger.info("Feature matrix shape: %s, target shape: %s", X.shape, y.shape)

    if not args.skip_baseline:
        baseline = SklearnBaseline()
        # The baseline trains its own TF-IDF; pass raw texts/scores for it.
        report = baseline.fit(
            resume_texts=[ex.resume_text for ex in examples],
            jd_texts=[ex.job_text for ex in examples],
            scores=[ex.score for ex in examples],
        )
        logger.info("Baseline report: %s", report)

    if not args.skip_torch:
        matcher = TorchMatcher()
        report = matcher.fit(X, y, epochs=args.epochs)
        logger.info("Torch report: %s", report)

    elapsed = time.time() - start
    logger.info("Done in %.1fs", elapsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
