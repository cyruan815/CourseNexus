from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.course_qa.models import Conversation, Message, SourceCitation
from app.modules.course_qa.repository import (
    get_active_conversation_by_id_for_user,
    get_active_conversation_for_user,
    list_active_conversations_for_course,
    list_messages_for_conversation,
    save_citations,
    save_conversation,
    save_message,
)
from app.modules.course_qa.schemas import CourseAnswerRead, CourseQuestionCreate, SourceCitationRead
from app.modules.courses.service import assert_course_owner
from app.modules.material_context.schemas import ContextChunk
from app.modules.material_context.service import resolve_context


def _new_conversation_id() -> str:
    return f"cnv_{uuid4().hex}"


def _new_message_id() -> str:
    return f"msg_{uuid4().hex}"


def _new_citation_id() -> str:
    return f"cit_{uuid4().hex}"


def ask_course_question(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: CourseQuestionCreate,
    model_provider: ModelProvider,
) -> CourseAnswerRead:
    assert_course_owner(db, user_id, course_id)
    conversation = _get_or_create_conversation(db, user_id=user_id, course_id=course_id, payload=payload)
    material_scope_json = payload.material_scope.model_dump(mode="json")
    user_message = save_message(
        db,
        Message(
            id=_new_message_id(),
            conversation_id=conversation.id,
            course_id=course_id,
            role="user",
            content=payload.question,
            material_scope_json=material_scope_json,
        ),
    )
    context = resolve_context(db, user_id, course_id, payload.material_scope)

    if context.no_parsed_material:
        assistant_message = save_message(
            db,
            Message(
                id=_new_message_id(),
                conversation_id=conversation.id,
                course_id=course_id,
                role="assistant",
                content="当前资料范围内没有已解析资料，无法基于课程资料回答。",
                answer_type="no_source",
                generation_status="success",
                material_scope_json=material_scope_json,
            ),
        )
        _touch_conversation(db, conversation)
        return CourseAnswerRead(
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            answer_text=assistant_message.content,
            answer_type="no_source",
            source_citations=[],
        )

    try:
        model_answer = model_provider.answer_question(question=payload.question, context_chunks=context.chunks)
    except CourseNexusError:
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
            ),
        )
        _touch_conversation(db, conversation)
        raise

    assistant_message = save_message(
        db,
        Message(
            id=_new_message_id(),
            conversation_id=conversation.id,
            course_id=course_id,
            role="assistant",
            content=model_answer.answer_text,
            answer_type="grounded",
            generation_status="success",
            material_scope_json=material_scope_json,
        ),
    )
    selected_chunks = _select_citation_chunks(context.chunks, model_answer.citation_chunk_ids)
    citations = save_citations(db, _build_citations(assistant_message.id, selected_chunks))
    _touch_conversation(db, conversation)

    return CourseAnswerRead(
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        answer_text=assistant_message.content,
        answer_type="grounded",
        source_citations=[SourceCitationRead.model_validate(citation) for citation in citations],
    )


def list_course_conversations(db: Session, *, user_id: str, course_id: str) -> list[Conversation]:
    assert_course_owner(db, user_id, course_id)
    return list_active_conversations_for_course(db, user_id=user_id, course_id=course_id)


def list_conversation_messages(db: Session, *, user_id: str, conversation_id: str) -> list[Message]:
    conversation = get_active_conversation_by_id_for_user(db, user_id=user_id, conversation_id=conversation_id)
    if conversation is None:
        raise CourseNexusError(code="NOT_FOUND", message="对话不存在", status_code=404)
    return list_messages_for_conversation(db, conversation_id=conversation_id)


def _get_or_create_conversation(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: CourseQuestionCreate,
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
    selected = [chunk_by_id[chunk_id] for chunk_id in citation_chunk_ids if chunk_id in chunk_by_id]
    return selected or chunks[:1]


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
