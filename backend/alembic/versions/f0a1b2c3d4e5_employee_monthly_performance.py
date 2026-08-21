"""employee_monthly_performance

Stores finalized monthly performance scores (/10) and AI summaries per employee.

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-08-21 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, None] = "e9f0a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "employee_monthly_performance" in insp.get_table_names():
        return
    op.create_table(
        "employee_monthly_performance",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("score_out_of_10", sa.Numeric(4, 2), nullable=False),
        sa.Column("overall_pct", sa.Float(), nullable=True),
        sa.Column("entries_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
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
            "period_year",
            "period_month",
            name="uq_employee_monthly_performance",
        ),
    )
    op.create_index(
        "ix_employee_monthly_performance_employee_id",
        "employee_monthly_performance",
        ["employee_id"],
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "employee_monthly_performance" not in insp.get_table_names():
        return
    op.drop_index(
        "ix_employee_monthly_performance_employee_id",
        table_name="employee_monthly_performance",
    )
    op.drop_table("employee_monthly_performance")
