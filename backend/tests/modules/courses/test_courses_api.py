from collections.abc import Generator
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.modules.courses.models import Course
from app.modules.materials.models import CourseMaterial
from app.modules.study_plans.models import StudyPlan, StudyTask
import app.db.models  # noqa: F401
from app.main import app


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
    app.state.courses_testing_session = testing_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        if hasattr(app.state, "courses_testing_session"):
            del app.state.courses_testing_session


def register_and_token(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_course_crud_flow(client: TestClient) -> None:
    token = register_and_token(client, "alice")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/v1/courses",
        json={"name": "Linear Algebra", "teacher": "Prof. A", "term": "2025-2026-spring"},
        headers=headers,
    )

    assert create_response.status_code == 200
    created_course = create_response.json()["data"]
    course_id = created_course["id"]
    assert created_course["name"] == "Linear Algebra"
    assert created_course["term"] == "2025-2026-spring"

    list_response = client.get("/api/v1/courses", headers=headers)

    assert list_response.status_code == 200
    assert [course["id"] for course in list_response.json()["data"]] == [course_id]

    detail_response = client.get(f"/api/v1/courses/{course_id}", headers=headers)

    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["id"] == course_id

    update_response = client.patch(
        f"/api/v1/courses/{course_id}",
        json={"name": "Linear Algebra II"},
        headers=headers,
    )

    assert update_response.status_code == 200
    assert update_response.json()["data"]["name"] == "Linear Algebra II"

    delete_response = client.delete(f"/api/v1/courses/{course_id}", headers=headers)

    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["status"] == "deleted"

    assert client.get("/api/v1/courses", headers=headers).json()["data"] == []


