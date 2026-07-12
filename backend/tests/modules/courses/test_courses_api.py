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


def register_and_token(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_course_crud_flow(client: TestClient) -> None:
    token = register_and_token(client, "alice")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/v1/courses",
        json={"name": "Linear Algebra", "teacher": "Prof. A", "term": "2025-2026-spring"},
        headers=headers,
    )

    assert create_response.status_code == 200
    created_course = create_response.json()["data"]
    course_id = created_course["id"]
    assert created_course["name"] == "Linear Algebra"
    assert created_course["term"] == "2025-2026-spring"

    list_response = client.get("/api/v1/courses", headers=headers)

    assert list_response.status_code == 200
    assert [course["id"] for course in list_response.json()["data"]] == [course_id]

    detail_response = client.get(f"/api/v1/courses/{course_id}", headers=headers)

    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["id"] == course_id

    update_response = client.patch(
        f"/api/v1/courses/{course_id}",
        json={"name": "Advanced Linear Algebra"},
        headers=headers,
    )

    assert update_response.status_code == 200
    assert update_response.json()["data"]["name"] == "Advanced Linear Algebra"

    delete_response = client.delete(f"/api/v1/courses/{course_id}", headers=headers)

    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["status"] == "deleted"

    assert client.get("/api/v1/courses", headers=headers).json()["data"] == []


def test_course_term_options_and_nullable_default(client: TestClient) -> None:
    token = register_and_token(client, "term-user")
    headers = {"Authorization": f"Bearer {token}"}

    options_response = client.get("/api/v1/course-terms", headers=headers)

    assert options_response.status_code == 200
    assert options_response.json()["data"] == [
        {"value": "2027-2028-autumn", "label": "2027-2028 秋季"},
        {"value": "2027-2028-spring", "label": "2027-2028 春季"},
        {"value": "2026-2027-autumn", "label": "2026-2027 秋季"},
        {"value": "2026-2027-spring", "label": "2026-2027 春季"},
        {"value": "2025-2026-autumn", "label": "2025-2026 秋季"},
        {"value": "2025-2026-spring", "label": "2025-2026 春季"},
        {"value": "2024-2025-autumn", "label": "2024-2025 秋季"},
        {"value": "2024-2025-spring", "label": "2024-2025 春季"},
    ]

    create_response = client.post("/api/v1/courses", json={"name": "No Term"}, headers=headers)

    assert create_response.status_code == 200
    assert create_response.json()["data"]["term"] is None


def test_course_create_and_update_reject_nonstandard_term(client: TestClient) -> None:
    token = register_and_token(client, "invalid-term-user")
    headers = {"Authorization": f"Bearer {token}"}

    invalid_create_response = client.post(
        "/api/v1/courses",
        json={"name": "Bad Term", "term": "2026 Spring"},
        headers=headers,
    )

    assert invalid_create_response.status_code == 422
    assert invalid_create_response.json()["error"]["code"] == "VALIDATION_ERROR"

    created = client.post("/api/v1/courses", json={"name": "Valid"}, headers=headers).json()["data"]
    invalid_update_response = client.patch(
        f"/api/v1/courses/{created['id']}",
        json={"term": "custom term"},
        headers=headers,
    )

    assert invalid_update_response.status_code == 422
    assert invalid_update_response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_course_api_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/courses")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"

    term_options_response = client.get("/api/v1/course-terms")

    assert term_options_response.status_code == 401
    assert term_options_response.json()["error"]["code"] == "UNAUTHORIZED"


def test_course_detail_does_not_cross_user_boundary(client: TestClient) -> None:
    alice_token = register_and_token(client, "alice")
    bob_token = register_and_token(client, "bob")

    bob_create_response = client.post(
        "/api/v1/courses",
        json={"name": "Databases"},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    bob_course_id = bob_create_response.json()["data"]["id"]

    response = client.get(
        f"/api/v1/courses/{bob_course_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
