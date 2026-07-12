from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MaterialFolder(Base):
    __tablename__ = "material_folders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_material_folders_user_id", "user_id"),
        Index("ix_material_folders_course_id", "course_id"),
        Index("ix_material_folders_course_name", "course_id", "name"),
        Index("ix_material_folders_course_sort", "course_id", "sort_order"),
        Index("ix_material_folders_deleted_at", "deleted_at"),
    )


class CourseMaterial(Base):
    __tablename__ = "course_materials"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    folder_id: Mapped[str | None] = mapped_column(ForeignKey("material_folders.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    material_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(2048))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    file_size: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(255))
    parse_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="uploaded",
        server_default="uploaded",
    )
    parse_error: Mapped[str | None] = mapped_column(Text)
    parse_quality: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="unknown",
        server_default="unknown",
    )
    parse_diagnostics_json: Mapped[dict | list | None] = mapped_column(JSON)
    page_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "material_type in ('pdf', 'ppt', 'word', 'markdown', 'image', 'text', 'link')",
            name="course_material_material_type",
        ),
        CheckConstraint("source_type in ('file', 'url')", name="course_material_source_type"),
        CheckConstraint(
            "parse_status in ('uploaded', 'parsing', 'parsed', 'parse_failed', 'deleted')",
            name="course_material_parse_status",
        ),
        CheckConstraint(
            "parse_quality in ('unknown', 'complete', 'partial')",
            name="course_material_parse_quality",
        ),
        CheckConstraint("source_type != 'file' or file_url is not null", name="course_material_file_url_required"),
        CheckConstraint("source_type != 'url' or source_url is not null", name="course_material_source_url_required"),
        Index("ix_course_materials_course_id", "course_id"),
        Index("ix_course_materials_user_id", "user_id"),
        Index("ix_course_materials_folder_id", "folder_id"),
        Index("ix_course_materials_course_name", "course_id", "name"),
        Index("ix_course_materials_material_type", "material_type"),
        Index("ix_course_materials_source_type", "source_type"),
        Index("ix_course_materials_course_parse_status", "course_id", "parse_status"),
        Index("ix_course_materials_created_at", "created_at"),
        Index("ix_course_materials_deleted_at", "deleted_at"),
    )


class MaterialChunk(Base):
    __tablename__ = "material_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    material_id: Mapped[str] = mapped_column(ForeignKey("course_materials.id"), nullable=False)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page: Mapped[str | None] = mapped_column(String(64))
    page_index: Mapped[int | None] = mapped_column(Integer)
    heading: Mapped[str | None] = mapped_column(String(500))
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("material_id", "chunk_index", name="uq_material_chunks_material_chunk_index"),
        Index("ix_material_chunks_material_id", "material_id"),
        Index("ix_material_chunks_course_id", "course_id"),
        Index("ix_material_chunks_page", "page"),
        Index("ix_material_chunks_page_index", "page_index"),
        Index("ix_material_chunks_embedding_id", "embedding_id"),
        Index("ix_material_chunks_course_material_chunk", "course_id", "material_id", "chunk_index"),
    )
