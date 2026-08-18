"""payroll sheet attendance overrides for live-editable salary calculation.

Revision ID: e5f6a7b8c9d0
Revises: c3d4e5f6a7b8
Create Date: 2026-08-18 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("payroll_sheet_adjustments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("days_present", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("days_absent", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("days_late", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("days_half_day", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("overtime_bonus_days", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("monthly_tax_override", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("payroll_sheet_adjustments", schema=None) as batch_op:
        batch_op.drop_column("monthly_tax_override")
        batch_op.drop_column("overtime_bonus_days")
        batch_op.drop_column("days_half_day")
        batch_op.drop_column("days_late")
        batch_op.drop_column("days_absent")
        batch_op.drop_column("days_present")
