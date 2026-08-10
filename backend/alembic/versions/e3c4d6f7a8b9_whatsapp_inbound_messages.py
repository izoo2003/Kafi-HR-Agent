"""whatsapp_inbound_messages

Queue for Meta WhatsApp Cloud API document messages pending Sync CVs.

Revision ID: e3c4d6f7a8b9
Revises: d2b3c5e8a1f4
Create Date: 2026-08-07 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e3c4d6f7a8b9"
down_revision: Union[str, None] = "d2b3c5e8a1f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_inbound_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("wa_message_id", sa.String(), nullable=False),
        sa.Column("from_phone", sa.String(), nullable=True),
        sa.Column("media_id", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=True),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("skip_reason", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("wa_message_id"),
    )
    op.create_index(
        op.f("ix_whatsapp_inbound_messages_wa_message_id"),
        "whatsapp_inbound_messages",
        ["wa_message_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_whatsapp_inbound_messages_status"),
        "whatsapp_inbound_messages",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_whatsapp_inbound_messages_status"), table_name="whatsapp_inbound_messages")
    op.drop_index(op.f("ix_whatsapp_inbound_messages_wa_message_id"), table_name="whatsapp_inbound_messages")
    op.drop_table("whatsapp_inbound_messages")
