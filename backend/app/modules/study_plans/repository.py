from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.modules.generated_content.models import AIGeneratedContent
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask


@dataclass(frozen=True)
class StudyPlanBundle:
    plan: StudyPlan
    tasks: list[StudyTask]
    subtasks: list[StudySubTask]


def add_study_plan_bundle(
    db: Session,
    *,
    plan: StudyPlan,
    tasks: list[StudyTask],
    subtasks: list[StudySubTask],
) -> StudyPlanBundle:
    db.add(plan)
    db.add_all(tasks)
    db.add_all(subtasks)
    db.flush()
    return StudyPlanBundle(plan=plan, tasks=tasks, subtasks=subtasks)


def save_study_plan_bundle(
    db: Session,
    *,
    plan: StudyPlan,
    tasks: list[StudyTask],
    subtasks: list[StudySubTask],
) -> StudyPlanBundle:
    bundle = add_study_plan_bundle(db, plan=plan, tasks=tasks, subtasks=subtasks)
    db.commit()
    db.refresh(plan)
    for task in tasks:
        db.refresh(task)
    for subtask in subtasks:
        db.refresh(subtask)
    return bundle


def list_active_study_plans_for_course(db: Session, *, user_id: str, course_id: str) -> list[StudyPlan]:
    return list(
        db.execute(
            select(StudyPlan)
            .where(
                StudyPlan.user_id == user_id,
                StudyPlan.course_id == course_id,
                StudyPlan.deleted_at.is_(None),
                StudyPlan.status != "deleted",
            )
            .order_by(StudyPlan.created_at.desc())
        ).scalars()
    )


def get_active_study_plan_for_user(db: Session, *, user_id: str, plan_id: str) -> StudyPlan | None:
    return db.execute(
        select(StudyPlan).where(
            StudyPlan.id == plan_id,
            StudyPlan.user_id == user_id,
            StudyPlan.deleted_at.is_(None),
            StudyPlan.status != "deleted",
        )
    ).scalar_one_or_none()


def get_active_study_plan_for_idempotency_key(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    key_hash: str,
) -> StudyPlan | None:
    plans = list_active_study_plans_for_course(db, user_id=user_id, course_id=course_id)
    for plan in plans:
        config = plan.parsed_config_json if isinstance(plan.parsed_config_json, dict) else {}
        idempotency = config.get("idempotency") if isinstance(config, dict) else None
        if isinstance(idempotency, dict) and idempotency.get("key_hash") == key_hash:
            return plan
    return None


def list_tasks_for_plan(db: Session, *, plan_id: str) -> list[StudyTask]:
    return list(
        db.execute(
            select(StudyTask).where(StudyTask.plan_id == plan_id).order_by(StudyTask.task_date, StudyTask.sort_order)
        ).scalars()
    )


def list_subtasks_for_plan(db: Session, *, plan_id: str) -> list[StudySubTask]:
    return list(
        db.execute(
            select(StudySubTask).where(StudySubTask.plan_id == plan_id).order_by(StudySubTask.sort_order)
        ).scalars()
    )


def delete_tasks_for_plan(db: Session, *, plan_id: str) -> None:
    db.execute(delete(StudySubTask).where(StudySubTask.plan_id == plan_id))
    db.execute(delete(StudyTask).where(StudyTask.plan_id == plan_id))
    db.flush()

def has_started_subtasks(db: Session, *, plan_id: str) -> bool:
    return bool(
        db.scalar(
            select(func.count())
            .select_from(StudySubTask)
            .where(StudySubTask.plan_id == plan_id, StudySubTask.status != "not_started")
        )
    )


def has_bound_generated_content(db: Session, *, plan_id: str) -> bool:
    return bool(
        db.scalar(
            select(func.count())
            .select_from(AIGeneratedContent)
            .join(StudySubTask, AIGeneratedContent.study_subtask_id == StudySubTask.id)
            .where(
                StudySubTask.plan_id == plan_id,
                AIGeneratedContent.deleted_at.is_(None),
            )
        )
    )