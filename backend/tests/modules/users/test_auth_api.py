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
