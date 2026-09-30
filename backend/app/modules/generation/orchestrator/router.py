from __future__ import annotations

from collections.abc import Callable
from typing import cast

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user
from app.core.config import MODEL_PURPOSES, ModelPurpose, get_settings
from app.core.errors import CourseNexusError
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.integrations.model_provider.base import ModelProvider
from app.integrations.model_provider.factory import create_model_provider
from app.modules.generated_content.service import build_generated_content_read
from app.modules.generation.orchestrator.contracts import GenerateContentRequest
from app.modules.generation.orchestrator.registry import GeneratorRegistry, default_generator_registry
from app.modules.generation.orchestrator.service import generate_content
from app.modules.users.models import User
from app.shared.responses import success_response

router = APIRouter(tags=["generation"])

GenerationModelProviderFactory = Callable[[str], ModelProvider]


def get_generator_registry() -> GeneratorRegistry:
    return default_generator_registry()


def get_generation_model_provider(content_type: str) -> ModelProvider:
    if content_type not in MODEL_PURPOSES:
        raise CourseNexusError(
            code="VALIDATION_ERROR",
            message="Generation model purpose is not configured",
            status_code=422,
            details={"content_type": content_type},
        )
    return create_model_provider(cast(ModelPurpose, content_type))


def get_generation_model_provider_factory() -> GenerationModelProviderFactory:
    return get_generation_model_provider


@router.post("/courses/{course_id}/generations")
def generate_content_endpoint(
    course_id: str,
    payload: GenerateContentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    registry: GeneratorRegistry = Depends(get_generator_registry),
    provider_factory: GenerationModelProviderFactory = Depends(get_generation_model_provider_factory),
) -> dict[str, object]:
    if payload.content_type not in registry.supported_content_types():
        raise CourseNexusError(
            code="VALIDATION_ERROR",
            message="Generation content type is not supported",
            status_code=422,
            details={"content_type": payload.content_type},
        )
    model_provider = provider_factory(payload.content_type)
    settings = get_settings()
    content = generate_content(
        db,
        user_id=current_user.id,
        course_id=course_id,
        payload=payload,
        registry=registry,
        model_provider=model_provider,
        max_context_tokens=settings.material_context_max_tokens,
    )
    data = build_generated_content_read(db, content).model_dump(mode="json")
    return success_response(data, request_id=get_request_id(request))
