from datetime import date, datetime, time

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    goal_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_config_json: Mapped[dict | list | None] = mapped_column(JSON)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    daily_available_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("status in ('draft', 'active', 'completed', 'deleted')", name="study_plan_status"),
        CheckConstraint("end_date >= start_date", name="study_plan_date_range"),
        CheckConstraint("daily_available_minutes > 0", name="study_plan_daily_minutes_positive"),
        Index("ix_study_plans_user_id", "user_id"),
        Index("ix_study_plans_course_id", "course_id"),
        Index("ix_study_plans_course_title", "course_id", "title"),
        Index("ix_study_plans_start_date", "start_date"),
        Index("ix_study_plans_end_date", "end_date"),
        Index("ix_study_plans_status", "status"),
        Index("ix_study_plans_deleted_at", "deleted_at"),
        Index("ix_study_plans_course_status_dates", "course_id", "status", "start_date", "end_date"),
    )


class StudyTask(Base):
    __tablename__ = "study_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("study_plans.id"), nullable=False)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    task_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="not_started",
        server_default="not_started",
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("status in ('not_started', 'in_progress', 'completed')", name="study_task_status"),
        CheckConstraint("sort_order > 0", name="study_task_sort_order_positive"),
        Index("ix_study_tasks_plan_id", "plan_id"),
        Index("ix_study_tasks_course_id", "course_id"),
        Index("ix_study_tasks_status", "status"),
        Index("ix_study_tasks_course_date", "course_id", "task_date"),
        Index("ix_study_tasks_plan_date_sort", "plan_id", "task_date", "sort_order"),
    )


class StudySubTask(Base):
    __tablename__ = "study_subtasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("study_tasks.id"), nullable=False)
    plan_id: Mapped[str] = mapped_column(ForeignKey("study_plans.id"), nullable=False)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtask_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    related_material_ids_json: Mapped[dict | list | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="not_started",
        server_default="not_started",
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("subtask_type in ('learn', 'review', 'quiz', 'test')", name="study_subtask_type"),
        CheckConstraint("status in ('not_started', 'in_progress', 'completed')", name="study_subtask_status"),
        CheckConstraint("sort_order > 0", name="study_subtask_sort_order_positive"),
        Index("ix_study_subtasks_task_id", "task_id"),
        Index("ix_study_subtasks_plan_id", "plan_id"),
        Index("ix_study_subtasks_course_id", "course_id"),
        Index("ix_study_subtasks_subtask_type", "subtask_type"),
        Index("ix_study_subtasks_status", "status"),
        Index("ix_study_subtasks_completed_at", "completed_at"),
        Index("ix_study_subtasks_task_sort", "task_id", "sort_order"),
        Index("ix_study_subtasks_course_status", "course_id", "status"),
    )
