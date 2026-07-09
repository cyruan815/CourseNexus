from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.modules.courses.service import assert_course_owner
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generated_content.repository import (
    get_active_generated_content_for_user,
    list_active_generated_contents_for_course,
)


def list_generated_contents(db: Session, *, user_id: str, course_id: str) -> list[AIGeneratedContent]:
    assert_course_owner(db, user_id, course_id)
    return list_active_generated_contents_for_course(db, user_id=user_id, course_id=course_id)


def get_generated_content_detail(db: Session, *, user_id: str, generated_content_id: str) -> AIGeneratedContent:
    content = get_active_generated_content_for_user(db, user_id=user_id, generated_content_id=generated_content_id)
    if content is None:
        raise CourseNexusError(code="NOT_FOUND", message="生成内容不存在", status_code=404)
    return content
