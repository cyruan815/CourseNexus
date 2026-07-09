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
from app.integrations.rag.fake import FakeRagIndex
from app.main import app
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
    app.dependency_overrides[get_rag_index] = FakeRagIndex
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_course_workspace_material_qa_flow(client: TestClient) -> None:
    register = client.post("/api/v1/auth/register", json={"username": "alice", "password": "password123"})
    assert register.status_code == 200
    token = register.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    course = client.post("/api/v1/courses", json={"name": "Linear Algebra"}, headers=headers)
    assert course.status_code == 200
    course_id = course.json()["data"]["id"]

    upload = client.post(
        f"/api/v1/courses/{course_id}/materials",
        headers=headers,
        files={"file": ("notes.md", b"# Intro\nAlpha\n", "text/markdown")},
    )
    assert upload.status_code == 200
    material_id = upload.json()["data"]["id"]

    parsed = client.post(f"/api/v1/materials/{material_id}/parse-retries", headers=headers)
    assert parsed.status_code == 200
    assert parsed.json()["data"]["parse_status"] == "parsed"

    answer = client.post(
        f"/api/v1/courses/{course_id}/qa/questions",
        headers=headers,
        json={
            "question": "What is Alpha?",
            "material_scope": {
                "include_all_parsed_materials": True,
                "folder_ids": [],
                "material_ids": [],
            },
            "source_page": "course_detail",
        },
    )

    assert answer.status_code == 200
    answer_data = answer.json()["data"]
    assert answer_data["answer_type"] == "grounded"
    assert answer_data["source_citations"][0]["material_id"] == material_id
    assert answer_data["source_citations"][0]["chunk_id"]

    messages = client.get(f"/api/v1/conversations/{answer_data['conversation_id']}/messages", headers=headers)
    assert messages.status_code == 200
    assert [message["role"] for message in messages.json()["data"]] == ["user", "assistant"]
