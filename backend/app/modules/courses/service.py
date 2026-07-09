from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.modules.courses.models import Course
from app.modules.courses.repository import get_active_course_for_user, list_active_courses_for_user, save_course
from app.modules.courses.schemas import CourseCreate, CourseUpdate


def _new_course_id() -> str:
    return f"crs_{uuid4().hex}"


def assert_course_owner(db: Session, user_id: str, course_id: str) -> Course:
    course = get_active_course_for_user(db, user_id, course_id)
    if course is None:
        raise CourseNexusError(code="NOT_FOUND", message="课程不存在", status_code=404)
    return course


def create_course(db: Session, user_id: str, payload: CourseCreate) -> Course:
    course = Course(
        id=_new_course_id(),
        user_id=user_id,
        name=payload.name,
        description=payload.description,
        teacher=payload.teacher,
        term=payload.term,
        status="active",
    )
    return save_course(db, course)


def list_courses(db: Session, user_id: str) -> list[Course]:
    return list_active_courses_for_user(db, user_id)


def get_course_detail(db: Session, user_id: str, course_id: str) -> Course:
    return assert_course_owner(db, user_id, course_id)


def update_course(db: Session, user_id: str, course_id: str, payload: CourseUpdate) -> Course:
    course = assert_course_owner(db, user_id, course_id)
    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(course, field_name, value)
    course.updated_at = datetime.now(timezone.utc)
    return save_course(db, course)


def delete_course(db: Session, user_id: str, course_id: str) -> Course:
    course = assert_course_owner(db, user_id, course_id)
    now = datetime.now(timezone.utc)
    course.status = "deleted"
    course.deleted_at = now
    course.updated_at = now
    return save_course(db, course)
