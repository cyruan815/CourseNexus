from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.main import app
from app.modules.materials.router import get_material_parser, get_material_storage, get_rag_index
from app.modules.study_plans import router as study_plan_router


class DiagnosticApiProvider:
    def __init__(self) -> None:
        self.batch_prompts: list[str] = []
        self.reduce_prompts: list[str] = []

    def generate_structured(self, *, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        if output_schema.__name__ == "PlanBatchExtraction":
            self.batch_prompts.append(prompt)
            material_id = _first_material_id_in_prompt(prompt)
            return output_schema.model_validate(
                {
                    "units": [
                        {
                            "topic": "diagnostic topic",
                            "summary": "diagnostic summary",
                            "difficulty": "medium",
                            "estimated_minutes": 60,
                            "related_material_ids": [material_id],
                            "citation_chunk_ids": ["chk_diagnostic"],
                        }
                    ],
                    "citation_chunk_ids": ["chk_diagnostic"],
                }
            )
        if output_schema.__name__ == "StudyPlanReduction":
            self.reduce_prompts.append(prompt)
            material_ids = sorted({part.strip(",;[]'") for part in prompt.split() if part.startswith("mat_")})
            return output_schema.model_validate(
                {
                    "title": "诊断后学习计划",
                    "tasks": [
                        {
                            "title": "按诊断结果学习",
                            "task_date": "2026-07-12",
                            "sort_order": 1,
                            "subtasks": [
                                {
                                    "title": "学习薄弱主题",
                                    "subtask_type": "learn",
                                    "description": "根据诊断 profile 继续生成 preview",
                                    "related_material_ids": material_ids,
                                    "estimated_minutes": 60,
                                    "citation_chunk_ids": ["chk_diagnostic"],
                                    "sort_order": 1,
                                }
                            ],
                        }
                    ],
                    "citation_chunk_ids": ["chk_diagnostic"],
                }
            )
        raise AssertionError(output_schema)


@pytest.fixture()
def api_context(tmp_path) -> Generator[tuple[TestClient, DiagnosticApiProvider], None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    provider = DiagnosticApiProvider()
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
    app.dependency_overrides[get_material_parser] = lambda: PlainTextParser()
    app.dependency_overrides[get_rag_index] = lambda: rag_index
    get_settings.cache_clear()
    try:
        yield TestClient(app), provider
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


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


def upload_and_parse_material(client: TestClient, token: str, course_id: str, filename: str, content: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    upload = client.post(
        f"/api/v1/courses/{course_id}/materials",
        headers=headers,
        files={"file": (filename, content.encode("utf-8"), "text/markdown")},
    )
    assert upload.status_code == 200
    material_id = upload.json()["data"]["id"]
    parsed = client.post(f"/api/v1/materials/{material_id}/parse-retries", headers=headers)
    assert parsed.status_code == 200
    return material_id


def _first_material_id_in_prompt(prompt: str) -> str:
    for token in prompt.split():
        if token.startswith("mat_"):
            return token.strip(",;[]'")
    return "mat_diagnostic"


def _diagnostic_questions_payload(material_id: str) -> dict[str, object]:
    return {
        "goal_text": "两天复习物理层核心内容",
        "material_scope": {
            "include_all_parsed_materials": False,
            "material_ids": [material_id],
        },
    }


def _topic_questions(data: dict[str, object]) -> list[dict[str, object]]:
    questions = data["questions"]
    assert isinstance(questions, list)
    return [question for question in questions if question["question_type"] == "topic_mastery"]


def test_diagnostic_questions_include_material_topics_weak_area_and_optional_note(
    api_context: tuple[TestClient, DiagnosticApiProvider],
) -> None:
    client, _ = api_context
    token = register_and_token(client, "diagnostic_questions")
    course_id = create_course(client, token)
    material_id = upload_and_parse_material(
        client,
        token,
        course_id,
        "physical-layer.md",
        "\n\n".join(
            [
                "# 物理层的基本功能\n物理层负责比特传输和接口特性。",
                "# Nyquist / Shannon 公式\n公式用于估算信道极限速率。",
                "# 传输介质与编码\n双绞线、光纤和编码方式影响传输质量。",
                "# 多余主题\n第四个主题不应进入第一版诊断问题。",
            ]
        ),
    )

    response = client.post(
        f"/api/v1/courses/{course_id}/study-plan-diagnostic-questions",
        headers={"Authorization": f"Bearer {token}"},
        json=_diagnostic_questions_payload(material_id),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["question_version"] == "study_plan_diagnostic_v1"
    topic_questions = _topic_questions(data)
    assert [question["topic_title"] for question in topic_questions] == [
        "物理层的基本功能",
        "Nyquist / Shannon 公式",
        "传输介质与编码",
    ]
    assert all(question["topic_id"] for question in topic_questions)
    assert all(
        [option["value"] for option in question["options"]] == ["none", "heard", "some", "familiar"]
        for question in topic_questions
    )
    assert all("学习方式" not in question["question_text"] and "资料范围" not in question["question_text"] for question in data["questions"])

    weak_area_questions = [question for question in data["questions"] if question["question_type"] == "weak_area"]
    assert len(weak_area_questions) == 1
    assert [option["value"] for option in weak_area_questions[0]["options"]] == [
        "concept",
        "calculation",
        "application",
        "memorization",
        "other",
    ]

    note_questions = [question for question in data["questions"] if question["question_type"] == "diagnostic_note"]
    assert len(note_questions) == 1
    assert note_questions[0]["required"] is False
    assert note_questions[0]["options"] == []


def test_diagnostic_questions_do_not_pad_when_only_one_stable_topic(
    api_context: tuple[TestClient, DiagnosticApiProvider],
) -> None:
    client, _ = api_context
    token = register_and_token(client, "diagnostic_one_topic")
    course_id = create_course(client, token)
    material_id = upload_and_parse_material(
        client,
        token,
        course_id,
        "single-topic.md",
        "# 可靠传输基础\n确认、重传和滑动窗口是本资料唯一稳定主题。",
    )

    response = client.post(
        f"/api/v1/courses/{course_id}/study-plan-diagnostic-questions",
        headers={"Authorization": f"Bearer {token}"},
        json=_diagnostic_questions_payload(material_id),
    )

    assert response.status_code == 200
    topic_questions = _topic_questions(response.json()["data"])
    assert len(topic_questions) == 1
    assert topic_questions[0]["topic_title"] == "可靠传输基础"


def test_diagnostic_profile_summarizes_answers_without_forcing_foundation(
    api_context: tuple[TestClient, DiagnosticApiProvider],
) -> None:
    client, _ = api_context
    token = register_and_token(client, "diagnostic_profile")
    course_id = create_course(client, token)
    material_id = upload_and_parse_material(
        client,
        token,
        course_id,
        "profile-topics.md",
        "\n\n".join(
            [
                "# 物理层接口特性\n机械、电气、功能、规程特性。",
                "# 信道容量\nNyquist 和 Shannon 公式。",
                "# 编码与调制\n数字编码和模拟调制。",
            ]
        ),
    )
    question_response = client.post(
        f"/api/v1/courses/{course_id}/study-plan-diagnostic-questions",
        headers={"Authorization": f"Bearer {token}"},
        json=_diagnostic_questions_payload(material_id),
    )
    topics = _topic_questions(question_response.json()["data"])

    response = client.post(
        f"/api/v1/courses/{course_id}/study-plan-diagnostic-profiles",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_version": "study_plan_diagnostic_v1",
            "topic_mastery": [
                {"topic_id": topics[0]["topic_id"], "topic_title": topics[0]["topic_title"], "mastery_level": "some"},
                {"topic_id": topics[1]["topic_id"], "topic_title": topics[1]["topic_title"], "mastery_level": "familiar"},
                {"topic_id": topics[2]["topic_id"], "topic_title": topics[2]["topic_title"], "mastery_level": "some"},
            ],
            "weak_area": "application",
            "diagnostic_note": "希望结合例题理解。",
            "material_scope": {"include_all_parsed_materials": False, "material_ids": [material_id]},
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["question_version"] == "study_plan_diagnostic_v1"
    assert data["foundation_needed"] is False
    assert data["weak_topics"] == []
    assert data["prior_knowledge_level"] in {"some", "solid"}
    assert data["weak_area"] == "application"
    assert data["explanation_style"] == "example_first"
    assert data["diagnostic_note"] == "希望结合例题理解。"


def test_diagnostic_profile_marks_weak_foundation_when_most_topics_are_weak(
    api_context: tuple[TestClient, DiagnosticApiProvider],
) -> None:
    client, _ = api_context
    token = register_and_token(client, "diagnostic_weak_foundation")
    course_id = create_course(client, token)
    material_id = upload_and_parse_material(
        client,
        token,
        course_id,
        "weak-topics.md",
        "\n\n".join(
            [
                "# OSI 分层\n网络体系结构分层。",
                "# 差错控制\n校验、确认与重传。",
                "# 流量控制\n窗口和速率控制。",
            ]
        ),
    )
    question_response = client.post(
        f"/api/v1/courses/{course_id}/study-plan-diagnostic-questions",
        headers={"Authorization": f"Bearer {token}"},
        json=_diagnostic_questions_payload(material_id),
    )
    topics = _topic_questions(question_response.json()["data"])

    response = client.post(
        f"/api/v1/courses/{course_id}/study-plan-diagnostic-profiles",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_version": "study_plan_diagnostic_v1",
            "topic_mastery": [
                {"topic_id": topics[0]["topic_id"], "topic_title": topics[0]["topic_title"], "mastery_level": "none"},
                {"topic_id": topics[1]["topic_id"], "topic_title": topics[1]["topic_title"], "mastery_level": "heard"},
                {"topic_id": topics[2]["topic_id"], "topic_title": topics[2]["topic_title"], "mastery_level": "some"},
            ],
            "weak_area": "calculation",
            "material_scope": {"include_all_parsed_materials": False, "material_ids": [material_id]},
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["foundation_needed"] is True
    assert data["prior_knowledge_level"] == "little"
    assert data["weak_topics"] == [topics[0]["topic_id"], topics[1]["topic_id"]]
    assert data["explanation_style"] == "step_by_step"


def test_diagnostic_profile_rejects_topic_outside_current_material_scope(
    api_context: tuple[TestClient, DiagnosticApiProvider],
) -> None:
    client, _ = api_context
    token = register_and_token(client, "diagnostic_stale")
    course_id = create_course(client, token)
    material_id = upload_and_parse_material(
        client,
        token,
        course_id,
        "stale-topic.md",
        "# 当前资料主题\n当前资料只包含这个主题。",
    )

    response = client.post(
        f"/api/v1/courses/{course_id}/study-plan-diagnostic-profiles",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_version": "study_plan_diagnostic_v1",
            "topic_mastery": [
                {"topic_id": "topic_from_old_scope", "topic_title": "旧资料主题", "mastery_level": "heard"},
            ],
            "weak_area": "concept",
            "material_scope": {"include_all_parsed_materials": False, "material_ids": [material_id]},
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DIAGNOSTIC_STALE"
    assert response.json()["error"]["details"]["invalid_topic_ids"] == ["topic_from_old_scope"]


def test_diagnostic_profile_can_be_sent_to_preview(
    api_context: tuple[TestClient, DiagnosticApiProvider],
) -> None:
    client, _ = api_context
    token = register_and_token(client, "diagnostic_preview")
    course_id = create_course(client, token)
    material_id = upload_and_parse_material(
        client,
        token,
        course_id,
        "preview-topic.md",
        "# 信道容量\nNyquist 和 Shannon 公式。",
    )
    question_response = client.post(
        f"/api/v1/courses/{course_id}/study-plan-diagnostic-questions",
        headers={"Authorization": f"Bearer {token}"},
        json=_diagnostic_questions_payload(material_id),
    )
    topic = _topic_questions(question_response.json()["data"])[0]
    profile_response = client.post(
        f"/api/v1/courses/{course_id}/study-plan-diagnostic-profiles",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question_version": "study_plan_diagnostic_v1",
            "topic_mastery": [
                {"topic_id": topic["topic_id"], "topic_title": topic["topic_title"], "mastery_level": "heard"},
            ],
            "weak_area": "calculation",
            "material_scope": {"include_all_parsed_materials": False, "material_ids": [material_id]},
        },
    )
    diagnostic_profile = profile_response.json()["data"]

    response = client.post(
        f"/api/v1/courses/{course_id}/study-plans/preview",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "goal_text": "两天复习物理层核心内容",
            "start_date": "2026-07-12",
            "duration_days": 1,
            "daily_available_minutes": 60,
            "preference": "balanced",
            "diagnostic_profile": diagnostic_profile,
            "material_scope": {"include_all_parsed_materials": False, "material_ids": [material_id]},
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["diagnostic_profile"] == diagnostic_profile
