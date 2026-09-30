from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
import app.db.models  # noqa: F401
from app.main import app


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_register_login_and_me_flow(client: TestClient) -> None:
    register_response = client.post(
        "/api/v1/auth/register",
        json={"username": "alice", "password": "password123", "nickname": "Alice"},
    )

    assert register_response.status_code == 200
    register_data = register_response.json()["data"]
    token = register_data["access_token"]
    assert register_data["token_type"] == "bearer"
    assert register_data["expires_at"]
    assert register_data["user"]["username"] == "alice"

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "password123"},
    )

    assert login_response.status_code == 200
    login_data = login_response.json()["data"]
    assert login_data["access_token"]

    me_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me_response.status_code == 200
    assert me_response.json()["data"]["username"] == "alice"


def test_me_requires_bearer_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_wrong_password_returns_unauthorized(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"username": "alice", "password": "password123"},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def register_and_token(client: TestClient, username: str, password: str = "password123") -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_change_password_revokes_all_existing_sessions(client: TestClient) -> None:
    token = register_and_token(client, "alice")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "password123", "new_password": "new-password456"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"password_changed": True, "relogin_required": True}

    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 401
    assert me_response.json()["error"]["code"] == "UNAUTHORIZED"

    old_login = client.post("/api/v1/auth/login", json={"username": "alice", "password": "password123"})
    assert old_login.status_code == 401

    new_login = client.post("/api/v1/auth/login", json={"username": "alice", "password": "new-password456"})
    assert new_login.status_code == 200
    new_token = new_login.json()["data"]["access_token"]
    me_with_new_token = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert me_with_new_token.status_code == 200


def test_change_password_with_wrong_current_password_keeps_session(client: TestClient, caplog) -> None:
    token = register_and_token(client, "alice")
    headers = {"Authorization": f"Bearer {token}"}

    with caplog.at_level("INFO"):
        response = client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": "wrong-password", "new_password": "new-password456"},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CURRENT_PASSWORD_MISMATCH"
    assert "wrong-password" not in caplog.text
    assert "new-password456" not in caplog.text

    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200

    old_login = client.post("/api/v1/auth/login", json={"username": "alice", "password": "password123"})
    assert old_login.status_code == 200


def test_change_password_rejects_same_or_too_short_new_password(client: TestClient) -> None:
    token = register_and_token(client, "alice")
    headers = {"Authorization": f"Bearer {token}"}

    same_response = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "password123", "new_password": "password123"},
    )
    assert same_response.status_code == 400
    assert same_response.json()["error"]["code"] == "VALIDATION_ERROR"

    short_response = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "password123", "new_password": "short"},
    )
    assert short_response.status_code == 422
    assert short_response.json()["error"]["code"] == "VALIDATION_ERROR"

    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200


def test_change_password_does_not_affect_other_users_sessions(client: TestClient) -> None:
    alice_token = register_and_token(client, "alice")
    bob_token = register_and_token(client, "bob")

    response = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"current_password": "password123", "new_password": "new-password456"},
    )
    assert response.status_code == 200

    bob_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bob_token}"})
    assert bob_me.status_code == 200
