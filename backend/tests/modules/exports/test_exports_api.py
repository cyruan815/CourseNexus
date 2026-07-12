from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
import app.db.models  # noqa: F401
from app.main import app
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.models import Course
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.materials.models import CourseMaterial
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
    try:
        yield ApiHarness(client=TestClient(app), db=session)
    finally:
        app.dependency_overrides.clear()
        session.close()


def _register_user_and_headers(api: ApiHarness, *, username: str = "alice") -> tuple[str, dict[str, str]]:
    response = api.client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    user_id = api.db.execute(select(User).where(User.username == username)).scalar_one().id
    return user_id, {"Authorization": f"Bearer {token}"}


def _seed_task_content_plan(
    api: ApiHarness,
    *,
    user_id: str,
    suffix: str = "exports",
    subtask_type: str = "quiz",
) -> str:
    course_id = f"crs_{suffix}"
    task_id = f"task_{suffix}"
    subtask_id = f"sub_{suffix}"
    api.db.add(Course(id=course_id, user_id=user_id, name="数据库", status="active"))
    api.db.add(
        CourseMaterial(
            id=f"mat_{suffix}",
            user_id=user_id,
            course_id=course_id,
            name="数据库讲义.pdf",
            material_type="pdf",
            source_type="file",
            file_url="/uploads/db.pdf",
            parse_status="parsed",
        )
    )
    api.db.add(
        StudyPlan(
            id=f"sp_{suffix}",
            user_id=user_id,
            course_id=course_id,
            title="数据库计划",
            goal_text="学习数据库",
            parsed_config_json={},
            start_date=date(2026, 7, 13),
            end_date=date(2026, 7, 13),
            daily_available_minutes=60,
            status="active",
        )
    )
    api.db.add(
        StudyTask(
            id=task_id,
            plan_id=f"sp_{suffix}",
            course_id=course_id,
            title="学习主键",
            task_date=date(2026, 7, 13),
            status="not_started",
            sort_order=1,
        )
    )
    api.db.add(
        StudySubTask(
            id=subtask_id,
            task_id=task_id,
            plan_id=f"sp_{suffix}",
            course_id=course_id,
            title="任务测试",
            subtask_type=subtask_type,
            description="完成测试题",
            related_material_ids_json=[f"mat_{suffix}"],
            status="not_started",
            sort_order=1,
        )
    )
    api.db.commit()
    return subtask_id


def _task_test_json(*, source_citation_ids: list[str] | None = None) -> dict[str, object]:
    return {
        "instructions": "完成下列题目。",
        "questions": [
            {
                "id": "q_1",
                "question_type": "single_choice",
                "question_text": "主键的作用是什么？",
                "options": [{"id": "A", "text": "唯一标识一行"}, {"id": "B", "text": "存储图片"}],
                "correct_answer": "A",
                "explanation": "主键用于唯一标识表中的一行。",
                "source_citation_ids": ["cit_task_test"] if source_citation_ids is None else source_citation_ids,
                "sort_order": 1,
            }
        ],
    }


def _handout_json(*, source_citation_ids: list[str] | None = None) -> dict[str, object]:
    return {
        "overview": "学习关系模型。",
        "learning_objectives": ["解释主键和关系"],
        "sections": [
            {
                "id": "sec_1",
                "title": "主键",
                "body": "主键用于唯一标识表中的一行。",
                "key_points": ["唯一标识"],
                "source_citation_ids": ["cit_task_test"] if source_citation_ids is None else source_citation_ids,
                "sort_order": 1,
            }
        ],
        "summary": "完成主键概念学习。",
    }


def _default_content_json(content_type: str) -> dict[str, object]:
    if content_type == "handout":
        return _handout_json()
    return _task_test_json()


