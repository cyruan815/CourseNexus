from __future__ import annotations

from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.core.logging import get_logger
from app.integrations.model_provider.base import ModelProvider
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.service import assert_course_owner
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generated_content.repository import (
    add_generated_content,
    add_generated_content_citations,
)
from app.modules.generation.orchestrator.contracts import GenerateContentRequest
from app.modules.generation.orchestrator.registry import GeneratorRegistry
from app.modules.material_context.schemas import ContextChunk
from app.modules.material_context.service import iter_material_context_batches


logger = get_logger("generation.content")


def _new_generated_content_id() -> str:
    return f"gen_{uuid4().hex}"


def _new_citation_id() -> str:
    return f"cit_{uuid4().hex}"


def _collect_object_ids(value: Any) -> set[str]:
    object_ids: set[str] = set()
    if isinstance(value, dict):
        item_id = value.get("id")
        if isinstance(item_id, str):
            object_ids.add(item_id)
        for child in value.values():
            object_ids.update(_collect_object_ids(child))
    elif isinstance(value, list):
        for child in value:
            object_ids.update(_collect_object_ids(child))
    return object_ids


def _bind_source_citation_ids(value: Any, bindings: dict[str, list[str]]) -> Any:
    if isinstance(value, dict):
        bound = {key: _bind_source_citation_ids(child, bindings) for key, child in value.items()}
        item_id = value.get("id")
        if isinstance(item_id, str) and item_id in bindings:
            bound["source_citation_ids"] = list(bindings[item_id])
        elif "source_citation_ids" in value:
            bound["source_citation_ids"] = []
        return bound
    if isinstance(value, list):
        return [_bind_source_citation_ids(child, bindings) for child in value]
    return value


def _prepare_citations(
    *,
    content_id: str,
    content_json: dict[str, Any],
    item_citation_chunk_ids: dict[str, list[str]],
    delivered_chunks: list[ContextChunk],
) -> tuple[dict[str, Any], list[SourceCitation]]:
    if not isinstance(content_json, dict):
        raise CourseNexusError(
            code="GENERATION_SCHEMA_INVALID",
            message="Generated content JSON must be an object",
        )

    chunk_by_id: dict[str, ContextChunk] = {}
    chunk_position: dict[str, int] = {}
    for chunk in delivered_chunks:
        if chunk.chunk_id not in chunk_by_id:
            chunk_position[chunk.chunk_id] = len(chunk_position)
            chunk_by_id[chunk.chunk_id] = chunk

    final_object_ids = _collect_object_ids(content_json)
    selected_chunk_ids_by_item: dict[str, list[str]] = {}
    for item_id, requested_chunk_ids in item_citation_chunk_ids.items():
        if item_id not in final_object_ids:
            continue
        seen_chunk_ids: set[str] = set()
        selected_chunk_ids: list[str] = []
        for chunk_id in requested_chunk_ids:
            if chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)
            if chunk_id in chunk_by_id:
                selected_chunk_ids.append(chunk_id)
        selected_chunk_ids_by_item[item_id] = selected_chunk_ids

    selected_chunk_ids = sorted(
        {chunk_id for chunk_ids in selected_chunk_ids_by_item.values() for chunk_id in chunk_ids},
        key=chunk_position.__getitem__,
    )
    citation_id_by_chunk_id = {chunk_id: _new_citation_id() for chunk_id in selected_chunk_ids}
    citation_ids_by_item = {
        item_id: [citation_id_by_chunk_id[chunk_id] for chunk_id in chunk_ids]
        for item_id, chunk_ids in selected_chunk_ids_by_item.items()
    }
    bound_content_json = _bind_source_citation_ids(content_json, citation_ids_by_item)
    if not isinstance(bound_content_json, dict):
        raise CourseNexusError(
            code="GENERATION_SCHEMA_INVALID",
            message="Generated content JSON must be an object",
        )

    citations = [
        SourceCitation(
            id=citation_id_by_chunk_id[chunk_id],
            generated_content_id=content_id,
            material_id=chunk_by_id[chunk_id].material_id,
            chunk_id=chunk_id,
            material_name=chunk_by_id[chunk_id].material_name,
            page=chunk_by_id[chunk_id].page,
            page_index=(
                0
                if chunk_by_id[chunk_id].page is None
                and chunk_by_id[chunk_id].page_index is None
                else chunk_by_id[chunk_id].page_index
            ),
            hit_text=chunk_by_id[chunk_id].content_text[:500],
            sort_order=sort_order,
        )
        for sort_order, chunk_id in enumerate(selected_chunk_ids, start=1)
    ]
    return bound_content_json, citations


