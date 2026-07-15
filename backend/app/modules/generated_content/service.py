from __future__ import annotations

from datetime import datetime, timezone

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.core.logging import get_logger
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.service import assert_course_owner
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generated_content.repository import (
    get_active_generated_content_for_user,
    list_active_generated_contents_for_course,
    list_generated_content_citations,
    permanently_delete_generated_content,
    save_generated_content,
)
from app.modules.generated_content.schemas import (
    FlashcardCardsUpdate,
    GeneratedContentCitationRead,
    GeneratedContentRead,
    GeneratedContentUpdate,
)
from app.modules.generation.generators.flashcard.schemas import FlashcardContent, FlashcardRead
from app.modules.generation.generators.knowledge_list.schemas import KnowledgeListContent


POC_GENERATION_TYPES = {"quiz", "flashcard", "mindmap", "outline", "knowledge_list"}
logger = get_logger("generated_content.flashcards")
knowledge_progress_logger = get_logger("generated_content.knowledge_progress")


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


def rename_generated_content(
    db: Session,
    *,
    user_id: str,
    generated_content_id: str,
    title: str,
) -> GeneratedContentRead:
    content = get_active_generated_content_for_user(db, user_id=user_id, generated_content_id=generated_content_id)
    if content is None:
        raise CourseNexusError(code="NOT_FOUND", message="生成内容不存在", status_code=404)
    content.title = GeneratedContentUpdate(title=title).title
    content.updated_at = datetime.now(timezone.utc)
    save_generated_content(db, content)
    return build_generated_content_read(db, content)


def delete_generated_content(
    db: Session,
    *,
    user_id: str,
    generated_content_id: str,
) -> GeneratedContentRead:
    content = get_active_generated_content_for_user(db, user_id=user_id, generated_content_id=generated_content_id)
    if content is None:
        raise CourseNexusError(code="NOT_FOUND", message="生成内容不存在", status_code=404)
    now = datetime.now(timezone.utc)
    deleted_snapshot = build_generated_content_read(db, content).model_copy(
        update={"deleted_at": now, "updated_at": now}
    )
    permanently_delete_generated_content(db, content)
    return deleted_snapshot


def update_flashcard_cards(
    db: Session,
    *,
    user_id: str,
    generated_content_id: str,
    cards: list[dict[str, object]],
) -> GeneratedContentRead:
    content = get_active_generated_content_for_user(db, user_id=user_id, generated_content_id=generated_content_id)
    if content is None:
        raise CourseNexusError(code="NOT_FOUND", message="生成内容不存在", status_code=404)
    if content.content_type != "flashcard":
        raise CourseNexusError(code="INVALID_GENERATED_CONTENT_TYPE", message="只有抽认卡内容可以编辑卡片", status_code=409)
    before_count = len(content.content_json.get("cards", [])) if isinstance(content.content_json, dict) else 0
    validated_cards = FlashcardCardsUpdate(cards=cards).cards
    normalized = FlashcardContent(cards=[
        FlashcardRead(
            id=f"card_{index:03d}",
            sort_order=index,
            mastery_status="unknown",
            **card.model_dump(mode="json"),
        )
        for index, card in enumerate(validated_cards, start=1)
    ])
    content.content_json = normalized.model_dump(mode="json")
    content.updated_at = datetime.now(timezone.utc)
    save_generated_content(db, content)
    logger.info(
        "Flashcard deck updated | content=%s user=%s before=%d after=%d",
        content.id,
        user_id,
        before_count,
        len(normalized.cards),
    )
    return build_generated_content_read(db, content)


def update_knowledge_item_learning_state(
    db: Session,
    *,
    user_id: str,
    generated_content_id: str,
    knowledge_item_id: str,
    learned: bool,
) -> GeneratedContentRead:
    content = get_active_generated_content_for_user(
        db,
        user_id=user_id,
        generated_content_id=generated_content_id,
    )
    if content is None:
        raise CourseNexusError(code="NOT_FOUND", message="生成内容不存在", status_code=404)
    if content.content_type != "knowledge_list":
        raise CourseNexusError(
            code="INVALID_GENERATED_CONTENT_TYPE",
            message="只有知识点清单可以更新学习状态",
            status_code=409,
        )
    if content.generation_status != "success":
        raise CourseNexusError(
            code="STATE_CONFLICT",
            message="只有生成成功的知识点清单可以更新学习状态",
            status_code=409,
        )
    try:
        knowledge_list = KnowledgeListContent.model_validate(content.content_json)
    except ValidationError as exc:
        raise CourseNexusError(
            code="GENERATED_CONTENT_SCHEMA_INVALID",
            message="知识点清单结构无效",
            status_code=409,
        ) from exc

    target = next((item for item in knowledge_list.items if item.id == knowledge_item_id), None)
    if target is None:
        raise CourseNexusError(code="NOT_FOUND", message="知识点不存在", status_code=404)
    target.learned = learned
    content.content_json = knowledge_list.model_dump(mode="json")
    content.updated_at = datetime.now(timezone.utc)
    save_generated_content(db, content)
    knowledge_progress_logger.info(
        "Knowledge item learning state updated | content=%s item=%s user=%s learned=%s",
        content.id,
        knowledge_item_id,
        user_id,
        learned,
    )
    return build_generated_content_read(db, content)
