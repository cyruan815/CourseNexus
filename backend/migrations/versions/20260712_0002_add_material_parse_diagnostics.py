"""add material parse diagnostics

Revision ID: 20260712_0002
Revises: 20260709_0001
Create Date: 2026-07-12
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260712_0002"
down_revision: str | None = "20260709_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("course_materials") as batch_op:
        batch_op.add_column(
            sa.Column(
                "parse_quality",
                sa.String(length=32),
                nullable=False,
                server_default="unknown",
            )
        )
        batch_op.add_column(sa.Column("parse_diagnostics_json", sa.JSON(), nullable=True))
        batch_op.create_check_constraint(
            "course_material_parse_quality",
            "parse_quality in ('unknown', 'complete', 'partial')",
        )


def downgrade() -> None:
    with op.batch_alter_table("course_materials") as batch_op:
        batch_op.drop_constraint("course_material_parse_quality", type_="check")
        batch_op.drop_column("parse_diagnostics_json")
        batch_op.drop_column("parse_quality")
