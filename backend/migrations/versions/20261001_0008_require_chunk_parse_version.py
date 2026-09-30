"""require every material chunk to belong to a parse version

Revision ID: 20261001_0008
Revises: 20261001_0007
Create Date: 2026-10-01
"""
from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa

revision: str = "20261001_0008"
down_revision: str | None = "20261001_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _recovery_version_id(material_id: str) -> str:
    value = uuid5(NAMESPACE_URL, f"course-nexus:unversioned-material-chunks:{material_id}")
    return f"mpv_{value.hex}"


def upgrade() -> None:
    _backfill_unversioned_chunks()
    with op.batch_alter_table("material_chunks") as batch_op:
        batch_op.alter_column(
            "parse_version_id",
            existing_type=sa.String(length=64),
            nullable=False,
        )


def _backfill_unversioned_chunks() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    materials = bind.execute(
        sa.text(
            "SELECT DISTINCT course_materials.id, course_materials.course_id, course_materials.user_id "
            "FROM course_materials JOIN material_chunks "
            "ON material_chunks.material_id = course_materials.id "
            "WHERE material_chunks.parse_version_id IS NULL"
        )
    ).mappings()

    for material in materials:
        material_id = str(material["id"])
        version_id = _recovery_version_id(material_id)
        if bind.execute(
            sa.text("SELECT COUNT(*) FROM material_parse_versions WHERE id = :version_id"),
            {"version_id": version_id},
        ).scalar_one() == 0:
            bind.execute(
                sa.text(
                    "INSERT INTO material_parse_versions "
                    "(id, material_id, course_id, user_id, status, parse_error, parse_quality, "
                    "created_at, updated_at, finished_at) "
                    "VALUES (:id, :material_id, :course_id, :user_id, 'retired', "
                    "'MIGRATION_UNVERSIONED_CHUNKS', 'unknown', :now, :now, :now)"
                ),
                {
                    "id": version_id,
                    "material_id": material_id,
                    "course_id": material["course_id"],
                    "user_id": material["user_id"],
                    "now": now,
                },
            )
        bind.execute(
            sa.text(
                "UPDATE material_chunks SET parse_version_id = :version_id "
                "WHERE material_id = :material_id AND parse_version_id IS NULL"
            ),
            {"version_id": version_id, "material_id": material_id},
        )

    remaining = bind.execute(
        sa.text("SELECT COUNT(*) FROM material_chunks WHERE parse_version_id IS NULL")
    ).scalar_one()
    if remaining:
        raise RuntimeError(f"cannot require parse versions: {remaining} chunks remain unversioned")


def downgrade() -> None:
    with op.batch_alter_table("material_chunks") as batch_op:
        batch_op.alter_column(
            "parse_version_id",
            existing_type=sa.String(length=64),
            nullable=True,
        )
