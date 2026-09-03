"""Add leave_used override on payroll sheet adjustments.

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-09-03 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "k5l6m7n8o9p0"
down_revision: Union[str, None] = "j4k5l6m7n8o9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("payroll_sheet_adjustments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("leave_used", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("payroll_sheet_adjustments", schema=None) as batch_op:
        batch_op.drop_column("leave_used")
