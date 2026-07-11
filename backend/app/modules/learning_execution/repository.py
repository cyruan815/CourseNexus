from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.modules.courses.models import Course
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.materials.models import CourseMaterial
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask


@dataclass(frozen=True)
class ExecutionTarget:
    subtask: StudySubTask
    task: StudyTask
    plan: StudyPlan
    course: Course


def get_execution_target(db: Session, *, user_id: str, subtask_id: str) -> ExecutionTarget:
    row = db.execute(
        select(StudySubTask, StudyTask, StudyPlan, Course)
        .join(StudyTask, StudyTask.id == StudySubTask.task_id)
        .join(StudyPlan, StudyPlan.id == StudySubTask.plan_id)
        .join(Course, Course.id == StudySubTask.course_id)
        .where(
            StudySubTask.id == subtask_id,
            StudyPlan.user_id == user_id,
            Course.user_id == user_id,
            StudyPlan.status != "deleted",
            StudyPlan.deleted_at.is_(None),
            Course.status != "deleted",
            Course.deleted_at.is_(None),
        )
    ).one_or_none()
    if row is None:
        raise CourseNexusError(code="NOT_FOUND", message="学习任务不存在", status_code=404)
    subtask, task, plan, course = row
    if subtask.task_id != task.id or subtask.plan_id != plan.id or task.plan_id != plan.id:
        raise CourseNexusError(code="STATE_CONFLICT", message="任务层级关系不一致", status_code=409)
    if subtask.course_id != course.id or task.course_id != course.id or plan.course_id != course.id:
        raise CourseNexusError(code="STATE_CONFLICT", message="任务课程归属不一致", status_code=409)
    return ExecutionTarget(subtask=subtask, task=task, plan=plan, course=course)


def list_tasks_for_plan_date(db: Session, *, plan_id: str, task_date: date) -> list[StudyTask]:
    return list(
        db.execute(
            select(StudyTask)
            .where(StudyTask.plan_id == plan_id, StudyTask.task_date == task_date)
            .order_by(StudyTask.sort_order, StudyTask.id)
        ).scalars()
    )


def list_subtasks_for_tasks(db: Session, *, task_ids: list[str]) -> list[StudySubTask]:
    if not task_ids:
        return []
    return list(
        db.execute(
            select(StudySubTask)
            .where(StudySubTask.task_id.in_(task_ids))
            .order_by(StudySubTask.task_id, StudySubTask.sort_order, StudySubTask.id)
        ).scalars()
    )


def list_materials_by_ids(db: Session, *, material_ids: list[str]) -> list[CourseMaterial]:
    if not material_ids:
        return []
    return list(db.execute(select(CourseMaterial).where(CourseMaterial.id.in_(material_ids))).scalars())


def get_latest_successful_task_content(
    db: Session,
    *,
    user_id: str,
    subtask_id: str,
    content_type: str,
) -> AIGeneratedContent | None:
    return db.execute(
        select(AIGeneratedContent)
        .where(
            AIGeneratedContent.user_id == user_id,
            AIGeneratedContent.study_subtask_id == subtask_id,
            AIGeneratedContent.content_type == content_type,
            AIGeneratedContent.generation_status == "success",
            AIGeneratedContent.deleted_at.is_(None),
        )
        .order_by(AIGeneratedContent.created_at.desc(), AIGeneratedContent.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_completion_target(db: Session, *, user_id: str, subtask_id: str) -> ExecutionTarget:
    return get_execution_target(db, user_id=user_id, subtask_id=subtask_id)


def list_subtasks_for_task(db: Session, *, task_id: str) -> list[StudySubTask]:
    return list(
        db.execute(
            select(StudySubTask).where(StudySubTask.task_id == task_id).order_by(StudySubTask.sort_order, StudySubTask.id)
        ).scalars()
    )


def list_tasks_for_plan(db: Session, *, plan_id: str) -> list[StudyTask]:
    return list(
        db.execute(select(StudyTask).where(StudyTask.plan_id == plan_id).order_by(StudyTask.task_date, StudyTask.sort_order, StudyTask.id)).scalars()
    )
