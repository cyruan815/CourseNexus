"""create core tables

Revision ID: 20260709_0001
Revises:
Create Date: 2026-07-09
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260709_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("nickname", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=2048), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('active', 'disabled')", name="ck_users_user_status"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])
    op.create_index("ix_users_status", "users", ["status"])

    op.create_table(
        "courses",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("teacher", sa.String(length=255), nullable=True),
        sa.Column("term", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('active', 'archived', 'deleted')", name="ck_courses_course_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_courses_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_courses"),
    )
    op.create_index("ix_courses_deleted_at", "courses", ["deleted_at"])
    op.create_index("ix_courses_status", "courses", ["status"])
    op.create_index("ix_courses_user_id", "courses", ["user_id"])
    op.create_index("ix_courses_user_id_name", "courses", ["user_id", "name"])
    op.create_index("ix_courses_user_status_updated", "courses", ["user_id", "status", "updated_at"])

    op.create_table(
        "material_folders",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("course_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name="fk_material_folders_course_id_courses"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_material_folders_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_material_folders"),
    )
    op.create_index("ix_material_folders_course_id", "material_folders", ["course_id"])
    op.create_index("ix_material_folders_course_name", "material_folders", ["course_id", "name"])
    op.create_index("ix_material_folders_course_sort", "material_folders", ["course_id", "sort_order"])
    op.create_index("ix_material_folders_deleted_at", "material_folders", ["deleted_at"])
    op.create_index("ix_material_folders_user_id", "material_folders", ["user_id"])

    op.create_table(
        "course_materials",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("course_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("folder_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("material_type", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("file_url", sa.String(length=2048), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("parse_status", sa.String(length=32), server_default="uploaded", nullable=False),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "material_type in ('pdf', 'ppt', 'word', 'markdown', 'image', 'text', 'link')",
            name="ck_course_materials_course_material_material_type",
        ),
        sa.CheckConstraint("source_type in ('file', 'url')", name="ck_course_materials_course_material_source_type"),
        sa.CheckConstraint(
            "parse_status in ('uploaded', 'parsing', 'parsed', 'parse_failed', 'deleted')",
            name="ck_course_materials_course_material_parse_status",
        ),
        sa.CheckConstraint(
            "source_type != 'file' or file_url is not null",
            name="ck_course_materials_course_material_file_url_required",
        ),
        sa.CheckConstraint(
            "source_type != 'url' or source_url is not null",
            name="ck_course_materials_course_material_source_url_required",
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name="fk_course_materials_course_id_courses"),
        sa.ForeignKeyConstraint(["folder_id"], ["material_folders.id"], name="fk_course_materials_folder_id_material_folders"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_course_materials_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_course_materials"),
    )
    op.create_index("ix_course_materials_course_id", "course_materials", ["course_id"])
    op.create_index("ix_course_materials_course_name", "course_materials", ["course_id", "name"])
    op.create_index("ix_course_materials_course_parse_status", "course_materials", ["course_id", "parse_status"])
    op.create_index("ix_course_materials_created_at", "course_materials", ["created_at"])
    op.create_index("ix_course_materials_deleted_at", "course_materials", ["deleted_at"])
    op.create_index("ix_course_materials_folder_id", "course_materials", ["folder_id"])
    op.create_index("ix_course_materials_material_type", "course_materials", ["material_type"])
    op.create_index("ix_course_materials_source_type", "course_materials", ["source_type"])
    op.create_index("ix_course_materials_user_id", "course_materials", ["user_id"])

    op.create_table(
        "material_chunks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("material_id", sa.String(length=64), nullable=False),
        sa.Column("course_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page", sa.String(length=64), nullable=True),
        sa.Column("page_index", sa.Integer(), nullable=True),
        sa.Column("heading", sa.String(length=500), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("embedding_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name="fk_material_chunks_course_id_courses"),
        sa.ForeignKeyConstraint(["material_id"], ["course_materials.id"], name="fk_material_chunks_material_id_course_materials"),
        sa.PrimaryKeyConstraint("id", name="pk_material_chunks"),
        sa.UniqueConstraint("material_id", "chunk_index", name="uq_material_chunks_material_chunk_index"),
    )
    op.create_index("ix_material_chunks_course_id", "material_chunks", ["course_id"])
    op.create_index("ix_material_chunks_course_material_chunk", "material_chunks", ["course_id", "material_id", "chunk_index"])
    op.create_index("ix_material_chunks_embedding_id", "material_chunks", ["embedding_id"])
    op.create_index("ix_material_chunks_material_id", "material_chunks", ["material_id"])
    op.create_index("ix_material_chunks_page", "material_chunks", ["page"])
    op.create_index("ix_material_chunks_page_index", "material_chunks", ["page_index"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("course_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("source_page", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('active', 'deleted')", name="ck_conversations_conversation_status"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name="fk_conversations_course_id_courses"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_conversations_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
    )
    op.create_index("ix_conversations_course_id", "conversations", ["course_id"])
    op.create_index("ix_conversations_course_status_updated", "conversations", ["course_id", "status", "updated_at"])
    op.create_index("ix_conversations_created_at", "conversations", ["created_at"])
    op.create_index("ix_conversations_deleted_at", "conversations", ["deleted_at"])
    op.create_index("ix_conversations_source_page", "conversations", ["source_page"])
    op.create_index("ix_conversations_status", "conversations", ["status"])
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("conversation_id", sa.String(length=64), nullable=False),
        sa.Column("course_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("answer_type", sa.String(length=32), nullable=True),
        sa.Column("generation_status", sa.String(length=32), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("material_scope_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role in ('user', 'assistant', 'system')", name="ck_messages_message_role"),
        sa.CheckConstraint(
            "answer_type is null or answer_type in ('grounded', 'partial_grounded', 'no_source')",
            name="ck_messages_message_answer_type",
        ),
        sa.CheckConstraint(
            "generation_status is null or generation_status in ('pending', 'generating', 'success', 'failed')",
            name="ck_messages_message_generation_status",
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name="fk_messages_conversation_id_conversations"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name="fk_messages_course_id_courses"),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
    )
    op.create_index("ix_messages_answer_type", "messages", ["answer_type"])
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"])
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_course_id", "messages", ["course_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])
    op.create_index("ix_messages_error_code", "messages", ["error_code"])
    op.create_index("ix_messages_generation_status", "messages", ["generation_status"])
    op.create_index("ix_messages_role", "messages", ["role"])

    op.create_table(
        "study_plans",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("course_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("goal_text", sa.Text(), nullable=False),
        sa.Column("parsed_config_json", sa.JSON(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("daily_available_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('draft', 'active', 'completed', 'deleted')", name="ck_study_plans_study_plan_status"),
        sa.CheckConstraint("end_date >= start_date", name="ck_study_plans_study_plan_date_range"),
        sa.CheckConstraint("daily_available_minutes > 0", name="ck_study_plans_study_plan_daily_minutes_positive"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name="fk_study_plans_course_id_courses"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_study_plans_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_study_plans"),
    )
    op.create_index("ix_study_plans_course_id", "study_plans", ["course_id"])
    op.create_index("ix_study_plans_course_status_dates", "study_plans", ["course_id", "status", "start_date", "end_date"])
    op.create_index("ix_study_plans_course_title", "study_plans", ["course_id", "title"])
    op.create_index("ix_study_plans_deleted_at", "study_plans", ["deleted_at"])
    op.create_index("ix_study_plans_end_date", "study_plans", ["end_date"])
    op.create_index("ix_study_plans_start_date", "study_plans", ["start_date"])
    op.create_index("ix_study_plans_status", "study_plans", ["status"])
    op.create_index("ix_study_plans_user_id", "study_plans", ["user_id"])

    op.create_table(
        "study_tasks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("course_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("task_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="not_started", nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status in ('not_started', 'in_progress', 'completed')", name="ck_study_tasks_study_task_status"),
        sa.CheckConstraint("sort_order > 0", name="ck_study_tasks_study_task_sort_order_positive"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name="fk_study_tasks_course_id_courses"),
        sa.ForeignKeyConstraint(["plan_id"], ["study_plans.id"], name="fk_study_tasks_plan_id_study_plans"),
        sa.PrimaryKeyConstraint("id", name="pk_study_tasks"),
    )
    op.create_index("ix_study_tasks_course_date", "study_tasks", ["course_id", "task_date"])
    op.create_index("ix_study_tasks_course_id", "study_tasks", ["course_id"])
    op.create_index("ix_study_tasks_plan_date_sort", "study_tasks", ["plan_id", "task_date", "sort_order"])
    op.create_index("ix_study_tasks_plan_id", "study_tasks", ["plan_id"])
    op.create_index("ix_study_tasks_status", "study_tasks", ["status"])

    op.create_table(
        "study_subtasks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("course_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subtask_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("related_material_ids_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="not_started", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("subtask_type in ('learn', 'review', 'quiz', 'test')", name="ck_study_subtasks_study_subtask_type"),
        sa.CheckConstraint("status in ('not_started', 'in_progress', 'completed')", name="ck_study_subtasks_study_subtask_status"),
        sa.CheckConstraint("sort_order > 0", name="ck_study_subtasks_study_subtask_sort_order_positive"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name="fk_study_subtasks_course_id_courses"),
        sa.ForeignKeyConstraint(["plan_id"], ["study_plans.id"], name="fk_study_subtasks_plan_id_study_plans"),
        sa.ForeignKeyConstraint(["task_id"], ["study_tasks.id"], name="fk_study_subtasks_task_id_study_tasks"),
        sa.PrimaryKeyConstraint("id", name="pk_study_subtasks"),
    )
    op.create_index("ix_study_subtasks_completed_at", "study_subtasks", ["completed_at"])
    op.create_index("ix_study_subtasks_course_id", "study_subtasks", ["course_id"])
    op.create_index("ix_study_subtasks_course_status", "study_subtasks", ["course_id", "status"])
    op.create_index("ix_study_subtasks_plan_id", "study_subtasks", ["plan_id"])
    op.create_index("ix_study_subtasks_status", "study_subtasks", ["status"])
    op.create_index("ix_study_subtasks_subtask_type", "study_subtasks", ["subtask_type"])
    op.create_index("ix_study_subtasks_task_id", "study_subtasks", ["task_id"])
    op.create_index("ix_study_subtasks_task_sort", "study_subtasks", ["task_id", "sort_order"])

    op.create_table(
        "ai_generated_contents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("course_id", sa.String(length=64), nullable=False),
        sa.Column("study_subtask_id", sa.String(length=64), nullable=True),
        sa.Column("source_message_id", sa.String(length=64), nullable=True),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("generation_status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("material_scope_json", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "content_type in ('quiz', 'flashcard', 'mindmap', 'outline', 'knowledge_list', 'note', 'handout', 'task_test')",
            name="ck_ai_generated_contents_ai_generated_content_type",
        ),
        sa.CheckConstraint(
            "generation_status in ('pending', 'generating', 'success', 'failed')",
            name="ck_ai_generated_contents_ai_generated_content_generation_status",
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name="fk_ai_generated_contents_course_id_courses"),
        sa.ForeignKeyConstraint(["source_message_id"], ["messages.id"], name="fk_ai_generated_contents_source_message_id_messages"),
        sa.ForeignKeyConstraint(
            ["study_subtask_id"],
            ["study_subtasks.id"],
            name="fk_ai_generated_contents_study_subtask_id_study_subtasks",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_ai_generated_contents_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_ai_generated_contents"),
    )
    op.create_index("ix_ai_generated_contents_course_id", "ai_generated_contents", ["course_id"])
    op.create_index("ix_ai_generated_contents_course_type", "ai_generated_contents", ["course_id", "content_type"])
    op.create_index("ix_ai_generated_contents_created_at", "ai_generated_contents", ["created_at"])
    op.create_index("ix_ai_generated_contents_deleted_at", "ai_generated_contents", ["deleted_at"])
    op.create_index("ix_ai_generated_contents_error_code", "ai_generated_contents", ["error_code"])
    op.create_index("ix_ai_generated_contents_generation_status", "ai_generated_contents", ["generation_status"])
    op.create_index(
        "ix_ai_generated_contents_history",
        "ai_generated_contents",
        ["course_id", "content_type", "generation_status", "created_at"],
    )
    op.create_index("ix_ai_generated_contents_source_message_id", "ai_generated_contents", ["source_message_id"])
    op.create_index("ix_ai_generated_contents_study_subtask_id", "ai_generated_contents", ["study_subtask_id"])
    op.create_index("ix_ai_generated_contents_user_id", "ai_generated_contents", ["user_id"])

    op.create_table(
        "source_citations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("message_id", sa.String(length=64), nullable=True),
        sa.Column("generated_content_id", sa.String(length=64), nullable=True),
        sa.Column("material_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_id", sa.String(length=64), nullable=True),
        sa.Column("material_name", sa.String(length=255), nullable=False),
        sa.Column("page", sa.String(length=64), nullable=True),
        sa.Column("page_index", sa.Integer(), nullable=True),
        sa.Column("hit_text", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "message_id is not null or generated_content_id is not null",
            name="ck_source_citations_source_citation_parent_required",
        ),
        sa.CheckConstraint(
            "page is not null or page_index is not null",
            name="ck_source_citations_source_citation_location_required",
        ),
        sa.ForeignKeyConstraint(["chunk_id"], ["material_chunks.id"], name="fk_source_citations_chunk_id_material_chunks"),
        sa.ForeignKeyConstraint(
            ["generated_content_id"],
            ["ai_generated_contents.id"],
            name="fk_source_citations_generated_content_id_ai_generated_contents",
        ),
        sa.ForeignKeyConstraint(["material_id"], ["course_materials.id"], name="fk_source_citations_material_id_course_materials"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], name="fk_source_citations_message_id_messages"),
        sa.PrimaryKeyConstraint("id", name="pk_source_citations"),
    )
    op.create_index("ix_source_citations_chunk_id", "source_citations", ["chunk_id"])
    op.create_index("ix_source_citations_generated_content_id", "source_citations", ["generated_content_id"])
    op.create_index("ix_source_citations_material_id", "source_citations", ["material_id"])
    op.create_index("ix_source_citations_message_id", "source_citations", ["message_id"])
    op.create_index("ix_source_citations_sort_order", "source_citations", ["sort_order"])

    op.create_table(
        "checkin_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("checkin_date", sa.Date(), nullable=False),
        sa.Column("total_subtask_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_subtask_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completion_ratio", sa.Numeric(5, 4), server_default="0", nullable=False),
        sa.Column("color_level", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("total_subtask_count >= 0", name="ck_checkin_records_checkin_total_count_non_negative"),
        sa.CheckConstraint("completed_subtask_count >= 0", name="ck_checkin_records_checkin_completed_count_non_negative"),
        sa.CheckConstraint(
            "completed_subtask_count <= total_subtask_count",
            name="ck_checkin_records_checkin_completed_not_greater_total",
        ),
        sa.CheckConstraint(
            "completion_ratio >= 0 and completion_ratio <= 1",
            name="ck_checkin_records_checkin_completion_ratio_range",
        ),
        sa.CheckConstraint("color_level >= 0 and color_level <= 5", name="ck_checkin_records_checkin_color_level_range"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_checkin_records_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_checkin_records"),
        sa.UniqueConstraint("user_id", "checkin_date", name="uq_checkin_records_user_date"),
    )
    op.create_index("ix_checkin_records_color_level", "checkin_records", ["color_level"])
    op.create_index("ix_checkin_records_user_date", "checkin_records", ["user_id", "checkin_date"])


def downgrade() -> None:
    op.drop_index("ix_checkin_records_user_date", table_name="checkin_records")
    op.drop_index("ix_checkin_records_color_level", table_name="checkin_records")
    op.drop_table("checkin_records")

    op.drop_index("ix_source_citations_sort_order", table_name="source_citations")
    op.drop_index("ix_source_citations_message_id", table_name="source_citations")
    op.drop_index("ix_source_citations_material_id", table_name="source_citations")
    op.drop_index("ix_source_citations_generated_content_id", table_name="source_citations")
    op.drop_index("ix_source_citations_chunk_id", table_name="source_citations")
    op.drop_table("source_citations")

    op.drop_index("ix_ai_generated_contents_user_id", table_name="ai_generated_contents")
    op.drop_index("ix_ai_generated_contents_study_subtask_id", table_name="ai_generated_contents")
    op.drop_index("ix_ai_generated_contents_source_message_id", table_name="ai_generated_contents")
    op.drop_index("ix_ai_generated_contents_history", table_name="ai_generated_contents")
    op.drop_index("ix_ai_generated_contents_generation_status", table_name="ai_generated_contents")
    op.drop_index("ix_ai_generated_contents_error_code", table_name="ai_generated_contents")
    op.drop_index("ix_ai_generated_contents_deleted_at", table_name="ai_generated_contents")
    op.drop_index("ix_ai_generated_contents_created_at", table_name="ai_generated_contents")
    op.drop_index("ix_ai_generated_contents_course_type", table_name="ai_generated_contents")
    op.drop_index("ix_ai_generated_contents_course_id", table_name="ai_generated_contents")
    op.drop_table("ai_generated_contents")

    op.drop_index("ix_study_subtasks_task_sort", table_name="study_subtasks")
    op.drop_index("ix_study_subtasks_task_id", table_name="study_subtasks")
    op.drop_index("ix_study_subtasks_subtask_type", table_name="study_subtasks")
    op.drop_index("ix_study_subtasks_status", table_name="study_subtasks")
    op.drop_index("ix_study_subtasks_plan_id", table_name="study_subtasks")
    op.drop_index("ix_study_subtasks_course_status", table_name="study_subtasks")
    op.drop_index("ix_study_subtasks_course_id", table_name="study_subtasks")
    op.drop_index("ix_study_subtasks_completed_at", table_name="study_subtasks")
    op.drop_table("study_subtasks")

    op.drop_index("ix_study_tasks_status", table_name="study_tasks")
    op.drop_index("ix_study_tasks_plan_id", table_name="study_tasks")
    op.drop_index("ix_study_tasks_plan_date_sort", table_name="study_tasks")
    op.drop_index("ix_study_tasks_course_id", table_name="study_tasks")
    op.drop_index("ix_study_tasks_course_date", table_name="study_tasks")
    op.drop_table("study_tasks")

    op.drop_index("ix_study_plans_user_id", table_name="study_plans")
    op.drop_index("ix_study_plans_status", table_name="study_plans")
    op.drop_index("ix_study_plans_start_date", table_name="study_plans")
    op.drop_index("ix_study_plans_end_date", table_name="study_plans")
    op.drop_index("ix_study_plans_deleted_at", table_name="study_plans")
    op.drop_index("ix_study_plans_course_title", table_name="study_plans")
    op.drop_index("ix_study_plans_course_status_dates", table_name="study_plans")
    op.drop_index("ix_study_plans_course_id", table_name="study_plans")
    op.drop_table("study_plans")

    op.drop_index("ix_messages_role", table_name="messages")
    op.drop_index("ix_messages_generation_status", table_name="messages")
    op.drop_index("ix_messages_error_code", table_name="messages")
    op.drop_index("ix_messages_created_at", table_name="messages")
    op.drop_index("ix_messages_course_id", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_index("ix_messages_answer_type", table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_index("ix_conversations_status", table_name="conversations")
    op.drop_index("ix_conversations_source_page", table_name="conversations")
    op.drop_index("ix_conversations_deleted_at", table_name="conversations")
    op.drop_index("ix_conversations_created_at", table_name="conversations")
    op.drop_index("ix_conversations_course_status_updated", table_name="conversations")
    op.drop_index("ix_conversations_course_id", table_name="conversations")
    op.drop_table("conversations")

    op.drop_index("ix_material_chunks_page_index", table_name="material_chunks")
    op.drop_index("ix_material_chunks_page", table_name="material_chunks")
    op.drop_index("ix_material_chunks_material_id", table_name="material_chunks")
    op.drop_index("ix_material_chunks_embedding_id", table_name="material_chunks")
    op.drop_index("ix_material_chunks_course_material_chunk", table_name="material_chunks")
    op.drop_index("ix_material_chunks_course_id", table_name="material_chunks")
    op.drop_table("material_chunks")

    op.drop_index("ix_course_materials_user_id", table_name="course_materials")
    op.drop_index("ix_course_materials_source_type", table_name="course_materials")
    op.drop_index("ix_course_materials_material_type", table_name="course_materials")
    op.drop_index("ix_course_materials_folder_id", table_name="course_materials")
    op.drop_index("ix_course_materials_deleted_at", table_name="course_materials")
    op.drop_index("ix_course_materials_created_at", table_name="course_materials")
    op.drop_index("ix_course_materials_course_parse_status", table_name="course_materials")
    op.drop_index("ix_course_materials_course_name", table_name="course_materials")
    op.drop_index("ix_course_materials_course_id", table_name="course_materials")
    op.drop_table("course_materials")

    op.drop_index("ix_material_folders_user_id", table_name="material_folders")
    op.drop_index("ix_material_folders_deleted_at", table_name="material_folders")
    op.drop_index("ix_material_folders_course_sort", table_name="material_folders")
    op.drop_index("ix_material_folders_course_name", table_name="material_folders")
    op.drop_index("ix_material_folders_course_id", table_name="material_folders")
    op.drop_table("material_folders")

    op.drop_index("ix_courses_user_status_updated", table_name="courses")
    op.drop_index("ix_courses_user_id_name", table_name="courses")
    op.drop_index("ix_courses_user_id", table_name="courses")
    op.drop_index("ix_courses_status", table_name="courses")
    op.drop_index("ix_courses_deleted_at", table_name="courses")
    op.drop_table("courses")

    op.drop_index("ix_users_status", table_name="users")
    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_table("users")
