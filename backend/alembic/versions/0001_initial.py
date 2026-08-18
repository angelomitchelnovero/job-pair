"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("sections", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("skills", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("experience", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("education", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("projects", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("certifications", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("skills_required", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("skills_preferred", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("responsibilities", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("experience_years", sa.Integer, nullable=True),
        sa.Column("education_required", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "matches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("resume_id", sa.String(length=36), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sklearn_score", sa.Float, nullable=False),
        sa.Column("pytorch_score", sa.Float, nullable=False),
        sa.Column("final_score", sa.Float, nullable=False),
        sa.Column("matching_skills", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("missing_skills", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("extra_skills", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("experience_alignment", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("education_alignment", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("recommendations", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("feature_breakdown", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("explanation", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_matches_resume_id", "matches", ["resume_id"])
    op.create_index("ix_matches_job_id", "matches", ["job_id"])

    op.create_table(
        "model_performance",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("metrics", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("training_samples", sa.Integer, nullable=False, server_default="0"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("model_performance")
    op.drop_index("ix_matches_job_id", table_name="matches")
    op.drop_index("ix_matches_resume_id", table_name="matches")
    op.drop_table("matches")
    op.drop_table("jobs")
    op.drop_table("resumes")
