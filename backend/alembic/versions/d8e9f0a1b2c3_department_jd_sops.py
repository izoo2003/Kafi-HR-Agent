"""department_jd_sops

Adds job_description_text and sops_text on departments.

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-08-21 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("departments")}
    missing_jd = "job_description_text" not in cols
    missing_sops = "sops_text" not in cols
    if not missing_jd and not missing_sops:
        return
    with op.batch_alter_table("departments", schema=None) as batch_op:
        if missing_jd:
            batch_op.add_column(sa.Column("job_description_text", sa.Text(), nullable=True))
        if missing_sops:
            batch_op.add_column(sa.Column("sops_text", sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("departments")}
    drop_sops = "sops_text" in cols
    drop_jd = "job_description_text" in cols
    if not drop_sops and not drop_jd:
        return
    with op.batch_alter_table("departments", schema=None) as batch_op:
        if drop_sops:
            batch_op.drop_column("sops_text")
        if drop_jd:
            batch_op.drop_column("job_description_text")
