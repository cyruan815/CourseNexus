from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.modules.courses.models import Course
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask


@dataclass(frozen=True)
class TodoTaskRow:
    course_id: str
    course_name: str
    plan_id: str
    plan_title: str
    plan_start_date: date
    plan_end_date: date
    task_id: str
    task_title: str
    task_date: date
    task_status: str
    task_sort_order: int
    subtask_id: str | None
    subtask_title: str | None
    subtask_type: str | None
    subtask_description: str | None
    subtask_status: str | None
    subtask_sort_order: int | None


def _base_task_rows_query(user_id: str):
    return (
        select(
            Course.id.label("course_id"),
            Course.name.label("course_name"),
            StudyPlan.id.label("plan_id"),
            StudyPlan.title.label("plan_title"),
            StudyPlan.start_date.label("plan_start_date"),
            StudyPlan.end_date.label("plan_end_date"),
            StudyTask.id.label("task_id"),
            StudyTask.title.label("task_title"),
            StudyTask.task_date.label("task_date"),
            StudyTask.status.label("task_status"),
            StudyTask.sort_order.label("task_sort_order"),
            StudySubTask.id.label("subtask_id"),
            StudySubTask.title.label("subtask_title"),
            StudySubTask.subtask_type.label("subtask_type"),
            StudySubTask.description.label("subtask_description"),
            StudySubTask.status.label("subtask_status"),
            StudySubTask.sort_order.label("subtask_sort_order"),
        )
        .select_from(StudyTask)
        .join(StudyPlan, StudyPlan.id == StudyTask.plan_id)
        .join(Course, Course.id == StudyTask.course_id)
        .outerjoin(StudySubTask, StudySubTask.task_id == StudyTask.id)
        .where(
            StudyPlan.user_id == user_id,
            Course.user_id == user_id,
            StudyPlan.status != "deleted",
            StudyPlan.deleted_at.is_(None),
            Course.status != "deleted",
            Course.deleted_at.is_(None),
        )
    )


def _rows_to_dataclasses(rows: list[object]) -> list[TodoTaskRow]:
    return [TodoTaskRow(**dict(row._mapping)) for row in rows]


def _get_active_course(db: Session, *, user_id: str, course_id: str) -> Course:
    course = db.execute(
        select(Course).where(
            Course.id == course_id,
            Course.user_id == user_id,
            Course.status != "deleted",
            Course.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if course is None:
        raise CourseNexusError(code="NOT_FOUND", message="课程不存在", status_code=404)
    return course


def list_task_rows_for_date(db: Session, *, user_id: str, target_date: date) -> list[TodoTaskRow]:
    rows = db.execute(
        _base_task_rows_query(user_id)
        .where(StudyTask.task_date == target_date)
        .order_by(Course.name, StudyTask.sort_order, StudySubTask.sort_order, StudyTask.id, StudySubTask.id)
    ).all()
    return _rows_to_dataclasses(rows)


def list_task_rows_for_month(db: Session, *, user_id: str, month_start: date, month_end: date) -> list[TodoTaskRow]:
    rows = db.execute(
        _base_task_rows_query(user_id)
        .where(StudyTask.task_date >= month_start, StudyTask.task_date < month_end)
        .order_by(StudyTask.task_date, Course.name, StudyTask.sort_order, StudySubTask.sort_order, StudyTask.id, StudySubTask.id)
    ).all()
    return _rows_to_dataclasses(rows)


def list_task_rows_for_course_date(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    target_date: date,
) -> tuple[Course, list[TodoTaskRow]]:
    course = _get_active_course(db, user_id=user_id, course_id=course_id)
    rows = db.execute(
        _base_task_rows_query(user_id)
        .where(StudyTask.course_id == course_id, StudyTask.task_date == target_date)
        .order_by(StudyTask.sort_order, StudySubTask.sort_order, StudyTask.id, StudySubTask.id)
    ).all()
    return course, _rows_to_dataclasses(rows)


def list_task_rows_for_course_month(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    month_start: date,
    month_end: date,
) -> tuple[Course, list[TodoTaskRow]]:
    course = _get_active_course(db, user_id=user_id, course_id=course_id)
    rows = db.execute(
        _base_task_rows_query(user_id)
        .where(StudyTask.course_id == course_id, StudyTask.task_date >= month_start, StudyTask.task_date < month_end)
        .order_by(StudyTask.task_date, StudyTask.sort_order, StudySubTask.sort_order, StudyTask.id, StudySubTask.id)
    ).all()
    return course, _rows_to_dataclasses(rows)