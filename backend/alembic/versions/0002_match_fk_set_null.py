"""Set Match FKs to nullable + ON DELETE SET NULL.

Lets deleting a resume or job leave the match history intact — the FKs
become NULL and the match's stored scores/explanations persist. The
frontend renders fallbacks ("Resume deleted", "Untitled role") when
the FK is null.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing CASCADE FKs, alter columns to nullable, recreate
    # the FKs with SET NULL. `batch_alter_table` is required on Postgres
    # for ALTER COLUMN with constraint rewrites — and groups everything
    # in one transaction so we don't briefly leave a nullable column
    # without a backing FK.
    with op.batch_alter_table("matches") as batch_op:
        batch_op.drop_constraint("matches_resume_id_fkey", type_="foreignkey")
        batch_op.drop_constraint("matches_job_id_fkey", type_="foreignkey")
        batch_op.alter_column(
            "resume_id", existing_type=sa.String(length=36), nullable=True
        )
        batch_op.alter_column(
            "job_id", existing_type=sa.String(length=36), nullable=True
        )
        batch_op.create_foreign_key(
            "matches_resume_id_fkey",
            "resumes",
            ["resume_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "matches_job_id_fkey",
            "jobs",
            ["job_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    # If there are existing rows with NULL FKs (because the user deleted
    # a resume/job under the new schema), re-marking the columns
    # nullable=False will fail. The caller is expected to clean up those
    # NULL FKs first — there's no good automated way to invent a missing
    # parent row.
    with op.batch_alter_table("matches") as batch_op:
        batch_op.drop_constraint("matches_resume_id_fkey", type_="foreignkey")
        batch_op.drop_constraint("matches_job_id_fkey", type_="foreignkey")
        batch_op.alter_column(
            "resume_id", existing_type=sa.String(length=36), nullable=False
        )
        batch_op.alter_column(
            "job_id", existing_type=sa.String(length=36), nullable=False
        )
        batch_op.create_foreign_key(
            "matches_resume_id_fkey",
            "resumes",
            ["resume_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "matches_job_id_fkey",
            "jobs",
            ["job_id"],
            ["id"],
            ondelete="CASCADE",
        )