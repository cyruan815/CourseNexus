from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.errors import CourseNexusError
from app.core.security import (
    _base64url_encode,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
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

    claims = decode_access_token(token, secret_key="test-secret", now=now)
    assert claims is not None
    assert claims.user_id == "usr_123"
    assert claims.token_epoch == 0
    assert decode_access_token(token, secret_key="test-secret", now=now + timedelta(minutes=6)) is None


def test_access_token_round_trips_epoch_and_legacy_token_defaults_to_zero() -> None:
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    token = create_access_token(
        user_id="usr_123",
        secret_key="test-secret",
        token_epoch=3,
        expires_at=now + timedelta(minutes=5),
    )

    claims = decode_access_token(token, secret_key="test-secret", now=now)
    assert claims is not None
    assert claims.token_epoch == 3

    import hashlib
    import hmac
    import json

    legacy_payload = json.dumps(
        {"sub": "usr_123", "exp": int((now + timedelta(minutes=5)).timestamp())},
        separators=(",", ":"),
        sort_keys=True,
    )
    payload_part = _base64url_encode(legacy_payload.encode("utf-8"))
    signature = hmac.new(b"test-secret", payload_part.encode("ascii"), hashlib.sha256).digest()
    legacy_token = f"{payload_part}.{_base64url_encode(signature)}"

    legacy_claims = decode_access_token(legacy_token, secret_key="test-secret", now=now)
    assert legacy_claims is not None
    assert legacy_claims.token_epoch == 0


def test_get_current_user_rejects_stale_token_epoch(db: Session) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    secret_key = get_settings().secret_key
    stale_token = create_access_token(user_id=user.id, secret_key=secret_key, token_epoch=0)

    assert get_current_user(f"Bearer {stale_token}", db) is not None

    user.token_epoch = 1
    db.commit()

    assert get_current_user(f"Bearer {stale_token}", db) is None

    fresh_token = create_access_token(user_id=user.id, secret_key=secret_key, token_epoch=1)
    current_user = get_current_user(f"Bearer {fresh_token}", db)
    assert current_user is not None
    assert current_user.id == user.id


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