def _seed_generated_content(
    api: ApiHarness,
    *,
    user_id: str,
    subtask_id: str,
    content_id: str = "gen_task_test",
    content_type: str = "task_test",
    generation_status: str = "success",
    content_json: dict[str, object] | None = None,
    with_citation: bool = True,
) -> str:
    subtask = api.db.get(StudySubTask, subtask_id)
    assert subtask is not None
    content = AIGeneratedContent(
        id=content_id,
        user_id=user_id,
        course_id=subtask.course_id,
        study_subtask_id=subtask_id,
        content_type=content_type,
        title="今日讲义" if content_type == "handout" else "任务测试题",
        content=None,
        content_json=_default_content_json(content_type) if content_json is None else content_json,
        generation_status=generation_status,
        material_scope_json={"include_all_parsed_materials": False, "material_ids": subtask.related_material_ids_json},
    )
    api.db.add(content)
    if with_citation:
        api.db.add(
            SourceCitation(
                id="cit_task_test",
                generated_content_id=content_id,
                material_id=subtask.related_material_ids_json[0],
                chunk_id="chunk_task_test",
                material_name="数据库讲义.pdf",
                page="1",
                page_index=0,
                hit_text="主键用于唯一标识表中的一行。",
                sort_order=1,
            )
        )
    api.db.commit()
    return content_id


