from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.generated_content.models import AIGeneratedContent


def save_generated_content(db: Session, content: AIGeneratedContent) -> AIGeneratedContent:
    db.add(content)
    db.commit()
    db.refresh(content)
    return content


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
