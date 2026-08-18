"""scikit-learn baseline: TF-IDF + cosine similarity + engineered features.

We train two heads:
1) A regression head (Ridge) that predicts a continuous match score (0..1).
2) A classifier head (LogisticRegression) that predicts good / average / poor.

Both consume the same feature vector (cosine similarity + engineered features).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import joblib
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.core.config import settings
from app.ml.feature_engineering import TfidfSimilarity, compute_features

logger = logging.getLogger(__name__)


@dataclass
class BaselineReport:
    model_version: str
    training_samples: int
    metrics: Dict[str, float]
    confusion: List[List[int]]


class SklearnBaseline:
    """Wrap the scikit-learn pipeline, including persistable artifacts."""

    MODEL_VERSION = "sklearn-baseline-v1"

    def __init__(self) -> None:
        self.tfidf = TfidfSimilarity()
        self.scaler: Optional[StandardScaler] = None
        self.regressor: Optional[Ridge] = None
        self.classifier: Optional[LogisticRegression] = None
        self.calibrator: Optional[IsotonicRegression] = None
        self._fitted = False

    # ----------------------------------------------------------- training
    def fit(
        self,
        resume_texts: Sequence[str],
        jd_texts: Sequence[str],
        scores: Sequence[float],
    ) -> BaselineReport:
        """Fit both heads. `scores` are continuous ground-truth in [0, 1]."""
        assert len(resume_texts) == len(jd_texts) == len(scores), "Lengths must match"

        # 1) Fit TF-IDF over the corpus
        corpus = list(resume_texts) + list(jd_texts)
        self.tfidf.fit(corpus)

        # 2) Compute engineered features for each pair
        # We approximate resume / JD skills using the taxonomy on raw text.
        from app.services.skills_taxonomy import detect_skills

        features: List[List[float]] = []
        scores_arr: List[float] = []
        labels: List[int] = []
        for rtxt, jtxt, score in zip(resume_texts, jd_texts, scores):
            r_skills = detect_skills(rtxt)
            j_skills = detect_skills(jtxt)
            ff = compute_features(
                resume_text=rtxt,
                jd_text=jtxt,
                resume_skills=r_skills,
                jd_required_skills=j_skills,
                jd_preferred_skills=[],
                years_required=0.0,
                years_estimated=0.0,
                education_required=False,
                education_present=False,
                tfidf=self.tfidf,
            )
            features.append(ff.to_vector())
            scores_arr.append(float(score))
            # Discrete label: 0 poor (<0.4), 1 average (<0.7), 2 good (>=0.7)
            if score >= 0.7:
                labels.append(2)
            elif score >= 0.4:
                labels.append(1)
            else:
                labels.append(0)

        X = np.array(features, dtype=np.float32)
        y_reg = np.array(scores_arr, dtype=np.float32)
        y_cls = np.array(labels, dtype=np.int64)

        X_train, X_test, y_reg_train, y_reg_test, y_cls_train, y_cls_test = train_test_split(
            X,
            y_reg,
            y_cls,
            test_size=0.2,
            random_state=42,
            stratify=y_cls,
        )

        self.scaler = StandardScaler().fit(X_train)
        X_train_s = self.scaler.transform(X_train)
        X_test_s = self.scaler.transform(X_test)

        # Regression head
        self.regressor = Ridge(alpha=1.0, random_state=42)
        self.regressor.fit(X_train_s, y_reg_train)
        reg_pred = np.clip(self.regressor.predict(X_test_s), 0.0, 1.0)

        # Isotonic calibration: maps raw regressor output -> true match probability.
        # Without this, the Ridge head over-spreads scores and the final blend
        # becomes a comparison of two differently-calibrated distributions.
        try:
            self.calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            self.calibrator.fit(reg_pred, y_reg_test)
        except Exception as exc:
            logger.warning("Isotonic calibration failed for sklearn baseline: %s", exc)
            self.calibrator = None

        # Classifier head
        self.classifier = LogisticRegression(max_iter=2000, multi_class="multinomial")
        self.classifier.fit(X_train_s, y_cls_train)
        cls_pred = self.classifier.predict(X_test_s)

        mse = float(mean_squared_error(y_reg_test, reg_pred))
        mae = float(mean_absolute_error(y_reg_test, reg_pred))
        r2 = float(r2_score(y_reg_test, reg_pred))
        precision = float(precision_score(y_cls_test, cls_pred, average="macro", zero_division=0))
        recall = float(recall_score(y_cls_test, cls_pred, average="macro", zero_division=0))
        f1 = float(f1_score(y_cls_test, cls_pred, average="macro", zero_division=0))
        try:
            auc = float(
                roc_auc_score(
                    y_cls_test,
                    self.classifier.predict_proba(X_test_s),
                    multi_class="ovr",
                )
            )
        except Exception:
            auc = 0.0
        cm = confusion_matrix(y_cls_test, cls_pred).tolist()

        metrics = {
            "mse": mse,
            "mae": mae,
            "r2": r2,
            "precision_macro": precision,
            "recall_macro": recall,
            "f1_macro": f1,
            "roc_auc_ovr": auc,
            "rmse": float(np.sqrt(mse)),
        }

        # Print for visibility
        logger.info("sklearn baseline trained on %d samples", len(resume_texts))
        logger.info("regression metrics: %s", json.dumps(metrics, indent=2))
        logger.info("classification report:\n%s", classification_report(y_cls_test, cls_pred, zero_division=0))

        self._fitted = True

        # Persist
        try:
            self.save()
        except Exception as exc:  # pragma: no cover - disk-only
            logger.warning("Could not persist baseline: %s", exc)

        return BaselineReport(
            model_version=self.MODEL_VERSION,
            training_samples=len(resume_texts),
            metrics=metrics,
            confusion=cm,
        )

    # ----------------------------------------------------------- inference
    def predict_score(self, features: Sequence[float]) -> float:
        """Predict a 0..1 score from a feature vector (raw regressor output)."""
        if not self._fitted:
            raise RuntimeError("Model not fitted / loaded. Call fit() or load().")
        arr = np.array(features, dtype=np.float32).reshape(1, -1)
        arr_s = self.scaler.transform(arr)
        pred = float(self.regressor.predict(arr_s)[0])
        return float(max(0.0, min(1.0, pred)))

    def predict_score_calibrated(self, features: Sequence[float]) -> float:
        """Predict a 0..1 calibrated match probability.

        Runs the raw regressor, then applies the isotonic calibrator fitted on
        the validation slice. Falls back to raw output if no calibrator is
        available (e.g. legacy model loaded from a pre-calibration checkpoint).
        """
        raw = self.predict_score(features)
        if self.calibrator is None:
            return raw
        try:
            return float(self.calibrator.predict([raw])[0])
        except Exception:
            return raw

    def predict_label(self, features: Sequence[float]) -> int:
        if not self._fitted:
            raise RuntimeError("Model not fitted / loaded. Call fit() or load().")
        arr = np.array(features, dtype=np.float32).reshape(1, -1)
        arr_s = self.scaler.transform(arr)
        return int(self.classifier.predict(arr_s)[0])

    # ----------------------------------------------------------- persistence
    def save(self) -> None:
        path = Path(settings.sklearn_model_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "scaler": self.scaler,
                "regressor": self.regressor,
                "classifier": self.classifier,
                "tfidf_vectorizer": self.tfidf.vectorizer,
                "calibrator": self.calibrator,
                "version": self.MODEL_VERSION,
            },
            path,
        )

    def load(self) -> bool:
        path = Path(settings.sklearn_model_path)
        if not path.exists():
            return False
        try:
            data = joblib.load(path)
            self.scaler = data["scaler"]
            self.regressor = data["regressor"]
            self.classifier = data["classifier"]
            self.tfidf.vectorizer = data["tfidf_vectorizer"]
            self.calibrator = data.get("calibrator")  # optional, pre-calibration models won't have it
            self.tfidf._fitted = True
            self.MODEL_VERSION = data.get("version", self.MODEL_VERSION)
            self._fitted = True
            return True
        except Exception as exc:
            logger.warning("Could not load sklearn baseline: %s", exc)
            return False

    @property
    def fitted(self) -> bool:
        return self._fitted
