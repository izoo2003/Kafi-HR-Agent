"""candidate_cv_intake_fields

Adds automated CV intake fields to candidates (FEATURE_CV_SCREENING.md §11):
source/source_ref/match_confidence/match_reasoning/submitted_at, and makes
job_description_id nullable so a fetched CV can sit in the "unassigned" pool
before it is matched or manually routed to a job.

Revision ID: c1a2f4e9b7d3
Revises: 7bfd2768b4d2
Create Date: 2026-08-06 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c1a2f4e9b7d3'
down_revision: Union[str, None] = '7bfd2768b4d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('candidates', schema=None) as batch_op:
        batch_op.alter_column('job_description_id', existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column('source', sa.String(), nullable=False, server_default='manual'))
        batch_op.add_column(sa.Column('source_ref', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('match_confidence', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('match_reasoning', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index(batch_op.f('ix_candidates_source_ref'), ['source_ref'], unique=False)

    # Drop the server_default after backfilling existing rows — new rows set it explicitly at the ORM layer.
    with op.batch_alter_table('candidates', schema=None) as batch_op:
        batch_op.alter_column('source', server_default=None)


def downgrade() -> None:
    with op.batch_alter_table('candidates', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_candidates_source_ref'))
        batch_op.drop_column('submitted_at')
        batch_op.drop_column('match_reasoning')
        batch_op.drop_column('match_confidence')
        batch_op.drop_column('source_ref')
        batch_op.drop_column('source')
        batch_op.alter_column('job_description_id', existing_type=sa.Integer(), nullable=False)
