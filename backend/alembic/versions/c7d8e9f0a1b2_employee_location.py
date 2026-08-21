"""employee_location

Adds workplace location on employees (Mill / Clifton Office / KMP House).
Also merges divergent Alembic heads.

Revision ID: c7d8e9f0a1b2
Revises: b9c0d1e2f3a4, e5f6a7b8c9d0
Create Date: 2026-08-21 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, tuple[str, ...], None] = ("b9c0d1e2f3a4", "e5f6a7b8c9d0")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("employees")}
    if "location" not in cols:
        with op.batch_alter_table("employees", schema=None) as batch_op:
            batch_op.add_column(sa.Column("location", sa.String(length=64), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("employees")}
    if "location" in cols:
        with op.batch_alter_table("employees", schema=None) as batch_op:
            batch_op.drop_column("location")
