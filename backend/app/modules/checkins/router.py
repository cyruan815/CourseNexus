from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.modules.checkins.schemas import CheckinRangeRead, CheckinRead
from app.modules.checkins.service import get_checkin_day, get_checkin_range
from app.modules.users.models import User
from app.shared.responses import success_response

router = APIRouter(tags=["checkins"])


@router.get("/checkins/{target_date}")
def get_checkin_day_endpoint(
    target_date: date,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    data = get_checkin_day(db, user_id=current_user.id, target_date=target_date)
    return success_response(CheckinRead.model_validate(data).model_dump(mode="json"), request_id=get_request_id(request))


@router.get("/checkins")
def get_checkin_range_endpoint(
    start_date: date,
    end_date: date,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    data = get_checkin_range(db, user_id=current_user.id, start_date=start_date, end_date=end_date)
    return success_response(CheckinRangeRead.model_validate(data).model_dump(mode="json"), request_id=get_request_id(request))