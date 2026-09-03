"""Add excluded flag on payroll sheet adjustments for removed rows.

Revision ID: l6m7n8o9p0q1
Revises: k5l6m7n8o9p0
Create Date: 2026-09-03 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "l6m7n8o9p0q1"
down_revision: Union[str, None] = "k5l6m7n8o9p0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("payroll_sheet_adjustments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("excluded", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("payroll_sheet_adjustments", schema=None) as batch_op:
        batch_op.drop_column("excluded")
