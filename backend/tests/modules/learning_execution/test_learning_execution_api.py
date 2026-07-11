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
from app.modules.courses.models import Course
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


def _register_and_headers(api: ApiHarness) -> tuple[str, dict[str, str]]:
    response = api.client.post("/api/v1/auth/register", json={"username": "alice", "password": "password123"})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    user_id = api.db.execute(select(User).where(User.username == "alice")).scalar_one().id
    return user_id, {"Authorization": f"Bearer {token}"}


def _seed_execution_plan(db: Session, *, user_id: str) -> str:
    db.add(Course(id="crs_api_exec", user_id=user_id, name="数据库", status="active"))
    db.add(
        StudyPlan(
            id="sp_api_exec",
            user_id=user_id,
            course_id="crs_api_exec",
            title="数据库计划",
            goal_text="学习数据库设计",
            parsed_config_json={},
            start_date=date(2026, 7, 11),
            end_date=date(2026, 7, 11),
            daily_available_minutes=60,
            status="active",
        )
    )
    db.add(StudyTask(id="task_api_exec", plan_id="sp_api_exec", course_id="crs_api_exec", title="数据库设计", task_date=date(2026, 7, 11), status="not_started", sort_order=1))
    db.add(StudySubTask(id="sub_api_exec", task_id="task_api_exec", plan_id="sp_api_exec", course_id="crs_api_exec", title="阅读 PPT", subtask_type="learn", description="阅读内容", related_material_ids_json=[], status="not_started", sort_order=1))
    db.commit()
    return "sub_api_exec"


def test_get_execution_context_api_returns_envelope(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_execution_plan(api.db, user_id=user_id)

    response = api.client.get(f"/api/v1/study-subtasks/{subtask_id}/execution-context", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert body["data"]["current_subtask_id"] == subtask_id
    assert body["data"]["execution_date"] == "2026-07-11"
    assert body["data"]["handout_content_id"] is None
    assert body["data"]["task_test_content_id"] is None


def test_get_execution_context_api_requires_auth(api: ApiHarness) -> None:
    user_id, _ = _register_and_headers(api)
    subtask_id = _seed_execution_plan(api.db, user_id=user_id)

    response = api.client.get(f"/api/v1/study-subtasks/{subtask_id}/execution-context")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"