from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    source_page: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("status in ('active', 'deleted')", name="conversation_status"),
        Index("ix_conversations_user_id", "user_id"),
        Index("ix_conversations_course_id", "course_id"),
        Index("ix_conversations_source_page", "source_page"),
        Index("ix_conversations_status", "status"),
        Index("ix_conversations_created_at", "created_at"),
        Index("ix_conversations_deleted_at", "deleted_at"),
        Index("ix_conversations_course_status_updated", "course_id", "status", "updated_at"),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    answer_type: Mapped[str | None] = mapped_column(String(32))
    generation_status: Mapped[str | None] = mapped_column(String(32))
    error_code: Mapped[str | None] = mapped_column(String(64))
    material_scope_json: Mapped[dict | list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("role in ('user', 'assistant', 'system')", name="message_role"),
        CheckConstraint(
            "answer_type is null or answer_type in ('grounded', 'partial_grounded', 'no_source')",
            name="message_answer_type",
        ),
        CheckConstraint(
            "generation_status is null or generation_status in ('pending', 'generating', 'success', 'failed')",
            name="message_generation_status",
        ),
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_course_id", "course_id"),
        Index("ix_messages_role", "role"),
        Index("ix_messages_answer_type", "answer_type"),
        Index("ix_messages_generation_status", "generation_status"),
        Index("ix_messages_error_code", "error_code"),
        Index("ix_messages_created_at", "created_at"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )


class SourceCitation(Base):
    __tablename__ = "source_citations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"))
    generated_content_id: Mapped[str | None] = mapped_column(ForeignKey("ai_generated_contents.id"))
    material_id: Mapped[str | None] = mapped_column(ForeignKey("course_materials.id"))
    chunk_id: Mapped[str | None] = mapped_column(ForeignKey("material_chunks.id"))
    material_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("material_parse_versions.id", ondelete="SET NULL")
    )
    material_name: Mapped[str] = mapped_column(String(255), nullable=False)
    page: Mapped[str | None] = mapped_column(String(64))
    page_index: Mapped[int | None] = mapped_column(Integer)
    hit_text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "message_id is not null or generated_content_id is not null",
            name="source_citation_parent_required",
        ),
        CheckConstraint("page is not null or page_index is not null", name="source_citation_location_required"),
        Index("ix_source_citations_message_id", "message_id"),
        Index("ix_source_citations_generated_content_id", "generated_content_id"),
        Index("ix_source_citations_material_id", "material_id"),
        Index("ix_source_citations_chunk_id", "chunk_id"),
        Index("ix_source_citations_material_version_id", "material_version_id"),
        Index("ix_source_citations_sort_order", "sort_order"),
    )
