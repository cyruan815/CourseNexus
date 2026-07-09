from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.courses.models import Course


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


def save_course(db: Session, course: Course) -> Course:
    db.add(course)
    db.commit()
    db.refresh(course)
    return course
