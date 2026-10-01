from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import CourseNexusError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.integrations.rag.base import RagIndex
from app.integrations.rag.manager import get_rag_index_manager
from app.modules.users.models import User
from app.modules.users.repository import get_user_by_id


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> User | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None

    settings = get_settings()
    claims = decode_access_token(token, secret_key=settings.secret_key)
    if claims is None:
        return None

    user = get_user_by_id(db, claims.user_id)
    if (
        user is None
        or user.status != "active"
        or user.deleted_at is not None
        or claims.token_epoch != user.token_epoch
    ):
        return None
    return user


def get_required_user(current_user: User | None = Depends(get_current_user)) -> User:
    if current_user is None:
        raise CourseNexusError(code="UNAUTHORIZED", message="未登录或登录失效", status_code=401)
    return current_user


def get_rag_index() -> RagIndex:
    return _create_openai_rag_index(
        missing_code="INDEXING_FAILED",
        missing_message="资料索引配置缺失",
    )


def get_retrieval_rag_index() -> RagIndex:
    return _create_openai_rag_index(
        missing_code="RETRIEVAL_FAILED",
        missing_message="资料检索配置缺失",
    )


def _create_openai_rag_index(*, missing_code: str, missing_message: str) -> RagIndex:
    return get_rag_index_manager().require_index(
        missing_code=missing_code,
        missing_message=missing_message,
    )
