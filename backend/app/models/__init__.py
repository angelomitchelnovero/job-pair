"""ORM models for resumes, jobs, and match results."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    """Adds created_at / updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Resume(Base, TimestampMixin):
    """Resume metadata + extracted content."""

    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    sections: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    experience: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    education: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    projects: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    certifications: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    matches: Mapped[list["Match"]] = relationship(
        "Match", back_populates="resume"
    )


class Job(Base, TimestampMixin):
    """Job description + parsed content."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    skills_required: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    skills_preferred: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    responsibilities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    experience_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    education_required: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    matches: Mapped[list["Match"]] = relationship(
        "Match", back_populates="job"
    )


class Match(Base, TimestampMixin):
    """A match analysis between a resume and a job."""

    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # FKs are nullable so deleting a Resume or Job leaves match history
    # intact — the FK becomes NULL and the match's stored scores persist.
    # The DB-level ON DELETE SET NULL handles the FK column; the ORM
    # matches relationships on Resume/Job no longer carry
    # cascade="all, delete-orphan" for the same reason.
    resume_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True
    )
    job_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )

    # Score components
    sklearn_score: Mapped[float] = mapped_column(Float, nullable=False)
    pytorch_score: Mapped[float] = mapped_column(Float, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Detailed analysis
    matching_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    missing_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    extra_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    experience_alignment: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    education_alignment: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    recommendations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    feature_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Relations
    resume: Mapped[Resume] = relationship("Resume", back_populates="matches")
    job: Mapped[Job] = relationship("Job", back_populates="matches")


class ModelPerformance(Base, TimestampMixin):
    """Stores model evaluation snapshots."""

    __tablename__ = "model_performance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    training_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
