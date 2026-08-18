"""Match analysis API endpoints."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import NotFoundError, ProcessingError, ModelNotFoundError
from app.db.session import get_db
from app.models import Job, Match, Resume
from app.schemas import (
    CombinedAnalysisRequest,
    MatchCreate,
    MatchResponse,
)
from app.services.job_parser import JobParser
from app.services.matching_engine import MatchingEngine
from app.services.resume_parser import ResumeParser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matches", tags=["matches"])


def _engine(request: Request) -> MatchingEngine:
    bundle = getattr(request.app.state, "model_bundle", None)
    if bundle is None or not bundle.loaded:
        raise ModelNotFoundError("Models are not loaded yet. Please try again shortly.")
    return MatchingEngine(bundle)


@router.post(
    "",
    response_model=MatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze a resume vs a job and persist the result",
)
async def create_match(
    payload: MatchCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MatchResponse:
    resume_text, resume_skills, years, edu_present, resume = await _resolve_resume(
        payload=payload, db=db
    )
    job_text, jd_required, jd_preferred, jd_required_years, jd_edu_required, job = await _resolve_job(
        payload=payload, db=db
    )

    engine = _engine(request)
    result = engine.match(
        resume_text=resume_text,
        resume_skills=resume_skills,
        resume_years=years,
        education_present=edu_present,
        jd_text=job_text,
        jd_required_skills=jd_required,
        jd_preferred_skills=jd_preferred,
        jd_required_years=jd_required_years,
        jd_education_required=jd_edu_required,
    )

    match = Match(
        resume_id=resume.id,
        job_id=job.id,
        sklearn_score=result.sklearn_score,
        pytorch_score=result.pytorch_score,
        final_score=result.final_score,
        matching_skills=result.matching_skills,
        missing_skills=result.missing_skills,
        extra_skills=result.extra_skills,
        experience_alignment=result.experience_alignment,
        education_alignment=result.education_alignment,
        recommendations=result.recommendations,
        feature_breakdown=[
            {"feature": k, "contribution": v, "direction": "positive" if v > 0 else "neutral"}
            for k, v in (result.feature_breakdown or {}).items()
        ],
        explanation=result.explanation,
    )
    db.add(match)
    await db.commit()
    await db.refresh(match)
    return MatchResponse.model_validate(match)


@router.post(
    "/preview",
    response_model=MatchResponse,
    summary="Analyze without persisting (live preview)",
)
async def preview_match(
    payload: CombinedAnalysisRequest,
    request: Request,
) -> MatchResponse:
    """Same matching as POST /matches but doesn't save anything."""
    resume_parser = ResumeParser()
    job_parser = JobParser()
    parsed_resume = resume_parser.parse_text(payload.resume_text)
    parsed_job = job_parser.parse(
        description=payload.job_text,
        title=payload.job_title,
        company=payload.job_company,
    )
    engine = _engine(request)
    result = engine.match(
        resume_text=payload.resume_text,
        resume_skills=parsed_resume.skills,
        resume_years=parsed_resume.years_experience_estimate or 0.0,
        education_present=bool(parsed_resume.education) or _detect_degree(payload.resume_text),
        jd_text=payload.job_text,
        jd_required_skills=parsed_job.skills_required,
        jd_preferred_skills=parsed_job.skills_preferred,
        jd_required_years=float(parsed_job.experience_years or 0),
        jd_education_required=bool(parsed_job.education_required),
    )

    return MatchResponse(
        id="preview",
        resume_id=None,
        job_id=None,
        sklearn_score=result.sklearn_score,
        pytorch_score=result.pytorch_score,
        final_score=result.final_score,
        matching_skills=result.matching_skills,
        missing_skills=result.missing_skills,
        extra_skills=result.extra_skills,
        experience_alignment=result.experience_alignment,
        education_alignment=result.education_alignment,
        recommendations=result.recommendations,
        feature_breakdown=[
            {"feature": k, "contribution": v, "direction": "positive" if v > 0 else "neutral"}
            for k, v in result.feature_breakdown.items()
        ],
        explanation=result.explanation,
        created_at=datetime.utcnow(),
    )


