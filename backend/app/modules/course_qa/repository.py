from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.course_qa.models import Conversation, Message, SourceCitation


def save_conversation(db: Session, conversation: Conversation) -> Conversation:
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def save_message(db: Session, message: Message) -> Message:
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def save_citations(db: Session, citations: list[SourceCitation]) -> list[SourceCitation]:
    db.add_all(citations)
    db.commit()
    for citation in citations:
        db.refresh(citation)
    return citations


def get_active_conversation_for_user(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    conversation_id: str,
) -> Conversation | None:
    return db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.course_id == course_id,
            Conversation.deleted_at.is_(None),
            Conversation.status == "active",
        )
    ).scalar_one_or_none()


def get_active_conversation_by_id_for_user(
    db: Session,
    *,
    user_id: str,
    conversation_id: str,
) -> Conversation | None:
    return db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
            Conversation.status == "active",
        )
    ).scalar_one_or_none()


def list_active_conversations_for_course(db: Session, *, user_id: str, course_id: str) -> list[Conversation]:
    return list(
        db.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.course_id == course_id,
                Conversation.deleted_at.is_(None),
                Conversation.status == "active",
            )
            .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
        ).scalars()
    )


def list_messages_for_conversation(db: Session, *, conversation_id: str) -> list[Message]:
    return list(
        db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        ).scalars()
    )


def list_citations_for_messages(db: Session, *, message_ids: list[str]) -> list[SourceCitation]:
    if not message_ids:
        return []
    return list(
        db.execute(
            select(SourceCitation)
            .where(SourceCitation.message_id.in_(message_ids))
            .order_by(SourceCitation.message_id.asc(), SourceCitation.sort_order.asc(), SourceCitation.id.asc())
        ).scalars()
    )
