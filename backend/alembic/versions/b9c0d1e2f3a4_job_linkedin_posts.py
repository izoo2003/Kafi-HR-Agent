"""Add job_descriptions.linkedin_posts for Open-status LinkedIn feed publishing.

Revision ID: b9c0d1e2f3a4
Revises: a8c9d0e1f2b3
Create Date: 2026-08-18 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b9c0d1e2f3a4"
down_revision: Union[str, None] = "a8c9d0e1f2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("job_descriptions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("linkedin_posts", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("job_descriptions", schema=None) as batch_op:
        batch_op.drop_column("linkedin_posts")