@router.get("", response_model=List[MatchResponse], summary="List previous matches")
async def list_matches(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[MatchResponse]:
    # joinedload eliminates the N+1 when `_match_response` reads
    # Match.job.title / .company / .description and Match.resume.filename.
    stmt = (
        select(Match)
        .options(joinedload(Match.job), joinedload(Match.resume))
        .order_by(Match.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().unique().all()
    return [_match_response(m) for m in rows]


@router.get("/{match_id}", response_model=MatchResponse, summary="Get a match by id")
async def get_match(match_id: str, db: AsyncSession = Depends(get_db)) -> MatchResponse:
    match = await db.get(Match, match_id)
    if not match:
        raise NotFoundError(f"Match {match_id} not found.")
    return _match_response(match)


@router.delete(
    "/{match_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,  # plain Response has no body — required for 204
    summary="Delete a match record (independent of resume/job delete)",
)
async def delete_match(match_id: str, db: AsyncSession = Depends(get_db)):
    # The preview-match sentinel from POST /matches/preview is not a real
    # row — there's nothing to delete, so reject it with 404 instead of
    # silently 204'ing on a non-existent id.
    if match_id == "preview":
        raise NotFoundError("Preview matches cannot be deleted.")
    match = await db.get(Match, match_id)
    if not match:
        raise NotFoundError(f"Match {match_id} not found.")
    await db.delete(match)
    await db.commit()


def _match_response(m: Match) -> MatchResponse:
    breakdown = m.feature_breakdown or {}
    weights = breakdown.get("weights") if isinstance(breakdown, dict) else {}
    feature_breakdown = [
        {"feature": k, "contribution": v, "direction": "positive" if v > 0 else "neutral"}
        for k, v in (weights or {}).items()
    ] if isinstance(weights, dict) else []
    # The eagerly-loaded relationships may be missing on freshly-flushed rows
    # (e.g. `create_match` calls `MatchResponse.model_validate(match)` directly
    # without eager loading), so use `getattr` with a default rather than
    # relying on `.job` being populated.
    job = getattr(m, "job", None)
    resume = getattr(m, "resume", None)
    return MatchResponse(
        id=m.id,
        resume_id=m.resume_id,
        job_id=m.job_id,
        job_title=job.title if job else None,
        job_company=job.company if job else None,
        job_description=job.description if job else None,
        resume_filename=resume.filename if resume else None,
        sklearn_score=m.sklearn_score,
        pytorch_score=m.pytorch_score,
        final_score=m.final_score,
        matching_skills=m.matching_skills or [],
        missing_skills=m.missing_skills or [],
        extra_skills=m.extra_skills or [],
        experience_alignment=m.experience_alignment or {},
        education_alignment=m.education_alignment or {},
        recommendations=m.recommendations or [],
        feature_breakdown=feature_breakdown,
        explanation=m.explanation,
        created_at=m.created_at,
    )


_DEGREE_WORDS = ("bachelor", "master", "phd", "doctorate", "degree", "mba", "b.sc", "m.sc")


def _detect_degree(text: str) -> bool:
    lower = text.lower()
    return any(w in lower for w in _DEGREE_WORDS)


async def _resolve_resume(
    *,
    payload: MatchCreate,
    db: AsyncSession,
) -> tuple[str, list, float, bool, Resume]:
    """Load or create a Resume from a MatchCreate payload.

    Returns (text, skills, years_estimate, education_present, orm_object).
    """
    if payload.resume_id:
        resume = await db.get(Resume, payload.resume_id)
        if not resume:
            raise NotFoundError(f"Resume {payload.resume_id} not found.")
        years = 0.0
        if resume.experience:
            years = sum(e.get("years_estimate") or 0 for e in resume.experience) or 0.0
        return (
            resume.raw_text,
            list(resume.skills or []),
            years,
            bool(resume.education) or _detect_degree(resume.raw_text),
            resume,
        )

    if payload.resume_text:
        parsed = ResumeParser().parse_text(payload.resume_text)
        resume = Resume(
            filename="pasted.txt",
            raw_text=payload.resume_text,
            skills=parsed.skills,
            experience=parsed.experience,
            education=parsed.education,
            projects=parsed.projects,
            certifications=parsed.certifications,
            sections=parsed.sections,
        )
        db.add(resume)
        await db.flush()
        return (
            payload.resume_text,
            parsed.skills,
            parsed.years_experience_estimate or 0.0,
            bool(parsed.education) or _detect_degree(payload.resume_text),
            resume,
        )

    raise ProcessingError(
        "Provide either resume_id or resume_text for matching.",
    )


async def _resolve_job(
    *,
    payload: MatchCreate,
    db: AsyncSession,
) -> tuple[str, list, list, float, bool, Job]:
    """Load or create a Job from a MatchCreate payload."""
    if payload.job_id:
        job = await db.get(Job, payload.job_id)
        if not job:
            raise NotFoundError(f"Job {payload.job_id} not found.")
        return (
            job.description,
            list(job.skills_required or []),
            list(job.skills_preferred or []),
            float(job.experience_years or 0),
            bool(job.education_required),
            job,
        )

    if payload.job_text:
        parser = JobParser()
        parsed = parser.parse(
            description=payload.job_text,
            title=payload.job_title or "Untitled",
            company=payload.job_company,
        )
        job = Job(
            title=parsed.title or payload.job_title or "Untitled",
            company=parsed.company or payload.job_company,
            description=payload.job_text,
            skills_required=parsed.skills_required,
            skills_preferred=parsed.skills_preferred,
            responsibilities=parsed.responsibilities,
            experience_years=parsed.experience_years,
            education_required=parsed.education_required,
        )
        db.add(job)
        await db.flush()
        return (
            payload.job_text,
            parsed.skills_required,
            parsed.skills_preferred,
            float(parsed.experience_years or 0),
            bool(parsed.education_required),
            job,
        )

    raise ProcessingError(
        "Provide either job_id or job_text for matching.",
    )
