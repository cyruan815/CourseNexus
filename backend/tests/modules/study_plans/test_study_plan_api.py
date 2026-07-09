from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.main import app
from app.modules.materials.router import get_material_storage


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
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
    app.dependency_overrides[get_material_storage] = lambda: LocalFileStorage(
        root_path=tmp_path,
        max_file_size_bytes=1024,
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def register_and_token(client: TestClient, username: str) -> str:
    response = client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def create_course(client: TestClient, token: str) -> str:
    response = client.post(
        "/api/v1/courses",
        json={"name": "Linear Algebra"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json()["data"]["id"]


def upload_and_parse_material(client: TestClient, token: str, course_id: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    upload = client.post(
        f"/api/v1/courses/{course_id}/materials",
        headers=headers,
        files={"file": ("notes.md", b"# Intro\nAlpha\n", "text/markdown")},
    )
    assert upload.status_code == 200
    material_id = upload.json()["data"]["id"]
    parse = client.post(f"/api/v1/materials/{material_id}/parse-retries", headers=headers)
    assert parse.status_code == 200


def build_payload() -> dict[str, object]:
    return {
        "goal_text": "期末复习",
        "start_date": "2026-07-10",
        "end_date": "2026-07-11",
        "daily_available_minutes": 60,
        "material_scope": {
            "include_all_parsed_materials": True,
            "folder_ids": [],
            "material_ids": [],
        },
    }


def test_study_plan_api_preview_save_list_and_detail(client: TestClient) -> None:
    token = register_and_token(client, "alice")
    course_id = create_course(client, token)
    upload_and_parse_material(client, token, course_id)
    headers = {"Authorization": f"Bearer {token}"}

    preview = client.post(f"/api/v1/courses/{course_id}/study-plans/preview", headers=headers, json=build_payload())

    assert preview.status_code == 200
    assert len(preview.json()["data"]["tasks"]) == 2

    saved = client.post(f"/api/v1/courses/{course_id}/study-plans", headers=headers, json=build_payload())

    assert saved.status_code == 200
    saved_data = saved.json()["data"]
    plan_id = saved_data["plan"]["id"]
    assert len(saved_data["tasks"]) == 2
    assert saved_data["subtasks"]

    listed = client.get(f"/api/v1/courses/{course_id}/study-plans", headers=headers)
    assert listed.status_code == 200
    assert [plan["id"] for plan in listed.json()["data"]] == [plan_id]

    detail = client.get(f"/api/v1/study-plans/{plan_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["plan"]["id"] == plan_id
