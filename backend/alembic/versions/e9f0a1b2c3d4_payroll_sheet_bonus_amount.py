"""payroll_sheet_bonus_amount

Adds bonus_amount on payroll_sheet_adjustments.

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-08-21 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e9f0a1b2c3d4"
down_revision: Union[str, None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("payroll_sheet_adjustments")}
    if "bonus_amount" in cols:
        return
    with op.batch_alter_table("payroll_sheet_adjustments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "bonus_amount",
                sa.Numeric(12, 2),
                nullable=False,
                server_default="0",
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("payroll_sheet_adjustments")}
    if "bonus_amount" not in cols:
        return
    with op.batch_alter_table("payroll_sheet_adjustments", schema=None) as batch_op:
        batch_op.drop_column("bonus_amount")