def test_course_list_includes_material_and_today_task_summaries(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.courses.router.today_shanghai", lambda: date(2026, 7, 13))

    token = register_and_token(client, "summary-user")
    headers = {"Authorization": f"Bearer {token}"}
    no_plan_course_id = client.post("/api/v1/courses", json={"name": "No Plan"}, headers=headers).json()["data"]["id"]
    no_task_course_id = client.post("/api/v1/courses", json={"name": "No Task"}, headers=headers).json()["data"]["id"]
    has_task_course_id = client.post("/api/v1/courses", json={"name": "Has Task"}, headers=headers).json()["data"]["id"]

    testing_session = client.app.state.courses_testing_session
    db = testing_session()
    try:
        courses = {
            course.id: course
            for course in db.execute(
                select(Course).where(Course.id.in_([no_plan_course_id, no_task_course_id, has_task_course_id]))
            ).scalars()
        }
        user_id = courses[no_plan_course_id].user_id
        db.add_all(
            [
                _material("mat_no_task_active", courses[no_task_course_id]),
                _material("mat_no_task_deleted", courses[no_task_course_id], deleted_at=datetime(2026, 7, 1, tzinfo=timezone.utc)),
                _material("mat_has_task", courses[has_task_course_id]),
                _study_plan("sp_no_task", user_id, no_task_course_id),
                _study_plan("sp_has_task", user_id, has_task_course_id),
                _study_plan("sp_deleted", user_id, no_task_course_id, status="deleted", deleted_at=datetime(2026, 7, 1, tzinfo=timezone.utc)),
                _study_task("tsk_no_task_tomorrow", "sp_no_task", no_task_course_id, date(2026, 7, 14)),
                _study_task("tsk_has_task_today", "sp_has_task", has_task_course_id, date(2026, 7, 13)),
                _study_task("tsk_deleted_plan_today", "sp_deleted", no_task_course_id, date(2026, 7, 13)),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/courses", headers=headers)

    assert response.status_code == 200
    summaries = {course["id"]: course for course in response.json()["data"]}
    assert summaries[no_plan_course_id]["material_count"] == 0
    assert summaries[no_plan_course_id]["today_task_status"] == "no_study_plan"
    assert summaries[no_task_course_id]["material_count"] == 1
    assert summaries[no_task_course_id]["today_task_status"] == "no_task_today"
    assert summaries[has_task_course_id]["material_count"] == 1
    assert summaries[has_task_course_id]["today_task_status"] == "has_task_today"

    detail_response = client.get(f"/api/v1/courses/{has_task_course_id}", headers=headers)
    assert detail_response.status_code == 200
    assert "material_count" not in detail_response.json()["data"]
    assert "today_task_status" not in detail_response.json()["data"]


def _material(material_id: str, course: Course, *, deleted_at: datetime | None = None) -> CourseMaterial:
    return CourseMaterial(
        id=material_id,
        user_id=course.user_id,
        course_id=course.id,
        name=f"{material_id}.txt",
        material_type="text",
        source_type="file",
        file_url=f"memory://{material_id}.txt",
        parse_status="deleted" if deleted_at else "uploaded",
        deleted_at=deleted_at,
    )


def _study_plan(
    plan_id: str,
    user_id: str,
    course_id: str,
    *,
    status: str = "active",
    deleted_at: datetime | None = None,
) -> StudyPlan:
    return StudyPlan(
        id=plan_id,
        user_id=user_id,
        course_id=course_id,
        title=f"{plan_id} plan",
        goal_text="复习",
        start_date=date(2026, 7, 13),
        end_date=date(2026, 7, 14),
        daily_available_minutes=60,
        status=status,
        deleted_at=deleted_at,
    )


def _study_task(task_id: str, plan_id: str, course_id: str, task_date: date) -> StudyTask:
    return StudyTask(
        id=task_id,
        plan_id=plan_id,
        course_id=course_id,
        title=f"{task_id} task",
        task_date=task_date,
        status="not_started",
        sort_order=1,
    )


def test_course_term_options_and_nullable_default(client: TestClient) -> None:
    token = register_and_token(client, "term-user")
    headers = {"Authorization": f"Bearer {token}"}

    options_response = client.get("/api/v1/course-terms", headers=headers)

    assert options_response.status_code == 200
    assert options_response.json()["data"] == [
        {"value": "2027-2028-autumn", "label": "2027-2028 秋季"},
        {"value": "2027-2028-spring", "label": "2027-2028 春季"},
        {"value": "2026-2027-autumn", "label": "2026-2027 秋季"},
        {"value": "2026-2027-spring", "label": "2026-2027 春季"},
        {"value": "2025-2026-autumn", "label": "2025-2026 秋季"},
        {"value": "2025-2026-spring", "label": "2025-2026 春季"},
        {"value": "2024-2025-autumn", "label": "2024-2025 秋季"},
        {"value": "2024-2025-spring", "label": "2024-2025 春季"},
    ]

    create_response = client.post("/api/v1/courses", json={"name": "No Term"}, headers=headers)

    assert create_response.status_code == 200
    assert create_response.json()["data"]["term"] is None


def test_course_text_fields_enforce_character_limits(client: TestClient) -> None:
    token = register_and_token(client, "course-text-limit-user")
    headers = {"Authorization": f"Bearer {token}"}
    valid_payload = {
        "name": "课" * 20,
        "description": "简" * 50,
        "teacher": "师" * 10,
    }

    create_response = client.post("/api/v1/courses", json=valid_payload, headers=headers)

    assert create_response.status_code == 200
    course_id = create_response.json()["data"]["id"]

    for field_name, over_limit_value in (
        ("name", "课" * 21),
        ("description", "简" * 51),
        ("teacher", "师" * 11),
    ):
        response = client.patch(
            f"/api/v1/courses/{course_id}",
            json={field_name: over_limit_value},
            headers=headers,
        )

        assert response.status_code == 422


def test_course_create_and_update_reject_nonstandard_term(client: TestClient) -> None:
    token = register_and_token(client, "invalid-term-user")
    headers = {"Authorization": f"Bearer {token}"}

    invalid_create_response = client.post(
        "/api/v1/courses",
        json={"name": "Bad Term", "term": "2026 Spring"},
        headers=headers,
    )

    assert invalid_create_response.status_code == 422
    assert invalid_create_response.json()["error"]["code"] == "VALIDATION_ERROR"

    created = client.post("/api/v1/courses", json={"name": "Valid"}, headers=headers).json()["data"]
    invalid_update_response = client.patch(
        f"/api/v1/courses/{created['id']}",
        json={"term": "custom term"},
        headers=headers,
    )

    assert invalid_update_response.status_code == 422
    assert invalid_update_response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_course_api_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/courses")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"

    term_options_response = client.get("/api/v1/course-terms")

    assert term_options_response.status_code == 401
    assert term_options_response.json()["error"]["code"] == "UNAUTHORIZED"


def test_course_detail_does_not_cross_user_boundary(client: TestClient) -> None:
    alice_token = register_and_token(client, "alice")
    bob_token = register_and_token(client, "bob")

    bob_create_response = client.post(
        "/api/v1/courses",
        json={"name": "Databases"},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    bob_course_id = bob_create_response.json()["data"]["id"]

    response = client.get(
        f"/api/v1/courses/{bob_course_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
