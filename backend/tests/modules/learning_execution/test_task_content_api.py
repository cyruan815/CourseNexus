from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.db.base import Base
from app.db.session import get_db
import app.db.models  # noqa: F401
from app.integrations.model_provider.mock import MockModelProvider
from app.main import app
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.models import Course
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generation.generators.handout.schemas import HandoutContent
from app.modules.generation.generators.task_test.schemas import TaskTestContent
from app.modules.learning_execution import router as learning_router
from app.modules.learning_execution.service import generate_task_test_for_subtask
from app.modules.materials.models import CourseMaterial, MaterialChunk
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask
from app.modules.users.models import User


@dataclass(frozen=True)
class ApiHarness:
    client: TestClient
    db: Session


@pytest.fixture()
def api() -> Generator[ApiHarness, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = testing_session()

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[learning_router.get_handout_model_provider] = lambda: MockModelProvider(
        structured_outputs={
            HandoutContent: {
                "overview": "学习关系模型。",
                "learning_objectives": ["解释主键和关系"],
                "sections": [
                    {
                        "id": "sec_1",
                        "title": "主键",
                        "body": "主键用于唯一标识表中的一行。",
                        "key_points": ["唯一标识"],
                        "source_citation_ids": ["chunk_api_content"],
                        "sort_order": 1,
                    }
                ],
                "summary": "完成主键概念学习。",
            }
        }
    )
    app.dependency_overrides[learning_router.get_task_test_model_provider] = lambda: MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [
                    {
                        "id": "q_1",
                        "question_type": "single_choice",
                        "question_text": "主键的作用是什么？",
                        "options": [{"id": "A", "text": "唯一标识一行"}, {"id": "B", "text": "存储图片"}, {"id": "C", "text": "表达外键"}, {"id": "D", "text": "删除数据"}],
                        "correct_answer": "A",
                        "explanation": "主键用于唯一标识表中的一行。",
                        "source_citation_ids": ["chunk_api_content"],
                        "sort_order": 1,
                    }
                ],
            }
        }
    )
    try:
        yield ApiHarness(client=TestClient(app), db=session)
    finally:
        app.dependency_overrides.clear()
        session.close()


def _register_and_headers(api: ApiHarness) -> tuple[str, dict[str, str]]:
    return _register_user_and_headers(api, username="alice")


def _register_user_and_headers(api: ApiHarness, *, username: str) -> tuple[str, dict[str, str]]:
    response = api.client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    user_id = api.db.execute(select(User).where(User.username == username)).scalar_one().id
    return user_id, {"Authorization": f"Bearer {token}"}


def _seed_task_content_plan(
    db: Session,
    *,
    user_id: str,
    subtask_type: str,
    material_ids: list[str] | None = None,
) -> str:
    db.add(Course(id="crs_api_content", user_id=user_id, name="数据库", status="active"))
    db.add(
        CourseMaterial(
            id="mat_api_content",
            user_id=user_id,
            course_id="crs_api_content",
            name="数据库讲义.pdf",
            material_type="pdf",
            source_type="file",
            file_url="/uploads/db.pdf",
            parse_status="parsed",
        )
    )
    db.add(
        MaterialChunk(
            id="chunk_api_content",
            material_id="mat_api_content",
            course_id="crs_api_content",
            chunk_index=0,
            page="1",
            page_index=0,
            heading="主键",
            content_text="主键用于唯一标识表中的一行。",
        )
    )
    db.add(
        StudyPlan(
            id="sp_api_content",
            user_id=user_id,
            course_id="crs_api_content",
            title="数据库计划",
            goal_text="学习数据库",
            parsed_config_json={},
            start_date=date(2026, 7, 12),
            end_date=date(2026, 7, 12),
            daily_available_minutes=60,
            status="active",
        )
    )
    db.add(
        StudyTask(
            id="task_api_content",
            plan_id="sp_api_content",
            course_id="crs_api_content",
            title="学习主键",
            task_date=date(2026, 7, 12),
            status="not_started",
            sort_order=1,
        )
    )
    subtask_id = f"sub_api_content_{subtask_type}"
    db.add(
        StudySubTask(
            id=subtask_id,
            task_id="task_api_content",
            plan_id="sp_api_content",
            course_id="crs_api_content",
            title="任务内容",
            subtask_type=subtask_type,
            description="生成任务内容",
            related_material_ids_json=["mat_api_content"] if material_ids is None else material_ids,
            status="not_started",
            sort_order=1,
        )
    )
    db.commit()
    return subtask_id


