from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user
from app.core.business_time import today_shanghai
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.modules.courses.schemas import CourseCreate, CourseListItemRead, CourseRead, CourseTermOptionRead, CourseUpdate
from app.modules.courses.service import create_course, delete_course, get_course_detail, list_course_list_items, update_course
from app.modules.courses.terms import COURSE_TERM_OPTIONS
from app.modules.users.models import User
from app.shared.responses import success_response

router = APIRouter(prefix="/courses", tags=["courses"])
term_router = APIRouter(prefix="/course-terms", tags=["courses"])


@term_router.get("")
def list_course_term_options_endpoint(
    request: Request,
    _current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    data = [
        CourseTermOptionRead(value=value, label=label).model_dump(mode="json")
        for value, label in COURSE_TERM_OPTIONS
    ]
    return success_response(data, request_id=get_request_id(request))


@router.get("")
def list_course_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    course_items = list_course_list_items(db, user_id=current_user.id, target_date=today_shanghai())
    data = [
        CourseListItemRead(
            **CourseRead.model_validate(item.course).model_dump(),
            material_count=item.material_count,
            today_task_status=item.today_task_status,
        ).model_dump(mode="json")
        for item in course_items
    ]
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
