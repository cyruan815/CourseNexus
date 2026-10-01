from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_retrieval_rag_index
from app.db.base import Base
from app.db.session import get_db
import app.db.models  # noqa: F401
from app.integrations.rag.base import RagChunk
from app.integrations.rag.fake import FakeRagIndex
from app.integrations.model_provider.mock import MockModelProvider
from app.main import app
from app.modules.checkins.models import CheckinRecord
from app.modules.course_qa.models import Conversation, Message
from app.modules.courses.models import Course
from app.modules.materials.models import CourseMaterial, MaterialChunk, MaterialParseVersion
from app.modules.learning_execution import router as learning_router
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask
from app.modules.users.models import User


@dataclass(frozen=True)
class ApiHarness:
    client: TestClient
    db: Session
    rag_index: FakeRagIndex


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
    rag_index = FakeRagIndex()

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_retrieval_rag_index] = lambda: rag_index
    app.dependency_overrides[learning_router.get_task_qa_model_provider] = (
        lambda: MockModelProvider()
    )
    try:
        yield ApiHarness(client=TestClient(app), db=session, rag_index=rag_index)
    finally:
        app.dependency_overrides.clear()
        session.close()


def _register_user_and_headers(api: ApiHarness, *, username: str) -> tuple[str, dict[str, str]]:
    response = api.client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    user_id = api.db.execute(select(User).where(User.username == username)).scalar_one().id
    return user_id, {"Authorization": f"Bearer {token}"}


def _seed_task_qa_plan(
    api: ApiHarness,
    *,
    user_id: str,
    related_material_ids: list[str] | None = None,
    include_chunks: bool = True,
    course_id: str = "crs_task_qa",
    subtask_id: str = "sub_task_qa",
) -> str:
    api.db.add(Course(id=course_id, user_id=user_id, name="Database Systems", status="active"))
    material_ids = ["mat_task_allowed"] if related_material_ids is None else related_material_ids
    for material_id in material_ids:
        parse_version_id = f"mpv_{material_id}" if include_chunks else None
        api.db.add(
            CourseMaterial(
                id=material_id,
                user_id=user_id,
                course_id=course_id,
                name=f"{material_id}.md",
                material_type="markdown",
                source_type="file",
                file_url=f"/uploads/{material_id}.md",
                parse_status="parsed" if include_chunks else "uploaded",
                active_parse_version_id=parse_version_id,
            )
        )
        if parse_version_id is not None:
            api.db.add(
                MaterialParseVersion(
                    id=parse_version_id,
                    material_id=material_id,
                    course_id=course_id,
                    user_id=user_id,
                    status="active",
                    parse_quality="complete",
                )
            )
    api.db.add(
        StudyPlan(
            id=f"sp_{subtask_id}",
            user_id=user_id,
            course_id=course_id,
            title="Database study plan",
            goal_text="Review database fundamentals",
            parsed_config_json={},
            start_date=date(2026, 7, 13),
            end_date=date(2026, 7, 13),
            daily_available_minutes=60,
            status="active",
        )
    )
    api.db.add(
        StudyTask(
            id=f"task_{subtask_id}",
            plan_id=f"sp_{subtask_id}",
            course_id=course_id,
            title="Study keys",
            task_date=date(2026, 7, 13),
            status="not_started",
            sort_order=1,
        )
    )
    api.db.add(
        StudySubTask(
            id=subtask_id,
            task_id=f"task_{subtask_id}",
            plan_id=f"sp_{subtask_id}",
            course_id=course_id,
            title="Read primary key notes",
            subtask_type="learn",
            description="Focus on primary keys.",
            related_material_ids_json=material_ids,
            status="not_started",
            sort_order=1,
        )
    )
    if include_chunks:
        for index, material_id in enumerate(material_ids):
            chunk_id = f"chunk_{material_id}"
            api.db.add(
                MaterialChunk(
                    id=chunk_id,
                    material_id=material_id,
                    parse_version_id=f"mpv_{material_id}",
                    course_id=course_id,
                    chunk_index=index,
                    page="1",
                    page_index=index,
                    heading="Keys",
                    content_text=f"primary key content from {material_id}",
                )
            )
            api.rag_index.index_chunks(
                [
                    RagChunk(
                        chunk_id=chunk_id,
                        user_id=user_id,
                        course_id=course_id,
                        material_id=material_id,
                        folder_id=None,
                        chunk_index=index,
                        text=f"primary key content from {material_id}",
                        page="1",
                        page_index=index,
                        heading="Keys",
                        parse_version_id=f"mpv_{material_id}",
                    )
                ]
            )
    api.db.commit()
    return subtask_id