def _add_related_material_without_chunks(db: Session, *, user_id: str, subtask_id: str) -> None:
    db.add(
        CourseMaterial(
            id="mat_api_content_empty",
            user_id=user_id,
            course_id="crs_api_content",
            name="空资料.pdf",
            material_type="pdf",
            source_type="file",
            file_url="/uploads/empty.pdf",
            parse_status="parsed",
        )
    )
    subtask = db.get(StudySubTask, subtask_id)
    assert subtask is not None
    subtask.related_material_ids_json = ["mat_api_content", "mat_api_content_empty"]
    db.add(subtask)
    db.commit()


def _add_related_material_with_chunk(db: Session, *, user_id: str, subtask_id: str) -> None:
    db.add(
        CourseMaterial(
            id="mat_api_content_second",
            user_id=user_id,
            course_id="crs_api_content",
            name="索引讲义.pdf",
            material_type="pdf",
            source_type="file",
            file_url="/uploads/index.pdf",
            parse_status="parsed",
        )
    )
    db.add(
        MaterialChunk(
            id="chunk_api_content_second",
            material_id="mat_api_content_second",
            course_id="crs_api_content",
            chunk_index=0,
            page="2",
            page_index=1,
            heading="索引",
            content_text="索引用于提高查询效率。",
        )
    )
    subtask = db.get(StudySubTask, subtask_id)
    assert subtask is not None
    subtask.related_material_ids_json = ["mat_api_content", "mat_api_content_second"]
    db.add(subtask)
    db.commit()


class CountingTaskTestModelProvider:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def answer_question(self, *, question, context_chunks):  # pragma: no cover - unused in S06 tests
        raise AssertionError("answer_question should not be called")

    def generate_structured(self, *, prompt, output_schema):
        self.prompts.append(prompt)
        assert output_schema is TaskTestContent
        return TaskTestContent.model_validate(
            {
                "instructions": "完成下列题目。",
                "questions": [
                    {
                        "id": "q_1",
                        "question_type": "single_choice",
                        "question_text": "主键的作用是什么？",
                        "options": [{"id": "A", "text": "唯一标识一行"}, {"id": "B", "text": "存储图片"}, {"id": "C", "text": "表达外键"}, {"id": "D", "text": "删除数据"}],
                        "correct_answer": "A",
                        "explanation": "主键用于唯一标识表中的一行。",
                        "source_citation_ids": ["chunk_api_content"],
                        "sort_order": 1,
                    },
                    {
                        "id": "q_2",
                        "question_type": "single_choice",
                        "question_text": "索引的作用是什么？",
                        "options": [{"id": "A", "text": "提高查询效率"}, {"id": "B", "text": "删除主键"}, {"id": "C", "text": "降低查询效率"}, {"id": "D", "text": "清空数据"}],
                        "correct_answer": "A",
                        "explanation": "索引用于提高查询效率。",
                        "source_citation_ids": ["chunk_api_content_second"],
                        "sort_order": 2,
                    },
                ],
            }
        )


class BrokenModelProvider:
    def answer_question(self, *, question, context_chunks):  # pragma: no cover - unused in S06 tests
        raise AssertionError("answer_question should not be called")

    def generate_structured(self, *, prompt, output_schema):
        raise RuntimeError("model unavailable")


