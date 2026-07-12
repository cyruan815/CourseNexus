"""allow citations to survive permanent material deletion

Revision ID: 20260713_0003
Revises: 20260712_0002
Create Date: 2026-07-13
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260713_0003"
down_revision: str | None = "20260712_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("source_citations") as batch_op:
        batch_op.alter_column(
            "material_id",
            existing_type=sa.String(length=64),
            nullable=True,
        )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM source_citations WHERE material_id IS NULL"))
    with op.batch_alter_table("source_citations") as batch_op:
        batch_op.alter_column(
            "material_id",
            existing_type=sa.String(length=64),
            nullable=False,
        )
