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
                        "options": [{"id": "A", "text": "唯一标识一行"}, {"id": "B", "text": "存储图片"}],
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
    response = api.client.post("/api/v1/auth/register", json={"username": "alice", "password": "password123"})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    user_id = api.db.execute(select(User).where(User.username == "alice")).scalar_one().id
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


def test_generate_handout_rejects_quiz_subtask(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/handouts", headers=headers, json={"parameters": {}})

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
