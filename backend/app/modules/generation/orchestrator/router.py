from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_required_user
from app.core.request_id import get_request_id
from app.db.session import get_db
from app.modules.generated_content.schemas import GeneratedContentRead
from app.modules.generation.orchestrator.contracts import GenerateContentRequest
from app.modules.generation.orchestrator.registry import GeneratorRegistry, default_generator_registry
from app.modules.generation.orchestrator.service import generate_content
from app.modules.users.models import User
from app.shared.responses import success_response

router = APIRouter(tags=["generation"])


def get_generator_registry() -> GeneratorRegistry:
    return default_generator_registry()


@router.post("/courses/{course_id}/generations")
def generate_content_endpoint(
    course_id: str,
    payload: GenerateContentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_required_user),
    registry: GeneratorRegistry = Depends(get_generator_registry),
) -> dict[str, object]:
    content = generate_content(
        db,
        user_id=current_user.id,
        course_id=course_id,
        payload=payload,
        registry=registry,
    )
    data = GeneratedContentRead.model_validate(content).model_dump(mode="json")
    return success_response(data, request_id=get_request_id(request))
