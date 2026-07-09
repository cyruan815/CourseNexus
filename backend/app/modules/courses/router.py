from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.modules.courses.schemas import CourseCreate, CourseRead, CourseUpdate
from app.modules.courses.service import create_course, delete_course, get_course_detail, list_courses, update_course
from app.modules.users.models import User
from app.shared.responses import success_response

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("")
def list_course_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    courses = list_courses(db, current_user.id)
    data = [CourseRead.model_validate(course).model_dump(mode="json") for course in courses]
    return success_response(data, request_id=get_request_id(request))


@router.post("")
def create_course_endpoint(
    payload: CourseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    course = create_course(db, current_user.id, payload)
    data = CourseRead.model_validate(course).model_dump(mode="json")
    return success_response(data, request_id=get_request_id(request))


@router.get("/{course_id}")
def get_course_endpoint(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    course = get_course_detail(db, current_user.id, course_id)
    data = CourseRead.model_validate(course).model_dump(mode="json")
    return success_response(data, request_id=get_request_id(request))


@router.patch("/{course_id}")
def update_course_endpoint(
    course_id: str,
    payload: CourseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    course = update_course(db, current_user.id, course_id, payload)
    data = CourseRead.model_validate(course).model_dump(mode="json")
    return success_response(data, request_id=get_request_id(request))


@router.delete("/{course_id}")
def delete_course_endpoint(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    course = delete_course(db, current_user.id, course_id)
    data = CourseRead.model_validate(course).model_dump(mode="json")
    return success_response(data, request_id=get_request_id(request))
