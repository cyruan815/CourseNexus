from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
import app.db.models  # noqa: F401
from app.integrations.model_provider.mock import MockModelProvider
from app.main import app
from app.modules.checkins.models import CheckinRecord
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.models import Course
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generation.generators.handout.schemas import HandoutContent
from app.modules.generation.generators.task_test.schemas import TaskTestContent
from app.modules.learning_execution import router as learning_router
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
                "schema_version": 2,
                "title": "数据库约束讲义",
                "overview": "学习数据库约束。",
                "learning_objectives": ["解释主键", "解释外键"],
                "sections": [
                    {
                        "id": "sec_1",
                        "title": "主键与外键",
                        "blocks": [{"type": "paragraph", "text": "主键唯一标识一行，外键表达表之间的关系。"}],
                        "key_points": ["主键唯一", "外键关联"],
                        "source_citation_ids": ["chunk_flow_1", "chunk_flow_2"],
                        "sort_order": 1,
                    }
                ],
                "summary": "完成数据库约束学习。",
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
                        "options": [{"id": "A", "text": "唯一标识一行"}, {"id": "B", "text": "表达外键"}, {"id": "C", "text": "存储图片"}, {"id": "D", "text": "删除数据"}],
                        "correct_answer": "A",
                        "explanation": "主键唯一标识一行。",
                        "source_citation_ids": ["chunk_flow_1", "chunk_flow_2"],
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
    response = api.client.post("/api/v1/auth/register", json={"username": "alice", "password": "password123"})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    user_id = api.db.execute(select(User).where(User.username == "alice")).scalar_one().id
    return user_id, {"Authorization": f"Bearer {token}"}


def _seed_plan_with_materials(db: Session, *, user_id: str) -> tuple[str, str]:
    db.add(Course(id="crs_flow", user_id=user_id, name="数据库", status="active"))
    for material_id, chunk_id, name, text in [
        ("mat_flow_1", "chunk_flow_1", "主键.pdf", "主键用于唯一标识表中的一行。"),
        ("mat_flow_2", "chunk_flow_2", "外键.pdf", "外键用于表达两个表之间的关系。"),
    ]:
        db.add(
            CourseMaterial(
                id=material_id,
                user_id=user_id,
                course_id="crs_flow",
                name=name,
                material_type="pdf",
                source_type="file",
                file_url=f"/uploads/{name}",
                parse_status="parsed",
            )
        )
        db.add(
            MaterialChunk(
                id=chunk_id,
                material_id=material_id,
                course_id="crs_flow",
                chunk_index=0,
                page="1",
                page_index=0,
                heading=name,
                content_text=text,
            )
        )

    db.add(
        StudyPlan(
            id="sp_flow",
            user_id=user_id,
            course_id="crs_flow",
            title="数据库计划",
            goal_text="学习数据库约束",
            parsed_config_json={},
            start_date=date(2026, 7, 12),
            end_date=date(2026, 7, 12),
            daily_available_minutes=60,
            status="active",
        )
    )
    db.add(
        StudyTask(
            id="task_flow",
            plan_id="sp_flow",
            course_id="crs_flow",
            title="数据库约束",
            task_date=date(2026, 7, 12),
            status="not_started",
            sort_order=1,
        )
    )
    db.add(
        StudySubTask(
            id="sub_flow_learn",
            task_id="task_flow",
            plan_id="sp_flow",
            course_id="crs_flow",
            title="学习约束",
            subtask_type="learn",
            description="学习主键和外键",
            related_material_ids_json=["mat_flow_1", "mat_flow_2"],
            status="not_started",
            sort_order=1,
        )
    )
    db.add(
        StudySubTask(
            id="sub_flow_quiz",
            task_id="task_flow",
            plan_id="sp_flow",
            course_id="crs_flow",
            title="测试约束",
            subtask_type="quiz",
            description="测试主键和外键",
            related_material_ids_json=["mat_flow_1", "mat_flow_2"],
            status="not_started",
            sort_order=2,
        )
    )
    db.commit()
    return "sub_flow_learn", "sub_flow_quiz"


