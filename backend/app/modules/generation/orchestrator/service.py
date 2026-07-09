from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.modules.course_qa.models import SourceCitation
from app.modules.course_qa.repository import save_citations
from app.modules.courses.service import assert_course_owner
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generated_content.repository import save_generated_content
from app.modules.generation.orchestrator.contracts import GenerateContentRequest, GeneratorOutput
from app.modules.generation.orchestrator.registry import GeneratorRegistry
from app.modules.material_context.schemas import ContextChunk
from app.modules.material_context.service import resolve_context


def _new_generated_content_id() -> str:
    return f"gen_{uuid4().hex}"


def _new_citation_id() -> str:
    return f"cit_{uuid4().hex}"


def generate_content(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: GenerateContentRequest,
    registry: GeneratorRegistry,
) -> AIGeneratedContent:
    assert_course_owner(db, user_id, course_id)
    generator = registry.get(payload.content_type)
    context = resolve_context(db, user_id, course_id, payload.material_scope)
    if context.no_parsed_material:
        raise CourseNexusError(code="NO_PARSED_MATERIAL", message="当前范围没有已解析资料", status_code=400)

    content_id = _new_generated_content_id()
    material_scope_json = payload.material_scope.model_dump(mode="json")
    try:
        output = generator.generate(context=context, parameters=payload.parameters)
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

    content = save_generated_content(
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
    citation_chunks = _select_citation_chunks(context.chunks, output)
    save_citations(db, _build_citations(content.id, citation_chunks))
    return content


def _select_citation_chunks(chunks: list[ContextChunk], output: GeneratorOutput) -> list[ContextChunk]:
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    selected = [chunk_by_id[chunk_id] for chunk_id in output.citation_chunk_ids if chunk_id in chunk_by_id]
    return selected or chunks[:1]


def _build_citations(generated_content_id: str, chunks: list[ContextChunk]) -> list[SourceCitation]:
    return [
        SourceCitation(
            id=_new_citation_id(),
            generated_content_id=generated_content_id,
            material_id=chunk.material_id,
            chunk_id=chunk.chunk_id,
            material_name=chunk.material_name,
            page=chunk.page,
            page_index=chunk.page_index if chunk.page_index is not None else 0,
            hit_text=chunk.content_text[:500],
            sort_order=index,
        )
        for index, chunk in enumerate(chunks)
    ]
