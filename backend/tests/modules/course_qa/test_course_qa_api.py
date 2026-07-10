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
from app.integrations.model_provider.mock import MockModelProvider
from app.integrations.rag.fake import FakeRagIndex
from app.main import app
from app.modules.course_qa.router import get_model_provider, get_retrieval_rag_index
from app.modules.materials.router import get_material_storage, get_rag_index


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    rag_index = FakeRagIndex()

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
    app.dependency_overrides[get_rag_index] = lambda: rag_index
    app.dependency_overrides[get_retrieval_rag_index] = lambda: rag_index
    app.dependency_overrides[get_model_provider] = lambda: MockModelProvider()
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


def test_course_qa_api_answers_with_citations(client: TestClient) -> None:
    token = register_and_token(client, "alice")
    course_id = create_course(client, token)
    upload_and_parse_material(client, token, course_id)

    response = client.post(
        f"/api/v1/courses/{course_id}/qa/questions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question": "What is Alpha?",
            "material_scope": {
                "include_all_parsed_materials": True,
                "material_ids": [],
            },
            "source_page": "course_detail",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer_type"] == "grounded"
    assert data["answer_text"]
    assert len(data["source_citations"]) == 1
    assert data["source_citations"][0]["material_name"] == "notes.md"


def test_course_qa_api_rejects_folder_scope(client: TestClient) -> None:
    token = register_and_token(client, "alice")
    course_id = create_course(client, token)

    response = client.post(
        f"/api/v1/courses/{course_id}/qa/questions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question": "What is Alpha?",
            "material_scope": {
                "include_all_parsed_materials": False,
                "folder_ids": ["fld_1"],
                "material_ids": [],
            },
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
