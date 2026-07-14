from __future__ import annotations

import re
from datetime import datetime, timezone
from time import perf_counter, time_ns
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.core.logging import get_logger
from app.integrations.model_provider.base import ModelProvider
from app.integrations.rag.base import RagIndex
from app.modules.course_qa.models import Conversation, Message, SourceCitation
from app.modules.course_qa.repository import (
    get_active_conversation_by_id_for_user,
    get_active_conversation_for_user,
    list_active_conversations_for_course,
    list_citations_for_messages,
    list_messages_for_conversation,
    save_citations,
    save_conversation,
    save_message,
)
from app.modules.course_qa.schemas import CourseAnswerRead, CourseQuestionCreate, MessageRead, SourceCitationRead
from app.modules.courses.service import assert_course_owner
from app.modules.material_context.schemas import ContextChunk
from app.modules.material_context.service import retrieve_relevant_context


logger = get_logger("course_qa.answer")

_INLINE_CITATION_PATTERN = re.compile(r"\[\[cite:[^\]]+\]\]")


def _new_conversation_id() -> str:
    return f"cnv_{uuid4().hex}"


def _new_message_id() -> str:
    return f"msg_{time_ns()}_{uuid4().hex}"


def _new_citation_id() -> str:
    return f"cit_{uuid4().hex}"


def ask_course_question(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: CourseQuestionCreate,
    model_provider: ModelProvider,
    rag_index: RagIndex,
    top_k: int = 8,
    allowed_conversation_source_pages: set[str] | None = None,
    material_scope_metadata: dict[str, object] | None = None,
    model_question_context: str | None = None,
) -> CourseAnswerRead:
    started_at = perf_counter()
    assert_course_owner(db, user_id, course_id)
    conversation = _get_or_create_conversation(
        db,
        user_id=user_id,
        course_id=course_id,
        payload=payload,
        allowed_source_pages=allowed_conversation_source_pages,
    )
    material_scope_json = _message_material_scope_json(
        payload,
        material_scope_metadata=material_scope_metadata,
        used_material_ids=[],
    )
    user_message = save_message(
        db,
        Message(
            id=_new_message_id(),
            conversation_id=conversation.id,
            course_id=course_id,
            role="user",
            content=payload.question,
            material_scope_json=material_scope_json,
            created_at=datetime.now(timezone.utc),
        ),
    )
    context = retrieve_relevant_context(
        db,
        user_id=user_id,
        course_id=course_id,
        query=payload.question,
        material_scope=payload.material_scope,
        rag_index=rag_index,
        top_k=top_k,
    )
    used_material_ids = _used_material_ids(context.chunks)
    material_scope_json = _message_material_scope_json(
        payload,
        material_scope_metadata=material_scope_metadata,
        used_material_ids=used_material_ids,
    )
    user_message.material_scope_json = material_scope_json
    user_message = save_message(db, user_message)

    if context.no_parsed_material or not context.chunks:
        answer_text = (
            "当前资料范围内没有已解析资料，无法基于课程资料回答。"
            if context.no_parsed_material
            else "当前资料范围内没有检索到相关内容，无法基于课程资料回答。"
        )
        assistant_message = save_message(
            db,
            Message(
                id=_new_message_id(),
                conversation_id=conversation.id,
                course_id=course_id,
                role="assistant",
                content=answer_text,
                answer_type="no_source",
                generation_status="success",
                material_scope_json=material_scope_json,
                created_at=datetime.now(timezone.utc),
            ),
        )
        _touch_conversation(db, conversation)
        logger.info(
            "问答结束：没有可用资料 | course=%s conversation=%s reason=%s cost_ms=%.2f",
            course_id,
            conversation.id,
            "no_parsed_material" if context.no_parsed_material else "no_retrieval_hits",
            (perf_counter() - started_at) * 1000,
        )
        return CourseAnswerRead(
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            answer_text=assistant_message.content,
            answer_type="no_source",
            source_citations=[],
            used_material_ids=used_material_ids,
        )

    try:
        model_answer = model_provider.answer_question(
            question=_model_question(payload.question, model_question_context),
            context_chunks=context.chunks,
        )
    except CourseNexusError as exc:
        assistant_message = save_message(
            db,
            Message(
                id=_new_message_id(),
                conversation_id=conversation.id,
                course_id=course_id,
                role="assistant",
                content="模型调用失败",
                answer_type="no_source",
                generation_status="failed",
                error_code="GENERATION_FAILED",
                material_scope_json=material_scope_json,
                created_at=datetime.now(timezone.utc),
            ),
        )
        _touch_conversation(db, conversation)
        logger.error(
            "问答失败：模型调用失败 | code=%s course=%s conversation=%s cost_ms=%.2f",
            exc.code,
            course_id,
            conversation.id,
            (perf_counter() - started_at) * 1000,
        )
        raise

    selected_chunks = _select_citation_chunks(context.chunks, model_answer.citation_chunk_ids)
    answer_text = _normalize_inline_citations(model_answer.answer_text, selected_chunks)
    assistant_message = save_message(
        db,
        Message(
            id=_new_message_id(),
            conversation_id=conversation.id,
            course_id=course_id,
            role="assistant",
            content=answer_text,
            answer_type="grounded",
            generation_status="success",
            material_scope_json=material_scope_json,
            created_at=datetime.now(timezone.utc),
        ),
    )
    citations = save_citations(db, _build_citations(assistant_message.id, selected_chunks))
    _touch_conversation(db, conversation)

    logger.info(
        "问答完成 | course=%s conversation=%s citations=%d cost_ms=%.2f",
        course_id,
        conversation.id,
        len(citations),
        (perf_counter() - started_at) * 1000,
    )

    return CourseAnswerRead(
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        answer_text=assistant_message.content,
        answer_type="grounded",
        source_citations=[SourceCitationRead.model_validate(citation) for citation in citations],
        used_material_ids=used_material_ids,
    )


