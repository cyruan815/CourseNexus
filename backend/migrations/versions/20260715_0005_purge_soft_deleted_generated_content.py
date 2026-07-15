"""purge soft-deleted generated content

Revision ID: 20260715_0005
Revises: 20260713_0004
Create Date: 2026-07-15
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260715_0005"
down_revision: str | None = "20260713_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM source_citations "
            "WHERE generated_content_id IN "
            "(SELECT id FROM ai_generated_contents WHERE deleted_at IS NOT NULL)"
        )
    )
    op.execute(
        sa.text("DELETE FROM ai_generated_contents WHERE deleted_at IS NOT NULL")
    )


def downgrade() -> None:
    # Permanently deleted user content cannot be reconstructed.
    pass
