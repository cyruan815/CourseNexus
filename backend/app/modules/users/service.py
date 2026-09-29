from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import CourseNexusError
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.users.models import User
from app.modules.users.repository import create_user, get_user_by_username, update_user
from app.modules.users.schemas import AuthResponse, UserCreate, UserRead


def _new_user_id() -> str:
    return f"usr_{uuid4().hex}"


def register_user(db: Session, payload: UserCreate) -> User:
    existing_user = get_user_by_username(db, payload.username)
    if existing_user is not None:
        raise CourseNexusError(code="CONFLICT", message="用户名已存在", status_code=409)

    user = User(
        id=_new_user_id(),
        username=payload.username,
        password_hash=hash_password(payload.password),
        nickname=payload.nickname,
        status="active",
    )
    return create_user(db, user)


def authenticate_user(db: Session, *, username: str, password: str) -> User:
    user = get_user_by_username(db, username)
    if (
        user is None
        or user.status != "active"
        or user.deleted_at is not None
        or not verify_password(password, user.password_hash)
    ):
        raise CourseNexusError(code="UNAUTHORIZED", message="用户名或密码错误", status_code=401)
    return user


def change_password(db: Session, *, user: User, current_password: str, new_password: str) -> User:
    # 旧密码校验失败使用 403 而不是 401：前端把 401 统一处理为清理 token 并跳转登录，
    # 不能把"当前密码输错"误伤成强制登出。
    if not verify_password(current_password, user.password_hash):
        raise CourseNexusError(code="CURRENT_PASSWORD_MISMATCH", message="当前密码不正确", status_code=403)
    if verify_password(new_password, user.password_hash):
        raise CourseNexusError(code="VALIDATION_ERROR", message="新密码不能与当前密码相同", status_code=400)

    user.password_hash = hash_password(new_password)
    # 递增 token_epoch 使该用户全部存量 token（含当前请求所用 token）立即失效。
    user.token_epoch += 1
    user.updated_at = datetime.now(timezone.utc)
    return update_user(db, user)


def build_auth_response(user: User) -> AuthResponse:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        user_id=user.id,
        secret_key=settings.secret_key,
        token_epoch=user.token_epoch,
        expires_at=expires_at,
    )
    return AuthResponse(
        access_token=access_token,
        expires_at=expires_at,
        user=UserRead.model_validate(user),
    )
