from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.service import assert_course_owner
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generated_content.repository import (
    get_active_generated_content_for_user,
    list_active_generated_contents_for_course,
    list_generated_content_citations,
)
from app.modules.generated_content.schemas import GeneratedContentCitationRead, GeneratedContentRead


POC_GENERATION_TYPES = {"quiz", "flashcard", "mindmap", "outline", "knowledge_list"}


def _assemble_generated_content_reads(
    contents: list[AIGeneratedContent],
    citations: list[SourceCitation],
) -> list[GeneratedContentRead]:
    citations_by_content_id: dict[str, list[GeneratedContentCitationRead]] = {
        content.id: [] for content in contents
    }
    for citation in citations:
        generated_content_id = citation.generated_content_id
        if generated_content_id is not None and generated_content_id in citations_by_content_id:
            citations_by_content_id[generated_content_id].append(
                GeneratedContentCitationRead.model_validate(citation)
            )
    return [
        GeneratedContentRead.model_validate(content).model_copy(
            update={"source_citations": citations_by_content_id[content.id]}
        )
        for content in contents
    ]


def build_generated_content_read(db: Session, content: AIGeneratedContent) -> GeneratedContentRead:
    citations = (
        []
        if content.content_type in POC_GENERATION_TYPES
        else list_generated_content_citations(db, [content.id])
    )
    return _assemble_generated_content_reads([content], citations)[0]


def list_generated_contents(db: Session, *, user_id: str, course_id: str) -> list[GeneratedContentRead]:
    assert_course_owner(db, user_id, course_id)
    contents = list_active_generated_contents_for_course(db, user_id=user_id, course_id=course_id)
    citation_content_ids = [
        content.id for content in contents if content.content_type not in POC_GENERATION_TYPES
    ]
    citations = list_generated_content_citations(db, citation_content_ids)
    return _assemble_generated_content_reads(contents, citations)


def get_generated_content_detail(
    db: Session,
    *,
    user_id: str,
    generated_content_id: str,
) -> GeneratedContentRead:
    content = get_active_generated_content_for_user(db, user_id=user_id, generated_content_id=generated_content_id)
    if content is None:
        raise CourseNexusError(code="NOT_FOUND", message="生成内容不存在", status_code=404)
    return build_generated_content_read(db, content)
