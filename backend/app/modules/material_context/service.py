from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.integrations.rag.base import RagIndex, RagScopeFilter
from app.modules.courses.service import assert_course_owner
from app.modules.material_context.repository import (
    has_parsed_context_chunks,
    list_active_scope_material_ids,
    list_context_chunks_by_ids,
    list_eligible_material_ids,
    list_parsed_context_chunks,
    list_parsed_context_chunks_for_scope,
)
from app.modules.material_context.schemas import (
    ContextChunk,
    MaterialContextBatch,
    MaterialContextResult,
    MaterialScope,
)
from app.modules.materials.models import MaterialChunk


@dataclass(frozen=True)
class _ResolvedScope:
    material_ids: tuple[str, ...]
    eligible_material_ids: tuple[str, ...]
    empty_selection: bool = False


def resolve_material_scope_ids(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_scope: MaterialScope | None,
) -> tuple[str, ...]:
    resolved_scope = _resolve_scope(db, user_id=user_id, course_id=course_id, material_scope=material_scope)
    if resolved_scope.empty_selection:
        return ()
    return resolved_scope.eligible_material_ids

def resolve_context(
    db: Session,
    user_id: str,
    course_id: str,
    material_scope: MaterialScope | None = None,
    limit: int = 20,
) -> MaterialContextResult:
    resolved_scope = _resolve_scope(db, user_id=user_id, course_id=course_id, material_scope=material_scope)
    if resolved_scope.empty_selection:
        return MaterialContextResult(chunks=[], no_parsed_material=True)

    rows = list_parsed_context_chunks(
        db,
        user_id=user_id,
        course_id=course_id,
        material_ids=list(resolved_scope.material_ids) or None,
        limit=limit,
    )
    chunks = [_to_context_chunk(chunk, material_name) for chunk, material_name in rows]
    return MaterialContextResult(chunks=chunks, no_parsed_material=len(chunks) == 0)


def retrieve_relevant_context(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    query: str,
    material_scope: MaterialScope | None,
    rag_index: RagIndex,
    top_k: int,
) -> MaterialContextResult:
    resolved_scope = _resolve_scope(db, user_id=user_id, course_id=course_id, material_scope=material_scope)
    if resolved_scope.empty_selection:
        return MaterialContextResult(chunks=[], no_parsed_material=True)

    material_ids = list(resolved_scope.material_ids) or None
    if not resolved_scope.eligible_material_ids or not has_parsed_context_chunks(
        db,
        user_id=user_id,
        course_id=course_id,
        material_ids=material_ids,
    ):
        return MaterialContextResult(chunks=[], no_parsed_material=True)

    hits = rag_index.retrieve(
        query=query,
        scope=_rag_scope_filter(user_id=user_id, course_id=course_id, resolved_scope=resolved_scope),
        top_k=top_k,
    )
    rows_by_chunk_id = {
        chunk.id: (chunk, material_name)
        for chunk, material_name in list_context_chunks_by_ids(
            db,
            user_id=user_id,
            course_id=course_id,
            chunk_ids=[hit.chunk_id for hit in hits],
            material_ids=material_ids,
        )
    }
    chunks = []
    for hit in hits:
        row = rows_by_chunk_id.get(hit.chunk_id)
        if row is None:
            continue
        chunk, material_name = row
        chunks.append(_to_context_chunk(chunk, material_name, score=hit.score))

    return MaterialContextResult(chunks=chunks, no_parsed_material=False)


def iter_material_context_batches(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_scope: MaterialScope | None,
    max_tokens: int,
) -> Iterator[MaterialContextBatch]:
    resolved_scope = _resolve_scope(db, user_id=user_id, course_id=course_id, material_scope=material_scope)
    if resolved_scope.empty_selection or not resolved_scope.eligible_material_ids:
        return

    rows = list_parsed_context_chunks_for_scope(
        db,
        user_id=user_id,
        course_id=course_id,
        material_ids=list(resolved_scope.material_ids) or None,
    )
    chunks = [_to_context_chunk(chunk, material_name) for chunk, material_name in rows]
    represented_material_ids = {chunk.material_id for chunk in chunks}
    if set(resolved_scope.eligible_material_ids) != represented_material_ids:
        raise CourseNexusError(
            code="MATERIAL_COVERAGE_INCOMPLETE",
            message="资料上下文覆盖不完整",
            status_code=409,
        )

    yield from _batch_context_chunks(chunks, max_tokens=max_tokens)


def _resolve_scope(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_scope: MaterialScope | None,
) -> _ResolvedScope:
    assert_course_owner(db, user_id, course_id)
    scope = material_scope or MaterialScope()

    if scope.include_all_parsed_materials:
        material_ids: tuple[str, ...] = ()
    else:
        material_ids = _unique_tuple(scope.material_ids)
        if not material_ids:
            return _ResolvedScope(material_ids=(), eligible_material_ids=(), empty_selection=True)

    active_material_ids = tuple(
        list_active_scope_material_ids(
            db,
            user_id=user_id,
            course_id=course_id,
            material_ids=list(material_ids) or None,
        )
    )
    if material_ids and not set(material_ids).issubset(active_material_ids):
        raise CourseNexusError(code="NOT_FOUND", message="资料不存在", status_code=404)

    eligible_material_ids = tuple(
        list_eligible_material_ids(
            db,
            user_id=user_id,
            course_id=course_id,
            material_ids=list(material_ids) or None,
        )
    )
    return _ResolvedScope(
        material_ids=material_ids,
        eligible_material_ids=eligible_material_ids,
    )


def _rag_scope_filter(*, user_id: str, course_id: str, resolved_scope: _ResolvedScope) -> RagScopeFilter:
    if resolved_scope.material_ids:
        return RagScopeFilter(
            user_id=user_id,
            course_id=course_id,
            material_ids=resolved_scope.eligible_material_ids,
        )
    return RagScopeFilter(user_id=user_id, course_id=course_id)


def _batch_context_chunks(chunks: list[ContextChunk], *, max_tokens: int) -> Iterator[MaterialContextBatch]:
    effective_max_tokens = max(1, max_tokens)
    current_chunks: list[ContextChunk] = []
    current_tokens = 0

    for chunk in chunks:
        chunk_tokens = _estimate_tokens(chunk.content_text)
        if current_chunks and current_tokens + chunk_tokens > effective_max_tokens:
            yield _make_batch(current_chunks, current_tokens)
            current_chunks = []
            current_tokens = 0

        current_chunks.append(chunk)
        current_tokens += chunk_tokens

    if current_chunks:
        yield _make_batch(current_chunks, current_tokens)


def _make_batch(chunks: list[ContextChunk], estimated_tokens: int) -> MaterialContextBatch:
    return MaterialContextBatch(
        chunks=chunks,
        material_ids=list(dict.fromkeys(chunk.material_id for chunk in chunks)),
        estimated_tokens=estimated_tokens,
    )


def _to_context_chunk(chunk: MaterialChunk, material_name: str, *, score: float | None = None) -> ContextChunk:
    return ContextChunk(
        material_id=chunk.material_id,
        chunk_id=chunk.id,
        chunk_index=chunk.chunk_index,
        material_name=material_name,
        page=chunk.page,
        page_index=chunk.page_index,
        heading=chunk.heading,
        content_text=chunk.content_text,
        score=score,
    )


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _unique_tuple(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))
