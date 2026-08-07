"""employee_job_description_text

Adds job_description_text on employees — internal duties/requirements for
active staff (distinct from hiring job_descriptions / Job Postings).

Revision ID: d2b3c5e8a1f4
Revises: c1a2f4e9b7d3
Create Date: 2026-08-07 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d2b3c5e8a1f4"
down_revision: Union[str, None] = "c1a2f4e9b7d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.add_column(sa.Column("job_description_text", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.drop_column("job_description_text")
