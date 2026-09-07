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
    StudyPlanDiagnosticProfileRequest,
    StudyPlanDiagnosticProfileResponse,
    StudyPlanDiagnosticQuestionRequest,
    StudyPlanDiagnosticQuestionsResponse,
    StudyPlanRead,
    StudyPlanPreview,
    StudyPlanRegenerationPreviewRequest,
    StudyPlanReplaceRequest,
    StudyPlanSaveRequest,
    StudySubTaskRead,
    StudyTaskRead,
)
from app.modules.study_plans.service import (
    build_study_plan_diagnostic_profile,
    build_study_plan_diagnostic_questions,
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


def _model_provider_for_purpose(
    *, purpose: str, api_key_env_name: str, api_style: str = "auto"
) -> ModelProvider:
    settings = get_settings()
    endpoint = settings.model_endpoint(purpose)
    if endpoint.api_key:
        return OpenAIModelProvider(
            api_key=endpoint.api_key,
            model=endpoint.model,
            base_url=endpoint.base_url,
            api_key_env_name=api_key_env_name,
            api_style=api_style,
        )
    return MockModelProvider()


def get_plan_parser_provider() -> ModelProvider:
    return _model_provider_for_purpose(
        purpose="study_plan_parser",
        api_key_env_name="STUDY_PLAN_PARSER_API_KEY",
    )


def get_plan_generator_provider() -> ModelProvider:
    return _model_provider_for_purpose(
        purpose="study_plan_generator",
        api_key_env_name="STUDY_PLAN_GENERATOR_API_KEY",
        api_style=get_settings().study_plan_generator_api_style,
    )


def get_plan_map_provider(
    model_provider: ModelProvider = Depends(get_plan_generator_provider),
) -> ModelProvider:
    settings = get_settings()
    if (
        not any(
            (
                settings.study_plan_map_api_key,
                settings.study_plan_map_base_url,
                settings.study_plan_map_model,
            )
        )
        and settings.study_plan_map_api_style == "auto"
    ):
        return model_provider

    generator_endpoint = settings.model_endpoint("study_plan_generator")
    api_key = settings.study_plan_map_api_key or generator_endpoint.api_key
    if not api_key:
        return MockModelProvider()
    return OpenAIModelProvider(
        api_key=api_key,
        model=settings.study_plan_map_model or generator_endpoint.model,
        base_url=settings.study_plan_map_base_url or generator_endpoint.base_url,
        api_key_env_name="STUDY_PLAN_MAP_API_KEY",
        api_style=settings.study_plan_map_api_style,
    )


def get_plan_diagnostic_provider() -> ModelProvider:
    return _model_provider_for_purpose(
        purpose="study_plan_diagnostic",
        api_key_env_name="STUDY_PLAN_DIAGNOSTIC_API_KEY",
    )


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
    model_provider: ModelProvider = Depends(get_plan_parser_provider),
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



@router.post("/courses/{course_id}/study-plan-diagnostic-questions")
def study_plan_diagnostic_questions_endpoint(
    course_id: str,
    payload: StudyPlanDiagnosticQuestionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    model_provider: ModelProvider = Depends(get_plan_diagnostic_provider),
) -> dict[str, object]:
    settings = get_settings()
    questions = build_study_plan_diagnostic_questions(
        db,
        user_id=current_user.id,
        course_id=course_id,
        payload=payload,
        model_provider=model_provider,
        max_tokens=settings.material_batch_max_tokens,
    )
    data = StudyPlanDiagnosticQuestionsResponse.model_validate(questions).model_dump(mode="json")
    return success_response(data, request_id=get_request_id(request))


@router.post("/courses/{course_id}/study-plan-diagnostic-profiles")
def study_plan_diagnostic_profiles_endpoint(
    course_id: str,
    payload: StudyPlanDiagnosticProfileRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
) -> dict[str, object]:
    settings = get_settings()
    profile = build_study_plan_diagnostic_profile(
        db,
        user_id=current_user.id,
        course_id=course_id,
        payload=payload,
        max_tokens=settings.material_batch_max_tokens,
    )
    data = StudyPlanDiagnosticProfileResponse.model_validate(profile).model_dump(mode="json")
    return success_response(data, request_id=get_request_id(request))


@router.post("/courses/{course_id}/study-plans/preview")
def preview_study_plan_endpoint(
    course_id: str,
    payload: StudyPlanBuildRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    model_provider: ModelProvider = Depends(get_plan_generator_provider),
    map_model_provider: ModelProvider = Depends(get_plan_map_provider),
) -> dict[str, object]:
    settings = get_settings()
    preview = preview_study_plan(
        db,
        user_id=current_user.id,
        course_id=course_id,
        payload=payload,
        model_provider=model_provider,
        map_model_provider=map_model_provider,
        max_tokens=settings.material_batch_max_tokens,
        map_concurrency=settings.study_plan_map_concurrency,
    )
    return success_response(StudyPlanPreview.model_validate(preview).model_dump(mode="json"), request_id=get_request_id(request))


@router.post("/courses/{course_id}/study-plans")
def save_study_plan_endpoint(
    course_id: str,
    payload: StudyPlanSaveRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    model_provider: ModelProvider = Depends(get_plan_generator_provider),
    map_model_provider: ModelProvider = Depends(get_plan_map_provider),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, object]:
    settings = get_settings()
    bundle = save_study_plan(
        db,
        user_id=current_user.id,
        course_id=course_id,
        payload=payload,
        model_provider=model_provider,
        map_model_provider=map_model_provider,
        max_tokens=settings.material_batch_max_tokens,
        idempotency_key=idempotency_key,
        map_concurrency=settings.study_plan_map_concurrency,
    )
    return success_response(_bundle_data(bundle), request_id=get_request_id(request))


@router.post("/study-plans/{plan_id}/regeneration-previews")
def regenerate_study_plan_preview_endpoint(
    plan_id: str,
    payload: StudyPlanRegenerationPreviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    model_provider: ModelProvider = Depends(get_plan_generator_provider),
    map_model_provider: ModelProvider = Depends(get_plan_map_provider),
) -> dict[str, object]:
    settings = get_settings()
    preview = preview_study_plan_regeneration(
        db,
        user_id=current_user.id,
        plan_id=plan_id,
        payload=payload,
        model_provider=model_provider,
        map_model_provider=map_model_provider,
        max_tokens=settings.material_batch_max_tokens,
        map_concurrency=settings.study_plan_map_concurrency,
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
