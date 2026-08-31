"""employee_resignation employee-initiated letters

Adds direction (hr | employee), rejection fields, and reviewed_by.

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-08-31 13:45:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "j4k5l6m7n8o9"
down_revision: Union[str, None] = "i3j4k5l6m7n8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "employee_resignation_notices" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("employee_resignation_notices")}
    if "direction" not in cols:
        op.add_column(
            "employee_resignation_notices",
            sa.Column("direction", sa.String(length=32), nullable=False, server_default="hr"),
        )
    if "rejected_at" not in cols:
        op.add_column(
            "employee_resignation_notices",
            sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "rejection_reason" not in cols:
        op.add_column(
            "employee_resignation_notices",
            sa.Column("rejection_reason", sa.Text(), nullable=True),
        )
    if "reviewed_by" not in cols:
        op.add_column(
            "employee_resignation_notices",
            sa.Column("reviewed_by", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_employee_resignation_notices_reviewed_by",
            "employee_resignation_notices",
            "users",
            ["reviewed_by"],
            ["id"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "employee_resignation_notices" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("employee_resignation_notices")}
    if "reviewed_by" in cols:
        try:
            op.drop_constraint(
                "fk_employee_resignation_notices_reviewed_by",
                "employee_resignation_notices",
                type_="foreignkey",
            )
        except Exception:
            pass
        op.drop_column("employee_resignation_notices", "reviewed_by")
    if "rejection_reason" in cols:
        op.drop_column("employee_resignation_notices", "rejection_reason")
    if "rejected_at" in cols:
        op.drop_column("employee_resignation_notices", "rejected_at")
    if "direction" in cols:
        op.drop_column("employee_resignation_notices", "direction")