def test_export_task_test_markdown_success(api: ApiHarness) -> None:
    user_id, headers = _register_user_and_headers(api)
    subtask_id = _seed_task_content_plan(api, user_id=user_id)
    content_id = _seed_generated_content(api, user_id=user_id, subtask_id=subtask_id)

    response = api.client.get(f"/api/v1/generated-contents/{content_id}/exports/markdown", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["content-disposition"] == 'attachment; filename="task-test-gen_task_test.md"'
    body = response.text
    assert "# 任务测试题" in body
    assert "## Instructions" in body
    assert "完成下列题目。" in body
    assert "### 1. 主键的作用是什么？" in body
    assert "- A. 唯一标识一行" in body
    assert "Answer: A" in body
    assert "Explanation: 主键用于唯一标识表中的一行。" in body
    assert "- 数据库讲义.pdf, p.1: 主键用于唯一标识表中的一行。" in body


def test_export_task_test_markdown_returns_not_found_for_cross_user_content(api: ApiHarness) -> None:
    alice_id, _ = _register_user_and_headers(api, username="alice")
    _, bob_headers = _register_user_and_headers(api, username="bob")
    subtask_id = _seed_task_content_plan(api, user_id=alice_id)
    content_id = _seed_generated_content(api, user_id=alice_id, subtask_id=subtask_id)

    response = api.client.get(f"/api/v1/generated-contents/{content_id}/exports/markdown", headers=bob_headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_export_markdown_rejects_non_task_test_content(api: ApiHarness) -> None:
    user_id, headers = _register_user_and_headers(api)
    subtask_id = _seed_task_content_plan(api, user_id=user_id)
    content_id = _seed_generated_content(api, user_id=user_id, subtask_id=subtask_id, content_type="handout")

    response = api.client.get(f"/api/v1/generated-contents/{content_id}/exports/markdown", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EXPORT_UNSUPPORTED_CONTENT_TYPE"


def test_export_markdown_rejects_non_success_content(api: ApiHarness) -> None:
    user_id, headers = _register_user_and_headers(api)
    subtask_id = _seed_task_content_plan(api, user_id=user_id)
    content_id = _seed_generated_content(
        api,
        user_id=user_id,
        subtask_id=subtask_id,
        generation_status="generating",
    )

    response = api.client.get(f"/api/v1/generated-contents/{content_id}/exports/markdown", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EXPORT_CONTENT_NOT_READY"


def test_export_markdown_rejects_invalid_task_test_content(api: ApiHarness) -> None:
    user_id, headers = _register_user_and_headers(api)
    subtask_id = _seed_task_content_plan(api, user_id=user_id)
    content_id = _seed_generated_content(
        api,
        user_id=user_id,
        subtask_id=subtask_id,
        content_json={"instructions": "完成下列题目。", "questions": []},
    )

    response = api.client.get(f"/api/v1/generated-contents/{content_id}/exports/markdown", headers=headers)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "EXPORT_CONTENT_INVALID"


def test_export_markdown_uses_unavailable_when_question_citation_is_missing(api: ApiHarness) -> None:
    user_id, headers = _register_user_and_headers(api)
    subtask_id = _seed_task_content_plan(api, user_id=user_id)
    content_id = _seed_generated_content(
        api,
        user_id=user_id,
        subtask_id=subtask_id,
        content_json=_task_test_json(source_citation_ids=["cit_missing"]),
        with_citation=False,
    )

    response = api.client.get(f"/api/v1/generated-contents/{content_id}/exports/markdown", headers=headers)

    assert response.status_code == 200
    assert "Sources: unavailable" in response.text


def test_export_handout_pdf_success(api: ApiHarness) -> None:
    user_id, headers = _register_user_and_headers(api)
    subtask_id = _seed_task_content_plan(api, user_id=user_id, subtask_type="learn")
    content_id = _seed_generated_content(
        api,
        user_id=user_id,
        subtask_id=subtask_id,
        content_id="gen_handout",
        content_type="handout",
    )

    response = api.client.get(f"/api/v1/generated-contents/{content_id}/exports/pdf", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="handout-gen_handout.pdf"'
    assert response.content.startswith(b"%PDF-1.4")
    assert b"/Type /Catalog" in response.content
    assert b"%%EOF" in response.content


def test_export_handout_pdf_returns_not_found_for_cross_user_content(api: ApiHarness) -> None:
    alice_id, _ = _register_user_and_headers(api, username="alice")
    _, bob_headers = _register_user_and_headers(api, username="bob")
    subtask_id = _seed_task_content_plan(api, user_id=alice_id, subtask_type="learn")
    content_id = _seed_generated_content(
        api,
        user_id=alice_id,
        subtask_id=subtask_id,
        content_id="gen_handout",
        content_type="handout",
    )

    response = api.client.get(f"/api/v1/generated-contents/{content_id}/exports/pdf", headers=bob_headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_export_pdf_rejects_task_test_content(api: ApiHarness) -> None:
    user_id, headers = _register_user_and_headers(api)
    subtask_id = _seed_task_content_plan(api, user_id=user_id)
    content_id = _seed_generated_content(api, user_id=user_id, subtask_id=subtask_id)

    response = api.client.get(f"/api/v1/generated-contents/{content_id}/exports/pdf", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EXPORT_UNSUPPORTED_CONTENT_TYPE"


@pytest.mark.parametrize("generation_status", ["generating", "failed"])
def test_export_pdf_rejects_non_success_handout_content(api: ApiHarness, generation_status: str) -> None:
    user_id, headers = _register_user_and_headers(api)
    subtask_id = _seed_task_content_plan(api, user_id=user_id, subtask_type="learn")
    content_id = _seed_generated_content(
        api,
        user_id=user_id,
        subtask_id=subtask_id,
        content_id="gen_handout",
        content_type="handout",
        generation_status=generation_status,
    )

    response = api.client.get(f"/api/v1/generated-contents/{content_id}/exports/pdf", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EXPORT_CONTENT_NOT_READY"


def test_export_pdf_rejects_invalid_handout_content(api: ApiHarness) -> None:
    user_id, headers = _register_user_and_headers(api)
    subtask_id = _seed_task_content_plan(api, user_id=user_id, subtask_type="learn")
    content_id = _seed_generated_content(
        api,
        user_id=user_id,
        subtask_id=subtask_id,
        content_id="gen_handout",
        content_type="handout",
        content_json={"overview": "学习关系模型。", "sections": []},
    )

    response = api.client.get(f"/api/v1/generated-contents/{content_id}/exports/pdf", headers=headers)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "EXPORT_CONTENT_INVALID"


def test_export_pdf_returns_export_failed_when_renderer_fails(api: ApiHarness, monkeypatch: pytest.MonkeyPatch) -> None:
    user_id, headers = _register_user_and_headers(api)
    subtask_id = _seed_task_content_plan(api, user_id=user_id, subtask_type="learn")
    content_id = _seed_generated_content(
        api,
        user_id=user_id,
        subtask_id=subtask_id,
        content_id="gen_handout",
        content_type="handout",
    )

    from app.modules.exports import service as export_service

    def broken_renderer(content: object) -> bytes:
        raise RuntimeError("pdf unavailable")

    monkeypatch.setattr(export_service, "render_handout_pdf", broken_renderer)

    response = api.client.get(f"/api/v1/generated-contents/{content_id}/exports/pdf", headers=headers)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "EXPORT_FAILED"