def _persist_generated_content(
    db: Session,
    content: AIGeneratedContent,
    citations: list[SourceCitation],
) -> AIGeneratedContent:
    try:
        add_generated_content(db, content)
        add_generated_content_citations(db, citations)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(content)
    return content


def _persist_failed_content(db: Session, content: AIGeneratedContent) -> AIGeneratedContent:
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
    max_batch_tokens: int,
) -> AIGeneratedContent:
    started_at = perf_counter()
    assert_course_owner(db, user_id, course_id)
    generator = registry.create(payload.content_type, model_provider)
    content_id = _new_generated_content_id()
    material_scope_json = payload.material_scope.model_dump(mode="json")
    try:
        batches = tuple(
            iter_material_context_batches(
                db,
                user_id=user_id,
                course_id=course_id,
                material_scope=payload.material_scope,
                max_tokens=max_batch_tokens,
            )
        )
    except CourseNexusError as exc:
        if exc.code != "MATERIAL_COVERAGE_INCOMPLETE":
            raise
        content = _persist_failed_content(
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
        _log_generation_failure(
            content=content,
            course_id=course_id,
            error_code=exc.code,
            started_at=started_at,
            exc=exc,
        )
        return content
    if not batches:
        raise CourseNexusError(
            code="NO_PARSED_MATERIAL",
            message="No parsed material exists in the selected scope",
            status_code=400,
        )
    expected_material_ids = frozenset(
        material_id for batch in batches for material_id in batch.material_ids
    )

    try:
        output = generator.generate(
            batches=batches,
            expected_material_ids=expected_material_ids,
            parameters=payload.parameters,
        )
    except CourseNexusError as exc:
        if exc.code == "VALIDATION_ERROR":
            raise
        content = _persist_failed_content(
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
        _log_generation_failure(
            content=content,
            course_id=course_id,
            error_code=exc.code,
            started_at=started_at,
            exc=exc,
        )
        return content
    except Exception as exc:
        content = _persist_failed_content(
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
        _log_generation_failure(
            content=content,
            course_id=course_id,
            error_code="GENERATION_FAILED",
            started_at=started_at,
            exc=exc,
        )
        return content

    delivered_chunks = [chunk for batch in batches for chunk in batch.chunks]
    bound_content_json, citations = _prepare_citations(
        content_id=content_id,
        content_json=output.content_json,
        item_citation_chunk_ids=output.item_citation_chunk_ids,
        delivered_chunks=delivered_chunks,
    )
    content = _persist_generated_content(
        db,
        AIGeneratedContent(
            id=content_id,
            user_id=user_id,
            course_id=course_id,
            content_type=payload.content_type,
            title=output.title,
            content=output.content,
            content_json=bound_content_json,
            generation_status="success",
            material_scope_json=material_scope_json,
        ),
        citations,
    )
    logger.info(
        "内容生成成功 | content_type=%s content=%s course=%s citations=%d cost_ms=%.2f",
        payload.content_type,
        content.id,
        course_id,
        len(citations),
        (perf_counter() - started_at) * 1000,
    )
    return content


def _log_generation_failure(
    *,
    content: AIGeneratedContent,
    course_id: str,
    error_code: str,
    started_at: float,
    exc: BaseException,
) -> None:
    cause = exc.__cause__ or exc
    logger.error(
        "内容生成失败 | code=%s content_type=%s content=%s course=%s cost_ms=%.2f",
        error_code,
        content.content_type,
        content.id,
        course_id,
        (perf_counter() - started_at) * 1000,
        exc_info=(type(cause), cause, cause.__traceback__),
    )
