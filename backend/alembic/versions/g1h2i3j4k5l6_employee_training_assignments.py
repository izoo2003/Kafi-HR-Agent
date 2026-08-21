"""employee_training_assignments

Stores courses recommended by AI and assigned to employees (Things To Learn).

Revision ID: g1h2i3j4k5l6
Revises: f0a1b2c3d4e5
Create Date: 2026-08-21 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, None] = "f0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "employee_training_assignments" in insp.get_table_names():
        return
    op.create_table(
        "employee_training_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=120), nullable=True),
        sa.Column("url_hint", sa.Text(), nullable=True),
        sa.Column("topic_prompt", sa.Text(), nullable=False),
        sa.Column("department_name", sa.String(length=200), nullable=True),
        sa.Column("role_title", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="assigned"),
        sa.Column("assigned_by", sa.Integer(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_employee_training_assignments_employee_id",
        "employee_training_assignments",
        ["employee_id"],
    )
    op.create_index(
        "ix_employee_training_assignments_status",
        "employee_training_assignments",
        ["status"],
    )


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "employee_training_assignments" not in insp.get_table_names():
        return
    op.drop_index(
        "ix_employee_training_assignments_status",
        table_name="employee_training_assignments",
    )
    op.drop_index(
        "ix_employee_training_assignments_employee_id",
        table_name="employee_training_assignments",
    )
    op.drop_table("employee_training_assignments")
