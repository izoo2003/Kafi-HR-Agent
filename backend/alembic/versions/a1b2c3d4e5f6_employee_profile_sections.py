"""employee_profile_sections

Expands employees with personal/bank fields and adds document + reference tables.

Revision ID: a1b2c3d4e5f6
Revises: f4a5b6c7d8e9
Create Date: 2026-08-13 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cnic", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("email", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("personal_mobile", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("alternate_mobile", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("father_name", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("date_of_birth", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("gender", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("marital_status", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("current_address", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("permanent_address", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("city", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("nationality", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("bank_name", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("account_title", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("account_number", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("iban", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("branch_name", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("branch_code", sa.String(length=64), nullable=True))

    op.create_table(
        "employee_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
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
    )
    op.create_index("ix_employee_documents_employee_id", "employee_documents", ["employee_id"])

    op.create_table(
        "employee_references",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("relation", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("cnic", sa.String(length=32), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
    )
    op.create_index("ix_employee_references_employee_id", "employee_references", ["employee_id"])

    op.create_table(
        "employee_reference_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reference_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
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
        sa.ForeignKeyConstraint(["reference_id"], ["employee_references.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_employee_reference_documents_reference_id",
        "employee_reference_documents",
        ["reference_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_employee_reference_documents_reference_id", table_name="employee_reference_documents")
    op.drop_table("employee_reference_documents")
    op.drop_index("ix_employee_references_employee_id", table_name="employee_references")
    op.drop_table("employee_references")
    op.drop_index("ix_employee_documents_employee_id", table_name="employee_documents")
    op.drop_table("employee_documents")

    with op.batch_alter_table("employees", schema=None) as batch_op:
        for col in (
            "cnic",
            "email",
            "personal_mobile",
            "alternate_mobile",
            "father_name",
            "date_of_birth",
            "gender",
            "marital_status",
            "current_address",
            "permanent_address",
            "city",
            "nationality",
            "bank_name",
            "account_title",
            "account_number",
            "iban",
            "branch_name",
            "branch_code",
        ):
            batch_op.drop_column(col)
