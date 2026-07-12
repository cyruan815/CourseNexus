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
    list_parsed_material_quality_for_scope,
)
from app.modules.material_context.schemas import (
    ContextChunk,
    MaterialContextBatch,
    MaterialContextResult,
    MaterialScope,
    MaterialQualitySummary,
    MaterialQualityWarning,
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


def summarize_material_quality_for_scope(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_scope: MaterialScope | None,
) -> MaterialQualitySummary:
    resolved_scope = _resolve_scope(db, user_id=user_id, course_id=course_id, material_scope=material_scope)
    if resolved_scope.empty_selection or not resolved_scope.eligible_material_ids:
        return MaterialQualitySummary()

    rows = list_parsed_material_quality_for_scope(
        db,
        user_id=user_id,
        course_id=course_id,
        material_ids=list(resolved_scope.eligible_material_ids),
    )
    warnings: list[MaterialQualityWarning] = []
    for material_id, material_name, parse_quality, diagnostics, page_count in rows:
        warnings.extend(
            _warnings_for_material_quality(
                material_id=material_id,
                material_name=material_name,
                parse_quality=parse_quality,
                diagnostics=diagnostics,
                page_count=page_count,
            )
        )
    return MaterialQualitySummary(warnings=warnings)


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


def _warnings_for_material_quality(
    *,
    material_id: str,
    material_name: str,
    parse_quality: str,
    diagnostics: dict | list | None,
    page_count: int | None,
) -> list[MaterialQualityWarning]:
    diagnostics_data = diagnostics if isinstance(diagnostics, dict) else {}
    warnings: list[MaterialQualityWarning] = []
    details = _material_quality_details(diagnostics_data, page_count=page_count)
    if parse_quality == "partial":
        warnings.append(
            MaterialQualityWarning(
                code="MATERIAL_PARSE_PARTIAL",
                message="资料解析不完整，学习计划可能遗漏部分页面或内容",
                material_id=material_id,
                material_name=material_name,
                parse_quality=parse_quality,
                details=details,
            )
        )
    elif parse_quality == "unknown":
        warnings.append(
            MaterialQualityWarning(
                code="MATERIAL_PARSE_QUALITY_UNKNOWN",
                message="资料解析质量未知，建议确认资料内容是否完整",
                material_id=material_id,
                material_name=material_name,
                parse_quality=parse_quality,
                details=details,
            )
        )

    warnings.extend(
        _diagnostic_warning_entries(
            material_id=material_id,
            material_name=material_name,
            parse_quality=parse_quality,
            diagnostics=diagnostics_data,
        )
    )
    return warnings


def _material_quality_details(diagnostics: dict[str, object], *, page_count: int | None) -> dict[str, object]:
    details: dict[str, object] = {}
    effective_page_count = page_count if page_count is not None else _optional_int(diagnostics.get("page_count"))
    if effective_page_count is not None:
        details["page_count"] = effective_page_count
    for key in ("parser", "profile", "conversion_status"):
        value = _optional_str(diagnostics.get(key))
        if value is not None:
            details[key] = value
    for key in ("processed_pages", "pages_with_content", "pages_with_chunks", "failed_pages"):
        pages = _int_list(diagnostics.get(key))
        if pages:
            details[key] = pages
    return details


def _diagnostic_warning_entries(
    *,
    material_id: str,
    material_name: str,
    parse_quality: str,
    diagnostics: dict[str, object],
) -> list[MaterialQualityWarning]:
    raw_warnings = diagnostics.get("warnings")
    if not isinstance(raw_warnings, list):
        return []

    parser = _optional_str(diagnostics.get("parser"))
    profile = _optional_str(diagnostics.get("profile"))
    warnings: list[MaterialQualityWarning] = []
    for raw_warning in raw_warnings:
        if not isinstance(raw_warning, dict):
            continue
        severity = _optional_str(raw_warning.get("severity")) or "warning"
        if severity != "warning":
            continue
        diagnostic_code = _optional_str(raw_warning.get("code")) or "UNKNOWN_PARSE_WARNING"
        diagnostic_message = _optional_str(raw_warning.get("message")) or "资料解析诊断 warning"
        details: dict[str, object] = {
            "diagnostic_code": diagnostic_code,
            "diagnostic_message": diagnostic_message,
            "severity": severity,
        }
        if parser is not None:
            details["parser"] = parser
        if profile is not None:
            details["profile"] = profile
        warnings.append(
            MaterialQualityWarning(
                code="MATERIAL_PARSE_DIAGNOSTIC_WARNING",
                message=diagnostic_message,
                material_id=material_id,
                material_name=material_name,
                parse_quality=parse_quality,
                page_no=_optional_int(raw_warning.get("page_no")),
                component=_optional_str(raw_warning.get("component")),
                details=details,
            )
        )
    return warnings


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _int_list(value: object) -> list[int]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, int) and not isinstance(item, bool)]