def list_course_conversations(db: Session, *, user_id: str, course_id: str) -> list[Conversation]:
    assert_course_owner(db, user_id, course_id)
    return list_active_conversations_for_course(db, user_id=user_id, course_id=course_id)


def list_conversation_messages(db: Session, *, user_id: str, conversation_id: str) -> list[MessageRead]:
    conversation = get_active_conversation_by_id_for_user(db, user_id=user_id, conversation_id=conversation_id)
    if conversation is None:
        raise CourseNexusError(code="NOT_FOUND", message="对话不存在", status_code=404)
    messages = list_messages_for_conversation(db, conversation_id=conversation_id)
    citations = list_citations_for_messages(db, message_ids=[message.id for message in messages])
    citations_by_message: dict[str, list[SourceCitationRead]] = {}
    for citation in citations:
        if citation.message_id is not None:
            citations_by_message.setdefault(citation.message_id, []).append(SourceCitationRead.model_validate(citation))
    return [
        MessageRead.model_validate(message).model_copy(
            update={"source_citations": citations_by_message.get(message.id, [])}
        )
        for message in messages
    ]


def _message_material_scope_json(
    payload: CourseQuestionCreate,
    *,
    material_scope_metadata: dict[str, object] | None,
    used_material_ids: list[str],
) -> dict[str, object]:
    data: dict[str, object] = payload.material_scope.model_dump(mode="json")
    if material_scope_metadata:
        data.update(material_scope_metadata)
    data["used_material_ids"] = used_material_ids
    return data


def _used_material_ids(chunks: list[ContextChunk]) -> list[str]:
    return list(dict.fromkeys(chunk.material_id for chunk in chunks))


def _model_question(question: str, context: str | None) -> str:
    if not context:
        return question
    return f"{question}\n\nTask context:\n{context}"


def _get_or_create_conversation(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: CourseQuestionCreate,
    allowed_source_pages: set[str] | None = None,
) -> Conversation:
    if payload.conversation_id:
        conversation = get_active_conversation_for_user(
            db,
            user_id=user_id,
            course_id=course_id,
            conversation_id=payload.conversation_id,
        )
        if conversation is None:
            raise CourseNexusError(code="NOT_FOUND", message="对话不存在", status_code=404)
        if allowed_source_pages is not None and conversation.source_page not in allowed_source_pages:
            raise CourseNexusError(code="NOT_FOUND", message="对话不存在", status_code=404)
        return conversation

    return save_conversation(
        db,
        Conversation(
            id=_new_conversation_id(),
            user_id=user_id,
            course_id=course_id,
            title=payload.question[:80],
            source_page=payload.source_page,
            status="active",
        ),
    )


def _select_citation_chunks(chunks: list[ContextChunk], citation_chunk_ids: list[str]) -> list[ContextChunk]:
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    return [chunk_by_id[chunk_id] for chunk_id in dict.fromkeys(citation_chunk_ids) if chunk_id in chunk_by_id]


def _normalize_inline_citations(answer_text: str, chunks: list[ContextChunk]) -> str:
    normalized = answer_text
    placeholders: dict[str, str] = {}
    for ordinal, chunk in enumerate(chunks, start=1):
        placeholder = f"\x00course-nexus-citation-{ordinal}\x00"
        marker = f"[[cite:{chunk.chunk_id}]]"
        if marker in normalized:
            normalized = normalized.replace(marker, placeholder)
            placeholders[placeholder] = f"[[cite:{ordinal}]]"

    normalized = _INLINE_CITATION_PATTERN.sub("", normalized)
    if chunks and not placeholders:
        suffix = " ".join(f"[[cite:{ordinal}]]" for ordinal in range(1, len(chunks) + 1))
        normalized = f"{normalized.rstrip()} {suffix}"
    else:
        for placeholder, marker in placeholders.items():
            normalized = normalized.replace(placeholder, marker)
    return normalized


def _build_citations(message_id: str, chunks: list[ContextChunk]) -> list[SourceCitation]:
    return [
        SourceCitation(
            id=_new_citation_id(),
            message_id=message_id,
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


def _touch_conversation(db: Session, conversation: Conversation) -> None:
    conversation.updated_at = datetime.now(timezone.utc)
    save_conversation(db, conversation)
