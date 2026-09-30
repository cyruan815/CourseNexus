from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.core.logging import get_logger
from app.integrations.model_provider.base import ModelProvider
from app.modules.courses.service import assert_course_owner
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generated_content.repository import add_generated_content
from app.modules.generation.orchestrator.contracts import GenerateContentRequest
from app.modules.generation.orchestrator.registry import GeneratorRegistry
from app.modules.material_context.schemas import build_material_scope_snapshot
from app.modules.material_context.service import resolve_generation_context


logger = get_logger("generation.content")


def _new_generated_content_id() -> str:
    return f"gen_{uuid4().hex}"


def _persist_content(db: Session, content: AIGeneratedContent) -> AIGeneratedContent:
    try:
        add_generated_content(db, content)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(content)
    return content


def generate_content(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: GenerateContentRequest,
    registry: GeneratorRegistry,
    model_provider: ModelProvider,
    max_context_tokens: int,
) -> AIGeneratedContent:
    started_at = perf_counter()
    assert_course_owner(db, user_id, course_id)
    generator = registry.create(payload.content_type, model_provider)
    context = resolve_generation_context(
        db,
        user_id=user_id,
        course_id=course_id,
        material_scope=payload.material_scope,
        max_tokens=max_context_tokens,
    )
    if context is None:
        raise CourseNexusError(
            code="NO_PARSED_MATERIAL",
            message="No parsed material exists in the selected scope",
            status_code=400,
        )
    material_scope_json = build_material_scope_snapshot(payload.material_scope, context.chunks)

    content_id = _new_generated_content_id()
    try:
        output = generator.generate(context=context, parameters=payload.parameters)
    except CourseNexusError as exc:
        if exc.code == "VALIDATION_ERROR":
            raise
        content = _persist_content(
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
        _log_generation_failure(content, course_id, started_at, exc)
        return content
    except Exception as exc:
        content = _persist_content(
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
        _log_generation_failure(content, course_id, started_at, exc)
        return content

    content = _persist_content(
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
    logger.info(
        "Content generated | content_type=%s content=%s course=%s cost_ms=%.2f",
        payload.content_type,
        content.id,
        course_id,
        (perf_counter() - started_at) * 1000,
    )
    return content


def _log_generation_failure(
    content: AIGeneratedContent,
    course_id: str,
    started_at: float,
    exc: BaseException,
) -> None:
    cause = exc.__cause__ or exc
    logger.error(
        "Content generation failed | code=%s content_type=%s content=%s course=%s cost_ms=%.2f",
        content.error_code,
        content.content_type,
        content.id,
        course_id,
        (perf_counter() - started_at) * 1000,
        exc_info=(type(cause), cause, cause.__traceback__),
    )
