from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import CourseNexusError
from app.core.security import decode_access_token
from app.db.session import get_db
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
    user_id = decode_access_token(token, secret_key=settings.secret_key)
    if user_id is None:
        return None

    user = get_user_by_id(db, user_id)
    if user is None or user.status != "active" or user.deleted_at is not None:
        return None
    return user


def get_required_user(current_user: User | None = Depends(get_current_user)) -> User:
    if current_user is None:
        raise CourseNexusError(code="UNAUTHORIZED", message="未登录或登录失效", status_code=401)
    return current_user
