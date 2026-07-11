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


class MaterialPlanProvider:
    def generate_structured(self, *, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        material_ids = sorted({part.strip(",;[]'") for part in prompt.split() if part.startswith("mat_")})
        if not material_ids:
            material_ids = ["mat_missing"]
        if output_schema.__name__ == "PlanBatchExtraction":
            return output_schema.model_validate(
                {
                    "units": [
                        {
                            "topic": "intro",
                            "summary": "summary",
                            "difficulty": "easy",
                            "estimated_minutes": 30,
                            "related_material_ids": [material_ids[0]],
                            "citation_chunk_ids": ["chk_flow"],
                        }
                    ],
                    "citation_chunk_ids": ["chk_flow"],
                }
            )
        if output_schema.__name__ == "StudyPlanReduction":
            return output_schema.model_validate(
                {
                    "title": "Linear Algebra 学习计划",
                    "tasks": [
                        {
                            "title": "第 1 天学习任务",
                            "task_date": "2026-07-10",
                            "sort_order": 1,
                            "subtasks": [
                                {
                                    "title": "学习: Intro",
                                    "subtask_type": "learn",
                                    "description": "Alpha",
                                    "related_material_ids": material_ids,
                                    "estimated_minutes": 30,
                                    "citation_chunk_ids": ["chk_flow"],
                                    "sort_order": 1,
                                }
                            ],
                        },
                        {
                            "title": "第 2 天学习任务",
                            "task_date": "2026-07-11",
                            "sort_order": 2,
                            "subtasks": [
                                {
                                    "title": "复习: Intro",
                                    "subtask_type": "review",
                                    "description": "Alpha",
                                    "related_material_ids": material_ids,
                                    "estimated_minutes": 30,
                                    "citation_chunk_ids": ["chk_flow"],
                                    "sort_order": 1,
                                }
                            ],
                        },
                    ],
                    "citation_chunk_ids": ["chk_flow"],
                }
            )
        raise AssertionError(output_schema)


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
    app.dependency_overrides[study_plan_router.get_plan_generator_provider] = lambda: MaterialPlanProvider()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_material_context_to_study_plan_flow(client: TestClient) -> None:
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
    parse = client.post(f"/api/v1/materials/{material_id}/parse-retries", headers=headers)
    assert parse.status_code == 200

    payload = {
        "goal_text": "期末复习",
        "start_date": "2026-07-10",
        "end_date": "2026-07-11",
        "daily_available_minutes": 60,
        "material_scope": {
            "include_all_parsed_materials": True,
            "material_ids": [],
        },
    }
    preview = client.post(f"/api/v1/courses/{course_id}/study-plans/preview", headers=headers, json=payload)
    assert preview.status_code == 200
    assert len(preview.json()["data"]["tasks"]) == 2
    assert preview.json()["data"]["coverage"]["expected_material_ids"] == [material_id]

    saved = client.post(f"/api/v1/courses/{course_id}/study-plans", headers=headers, json=payload)
    assert saved.status_code == 200
    saved_data = saved.json()["data"]
    assert saved_data["plan"]["course_id"] == course_id
    assert {task["course_id"] for task in saved_data["tasks"]} == {course_id}
    assert {subtask["course_id"] for subtask in saved_data["subtasks"]} == {course_id}
    assert saved_data["subtasks"][0]["related_material_ids_json"] == [material_id]