def _set_content_created_at(db: Session, *, content_id: str, created_at: datetime) -> None:
    content = db.get(AIGeneratedContent, content_id)
    assert content is not None
    content.created_at = created_at
    db.add(content)
    db.commit()


def test_task_content_generation_flow_preserves_task_and_checkin_state(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    learn_subtask_id, quiz_subtask_id = _seed_plan_with_materials(api.db, user_id=user_id)

    handout_response = api.client.post(
        f"/api/v1/study-subtasks/{learn_subtask_id}/handouts",
        headers=headers,
        json={"parameters": {}},
    )
    task_test_response = api.client.post(
        f"/api/v1/study-subtasks/{quiz_subtask_id}/task-tests",
        headers=headers,
        json={"parameters": {"question_count": 1}},
    )

    assert handout_response.status_code == 200
    assert task_test_response.status_code == 200
    handout = handout_response.json()["data"]
    task_test = task_test_response.json()["data"]
    assert handout["study_subtask_id"] == learn_subtask_id
    assert task_test["study_subtask_id"] == quiz_subtask_id
    assert handout["source_citations"]
    assert task_test["source_citations"]
    handout_citation_ids = {citation["id"] for citation in handout["source_citations"]}
    task_test_citation_ids = {citation["id"] for citation in task_test["source_citations"]}
    assert set(handout["content_json"]["sections"][0]["source_citation_ids"]).issubset(handout_citation_ids)
    assert set(task_test["content_json"]["questions"][0]["source_citation_ids"]).issubset(task_test_citation_ids)

    learn_context = api.client.get(f"/api/v1/study-subtasks/{learn_subtask_id}/execution-context", headers=headers).json()["data"]
    quiz_context = api.client.get(f"/api/v1/study-subtasks/{quiz_subtask_id}/execution-context", headers=headers).json()["data"]
    assert learn_context["handout_content_id"] == handout["id"]
    assert quiz_context["task_test_content_id"] == task_test["id"]

    handout_citations = api.db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == handout["id"])).scalars().all()
    task_test_citations = api.db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == task_test["id"])).scalars().all()
    assert {citation.chunk_id for citation in handout_citations} == {"chunk_flow_1", "chunk_flow_2"}
    assert {citation.chunk_id for citation in task_test_citations} == {"chunk_flow_1", "chunk_flow_2"}

    markdown_response = api.client.get(f"/api/v1/generated-contents/{task_test['id']}/exports/markdown", headers=headers)
    assert markdown_response.status_code == 200
    assert "Sources: unavailable" not in markdown_response.text
    assert "主键.pdf, p.1" in markdown_response.text

    learn_subtask = api.db.get(StudySubTask, learn_subtask_id)
    quiz_subtask = api.db.get(StudySubTask, quiz_subtask_id)
    task = api.db.get(StudyTask, "task_flow")
    assert learn_subtask is not None
    assert quiz_subtask is not None
    assert task is not None
    assert learn_subtask.status == "not_started"
    assert quiz_subtask.status == "not_started"
    assert task.status == "not_started"
    assert api.db.execute(select(CheckinRecord)).scalars().all() == []


