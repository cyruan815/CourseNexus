from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from sqlalchemy import case, func, literal, select
from sqlalchemy.orm import Session

from app.modules.courses.models import Course
from app.modules.materials.models import CourseMaterial
from app.modules.study_plans.models import StudyPlan, StudyTask


TodayTaskStatus = Literal["no_study_plan", "no_task_today", "has_task_today"]


@dataclass(frozen=True)
class CourseListItem:
    course: Course
    material_count: int
    today_task_status: TodayTaskStatus


def get_course_by_id(db: Session, course_id: str) -> Course | None:
    return db.execute(select(Course).where(Course.id == course_id)).scalar_one_or_none()


def get_active_course_for_user(db: Session, user_id: str, course_id: str) -> Course | None:
    return db.execute(
        select(Course).where(
            Course.id == course_id,
            Course.user_id == user_id,
            Course.deleted_at.is_(None),
            Course.status != "deleted",
        )
    ).scalar_one_or_none()


def list_active_courses_for_user(db: Session, user_id: str) -> list[Course]:
    return list(
        db.execute(
            select(Course)
            .where(
                Course.user_id == user_id,
                Course.deleted_at.is_(None),
                Course.status != "deleted",
            )
            .order_by(Course.updated_at.desc(), Course.created_at.desc())
        ).scalars()
    )


def list_course_list_items_for_user(db: Session, *, user_id: str, target_date: date) -> list[CourseListItem]:
    material_counts = (
        select(
            CourseMaterial.course_id.label("course_id"),
            func.count(CourseMaterial.id).label("material_count"),
        )
        .where(
            CourseMaterial.user_id == user_id,
            CourseMaterial.deleted_at.is_(None),
            CourseMaterial.parse_status != "deleted",
        )
        .group_by(CourseMaterial.course_id)
        .subquery()
    )
    plan_courses = (
        select(StudyPlan.course_id.label("course_id"))
        .where(
            StudyPlan.user_id == user_id,
            StudyPlan.deleted_at.is_(None),
            StudyPlan.status != "deleted",
        )
        .group_by(StudyPlan.course_id)
        .subquery()
    )
    today_task_courses = (
        select(StudyTask.course_id.label("course_id"))
        .join(StudyPlan, StudyPlan.id == StudyTask.plan_id)
        .where(
            StudyPlan.user_id == user_id,
            StudyPlan.deleted_at.is_(None),
            StudyPlan.status != "deleted",
            StudyPlan.course_id == StudyTask.course_id,
            StudyTask.task_date == target_date,
        )
        .group_by(StudyTask.course_id)
        .subquery()
    )
    status = case(
        (plan_courses.c.course_id.is_(None), literal("no_study_plan")),
        (today_task_courses.c.course_id.is_(None), literal("no_task_today")),
        else_=literal("has_task_today"),
    ).label("today_task_status")
    rows = db.execute(
        select(
            Course,
            func.coalesce(material_counts.c.material_count, 0).label("material_count"),
            status,
        )
        .outerjoin(material_counts, material_counts.c.course_id == Course.id)
        .outerjoin(plan_courses, plan_courses.c.course_id == Course.id)
        .outerjoin(today_task_courses, today_task_courses.c.course_id == Course.id)
        .where(
            Course.user_id == user_id,
            Course.deleted_at.is_(None),
            Course.status != "deleted",
        )
        .order_by(Course.updated_at.desc(), Course.created_at.desc())
    ).all()
    return [
        CourseListItem(
            course=row.Course,
            material_count=int(row.material_count),
            today_task_status=row.today_task_status,
        )
        for row in rows
    ]


def save_course(db: Session, course: Course) -> Course:
    db.add(course)
    db.commit()
    db.refresh(course)
    return course
