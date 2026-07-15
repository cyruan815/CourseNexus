from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.course_qa.models import SourceCitation
from app.modules.generated_content.models import AIGeneratedContent


def add_generated_content(db: Session, content: AIGeneratedContent) -> AIGeneratedContent:
    db.add(content)
    db.flush()
    return content


def add_generated_content_citations(db: Session, citations: list[SourceCitation]) -> None:
    db.add_all(citations)
    db.flush()


def save_generated_content(db: Session, content: AIGeneratedContent) -> AIGeneratedContent:
    db.add(content)
    db.commit()
    db.refresh(content)
    return content


def permanently_delete_generated_content(db: Session, content: AIGeneratedContent) -> None:
    db.execute(
        delete(SourceCitation).where(SourceCitation.generated_content_id == content.id)
    )
    db.delete(content)
    db.commit()


def list_active_generated_contents_for_course(
    db: Session,
    *,
    user_id: str,
    course_id: str,
) -> list[AIGeneratedContent]:
    return list(
        db.execute(
            select(AIGeneratedContent)
            .where(
                AIGeneratedContent.user_id == user_id,
                AIGeneratedContent.course_id == course_id,
                AIGeneratedContent.deleted_at.is_(None),
            )
            .order_by(AIGeneratedContent.created_at.desc())
        ).scalars()
    )


def get_active_generated_content_for_user(
    db: Session,
    *,
    user_id: str,
    generated_content_id: str,
) -> AIGeneratedContent | None:
    return db.execute(
        select(AIGeneratedContent).where(
            AIGeneratedContent.id == generated_content_id,
            AIGeneratedContent.user_id == user_id,
            AIGeneratedContent.deleted_at.is_(None),
        )
    ).scalar_one_or_none()


def list_generated_content_citations(
    db: Session,
    generated_content_ids: list[str],
) -> list[SourceCitation]:
    if not generated_content_ids:
        return []
    return list(
        db.execute(
            select(SourceCitation)
            .where(SourceCitation.generated_content_id.in_(generated_content_ids))
            .order_by(
                SourceCitation.generated_content_id,
                SourceCitation.sort_order.asc().nulls_last(),
                SourceCitation.id,
            )
        ).scalars()
    )
