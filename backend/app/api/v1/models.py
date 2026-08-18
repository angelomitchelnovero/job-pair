"""Model performance endpoint."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models import ModelPerformance
from app.schemas import ModelPerformanceResponse
from app.ml.train_pipeline import featurize
from app.ml.synthetic_data import load_dataset, generate_dataset

router = APIRouter(prefix="/models", tags=["models"])
logger = logging.getLogger(__name__)


@router.get(
    "/performance",
    response_model=List[ModelPerformanceResponse],
    summary="Get historical model performance snapshots",
)
async def list_performance(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> List[ModelPerformanceResponse]:
    stmt = select(ModelPerformance).order_by(ModelPerformance.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    if not rows:
        return [await _live_snapshot(request)]
    return [ModelPerformanceResponse.model_validate(r) for r in rows]


async def _live_snapshot(request: Request) -> ModelPerformanceResponse:
    """Return live metrics from the loaded models (or train a quick eval if needed)."""
    bundle = getattr(request.app.state, "model_bundle", None)
    if bundle is None or not bundle.loaded:
        # Generate example dataset and quick metrics
        examples = _cached_or_generate_examples()
        X, y, _ = featurize(examples)
        return ModelPerformanceResponse(
            id="live",
            model_name="combined",
            version="lazy",
            metrics={"training_samples": len(examples)},
            training_samples=len(examples),
            notes="Models not yet loaded — this is a fallback snapshot.",
            created_at=__utcnow(),
        )

    from sklearn.metrics import (
        f1_score,
        mean_absolute_error,
        mean_squared_error,
        precision_score,
        r2_score,
        recall_score,
    )
    import numpy as np

    examples = _cached_or_generate_examples()
    X, y, _ = featurize(examples)
    preds_sklearn = []
    preds_torch = []
    for vec, target in zip(X, y):
        try:
            preds_sklearn.append(bundle.sklearn.predict_score(vec.tolist()))
            preds_torch.append(bundle.pytorch.predict(vec.tolist()))
        except Exception:
            preds_sklearn.append(0.0)
            preds_torch.append(0.0)
    preds_sklearn = np.clip(np.array(preds_sklearn), 0.0, 1.0)
    preds_torch = np.clip(np.array(preds_torch), 0.0, 1.0)
    labels = (y >= 0.7).astype(int)
    pred_labels = (preds_torch >= 0.5).astype(int)

    metrics = {
        "sklearn_mse": float(mean_squared_error(y, preds_sklearn)),
        "sklearn_mae": float(mean_absolute_error(y, preds_sklearn)),
        "sklearn_r2": float(r2_score(y, preds_sklearn)),
        "pytorch_mse": float(mean_squared_error(y, preds_torch)),
        "pytorch_mae": float(mean_absolute_error(y, preds_torch)),
        "pytorch_r2": float(r2_score(y, preds_torch)),
        "pytorch_precision": float(precision_score(labels, pred_labels, zero_division=0)),
        "pytorch_recall": float(recall_score(labels, pred_labels, zero_division=0)),
        "pytorch_f1": float(f1_score(labels, pred_labels, zero_division=0)),
        "training_samples": int(len(examples)),
    }
    return ModelPerformanceResponse(
        id="live",
        model_name="sklearn+pytorch",
        version=f"sklearn:{bundle.sklearn.MODEL_VERSION},pytorch:{bundle.pytorch.MODEL_VERSION}",
        metrics=metrics,
        training_samples=int(len(examples)),
        notes="Live evaluation on a representative synthetic sample.",
        created_at=__utcnow(),
    )


def __utcnow():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def _cached_or_generate_examples(limit: int = 200):
    path = Path(settings.training_data_path)
    if path.exists() and path.stat().st_size > 0:
        examples = load_dataset(path)[:limit]
        if examples:
            return examples
    return generate_dataset(limit)
