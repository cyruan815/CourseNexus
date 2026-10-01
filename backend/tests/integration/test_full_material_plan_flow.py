from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
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
from app.modules.study_plans import router as study_plan_router


class PlanPreviewProvider:
    def __init__(self) -> None:
        self.batch_prompts: list[str] = []
        self.reduce_prompts: list[str] = []

    def generate_structured(self, *, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        if output_schema.__name__ == "PlanBatchExtraction":
            self.batch_prompts.append(prompt)
            material_id = "mat_missing"
            for token in prompt.split():
                if token.startswith("mat_"):
                    material_id = token.strip(",;")
                    break
            return output_schema.model_validate(
                {
                    "units": [
                        {
                            "topic": "material topic",
                            "summary": "material summary",
                            "difficulty": "medium",
                            "estimated_minutes": 30,
                            "related_material_ids": [material_id],
                            "citation_chunk_ids": ["chk_api"],
                        }
                    ],
                    "citation_chunk_ids": ["chk_api"],
                }
            )
        if output_schema.__name__ == "StudyPlanReduction":
            self.reduce_prompts.append(prompt)
            material_ids = sorted({part.strip(",;[]'") for part in prompt.split() if part.startswith("mat_")})
            return output_schema.model_validate(
                {
                    "title": "Computer Networks 学习计划",
                    "tasks": [
                        {
                            "title": "传输层集中学习",
                            "task_date": "2026-07-11",
                            "sort_order": 1,
                            "subtasks": [
                                {
                                    "title": "理解可靠传输",
                                    "subtask_type": "learn",
                                    "description": "学习可靠传输",
                                    "related_material_ids": material_ids,
                                    "estimated_minutes": 45,
                                    "citation_chunk_ids": ["chk_api"],
                                    "sort_order": 1,
                                },
                                {
                                    "title": "传输层综合自测",
                                    "subtask_type": "test",
                                    "description": "检查核心概念掌握情况",
                                    "related_material_ids": material_ids,
                                    "estimated_minutes": 15,
                                    "citation_chunk_ids": ["chk_api"],
                                    "sort_order": 2,
                                }
                            ],
                        }
                    ],
                    "citation_chunk_ids": ["chk_api"],
                }
            )
        raise AssertionError(output_schema)


@pytest.fixture()
def client_and_provider(tmp_path) -> Generator[tuple[TestClient, PlanPreviewProvider], None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    rag_index = FakeRagIndex()
    provider = PlanPreviewProvider()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_material_storage] = lambda: LocalFileStorage(
        root_path=tmp_path,
        max_file_size_bytes=4096,
    )
    app.dependency_overrides[get_rag_index] = lambda: rag_index
    app.dependency_overrides[study_plan_router.get_plan_generator_provider] = lambda: provider
    app.dependency_overrides[study_plan_router.get_plan_map_provider] = lambda: provider
    try:
        yield TestClient(app), provider
    finally:
        app.dependency_overrides.clear()


def register_and_token(client: TestClient, username: str) -> str:
    response = client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def create_course(client: TestClient, token: str) -> str:
    response = client.post(
        "/api/v1/courses",
        json={"name": "Computer Networks"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json()["data"]["id"]


def upload_and_parse_material(client: TestClient, token: str, course_id: str, filename: str, content: bytes) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    upload = client.post(
        f"/api/v1/courses/{course_id}/materials",
        headers=headers,
        files={"file": (filename, content, "text/plain")},
    )
    assert upload.status_code == 200
    material_id = upload.json()["data"]["id"]
    parse = client.post(f"/api/v1/materials/{material_id}/parse-retries", headers=headers)
    assert parse.status_code == 200
    return material_id


def test_preview_uses_all_parsed_materials_and_returns_coverage(
    client_and_provider: tuple[TestClient, PlanPreviewProvider],
) -> None:
    client, provider = client_and_provider
    token = register_and_token(client, "alice")
    course_id = create_course(client, token)
    material_ids = [
        upload_and_parse_material(client, token, course_id, "transport-a.txt", b"Alpha reliable transport"),
        upload_and_parse_material(client, token, course_id, "transport-b.txt", b"Beta congestion control"),
    ]

    response = client.post(
        f"/api/v1/courses/{course_id}/study-plans/preview",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "goal_text": "掌握传输层",
            "start_date": "2026-07-11",
            "end_date": "2026-07-11",
            "daily_available_minutes": 60,
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["coverage"]["expected_material_ids"] == sorted(material_ids)
    assert data["coverage"]["processed_material_ids"] == sorted(material_ids)
    assert data["coverage"]["batch_count"] == len(provider.batch_prompts)
    assert provider.batch_prompts
    assert provider.reduce_prompts