def _add_same_course_out_of_scope_material(api: ApiHarness, *, user_id: str) -> None:
    parse_version_id = "mpv_mat_task_out_of_scope"
    api.db.add(
        CourseMaterial(
            id="mat_task_out_of_scope",
            user_id=user_id,
            course_id="crs_task_qa",
            name="out-of-scope.md",
            material_type="markdown",
            source_type="file",
            file_url="/uploads/out-of-scope.md",
            parse_status="parsed",
            active_parse_version_id=parse_version_id,
        )
    )
    api.db.add(
        MaterialParseVersion(
            id=parse_version_id,
            material_id="mat_task_out_of_scope",
            course_id="crs_task_qa",
            user_id=user_id,
            status="active",
            parse_quality="complete",
        )
    )
    api.db.add(
        MaterialChunk(
            id="chunk_task_out_of_scope",
            material_id="mat_task_out_of_scope",
            parse_version_id=parse_version_id,
            course_id="crs_task_qa",
            chunk_index=0,
            page="1",
            page_index=0,
            heading="Keys",
            content_text="primary key content from out of scope material",
        )
    )
    api.rag_index.index_chunks(
        [
            RagChunk(
                chunk_id="chunk_task_out_of_scope",
                user_id=user_id,
                course_id="crs_task_qa",
                material_id="mat_task_out_of_scope",
                folder_id=None,
                chunk_index=0,
                text="primary key content from out of scope material",
                page="1",
                page_index=0,
                heading="Keys",
                parse_version_id=parse_version_id,
            )
        ]
    )
    api.db.commit()


def test_task_qa_returns_citations_and_only_uses_current_subtask_materials(api: ApiHarness) -> None:
    user_id, headers = _register_user_and_headers(api, username="alice")
    subtask_id = _seed_task_qa_plan(api, user_id=user_id, related_material_ids=["mat_task_allowed"])
    _add_same_course_out_of_scope_material(api, user_id=user_id)

    response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/qa/questions",
        headers=headers,
        json={"conversation_id": None, "question": "What is a primary key?"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer_type"] == "grounded"
    assert data["used_material_ids"] == ["mat_task_allowed"]
    assert [citation["material_id"] for citation in data["source_citations"]] == ["mat_task_allowed"]
    assert [citation["material_version_id"] for citation in data["source_citations"]] == [
        "mpv_mat_task_allowed"
    ]

    conversation = api.db.get(Conversation, data["conversation_id"])
    assert conversation is not None
    assert conversation.source_page == "task_execution"
    user_message = api.db.execute(select(Message).where(Message.id == data["user_message_id"])).scalar_one()
    assert user_message.material_scope_json["subtask_id"] == subtask_id
    assert user_message.material_scope_json["task_id"] == f"task_{subtask_id}"
    assert user_message.material_scope_json["used_material_ids"] == ["mat_task_allowed"]
    assert api.db.get(StudySubTask, subtask_id).status == "not_started"
    assert api.db.scalar(select(func.count()).select_from(CheckinRecord)) == 0


def test_task_qa_returns_not_found_for_cross_user_subtask(api: ApiHarness) -> None:
    alice_id, _ = _register_user_and_headers(api, username="alice")
    _, bob_headers = _register_user_and_headers(api, username="bob")
    subtask_id = _seed_task_qa_plan(api, user_id=alice_id)

    response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/qa/questions",
        headers=bob_headers,
        json={"question": "What is a primary key?"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_task_qa_rejects_cross_course_conversation_reuse(api: ApiHarness) -> None:
    user_id, headers = _register_user_and_headers(api, username="alice")
    subtask_id = _seed_task_qa_plan(api, user_id=user_id)
    api.db.add(Course(id="crs_other_task_qa", user_id=user_id, name="Other course", status="active"))
    api.db.add(
        Conversation(
            id="cnv_other_course",
            user_id=user_id,
            course_id="crs_other_task_qa",
            title="Other",
            source_page="task_execution",
            status="active",
        )
    )
    api.db.commit()

    response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/qa/questions",
        headers=headers,
        json={"conversation_id": "cnv_other_course", "question": "What is a primary key?"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_task_qa_rejects_non_task_execution_conversation_reuse(api: ApiHarness) -> None:
    user_id, headers = _register_user_and_headers(api, username="alice")
    subtask_id = _seed_task_qa_plan(api, user_id=user_id)
    api.db.add(
        Conversation(
            id="cnv_course_detail",
            user_id=user_id,
            course_id="crs_task_qa",
            title="Course detail",
            source_page="course_detail",
            status="active",
        )
    )
    api.db.commit()

    response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/qa/questions",
        headers=headers,
        json={"conversation_id": "cnv_course_detail", "question": "What is a primary key?"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_task_qa_without_parsed_task_materials_returns_no_source(api: ApiHarness) -> None:
    user_id, headers = _register_user_and_headers(api, username="alice")
    subtask_id = _seed_task_qa_plan(
        api,
        user_id=user_id,
        related_material_ids=["mat_task_unparsed"],
        include_chunks=False,
    )

    response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/qa/questions",
        headers=headers,
        json={"question": "What is a primary key?"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer_type"] == "no_source"
    assert data["source_citations"] == []
    assert data["used_material_ids"] == []
    user_message = api.db.execute(select(Message).where(Message.id == data["user_message_id"])).scalar_one()
    assert user_message.material_scope_json["subtask_id"] == subtask_id
    assert user_message.material_scope_json["used_material_ids"] == []
    assert api.db.get(StudySubTask, subtask_id).status == "not_started"
    assert api.db.scalar(select(func.count()).select_from(CheckinRecord)) == 0
