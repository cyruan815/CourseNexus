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


class StudyPlanApiProvider:
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
                            "citation_chunk_ids": ["chk_api"],
                        }
                    ],
                    "citation_chunk_ids": ["chk_api"],
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
                                    "estimated_minutes": 45,
                                    "citation_chunk_ids": ["chk_api"],
                                    "sort_order": 1,
                                },
                                {
                                    "title": "daily quiz",
                                    "subtask_type": "quiz",
                                    "description": "check day scope",
                                    "related_material_ids": material_ids,
                                    "estimated_minutes": 15,
                                    "citation_chunk_ids": ["chk_api"],
                                    "sort_order": 2,
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
                                    "estimated_minutes": 45,
                                    "citation_chunk_ids": ["chk_api"],
                                    "sort_order": 1,
                                },
                                {
                                    "title": "final test",
                                    "subtask_type": "test",
                                    "description": "cover full plan",
                                    "related_material_ids": material_ids,
                                    "estimated_minutes": 15,
                                    "citation_chunk_ids": ["chk_api"],
                                    "sort_order": 2,
                                }
                            ],
                        },
                    ],
                    "citation_chunk_ids": ["chk_api"],
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
    provider = StudyPlanApiProvider()
    app.dependency_overrides[study_plan_router.get_plan_generator_provider] = lambda: provider
    app.dependency_overrides[study_plan_router.get_plan_map_provider] = lambda: provider
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


def upload_and_parse_material(client: TestClient, token: str, course_id: str) -> str:
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
    return material_id


def build_payload() -> dict[str, object]:
    return {
        "goal_text": "期末复习",
        "start_date": "2026-07-10",
        "end_date": "2026-07-11",
        "daily_available_minutes": 60,
        "material_scope": {
            "include_all_parsed_materials": True,
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
    assert preview.json()["data"]["coverage"]["expected_material_ids"]

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

def test_study_plan_api_rejects_confirmed_tasks_without_daily_test(client: TestClient) -> None:
    token = register_and_token(client, "bob")
    course_id = create_course(client, token)
    material_id = upload_and_parse_material(client, token, course_id)
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "invalid-tree-key"}
    payload = build_payload() | {
        "client_flow": "wizard_v1",
        "tasks": [
            {
                "title": "? 1 ?????",
                "task_date": "2026-07-10",
                "sort_order": 1,
                "subtasks": [
                    {
                        "title": "??: Intro",
                        "subtask_type": "learn",
                        "description": "Alpha",
                        "related_material_ids": [material_id],
                        "estimated_minutes": 60,
                        "citation_chunk_ids": ["chk_api"],
                        "sort_order": 1,
                    }
                ],
            },
            {
                "title": "? 2 ?????",
                "task_date": "2026-07-11",
                "sort_order": 2,
                "subtasks": [
                    {
                        "title": "????",
                        "subtask_type": "test",
                        "description": "????????",
                        "related_material_ids": [material_id],
                        "estimated_minutes": 60,
                        "citation_chunk_ids": ["chk_api"],
                        "sort_order": 1,
                    }
                ],
            },
        ],
    }

    response = client.post(f"/api/v1/courses/{course_id}/study-plans", headers=headers, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["message"] == "每天必须包含且只包含一个测试任务"
