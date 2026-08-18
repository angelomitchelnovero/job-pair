"""Job description API endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models import Job
from app.schemas import JobCreate, JobResponse
from app.services.job_parser import JobParser

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job description",
)
async def create_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    parser = JobParser()
    parsed = parser.parse(
        description=payload.description,
        title=payload.title,
        company=payload.company,
    )
    job = Job(
        title=parsed.title or payload.title,
        company=parsed.company or payload.company,
        description=payload.description,
        skills_required=payload.skills_required or parsed.skills_required,
        skills_preferred=payload.skills_preferred or parsed.skills_preferred,
        responsibilities=payload.responsibilities or parsed.responsibilities,
        experience_years=payload.experience_years if payload.experience_years is not None else parsed.experience_years,
        education_required=payload.education_required or parsed.education_required,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return JobResponse.model_validate(job)


@router.get("", response_model=List[JobResponse], summary="List job descriptions")
async def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[JobResponse]:
    stmt = (
        select(Job)
        .order_by(Job.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [JobResponse.model_validate(r) for r in rows]


@router.get("/{job_id}", response_model=JobResponse, summary="Get a job description by id")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)) -> JobResponse:
    job = await db.get(Job, job_id)
    if not job:
        raise NotFoundError(f"Job {job_id} not found.")
    return JobResponse.model_validate(job)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,  # plain Response has no body — required for 204
    summary="Delete a job",
)
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(Job, job_id)
    if not job:
        raise NotFoundError(f"Job {job_id} not found.")
    await db.delete(job)
    await db.commit()
