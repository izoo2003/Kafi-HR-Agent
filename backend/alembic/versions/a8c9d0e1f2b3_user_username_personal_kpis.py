"""Add users.username and personal KPI owner.

Revision ID: a8c9d0e1f2b3
Revises: f4a5b6c7d8e9
Create Date: 2026-08-18 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a8c9d0e1f2b3"
down_revision: Union[str, None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("username", sa.String(), nullable=True))
        batch_op.create_index("ix_users_username", ["username"], unique=True)

    with op.batch_alter_table("kpi_definitions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("owner_employee_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            "ix_kpi_definitions_owner_employee_id", ["owner_employee_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_kpi_definitions_owner_employee",
            "employees",
            ["owner_employee_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("kpi_definitions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_kpi_definitions_owner_employee", type_="foreignkey")
        batch_op.drop_index("ix_kpi_definitions_owner_employee_id")
        batch_op.drop_column("owner_employee_id")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index("ix_users_username")
        batch_op.drop_column("username")
