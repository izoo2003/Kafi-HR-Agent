"""whatsapp already ahead; app_notifications for in-app KPI reminders.

Revision ID: f4a5b6c7d8e9
Revises: e3c4d6f7a8b9
Create Date: 2026-08-10 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, None] = "e3c4d6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_app_notifications_user_id"), "app_notifications", ["user_id"], unique=False
    )
    op.create_index(op.f("ix_app_notifications_kind"), "app_notifications", ["kind"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_app_notifications_kind"), table_name="app_notifications")
    op.drop_index(op.f("ix_app_notifications_user_id"), table_name="app_notifications")
    op.drop_table("app_notifications")
