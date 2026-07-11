from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user
from app.core.config import get_settings
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.integrations.model_provider.base import ModelProvider
from app.integrations.model_provider.mock import MockModelProvider
from app.integrations.model_provider.openai import OpenAIModelProvider
from app.modules.study_plans.repository import StudyPlanBundle
from app.modules.study_plans.schemas import (
    StudyPlanBuildRequest,
    StudyPlanBundleRead,
    StudyPlanConfigParseRequest,
    StudyPlanConfigParseResponse,
    StudyPlanRead,
    StudyPlanPreview,
    StudyPlanRegenerationPreviewRequest,
    StudyPlanReplaceRequest,
    StudyPlanSaveRequest,
    StudySubTaskRead,
    StudyTaskRead,
)
from app.modules.study_plans.service import (
    delete_study_plan,
    get_study_plan_detail,
    list_study_plans,
    parse_study_plan_config,
    preview_study_plan,
    preview_study_plan_regeneration,
    replace_study_plan,
    save_study_plan,
)
from app.modules.users.models import User
from app.shared.responses import success_response

router = APIRouter(tags=["study_plans"])


def get_model_provider() -> ModelProvider:
    settings = get_settings()
    endpoint = settings.model_endpoint("study_plan_parser")
    if endpoint.api_key:
        return OpenAIModelProvider(
            api_key=endpoint.api_key,
            model=endpoint.model,
            base_url=endpoint.base_url,
            api_key_env_name="STUDY_PLAN_PARSER_API_KEY",
        )
    return MockModelProvider()


def _bundle_data(bundle: StudyPlanBundle) -> dict[str, object]:
    data = StudyPlanBundleRead(
        plan=StudyPlanRead.model_validate(bundle.plan),
        tasks=[StudyTaskRead.model_validate(task) for task in bundle.tasks],
        subtasks=[StudySubTaskRead.model_validate(subtask) for subtask in bundle.subtasks],
    )
    return data.model_dump(mode="json")


@router.post("/courses/{course_id}/study-plan-config-parses")
def parse_study_plan_config_endpoint(
    course_id: str,
    payload: StudyPlanConfigParseRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    model_provider: ModelProvider = Depends(get_model_provider),
) -> dict[str, object]:
    parsed = parse_study_plan_config(
        db,
        user_id=current_user.id,
        course_id=course_id,
        payload=payload,
        model_provider=model_provider,
    )
    data = StudyPlanConfigParseResponse.model_validate(parsed.model_dump(mode="json")).model_dump(mode="json")
    return success_response(data, request_id=get_request_id(request))


@router.post("/courses/{course_id}/study-plans/preview")
def preview_study_plan_endpoint(
    course_id: str,
    payload: StudyPlanBuildRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    model_provider: ModelProvider = Depends(get_model_provider),
) -> dict[str, object]:
    settings = get_settings()
    preview = preview_study_plan(
        db,
        user_id=current_user.id,
        course_id=course_id,
        payload=payload,
        model_provider=model_provider,
        max_tokens=settings.material_batch_max_tokens,
    )
    return success_response(StudyPlanPreview.model_validate(preview).model_dump(mode="json"), request_id=get_request_id(request))


@router.post("/courses/{course_id}/study-plans")
def save_study_plan_endpoint(
    course_id: str,
    payload: StudyPlanSaveRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    model_provider: ModelProvider = Depends(get_model_provider),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, object]:
    settings = get_settings()
    bundle = save_study_plan(
        db,
        user_id=current_user.id,
        course_id=course_id,
        payload=payload,
        model_provider=model_provider,
        max_tokens=settings.material_batch_max_tokens,
        idempotency_key=idempotency_key,
    )
    return success_response(_bundle_data(bundle), request_id=get_request_id(request))


@router.post("/study-plans/{plan_id}/regeneration-previews")
def regenerate_study_plan_preview_endpoint(
    plan_id: str,
    payload: StudyPlanRegenerationPreviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    model_provider: ModelProvider = Depends(get_model_provider),
) -> dict[str, object]:
    settings = get_settings()
    preview = preview_study_plan_regeneration(
        db,
        user_id=current_user.id,
        plan_id=plan_id,
        payload=payload,
        model_provider=model_provider,
        max_tokens=settings.material_batch_max_tokens,
    )
    data = StudyPlanPreview.model_validate(preview).model_dump(mode="json")
    return success_response(data, request_id=get_request_id(request))


@router.put("/study-plans/{plan_id}")
def replace_study_plan_endpoint(
    plan_id: str,
    payload: StudyPlanReplaceRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    bundle = replace_study_plan(db, user_id=current_user.id, plan_id=plan_id, payload=payload)
    return success_response(_bundle_data(bundle), request_id=get_request_id(request))


@router.delete("/study-plans/{plan_id}")
def delete_study_plan_endpoint(
    plan_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    plan = delete_study_plan(db, user_id=current_user.id, plan_id=plan_id)
    data = StudyPlanRead.model_validate(plan).model_dump(mode="json")
    return success_response(data, request_id=get_request_id(request))


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