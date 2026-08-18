"""API v1 router aggregator."""
from fastapi import APIRouter

from app.api.v1 import jobs, matches, models, resumes

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(resumes.router)
api_router.include_router(jobs.router)
api_router.include_router(matches.router)
api_router.include_router(models.router)
