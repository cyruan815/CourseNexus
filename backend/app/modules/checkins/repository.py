from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.modules.checkins.models import CheckinRecord
from app.modules.courses.models import Course
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask


@dataclass(frozen=True)
class CheckinCounts:
    total_subtask_count: int
    completed_subtask_count: int


def count_subtasks_for_date(db: Session, *, user_id: str, checkin_date: date) -> CheckinCounts:
    row = db.execute(
        select(
            func.count(StudySubTask.id).label("total"),
            func.coalesce(func.sum(case((StudySubTask.status == "completed", 1), else_=0)), 0).label("completed"),
        )
        .select_from(StudySubTask)
        .join(StudyTask, StudyTask.id == StudySubTask.task_id)
        .join(StudyPlan, StudyPlan.id == StudySubTask.plan_id)
        .join(Course, Course.id == StudySubTask.course_id)
        .where(
            StudyPlan.user_id == user_id,
            Course.user_id == user_id,
            StudyTask.task_date == checkin_date,
            StudyPlan.status != "deleted",
            StudyPlan.deleted_at.is_(None),
            Course.status != "deleted",
            Course.deleted_at.is_(None),
        )
    ).one()
    return CheckinCounts(total_subtask_count=int(row.total or 0), completed_subtask_count=int(row.completed or 0))


def get_checkin_record(db: Session, *, user_id: str, checkin_date: date) -> CheckinRecord | None:
    return db.execute(
        select(CheckinRecord).where(CheckinRecord.user_id == user_id, CheckinRecord.checkin_date == checkin_date)
    ).scalar_one_or_none()


def list_checkin_records(db: Session, *, user_id: str, start_date: date, end_date: date) -> list[CheckinRecord]:
    return list(
        db.execute(
            select(CheckinRecord)
            .where(
                CheckinRecord.user_id == user_id,
                CheckinRecord.checkin_date >= start_date,
                CheckinRecord.checkin_date <= end_date,
            )
            .order_by(CheckinRecord.checkin_date)
        ).scalars()
    )