def _successful_contents(db: Session, *, subtask_id: str, content_type: str) -> list[AIGeneratedContent]:
    return list(
        db.execute(
            select(AIGeneratedContent)
            .where(
                AIGeneratedContent.study_subtask_id == subtask_id,
                AIGeneratedContent.content_type == content_type,
                AIGeneratedContent.generation_status == "success",
            )
            .order_by(AIGeneratedContent.created_at, AIGeneratedContent.id)
        ).scalars()
    )


def test_generate_handout_for_learn_subtask_saves_content_and_citations(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")

    response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/handouts",
        headers=headers,
        json={"parameters": {"language": "zh-CN", "detail_level": "standard"}},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["content_type"] == "handout"
    assert data["study_subtask_id"] == subtask_id
    assert data["generation_status"] == "success"
    assert data["content_json"]["overview"] == "学习关系模型。"
    content = api.db.get(AIGeneratedContent, data["id"])
    assert content is not None
    assert content.study_subtask_id == subtask_id
    citations = api.db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == data["id"])).scalars().all()
    assert [citation.chunk_id for citation in citations] == ["chunk_api_content"]


def test_generate_task_test_for_quiz_subtask_saves_content(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")

    response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/task-tests",
        headers=headers,
        json={"parameters": {"question_count": 1, "question_types": ["single_choice"], "difficulty": "medium"}},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["content_type"] == "task_test"
    assert data["study_subtask_id"] == subtask_id
    assert data["generation_status"] == "success"
    assert data["content_json"]["questions"][0]["question_type"] == "single_choice"


def test_generate_task_test_multi_batch_generates_requested_question_count_once(api: ApiHarness) -> None:
    user_id, _ = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")
    _add_related_material_with_chunk(api.db, user_id=user_id, subtask_id=subtask_id)
    provider = CountingTaskTestModelProvider()

    result = generate_task_test_for_subtask(
        api.db,
        user_id=user_id,
        subtask_id=subtask_id,
        parameters={"question_count": 2, "question_types": ["single_choice"], "difficulty": "medium"},
        force_regenerate=True,
        model_provider=provider,
        max_tokens=1,
    )

    assert len(provider.prompts) == 1
    assert "chunk_api_content" in provider.prompts[0]
    assert "chunk_api_content_second" in provider.prompts[0]
    assert len(result.content_json["questions"]) == 2
    assert [question["id"] for question in result.content_json["questions"]] == ["q_1", "q_2"]
    citations = api.db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == result.id)).scalars().all()
    assert {citation.chunk_id for citation in citations} == {"chunk_api_content", "chunk_api_content_second"}


def test_generate_handout_is_idempotent_for_existing_success(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")

    first_response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/handouts",
        headers=headers,
        json={"parameters": {"language": "zh-CN", "detail_level": "standard"}},
    )
    assert first_response.status_code == 200
    first = first_response.json()["data"]

    app.dependency_overrides[learning_router.get_handout_model_provider] = lambda: BrokenModelProvider()
    second_response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/handouts",
        headers=headers,
        json={"parameters": {"language": "zh-CN", "detail_level": "standard"}},
    )

    assert second_response.status_code == 200
    second = second_response.json()["data"]
    assert second["id"] == first["id"]
    assert [content.id for content in _successful_contents(api.db, subtask_id=subtask_id, content_type="handout")] == [first["id"]]


def test_generate_task_test_is_idempotent_for_existing_success(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")

    first_response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/task-tests",
        headers=headers,
        json={"parameters": {"question_count": 1, "question_types": ["single_choice"], "difficulty": "medium"}},
    )
    assert first_response.status_code == 200
    first = first_response.json()["data"]

    app.dependency_overrides[learning_router.get_task_test_model_provider] = lambda: BrokenModelProvider()
    second_response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/task-tests",
        headers=headers,
        json={"parameters": {"question_count": 1, "question_types": ["single_choice"], "difficulty": "medium"}},
    )

    assert second_response.status_code == 200
    second = second_response.json()["data"]
    assert second["id"] == first["id"]
    assert [content.id for content in _successful_contents(api.db, subtask_id=subtask_id, content_type="task_test")] == [first["id"]]


