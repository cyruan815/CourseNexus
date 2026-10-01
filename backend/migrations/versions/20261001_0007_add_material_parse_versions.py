"""add material parse versions

Revision ID: 20261001_0007
Revises: 20260930_0006
Create Date: 2026-10-01
"""
from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa

revision: str = "20261001_0007"
down_revision: str | None = "20260930_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _legacy_version_id(material_id: str) -> str:
    return f"mpv_{uuid5(NAMESPACE_URL, f'course-nexus:material-parse:{material_id}').hex}"


def upgrade() -> None:
    op.create_table(
        "material_parse_versions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("material_id", sa.String(length=64), nullable=False),
        sa.Column("course_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("parse_quality", sa.String(length=32), server_default="unknown", nullable=False),
        sa.Column("parse_diagnostics_json", sa.JSON(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('building', 'active', 'failed', 'retired')",
            name="ck_material_parse_versions_material_parse_version_status",
        ),
        sa.CheckConstraint(
            "parse_quality in ('unknown', 'complete', 'partial')",
            name="ck_material_parse_versions_material_parse_version_parse_quality",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_material_parse_versions_course_id_courses",
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["course_materials.id"],
            name="fk_material_parse_versions_material_id_course_materials",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_material_parse_versions_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_material_parse_versions"),
    )
    op.create_index(
        "ix_material_parse_versions_material_id",
        "material_parse_versions",
        ["material_id"],
    )
    op.create_index("ix_material_parse_versions_course_id", "material_parse_versions", ["course_id"])
    op.create_index("ix_material_parse_versions_user_id", "material_parse_versions", ["user_id"])
    op.create_index("ix_material_parse_versions_status", "material_parse_versions", ["status"])
    op.create_index("ix_material_parse_versions_created_at", "material_parse_versions", ["created_at"])
    op.create_index(
        "uq_material_parse_versions_one_building",
        "material_parse_versions",
        ["material_id"],
        unique=True,
        sqlite_where=sa.text("status = 'building'"),
    )

    with op.batch_alter_table("course_materials") as batch_op:
        batch_op.add_column(sa.Column("active_parse_version_id", sa.String(length=64), nullable=True))
        batch_op.create_foreign_key(
            "fk_course_materials_active_parse_version_id_material_parse_versions",
            "material_parse_versions",
            ["active_parse_version_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_course_materials_active_parse_version_id",
            ["active_parse_version_id"],
            unique=False,
        )

    with op.batch_alter_table("material_chunks") as batch_op:
        batch_op.add_column(sa.Column("parse_version_id", sa.String(length=64), nullable=True))

    with op.batch_alter_table("source_citations") as batch_op:
        batch_op.add_column(sa.Column("material_version_id", sa.String(length=64), nullable=True))

    _backfill_legacy_versions()

    with op.batch_alter_table("material_chunks") as batch_op:
        batch_op.drop_constraint("uq_material_chunks_material_chunk_index", type_="unique")
        batch_op.create_foreign_key(
            "fk_material_chunks_parse_version_id_material_parse_versions",
            "material_parse_versions",
            ["parse_version_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint(
            "uq_material_chunks_version_chunk_index",
            ["parse_version_id", "chunk_index"],
        )
        batch_op.create_index("ix_material_chunks_parse_version_id", ["parse_version_id"], unique=False)

    with op.batch_alter_table("source_citations") as batch_op:
        batch_op.create_foreign_key(
            "fk_source_citations_material_version_id_material_parse_versions",
            "material_parse_versions",
            ["material_version_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_source_citations_material_version_id",
            ["material_version_id"],
            unique=False,
        )


def _backfill_legacy_versions() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    materials = bind.execute(
        sa.text(
            "SELECT id, course_id, user_id, parse_status, parse_error, parse_quality, "
            "parse_diagnostics_json, page_count, created_at, updated_at "
            "FROM course_materials WHERE parse_status != 'deleted'"
        )
    ).mappings()

    for material in materials:
        material_id = str(material["id"])
        chunk_count = int(
            bind.execute(
                sa.text("SELECT COUNT(*) FROM material_chunks WHERE material_id = :material_id"),
                {"material_id": material_id},
            ).scalar_one()
        )
        parse_status = str(material["parse_status"])
        if parse_status == "uploaded" and chunk_count == 0:
            continue

        version_status = "retired" if chunk_count else "failed"
        parse_error = material["parse_error"]
        if parse_status == "parsed" and chunk_count:
            version_status = "active"
        elif parse_status == "parsed":
            parse_error = "MIGRATION_EMPTY_PARSE"
        elif parse_status == "parsing":
            parse_error = parse_error or "MIGRATION_INTERRUPTED_PARSE"

        version_id = _legacy_version_id(material_id)
        activated_at = (material["updated_at"] or now) if version_status == "active" else None
        bind.execute(
            sa.text(
                "INSERT INTO material_parse_versions "
                "(id, material_id, course_id, user_id, status, parse_error, parse_quality, "
                "parse_diagnostics_json, page_count, created_at, updated_at, activated_at, finished_at) "
                "VALUES (:id, :material_id, :course_id, :user_id, :status, :parse_error, :parse_quality, "
                ":parse_diagnostics_json, :page_count, :created_at, :updated_at, :activated_at, :finished_at)"
            ),
            {
                "id": version_id,
                "material_id": material_id,
                "course_id": material["course_id"],
                "user_id": material["user_id"],
                "status": version_status,
                "parse_error": parse_error,
                "parse_quality": material["parse_quality"] if version_status == "active" else "unknown",
                "parse_diagnostics_json": (
                    material["parse_diagnostics_json"] if version_status == "active" else None
                ),
                "page_count": material["page_count"] if version_status == "active" else None,
                "created_at": material["created_at"] or now,
                "updated_at": material["updated_at"] or now,
                "activated_at": activated_at,
                "finished_at": material["updated_at"] or now,
            },
        )
        if chunk_count:
            bind.execute(
                sa.text(
                    "UPDATE material_chunks SET parse_version_id = :version_id "
                    "WHERE material_id = :material_id"
                ),
                {"version_id": version_id, "material_id": material_id},
            )
        if version_status == "active":
            bind.execute(
                sa.text(
                    "UPDATE course_materials SET active_parse_version_id = :version_id "
                    "WHERE id = :material_id"
                ),
                {"version_id": version_id, "material_id": material_id},
            )
        elif parse_status in {"parsed", "parsing"}:
            bind.execute(
                sa.text(
                    "UPDATE course_materials SET parse_status = 'parse_failed', parse_error = :parse_error, "
                    "parse_quality = 'unknown', parse_diagnostics_json = NULL, page_count = NULL "
                    "WHERE id = :material_id"
                ),
                {"parse_error": parse_error, "material_id": material_id},
            )

    bind.execute(
        sa.text(
            "UPDATE source_citations SET material_version_id = "
            "(SELECT material_chunks.parse_version_id FROM material_chunks "
            "WHERE material_chunks.id = source_citations.chunk_id) "
            "WHERE chunk_id IS NOT NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE source_citations SET material_version_id = "
            "(SELECT course_materials.active_parse_version_id FROM course_materials "
            "WHERE course_materials.id = source_citations.material_id) "
            "WHERE material_version_id IS NULL AND material_id IS NOT NULL"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE source_citations SET chunk_id = NULL WHERE chunk_id IN ("
            "SELECT material_chunks.id FROM material_chunks "
            "JOIN course_materials ON course_materials.id = material_chunks.material_id "
            "WHERE material_chunks.parse_version_id != course_materials.active_parse_version_id "
            "OR course_materials.active_parse_version_id IS NULL)"
        )
    )
    bind.execute(
        sa.text(
            "DELETE FROM material_chunks WHERE id IN ("
            "SELECT material_chunks.id FROM material_chunks "
            "JOIN course_materials ON course_materials.id = material_chunks.material_id "
            "WHERE material_chunks.parse_version_id != course_materials.active_parse_version_id "
            "OR course_materials.active_parse_version_id IS NULL)"
        )
    )

    with op.batch_alter_table("source_citations") as batch_op:
        batch_op.drop_index("ix_source_citations_material_version_id")
        batch_op.drop_constraint(
            "fk_source_citations_material_version_id_material_parse_versions",
            type_="foreignkey",
        )
        batch_op.drop_column("material_version_id")

    with op.batch_alter_table("material_chunks") as batch_op:
        batch_op.drop_index("ix_material_chunks_parse_version_id")
        batch_op.drop_constraint("uq_material_chunks_version_chunk_index", type_="unique")
        batch_op.drop_constraint(
            "fk_material_chunks_parse_version_id_material_parse_versions",
            type_="foreignkey",
        )
        batch_op.drop_column("parse_version_id")
        batch_op.create_unique_constraint(
            "uq_material_chunks_material_chunk_index",
            ["material_id", "chunk_index"],
        )

    with op.batch_alter_table("course_materials") as batch_op:
        batch_op.drop_index("ix_course_materials_active_parse_version_id")
        batch_op.drop_constraint(
            "fk_course_materials_active_parse_version_id_material_parse_versions",
            type_="foreignkey",
        )
        batch_op.drop_column("active_parse_version_id")

    op.drop_index("uq_material_parse_versions_one_building", table_name="material_parse_versions")
    op.drop_index("ix_material_parse_versions_created_at", table_name="material_parse_versions")
    op.drop_index("ix_material_parse_versions_status", table_name="material_parse_versions")
    op.drop_index("ix_material_parse_versions_user_id", table_name="material_parse_versions")
    op.drop_index("ix_material_parse_versions_course_id", table_name="material_parse_versions")
    op.drop_index("ix_material_parse_versions_material_id", table_name="material_parse_versions")
    op.drop_table("material_parse_versions")
