from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.courses.service import assert_course_owner
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generated_content.repository import save_generated_content
from app.modules.generation.orchestrator.contracts import GenerateContentRequest
from app.modules.generation.orchestrator.registry import GeneratorRegistry
from app.modules.material_context.service import iter_material_context_batches


def _new_generated_content_id() -> str:
    return f"gen_{uuid4().hex}"


def generate_content(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: GenerateContentRequest,
    registry: GeneratorRegistry,
    model_provider: ModelProvider,
    max_batch_tokens: int,
) -> AIGeneratedContent:
    assert_course_owner(db, user_id, course_id)
    generator = registry.create(payload.content_type, model_provider)
    batches = tuple(
        iter_material_context_batches(
            db,
            user_id=user_id,
            course_id=course_id,
            material_scope=payload.material_scope,
            max_tokens=max_batch_tokens,
        )
    )
    if not batches:
        raise CourseNexusError(
            code="NO_PARSED_MATERIAL",
            message="No parsed material exists in the selected scope",
            status_code=400,
        )
    expected_material_ids = frozenset(
        material_id for batch in batches for material_id in batch.material_ids
    )

    content_id = _new_generated_content_id()
    material_scope_json = payload.material_scope.model_dump(mode="json")
    try:
        output = generator.generate(
            batches=batches,
            expected_material_ids=expected_material_ids,
            parameters=payload.parameters,
        )
    except CourseNexusError as exc:
        return save_generated_content(
            db,
            AIGeneratedContent(
                id=content_id,
                user_id=user_id,
                course_id=course_id,
                content_type=payload.content_type,
                title=payload.content_type.replace("_", " ").title(),
                generation_status="failed",
                material_scope_json=material_scope_json,
                error_code=exc.code,
            ),
        )
    except Exception:
        return save_generated_content(
            db,
            AIGeneratedContent(
                id=content_id,
                user_id=user_id,
                course_id=course_id,
                content_type=payload.content_type,
                title=payload.content_type.replace("_", " ").title(),
                generation_status="failed",
                material_scope_json=material_scope_json,
                error_code="GENERATION_FAILED",
            ),
        )

    return save_generated_content(
        db,
        AIGeneratedContent(
            id=content_id,
            user_id=user_id,
            course_id=course_id,
            content_type=payload.content_type,
            title=output.title,
            content=output.content,
            content_json=output.content_json,
            generation_status="success",
            material_scope_json=material_scope_json,
        ),
    )