def test_force_regenerate_handout_creates_new_success(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")

    first_response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/handouts",
        headers=headers,
        json={"parameters": {"language": "zh-CN", "detail_level": "standard"}},
    )
    second_response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/handouts",
        headers=headers,
        json={"force_regenerate": True, "parameters": {"language": "zh-CN", "detail_level": "standard"}},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first = first_response.json()["data"]
    second = second_response.json()["data"]
    assert second["id"] != first["id"]
    assert len(_successful_contents(api.db, subtask_id=subtask_id, content_type="handout")) == 2


def test_failed_task_test_record_does_not_block_retry(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")
    app.dependency_overrides[learning_router.get_task_test_model_provider] = lambda: BrokenModelProvider()

    failed_response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/task-tests", headers=headers, json={"parameters": {}})
    assert failed_response.status_code == 502
    failed = api.db.execute(select(AIGeneratedContent)).scalar_one()
    assert failed.generation_status == "failed"

    app.dependency_overrides[learning_router.get_task_test_model_provider] = lambda: MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [
                    {
                        "id": "q_1",
                        "question_type": "single_choice",
                        "question_text": "主键的作用是什么？",
                        "options": [{"id": "A", "text": "唯一标识一行"}, {"id": "B", "text": "存储图片"}, {"id": "C", "text": "表达外键"}, {"id": "D", "text": "删除数据"}],
                        "correct_answer": "A",
                        "explanation": "主键用于唯一标识表中的一行。",
                        "source_citation_ids": ["chunk_api_content"],
                        "sort_order": 1,
                    }
                ],
            }
        }
    )
    retry_response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/task-tests",
        headers=headers,
        json={"parameters": {"question_count": 1, "question_types": ["single_choice"], "difficulty": "medium"}},
    )

    assert retry_response.status_code == 200
    retry = retry_response.json()["data"]
    assert retry["id"] != failed.id
    assert retry["generation_status"] == "success"
    assert len(_successful_contents(api.db, subtask_id=subtask_id, content_type="task_test")) == 1


@pytest.mark.parametrize("subtask_type", ["quiz", "test"])
def test_generate_handout_rejects_quiz_and_test_subtasks(api: ApiHarness, subtask_type: str) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type=subtask_type)

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/handouts", headers=headers, json={"parameters": {}})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STATE_CONFLICT"
    assert api.db.execute(select(AIGeneratedContent)).scalars().all() == []


@pytest.mark.parametrize("subtask_type", ["learn", "review"])
def test_generate_task_test_rejects_learn_and_review_subtasks(api: ApiHarness, subtask_type: str) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type=subtask_type)

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/task-tests", headers=headers, json={"parameters": {}})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STATE_CONFLICT"
    assert api.db.execute(select(AIGeneratedContent)).scalars().all() == []


