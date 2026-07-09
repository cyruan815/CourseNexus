from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import CourseNexusError
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.db.base import Base
import app.db.models  # noqa: F401
from app.modules.users.schemas import UserCreate
from app.modules.users.service import authenticate_user, register_user


@pytest.fixture()
def db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


def test_password_hash_is_not_plaintext_and_verifies() -> None:
    password_hash = hash_password("secret-password")

    assert password_hash != "secret-password"
    assert verify_password("secret-password", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_token_decodes_user_id_and_rejects_expired_token() -> None:
    now = datetime(2026, 7, 9, tzinfo=timezone.utc)
    token = create_access_token(
        user_id="usr_123",
        secret_key="test-secret",
        expires_at=now + timedelta(minutes=5),
    )

    assert decode_access_token(token, secret_key="test-secret", now=now) == "usr_123"
    assert decode_access_token(token, secret_key="test-secret", now=now + timedelta(minutes=6)) is None


def test_register_user_rejects_duplicate_username(db: Session) -> None:
    register_user(db, UserCreate(username="alice", password="password123", nickname="Alice"))

    with pytest.raises(CourseNexusError) as exc_info:
        register_user(db, UserCreate(username="alice", password="password456"))

    assert exc_info.value.code == "CONFLICT"


def test_disabled_or_deleted_user_cannot_login(db: Session) -> None:
    disabled_user = register_user(db, UserCreate(username="disabled", password="password123"))
    disabled_user.status = "disabled"

    deleted_user = register_user(db, UserCreate(username="deleted", password="password123"))
    deleted_user.deleted_at = datetime.now(timezone.utc)
    db.commit()

    with pytest.raises(CourseNexusError) as disabled_exc:
        authenticate_user(db, username="disabled", password="password123")

    with pytest.raises(CourseNexusError) as deleted_exc:
        authenticate_user(db, username="deleted", password="password123")

    assert disabled_exc.value.code == "UNAUTHORIZED"
    assert deleted_exc.value.code == "UNAUTHORIZED"
