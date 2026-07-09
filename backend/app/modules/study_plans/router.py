from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.modules.study_plans.repository import StudyPlanBundle
from app.modules.study_plans.schemas import (
    StudyPlanBuildRequest,
    StudyPlanBundleRead,
    StudyPlanRead,
    StudyPlanPreview,
    StudySubTaskRead,
    StudyTaskRead,
)
from app.modules.study_plans.service import (
    get_study_plan_detail,
    list_study_plans,
    preview_study_plan,
    save_study_plan,
)
from app.modules.users.models import User
from app.shared.responses import success_response

router = APIRouter(tags=["study_plans"])


def _bundle_data(bundle: StudyPlanBundle) -> dict[str, object]:
    data = StudyPlanBundleRead(
        plan=StudyPlanRead.model_validate(bundle.plan),
        tasks=[StudyTaskRead.model_validate(task) for task in bundle.tasks],
        subtasks=[StudySubTaskRead.model_validate(subtask) for subtask in bundle.subtasks],
    )
    return data.model_dump(mode="json")


@router.post("/courses/{course_id}/study-plans/preview")
def preview_study_plan_endpoint(
    course_id: str,
    payload: StudyPlanBuildRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    preview = preview_study_plan(db, user_id=current_user.id, course_id=course_id, payload=payload)
    return success_response(StudyPlanPreview.model_validate(preview).model_dump(mode="json"), request_id=get_request_id(request))


@router.post("/courses/{course_id}/study-plans")
def save_study_plan_endpoint(
    course_id: str,
    payload: StudyPlanBuildRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    bundle = save_study_plan(db, user_id=current_user.id, course_id=course_id, payload=payload)
    return success_response(_bundle_data(bundle), request_id=get_request_id(request))


@router.get("/courses/{course_id}/study-plans")
def list_study_plans_endpoint(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    plans = list_study_plans(db, user_id=current_user.id, course_id=course_id)
    data = [StudyPlanRead.model_validate(plan).model_dump(mode="json") for plan in plans]
    return success_response(data, request_id=get_request_id(request))


@router.get("/study-plans/{plan_id}")
def get_study_plan_endpoint(
    plan_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    bundle = get_study_plan_detail(db, user_id=current_user.id, plan_id=plan_id)
    return success_response(_bundle_data(bundle), request_id=get_request_id(request))
