"""FastAPI application entry point."""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging
from app.ml.pytorch_model import TorchMatcher
from app.ml.sklearn_baseline import SklearnBaseline
from app.services.matching_engine import ModelBundle, load_models_if_needed

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load ML models on startup."""
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    bundle = ModelBundle(
        sklearn=SklearnBaseline(),
        pytorch=TorchMatcher(),
        tfidf=SklearnBaseline().tfidf,  # placeholder; replaced by load_models_if_needed
    )
    try:
        load_models_if_needed(bundle)
        app.state.model_bundle = bundle
        logger.info(
            "Models ready. sklearn_loaded=%s pytorch_loaded=%s",
            bundle.sklearn.fitted,
            bundle.pytorch.fitted,
        )
    except Exception as exc:
        logger.exception("Failed to load models: %s", exc)
        app.state.model_bundle = bundle  # type: ignore
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-powered Resume-to-Job matching platform. "
        "Combines a scikit-learn TF-IDF/cosine baseline with a PyTorch matching network."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        raise
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Response-Time-ms"] = f"{duration_ms:.1f}"
    return response


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Request validation failed.",
            "details": exc.errors(),
        },
    )


@app.get("/", tags=["meta"], summary="Root info")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "api": "/api/v1",
    }


@app.get("/health", tags=["meta"], summary="Health check")
async def health(request: Request) -> dict:
    bundle = getattr(request.app.state, "model_bundle", None)
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.app_env,
        "sklearn_loaded": bool(bundle and bundle.sklearn.fitted),
        "pytorch_loaded": bool(bundle and bundle.pytorch.fitted),
    }


app.include_router(api_router)
