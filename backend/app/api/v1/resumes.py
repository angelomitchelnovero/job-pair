"""Resume-related API endpoints."""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidFileTypeError, NotFoundError, FileTooLargeError
from app.core.config import settings
from app.db.session import get_db
from app.models import Resume
from app.schemas import ResumeResponse
from app.services.resume_parser import ResumeParser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post(
    "",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF resume or submit raw text",
)
async def upload_resume(
    file: UploadFile = File(..., description="PDF resume file"),
    db: AsyncSession = Depends(get_db),
) -> ResumeResponse:
    if not file.filename or not file.filename.lower().endswith(tuple(settings.allowed_extensions)):
        raise InvalidFileTypeError(
            f"Only {', '.join(settings.allowed_extensions)} files are supported.",
            details={"filename": file.filename},
        )

    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_bytes:
        raise FileTooLargeError(
            f"File exceeds maximum size of {settings.max_upload_size_mb} MB.",
            details={"size_bytes": len(file_bytes)},
        )

    parser = ResumeParser()
    parsed = parser.parse_pdf(file_bytes)

    resume = Resume(
        filename=file.filename,
        full_name=parsed.full_name,
        email=parsed.email,
        raw_text=parsed.raw_text,
        sections=parsed.sections,
        skills=parsed.skills,
        experience=parsed.experience,
        education=parsed.education,
        projects=parsed.projects,
        certifications=parsed.certifications,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    logger.info("Resume uploaded: id=%s filename=%s skills=%d", resume.id, resume.filename, len(resume.skills))
    return ResumeResponse.model_validate(resume)


@router.get("", response_model=List[ResumeResponse], summary="List uploaded resumes")
async def list_resumes(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[ResumeResponse]:
    stmt = (
        select(Resume)
        .order_by(Resume.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [ResumeResponse.model_validate(r) for r in rows]


@router.get("/{resume_id}", response_model=ResumeResponse, summary="Retrieve a resume by id")
async def get_resume(resume_id: str, db: AsyncSession = Depends(get_db)) -> ResumeResponse:
    resume = await db.get(Resume, resume_id)
    if not resume:
        raise NotFoundError(f"Resume {resume_id} not found.")
    return ResumeResponse.model_validate(resume)


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,  # plain Response has no body — required for 204
    summary="Delete a resume",
)
async def delete_resume(resume_id: str, db: AsyncSession = Depends(get_db)):
    resume = await db.get(Resume, resume_id)
    if not resume:
        raise NotFoundError(f"Resume {resume_id} not found.")
    await db.delete(resume)
    await db.commit()
