from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AIGeneratedContent(Base):
    __tablename__ = "ai_generated_contents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), nullable=False)
    study_subtask_id: Mapped[str | None] = mapped_column(ForeignKey("study_subtasks.id"))
    source_message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"))
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    content_json: Mapped[dict | list | None] = mapped_column(JSON)
    generation_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    material_scope_json: Mapped[dict | list | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "content_type in ('quiz', 'flashcard', 'mindmap', 'outline', 'knowledge_list', 'note', 'handout', 'task_test')",
            name="ai_generated_content_type",
        ),
        CheckConstraint(
            "generation_status in ('pending', 'generating', 'success', 'failed')",
            name="ai_generated_content_generation_status",
        ),
        Index("ix_ai_generated_contents_user_id", "user_id"),
        Index("ix_ai_generated_contents_course_id", "course_id"),
        Index("ix_ai_generated_contents_study_subtask_id", "study_subtask_id"),
        Index("ix_ai_generated_contents_source_message_id", "source_message_id"),
        Index("ix_ai_generated_contents_generation_status", "generation_status"),
        Index("ix_ai_generated_contents_error_code", "error_code"),
        Index("ix_ai_generated_contents_created_at", "created_at"),
        Index("ix_ai_generated_contents_deleted_at", "deleted_at"),
        Index("ix_ai_generated_contents_course_type", "course_id", "content_type"),
        Index(
            "ix_ai_generated_contents_history",
            "course_id",
            "content_type",
            "generation_status",
            "created_at",
        ),
    )
