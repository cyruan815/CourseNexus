from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.modules.courses.models import Course
from app.modules.materials.models import CourseMaterial, MaterialChunk
import app.db.models  # noqa: F401
from app.main import app
from tests.fixtures.study_mode_samples import compliant_daily_task


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.state.todos_calendar_testing_session = testing_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        if hasattr(app.state, "todos_calendar_testing_session"):
            del app.state.todos_calendar_testing_session


def _register_and_token(client: TestClient, username: str) -> str:
    response = client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def _create_course(client: TestClient, token: str, name: str) -> str:
    response = client.post(
        "/api/v1/courses",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json()["data"]["id"]


def _plan_payload(*, title: str, material_id: str, task_date: str = "2026-07-11", task_count: int = 1) -> dict[str, object]:
    return {
        "title": title,
        "goal_text": "掌握传输层",
        "start_date": "2026-07-11",
        "end_date": "2026-07-20",
        "daily_available_minutes": 60,
        "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        "tasks": [
            # 保存契约要求每天恰好一个测试任务并排在最后（见 tests/fixtures/study_mode_samples.py）。
            compliant_daily_task(
                title=f"{title} 任务 {index}",
                task_date=task_date,
                sort_order=index,
                plan_material_ids=[material_id],
            )
            for index in range(1, task_count + 1)
        ],
    }


def _seed_parsed_material(client: TestClient, course_id: str, material_id: str) -> str:
    testing_session = client.app.state.todos_calendar_testing_session
    db = testing_session()
    try:
        course = db.get(Course, course_id)
        assert course is not None
        db.add_all(
            [
                CourseMaterial(
                    id=material_id,
                    user_id=course.user_id,
                    course_id=course.id,
                    name=f"{material_id}.txt",
                    material_type="text",
                    source_type="file",
                    file_url=f"memory://{material_id}.txt",
                    file_size=16,
                    mime_type="text/plain",
                    parse_status="parsed",
                ),
                MaterialChunk(
                    id=f"chk_{material_id}_000001",
                    material_id=material_id,
                    course_id=course.id,
                    chunk_index=1,
                    heading="Calendar",
                    content_text="Calendar material",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()
    return material_id

def _save_plan(client: TestClient, token: str, course_id: str, payload: dict[str, object]) -> dict[str, object]:
    response = client.post(
        f"/api/v1/courses/{course_id}/study-plans",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 200
    return response.json()["data"]


def _seed_api_data(client: TestClient) -> tuple[str, str, str, str]:
    token = _register_and_token(client, "alice")
    net_course_id = _create_course(client, token, "Computer Networks")
    math_course_id = _create_course(client, token, "Math")
    other_token = _register_and_token(client, "bob")
    other_course_id = _create_course(client, other_token, "Other")
    net_material_id = _seed_parsed_material(client, net_course_id, "mat_api_net")
    math_material_id = _seed_parsed_material(client, math_course_id, "mat_api_math")
    other_material_id = _seed_parsed_material(client, other_course_id, "mat_api_other")
    _save_plan(client, token, net_course_id, _plan_payload(title="网络", material_id=net_material_id, task_count=4))
    _save_plan(client, token, math_course_id, _plan_payload(title="数学", material_id=math_material_id, task_count=1))
    _save_plan(client, other_token, other_course_id, _plan_payload(title="其他", material_id=other_material_id, task_count=1))
    return token, net_course_id, math_course_id, other_course_id


def test_today_todos_endpoint_returns_nested_tasks_without_plan_title(client: TestClient) -> None:
    token, _, _, _ = _seed_api_data(client)

    response = client.get("/api/v1/todos/today?date=2026-07-11", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["date"] == "2026-07-11"
    assert data["tasks"][0]["subtasks"]
    assert "plan_title" not in data["tasks"][0]
    assert {task["course_name"] for task in data["tasks"]} == {"Computer Networks", "Math"}


def test_month_calendar_endpoint_limits_task_summaries_to_three(client: TestClient) -> None:
    token, _, _, _ = _seed_api_data(client)

    response = client.get("/api/v1/calendar/month?month=2026-07", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    day = response.json()["data"]["days"][0]
    assert day["task_count"] == 5
    assert len(day["task_summaries"]) == 3
    assert day["hidden_task_count"] == 2


def test_global_day_todos_endpoint_returns_course_groups(client: TestClient) -> None:
    token, _, _, _ = _seed_api_data(client)

    response = client.get("/api/v1/calendar/days/2026-07-11/todos", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert [course["course_name"] for course in data["courses"]] == ["Computer Networks", "Math"]
    assert data["courses"][0]["tasks"][0]["subtasks"]


def test_course_calendar_and_day_endpoints_are_course_scoped(client: TestClient) -> None:
    token, net_course_id, _, _ = _seed_api_data(client)
    headers = {"Authorization": f"Bearer {token}"}

    month = client.get(f"/api/v1/courses/{net_course_id}/study-calendar?month=2026-07", headers=headers)
    day = client.get(f"/api/v1/courses/{net_course_id}/study-calendar/days/2026-07-11", headers=headers)

    assert month.status_code == 200
    assert month.json()["data"]["course_id"] == net_course_id
    assert month.json()["data"]["days"][0]["course_count"] == 1
    assert day.status_code == 200
    assert day.json()["data"]["course_id"] == net_course_id
    assert {task["course_id"] for task in day.json()["data"]["tasks"]} == {net_course_id}


def test_course_day_endpoint_returns_empty_tasks_for_empty_date(client: TestClient) -> None:
    token, _, math_course_id, _ = _seed_api_data(client)

    response = client.get(
        f"/api/v1/courses/{math_course_id}/study-calendar/days/2026-07-12",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["tasks"] == []


def test_calendar_endpoints_auth_not_found_and_validation_errors(client: TestClient) -> None:
    token, _, _, other_course_id = _seed_api_data(client)

    unauthorized = client.get("/api/v1/todos/today?date=2026-07-11")
    cross_user = client.get(
        f"/api/v1/courses/{other_course_id}/study-calendar?month=2026-07",
        headers={"Authorization": f"Bearer {token}"},
    )
    invalid_month = client.get("/api/v1/calendar/month?month=2026-13", headers={"Authorization": f"Bearer {token}"})
    invalid_date = client.get("/api/v1/calendar/days/2026-02-30/todos", headers={"Authorization": f"Bearer {token}"})

    assert unauthorized.status_code == 401
    assert cross_user.status_code == 404
    assert invalid_month.status_code == 422
    assert invalid_month.json()["error"]["code"] == "VALIDATION_ERROR"
    assert invalid_date.status_code == 422