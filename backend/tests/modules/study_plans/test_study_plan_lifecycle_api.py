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
from app.core.config import get_settings
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.model_provider.openai import OpenAIModelProvider
from app.integrations.rag.fake import FakeRagIndex
from app.main import app
from app.modules.materials.router import get_material_storage, get_rag_index
from app.modules.study_plans import router as study_plan_router


class ConfigParseProvider:
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.batch_prompts: list[str] = []
        self.reduce_prompts: list[str] = []

    def generate_structured(self, *, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        self.prompts.append(prompt)
        if output_schema.__name__ == "StudyPlanConfigExtraction":
            return output_schema.model_validate(
                {
                    "start_date": "2026-07-11",
                    "end_date": "2026-07-24",
                    "daily_available_minutes": 60,
                    "preference": "mastery",
                }
            )
        if output_schema.__name__ == "PlanBatchExtraction":
            self.batch_prompts.append(prompt)
            material_id = "mat_api"
            for token in prompt.split():
                if token.startswith("mat_"):
                    material_id = token.strip(",;[]'")
                    break
            return output_schema.model_validate(
                {
                    "units": [
                        {
                            "topic": "material topic",
                            "summary": "material summary",
                            "difficulty": "medium",
                            "estimated_minutes": 60,
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
                            "title": "期末复习",
                            "task_date": "2026-07-10",
                            "sort_order": 1,
                            "subtasks": [
                                {
                                    "title": "理解核心概念",
                                    "subtask_type": "learn",
                                    "description": "学习核心概念",
                                    "related_material_ids": material_ids,
                                    "estimated_minutes": 60,
                                    "citation_chunk_ids": ["chk_api"],
                                    "sort_order": 1,
                                }
                            ],
                        }
                    ],
                    "citation_chunk_ids": ["chk_api"],
                }
            )
        raise AssertionError(output_schema)

@pytest.fixture()
def api_context(tmp_path) -> Generator[tuple[TestClient, ConfigParseProvider], None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    provider = ConfigParseProvider()
    rag_index = FakeRagIndex()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[study_plan_router.get_plan_parser_provider] = lambda: provider
    app.dependency_overrides[study_plan_router.get_plan_generator_provider] = lambda: provider
    app.dependency_overrides[get_material_storage] = lambda: LocalFileStorage(root_path=tmp_path, max_file_size_bytes=4096)
    app.dependency_overrides[get_rag_index] = lambda: rag_index
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


def upload_and_parse_material(client: TestClient, token: str, course_id: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    upload = client.post(
        f"/api/v1/courses/{course_id}/materials",
        headers=headers,
        files={"file": ("wizard.txt", b"Wizard material", "text/plain")},
    )
    assert upload.status_code == 200
    material_id = upload.json()["data"]["id"]
    parsed = client.post(f"/api/v1/materials/{material_id}/parse-retries", headers=headers)
    assert parsed.status_code == 200
    return material_id


def test_model_provider_dependencies_use_distinct_parser_and_generator_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STUDY_PLAN_PARSER_API_KEY", "parser-key")
    monkeypatch.setenv("STUDY_PLAN_PARSER_BASE_URL", "https://parser.example/v1")
    monkeypatch.setenv("STUDY_PLAN_PARSER_MODEL", "parser-model")
    monkeypatch.setenv("STUDY_PLAN_GENERATOR_API_KEY", "generator-key")
    monkeypatch.setenv("STUDY_PLAN_GENERATOR_BASE_URL", "https://generator.example/v1")
    monkeypatch.setenv("STUDY_PLAN_GENERATOR_MODEL", "generator-model")
    get_settings.cache_clear()
    try:
        parser_provider = study_plan_router.get_plan_parser_provider()
        generator_provider = study_plan_router.get_plan_generator_provider()
    finally:
        get_settings.cache_clear()

    assert isinstance(parser_provider, OpenAIModelProvider)
    assert isinstance(generator_provider, OpenAIModelProvider)
    assert parser_provider.model == "parser-model"
    assert generator_provider.model == "generator-model"

def test_config_parse_endpoint_returns_success_envelope(
    api_context: tuple[TestClient, ConfigParseProvider],
) -> None:
    client, provider = api_context
    token = register_and_token(client, "alice")
    course_id = create_course(client, token)

    response = client.post(
        f"/api/v1/courses/{course_id}/study-plan-config-parses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "goal_text": "从 2026-07-11 到 2026-07-24，每天 60 分钟精通传输层",
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["goal_text"] == "从 2026-07-11 到 2026-07-24，每天 60 分钟精通传输层"
    assert data["start_date"] == "2026-07-11"
    assert data["end_date"] == "2026-07-24"
    assert data["duration_days"] == 14
    assert data["daily_available_minutes"] == 60
    assert data["preference"] == "mastery"
    assert data["material_scope"] == {"include_all_parsed_materials": True, "material_ids": []}
    assert data["unresolved_fields"] == []
    assert provider.prompts


def test_config_parse_endpoint_requires_authentication(
    api_context: tuple[TestClient, ConfigParseProvider],
) -> None:
    client, _ = api_context

    response = client.post(
        "/api/v1/courses/crs_missing/study-plan-config-parses",
        json={"goal_text": "两周掌握传输层"},
    )

    assert response.status_code == 401

def _save_payload(title: str = "传输层冲刺计划", material_id: str = "mat_api") -> dict[str, object]:
    return {
        "title": title,
        "goal_text": "掌握传输层",
        "start_date": "2026-07-11",
        "end_date": "2026-07-11",
        "daily_available_minutes": 60,
        "preference": "fast_track",
        "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        "tasks": [
            {
                "title": "用户调整后的任务",
                "task_date": "2026-07-11",
                "sort_order": 1,
                "subtasks": [
                    {
                        "title": "用户调整后的学习项",
                        "subtask_type": "learn",
                        "description": "按用户确认内容保存",
                        "related_material_ids": [material_id],
                        "estimated_minutes": 60,
                        "citation_chunk_ids": ["chk_api"],
                        "sort_order": 1,
                    }
                ],
            }
        ],
    }


def test_save_endpoint_replays_same_idempotency_key(
    api_context: tuple[TestClient, ConfigParseProvider],
) -> None:
    client, _ = api_context
    token = register_and_token(client, "bob")
    course_id = create_course(client, token)
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "api-stable-key"}
    material_id = upload_and_parse_material(client, token, course_id)

    first = client.post(f"/api/v1/courses/{course_id}/study-plans", headers=headers, json=_save_payload(material_id=material_id))
    second = client.post(f"/api/v1/courses/{course_id}/study-plans", headers=headers, json=_save_payload(material_id=material_id))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["plan"]["id"] == second.json()["data"]["plan"]["id"]
    assert first.json()["data"]["tasks"][0]["title"] == "用户调整后的任务"


def test_save_endpoint_rejects_same_idempotency_key_with_changed_body(
    api_context: tuple[TestClient, ConfigParseProvider],
) -> None:
    client, _ = api_context
    token = register_and_token(client, "chris")
    course_id = create_course(client, token)
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "api-conflict-key"}
    material_id = upload_and_parse_material(client, token, course_id)

    first = client.post(f"/api/v1/courses/{course_id}/study-plans", headers=headers, json=_save_payload(material_id=material_id))
    second = client.post(f"/api/v1/courses/{course_id}/study-plans", headers=headers, json=_save_payload("另一个计划标题", material_id=material_id))

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"

def build_wizard_payload(material_id: str = "mat_api") -> dict[str, object]:
    return {
        "goal_text": "期末复习",
        "start_date": "2026-07-10",
        "duration_days": 2,
        "daily_available_minutes": 60,
        "recommended_daily_minutes": 60,
        "daily_minutes_source": "system_estimated",
        "preference": "sprint",
        "diagnostic_profile": {"question_version": "study_plan_diagnostic_v1"},
        "material_snapshot": {"mode": "selected", "material_ids": [material_id]},
        "capacity": {
            "estimated_total_minutes": 120,
            "available_total_minutes": 120,
            "feasibility_status": "ok",
            "warnings": [],
        },
        "generation_metadata": {"schema_version": 1},
        "material_scope": {
            "include_all_parsed_materials": True,
            "material_ids": [],
        },
    }



def build_auto_minutes_wizard_payload() -> dict[str, object]:
    return {
        "goal_text": "期末复习",
        "start_date": "2026-07-10",
        "duration_days": 1,
        "preference": "sprint",
        "diagnostic_profile": {"question_version": "study_plan_diagnostic_v1"},
        "material_scope": {
            "include_all_parsed_materials": True,
            "material_ids": [],
        },
    }


def test_legacy_save_endpoint_without_client_flow_keeps_preview_generation_compatibility(
    api_context: tuple[TestClient, ConfigParseProvider],
) -> None:
    client, provider = api_context
    token = register_and_token(client, "legacy_save_without_tasks")
    course_id = create_course(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    upload_and_parse_material(client, token, course_id)

    response = client.post(
        f"/api/v1/courses/{course_id}/study-plans",
        headers=headers,
        json=build_auto_minutes_wizard_payload(),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["tasks"]
    assert data["plan"]["parsed_config_json"]["tasks_source"] == "generated"
    assert provider.batch_prompts



def test_wizard_v1_save_endpoint_requires_preview_tasks_when_missing(
    api_context: tuple[TestClient, ConfigParseProvider],
) -> None:
    client, provider = api_context
    token = register_and_token(client, "wizard_missing_tasks")
    course_id = create_course(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    material_id = upload_and_parse_material(client, token, course_id)
    prompt_count = len(provider.batch_prompts)

    response = client.post(
        f"/api/v1/courses/{course_id}/study-plans",
        headers=headers,
        json=build_wizard_payload(material_id) | {"client_flow": "wizard_v1"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PREVIEW_TASKS_REQUIRED"
    assert len(provider.batch_prompts) == prompt_count



def test_wizard_v1_save_endpoint_requires_preview_tasks_when_empty(
    api_context: tuple[TestClient, ConfigParseProvider],
) -> None:
    client, provider = api_context
    token = register_and_token(client, "wizard_empty_tasks")
    course_id = create_course(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    material_id = upload_and_parse_material(client, token, course_id)
    prompt_count = len(provider.batch_prompts)

    response = client.post(
        f"/api/v1/courses/{course_id}/study-plans",
        headers=headers,
        json=build_wizard_payload(material_id) | {"client_flow": "wizard_v1", "tasks": []},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PREVIEW_TASKS_REQUIRED"
    assert len(provider.batch_prompts) == prompt_count


def test_preview_without_daily_minutes_estimates_and_save_traces_capacity(
    api_context: tuple[TestClient, ConfigParseProvider],
) -> None:
    client, _ = api_context
    token = register_and_token(client, "auto_daily_minutes")
    course_id = create_course(client, token)
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "auto-daily-minutes-key"}
    upload_and_parse_material(client, token, course_id)

    preview = client.post(
        f"/api/v1/courses/{course_id}/study-plans/preview",
        headers=headers,
        json=build_auto_minutes_wizard_payload(),
    )

    assert preview.status_code == 200
    preview_data = preview.json()["data"]
    assert preview_data["daily_available_minutes"] == 60
    assert preview_data["recommended_daily_minutes"] == 60
    assert preview_data["daily_minutes_source"] == "system_estimated"
    assert preview_data["capacity"]["estimated_total_minutes"] == 60
    assert preview_data["capacity"]["available_total_minutes"] == 60
    assert preview_data["capacity"]["feasibility_status"] == "tight"

    saved = client.post(f"/api/v1/courses/{course_id}/study-plans", headers=headers, json=preview_data)

    assert saved.status_code == 200
    parsed_config = saved.json()["data"]["plan"]["parsed_config_json"]
    assert parsed_config["confirmed_config"]["daily_available_minutes"] == 60
    assert parsed_config["confirmed_config"]["recommended_daily_minutes"] == 60
    assert parsed_config["confirmed_config"]["daily_minutes_source"] == "system_estimated"
    assert parsed_config["recommended_daily_minutes"] == 60
    assert parsed_config["daily_minutes_source"] == "system_estimated"
    assert parsed_config["capacity"]["available_total_minutes"] == 60
def test_preview_preserves_user_modified_daily_minutes(
    api_context: tuple[TestClient, ConfigParseProvider],
) -> None:
    client, _ = api_context
    token = register_and_token(client, "manual_daily_minutes")
    course_id = create_course(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    upload_and_parse_material(client, token, course_id)
    payload = build_auto_minutes_wizard_payload() | {
        "daily_available_minutes": 75,
        "daily_minutes_source": "user_modified",
    }

    preview = client.post(f"/api/v1/courses/{course_id}/study-plans/preview", headers=headers, json=payload)

    assert preview.status_code == 200
    preview_data = preview.json()["data"]
    assert preview_data["daily_available_minutes"] == 75
    assert preview_data["recommended_daily_minutes"] == 60
    assert preview_data["daily_minutes_source"] == "user_modified"
    assert preview_data["capacity"]["available_total_minutes"] == 75
def test_preview_and_save_accept_wizard_metadata_and_exact_tasks(
    api_context: tuple[TestClient, ConfigParseProvider],
) -> None:
    client, _ = api_context
    token = register_and_token(client, "diana")
    course_id = create_course(client, token)
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "wizard-contract-key"}
    material_id = upload_and_parse_material(client, token, course_id)

    preview = client.post(f"/api/v1/courses/{course_id}/study-plans/preview", headers=headers, json=build_wizard_payload(material_id))

    assert preview.status_code == 200
    preview_data = preview.json()["data"]
    assert preview_data["duration_days"] == 2
    assert preview_data["daily_available_minutes"] == 60
    assert preview_data["recommended_daily_minutes"] == 30
    assert preview_data["daily_minutes_source"] == "system_estimated"
    assert preview_data["diagnostic_profile"]["question_version"] == "study_plan_diagnostic_v1"
    assert preview_data["capacity"]["feasibility_status"] == "ok"
    assert preview_data["tasks"]

    saved = client.post(
        f"/api/v1/courses/{course_id}/study-plans",
        headers=headers,
        json=preview_data | {"client_flow": "wizard_v1"},
    )

    assert saved.status_code == 200
    saved_data = saved.json()["data"]
    assert saved_data["plan"]["parsed_config_json"]["schema_version"] == 1
    assert saved_data["plan"]["parsed_config_json"]["confirmed_config"]["duration_days"] == 2
    assert saved_data["plan"]["parsed_config_json"]["tasks_source"] == "confirmed"
    assert saved_data["plan"]["parsed_config_json"]["task_snapshot"][0]["title"] == preview_data["tasks"][0]["title"]
    assert saved_data["tasks"][0]["title"] == preview_data["tasks"][0]["title"]


def test_regeneration_preview_api_accepts_duration_and_diagnostic_profile_override(
    api_context: tuple[TestClient, ConfigParseProvider],
) -> None:
    client, _ = api_context
    token = register_and_token(client, "regen_api_merge")
    course_id = create_course(client, token)
    material_id = upload_and_parse_material(client, token, course_id)
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "regen-api-save-key"}

    preview = client.post(f"/api/v1/courses/{course_id}/study-plans/preview", headers=headers, json=build_wizard_payload(material_id))
    assert preview.status_code == 200
    preview_data = preview.json()["data"]
    saved = client.post(
        f"/api/v1/courses/{course_id}/study-plans",
        headers=headers,
        json=preview_data | {"client_flow": "wizard_v1"},
    )
    assert saved.status_code == 200
    plan_id = saved.json()["data"]["plan"]["id"]
    override_profile = {
        "question_version": "study_plan_diagnostic_v1",
        "prior_knowledge_level": "some",
        "foundation_needed": False,
        "weak_topics": ["api-topic"],
        "weak_area": "application",
        "explanation_style": "example_first",
    }

    regenerated = client.post(
        f"/api/v1/study-plans/{plan_id}/regeneration-previews",
        headers={"Authorization": f"Bearer {token}"},
        json={"duration_days": 3, "diagnostic_profile": override_profile},
    )

    assert regenerated.status_code == 200
    data = regenerated.json()["data"]
    assert data["start_date"] == "2026-07-10"
    assert data["end_date"] == "2026-07-12"
    assert data["duration_days"] == 3
    assert data["diagnostic_profile"] == override_profile
    assert data["generation_metadata"]["planner_strategy"]["weak_topics"] == ["api-topic"]
    assert data["generation_metadata"]["planner_strategy"]["explanation_style"] == "example_first"