def test_execution_context_returns_latest_successful_task_content_after_regeneration(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    learn_subtask_id, quiz_subtask_id = _seed_plan_with_materials(api.db, user_id=user_id)

    first_handout_response = api.client.post(
        f"/api/v1/study-subtasks/{learn_subtask_id}/handouts",
        headers=headers,
        json={"parameters": {}},
    )
    first_task_test_response = api.client.post(
        f"/api/v1/study-subtasks/{quiz_subtask_id}/task-tests",
        headers=headers,
        json={"parameters": {"question_count": 1}},
    )
    assert first_handout_response.status_code == 200
    assert first_task_test_response.status_code == 200
    first_handout = first_handout_response.json()["data"]
    first_task_test = first_task_test_response.json()["data"]

    stale_created_at = datetime(2000, 1, 1)
    _set_content_created_at(api.db, content_id=first_handout["id"], created_at=stale_created_at)
    _set_content_created_at(api.db, content_id=first_task_test["id"], created_at=stale_created_at)

    second_handout_response = api.client.post(
        f"/api/v1/study-subtasks/{learn_subtask_id}/handouts",
        headers=headers,
        json={"force_regenerate": True, "parameters": {}},
    )
    second_task_test_response = api.client.post(
        f"/api/v1/study-subtasks/{quiz_subtask_id}/task-tests",
        headers=headers,
        json={"force_regenerate": True, "parameters": {"question_count": 1}},
    )
    assert second_handout_response.status_code == 200
    assert second_task_test_response.status_code == 200
    second_handout = second_handout_response.json()["data"]
    second_task_test = second_task_test_response.json()["data"]

    api.db.add(
        AIGeneratedContent(
            id="gen_flow_failed_handout_latest",
            user_id=user_id,
            course_id="crs_flow",
            study_subtask_id=learn_subtask_id,
            content_type="handout",
            title="失败讲义",
            generation_status="failed",
            error_code="GENERATION_FAILED",
            created_at=datetime(2099, 1, 1),
        )
    )
    api.db.add(
        AIGeneratedContent(
            id="gen_flow_failed_task_test_latest",
            user_id=user_id,
            course_id="crs_flow",
            study_subtask_id=quiz_subtask_id,
            content_type="task_test",
            title="失败测试题",
            generation_status="failed",
            error_code="GENERATION_FAILED",
            created_at=datetime(2099, 1, 1),
        )
    )
    api.db.commit()
    learn_context_response = api.client.get(f"/api/v1/study-subtasks/{learn_subtask_id}/execution-context", headers=headers)
    quiz_context_response = api.client.get(f"/api/v1/study-subtasks/{quiz_subtask_id}/execution-context", headers=headers)
    assert learn_context_response.status_code == 200, learn_context_response.text
    assert quiz_context_response.status_code == 200, quiz_context_response.text
    learn_context = learn_context_response.json()["data"]
    quiz_context = quiz_context_response.json()["data"]
    assert learn_context["handout_content_id"] == second_handout["id"]
    assert quiz_context["task_test_content_id"] == second_task_test["id"]


def test_task_test_generation_defaults_to_saved_subtask_parameters(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    _, quiz_subtask_id = _seed_plan_with_materials(api.db, user_id=user_id)
    plan = api.db.get(StudyPlan, "sp_flow")
    assert plan is not None
    plan.parsed_config_json = {
        "task_snapshot": [
            {
                "sort_order": 1,
                "subtasks": [
                    {"sort_order": 1},
                    {
                        "sort_order": 2,
                        "generation_parameters": {
                            "task_test": {
                                "question_count": 2,
                                "question_types": ["single_choice", "short_answer"],
                                "question_type_counts": [
                                    {"question_type": "single_choice", "question_count": 1},
                                    {"question_type": "short_answer", "question_count": 1},
                                ],
                                "difficulty": "hard",
                            }
                        },
                    },
                ],
            }
        ]
    }
    api.db.add(plan)
    api.db.commit()

    app.dependency_overrides[learning_router.get_task_test_model_provider] = lambda: MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [
                    {
                        "id": "q_1",
                        "question_type": "single_choice",
                        "question_text": "主键的作用是什么？",
                        "options": [{"id": "A", "text": "唯一标识一行"}, {"id": "B", "text": "表达外键"}, {"id": "C", "text": "存储图片"}, {"id": "D", "text": "删除数据"}],
                        "correct_answer": "A",
                        "explanation": "主键唯一标识一行。",
                        "source_citation_ids": ["chunk_flow_1"],
                        "sort_order": 1,
                    },
                    {
                        "id": "q_2",
                        "question_type": "short_answer",
                        "question_text": "说明外键的作用。",
                        "options": [],
                        "correct_answer": "外键用于表达两个表之间的关系。",
                        "explanation": "外键把一张表的字段关联到另一张表的主键或唯一键。",
                        "source_citation_ids": ["chunk_flow_2"],
                        "sort_order": 2,
                    },
                ],
            }
        }
    )

    response = api.client.post(
        f"/api/v1/study-subtasks/{quiz_subtask_id}/task-tests",
        headers=headers,
        json={"force_regenerate": True},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    questions = data["content_json"]["questions"]
    assert len(questions) == 2
    assert [question["question_type"] for question in questions] == ["single_choice", "short_answer"]
