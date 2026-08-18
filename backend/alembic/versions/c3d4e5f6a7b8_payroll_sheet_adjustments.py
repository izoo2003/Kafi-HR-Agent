"""payroll_sheet_adjustments for monthly salary-sheet extras.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-18 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payroll_sheet_adjustments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("allowance_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("loan_deduction_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("advance_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("payment_mode", sa.String(length=32), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "employee_id",
            "period_month",
            "period_year",
            name="uq_payroll_sheet_employee_period",
        ),
    )
    op.create_index(
        "ix_payroll_sheet_adjustments_employee_id",
        "payroll_sheet_adjustments",
        ["employee_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_payroll_sheet_adjustments_employee_id", table_name="payroll_sheet_adjustments")
    op.drop_table("payroll_sheet_adjustments")