def test_generate_task_test_rejects_empty_material_scope_and_saves_failed_record(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz", material_ids=[])

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/task-tests", headers=headers, json={"parameters": {}})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "NO_PARSED_MATERIAL"
    content = api.db.execute(select(AIGeneratedContent)).scalar_one()
    assert content.content_type == "task_test"
    assert content.study_subtask_id == subtask_id
    assert content.generation_status == "failed"
    assert content.error_code == "NO_PARSED_MATERIAL"


def test_generate_task_content_requires_auth(api: ApiHarness) -> None:
    user_id, _ = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/handouts", json={"parameters": {}})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_generate_task_content_returns_not_found_for_missing_subtask(api: ApiHarness) -> None:
    _, headers = _register_and_headers(api)

    response = api.client.post("/api/v1/study-subtasks/sub_missing/handouts", headers=headers, json={"parameters": {}})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert api.db.execute(select(AIGeneratedContent)).scalars().all() == []


def test_generate_task_content_rejects_cross_user_subtask_without_failed_record(api: ApiHarness) -> None:
    alice_id, _ = _register_user_and_headers(api, username="alice")
    _, bob_headers = _register_user_and_headers(api, username="bob")
    subtask_id = _seed_task_content_plan(api.db, user_id=alice_id, subtask_type="learn")

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/handouts", headers=bob_headers, json={"parameters": {}})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert api.db.execute(select(AIGeneratedContent)).scalars().all() == []


def test_generate_task_content_rejects_invalid_request_parameters(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")

    response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/task-tests",
        headers=headers,
        json={"parameters": {"question_count": 0}},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert api.db.execute(select(AIGeneratedContent)).scalars().all() == []




def test_generate_task_test_with_stale_invalid_saved_parameters_saves_failed_record(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")
    plan = api.db.get(StudyPlan, "sp_api_content")
    assert plan is not None
    plan.parsed_config_json = {
        "task_snapshot": [
            {
                "sort_order": 1,
                "subtasks": [
                    {
                        "sort_order": 1,
                        "generation_parameters": {"task_test": {"question_count": 0}},
                    }
                ],
            }
        ]
    }
    api.db.add(plan)
    api.db.commit()

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/task-tests", headers=headers, json={"parameters": {}})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "GENERATION_SCHEMA_INVALID"
    content = api.db.execute(select(AIGeneratedContent)).scalar_one()
    assert content.content_type == "task_test"
    assert content.study_subtask_id == subtask_id
    assert content.generation_status == "failed"
    assert content.error_code == "GENERATION_SCHEMA_INVALID"
def test_generate_handout_schema_invalid_saves_failed_record(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")
    app.dependency_overrides[learning_router.get_handout_model_provider] = lambda: MockModelProvider(
        structured_outputs={
            HandoutContent: {
                "overview": "学习关系模型。",
                "learning_objectives": ["解释主键"],
                "sections": [
                    {
                        "id": "sec_1",
                        "title": "主键",
                        "body": "主键用于唯一标识表中的一行。",
                        "key_points": ["唯一标识"],
                        "source_citation_ids": ["chunk_not_in_context"],
                        "sort_order": 1,
                    }
                ],
                "summary": "完成主键概念学习。",
            }
        }
    )

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/handouts", headers=headers, json={"parameters": {}})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "GENERATION_SCHEMA_INVALID"
    content = api.db.execute(select(AIGeneratedContent)).scalar_one()
    assert content.content_type == "handout"
    assert content.study_subtask_id == subtask_id
    assert content.generation_status == "failed"
    assert content.error_code == "GENERATION_SCHEMA_INVALID"


def test_generate_task_test_model_failure_saves_failed_record(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")
    app.dependency_overrides[learning_router.get_task_test_model_provider] = lambda: BrokenModelProvider()

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/task-tests", headers=headers, json={"parameters": {}})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "GENERATION_FAILED"
    content = api.db.execute(select(AIGeneratedContent)).scalar_one()
    assert content.content_type == "task_test"
    assert content.study_subtask_id == subtask_id
    assert content.generation_status == "failed"
    assert content.error_code == "GENERATION_FAILED"


def test_generate_handout_material_coverage_incomplete_saves_failed_record(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")
    _add_related_material_without_chunks(api.db, user_id=user_id, subtask_id=subtask_id)

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/handouts", headers=headers, json={"parameters": {}})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "MATERIAL_COVERAGE_INCOMPLETE"
    content = api.db.execute(select(AIGeneratedContent)).scalar_one()
    assert content.content_type == "handout"
    assert content.study_subtask_id == subtask_id
    assert content.generation_status == "failed"
    assert content.error_code == "MATERIAL_COVERAGE_INCOMPLETE"
