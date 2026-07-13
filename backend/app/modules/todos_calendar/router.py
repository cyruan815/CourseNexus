from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user
from app.core.business_time import today_shanghai
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.modules.todos_calendar.schemas import CalendarMonthRead, CourseCalendarMonthRead, CourseDayTodosRead, DayTodosRead, TodayTodosRead
from app.modules.todos_calendar.service import (
    get_course_day_todos,
    get_course_month_calendar,
    get_global_day_todos,
    get_global_month_calendar,
    get_today_todos,
)
from app.modules.users.models import User
from app.shared.responses import success_response

router = APIRouter(tags=["todos_calendar"])


@router.get("/todos/today")
def get_today_todos_endpoint(
    request: Request,
    query_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    selected_date = query_date or today_shanghai()
    data = get_today_todos(db, user_id=current_user.id, target_date=selected_date)
    return success_response(TodayTodosRead.model_validate(data).model_dump(mode="json"), request_id=get_request_id(request))


@router.get("/calendar/month")
def get_global_month_calendar_endpoint(
    month: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    data = get_global_month_calendar(db, user_id=current_user.id, month=month)
    return success_response(CalendarMonthRead.model_validate(data).model_dump(mode="json"), request_id=get_request_id(request))


@router.get("/calendar/days/{target_date}/todos")
def get_global_day_todos_endpoint(
    target_date: date,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    data = get_global_day_todos(db, user_id=current_user.id, target_date=target_date)
    return success_response(DayTodosRead.model_validate(data).model_dump(mode="json"), request_id=get_request_id(request))


@router.get("/courses/{course_id}/study-calendar")
def get_course_month_calendar_endpoint(
    course_id: str,
    month: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    data = get_course_month_calendar(db, user_id=current_user.id, course_id=course_id, month=month)
    return success_response(CourseCalendarMonthRead.model_validate(data).model_dump(mode="json"), request_id=get_request_id(request))


@router.get("/courses/{course_id}/study-calendar/days/{target_date}")
def get_course_day_todos_endpoint(
    course_id: str,
    target_date: date,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    data = get_course_day_todos(db, user_id=current_user.id, course_id=course_id, target_date=target_date)
    return success_response(CourseDayTodosRead.model_validate(data).model_dump(mode="json"), request_id=get_request_id(request))
