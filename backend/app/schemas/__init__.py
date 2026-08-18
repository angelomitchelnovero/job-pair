"""Pydantic schemas (request/response models)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ResumeBase(BaseModel):
    filename: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class ResumeCreate(ResumeBase):
    pass


class ResumeResponse(ResumeBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    raw_text: str
    skills: List[str] = Field(default_factory=list)
    experience: List[dict] = Field(default_factory=list)
    education: List[dict] = Field(default_factory=list)
    projects: List[dict] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    sections: dict = Field(default_factory=dict)
    created_at: datetime


class JobBase(BaseModel):
    title: str
    company: Optional[str] = None
    description: str
    skills_required: List[str] = Field(default_factory=list)
    skills_preferred: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    experience_years: Optional[int] = None
    education_required: Optional[str] = None


class JobCreate(JobBase):
    pass


class JobResponse(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class SkillScore(BaseModel):
    name: str
    matched: bool | str = False


class ExperienceAlignment(BaseModel):
    required_years: Optional[int] = None
    estimated_years: Optional[float] = None
    matched: bool = False
    notes: str = ""


class EducationAlignment(BaseModel):
    required: Optional[str] = None
    candidates: List[str] = Field(default_factory=list)
    matched: bool = False
    notes: str = ""


class FeatureContribution(BaseModel):
    feature: str
    contribution: float
    direction: str  # positive / negative


class MatchRequest(BaseModel):
    resume_id: str
    job_id: str


class MatchCreate(BaseModel):
    resume_id: Optional[str] = None
    job_id: Optional[str] = None
    resume_text: Optional[str] = None
    job_text: Optional[str] = None
    job_title: Optional[str] = None
    job_company: Optional[str] = None


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    resume_id: Optional[str] = None
    job_id: Optional[str] = None
    # Eagerly-loaded fields populated by `_match_response()` from the related
    # `Match.job` / `Match.resume` rows. Optional because `preview_match`
    # never has FKs and `id="preview"` rows won't have these populated.
    job_title: Optional[str] = None
    job_company: Optional[str] = None
    job_description: Optional[str] = None
    resume_filename: Optional[str] = None
    sklearn_score: float
    pytorch_score: float
    final_score: float
    matching_skills: List[SkillScore]
    missing_skills: List[SkillScore]
    extra_skills: List[str] = Field(default_factory=list)
    experience_alignment: ExperienceAlignment
    education_alignment: EducationAlignment
    recommendations: List[str]
    feature_breakdown: List[FeatureContribution]
    explanation: str
    created_at: datetime


class ModelPerformanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_name: str
    version: str
    metrics: dict
    training_samples: int
    notes: Optional[str] = None
    created_at: datetime


class CombinedAnalysisRequest(BaseModel):
    """Analyze a resume + JD in one shot without persisting first."""
    resume_text: str = Field(..., min_length=1)
    job_text: str = Field(..., min_length=1)
    job_title: str = "Untitled Position"
    job_company: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    sklearn_loaded: bool
    pytorch_loaded: bool
