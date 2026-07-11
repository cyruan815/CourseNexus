from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
import app.db.models  # noqa: F401
from app.main import app
from app.modules.checkins.models import CheckinRecord
from app.modules.checkins.service import recalculate_checkin
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


def _register_and_headers(client: TestClient, username: str = "alice") -> dict[str, str]:
    response = client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _user_id(db: Session, username: str = "alice") -> str:
    return db.execute(select(User).where(User.username == username)).scalar_one().id


def _seed_course(db: Session, *, user_id: str, course_id: str = "crs_a") -> None:
    db.add(Course(id=course_id, user_id=user_id, name="数据库", status="active"))


def _seed_plan_day(
    db: Session,
    *,
    user_id: str,
    course_id: str = "crs_a",
    plan_id: str = "sp_a",
    task_id: str = "task_a",
    task_date: date = date(2026, 7, 11),
    subtask_statuses: tuple[str, ...] = ("not_started", "not_started"),
) -> None:
    db.add(
        StudyPlan(
            id=plan_id,
            user_id=user_id,
            course_id=course_id,
            title="数据库两周计划",
            goal_text="学习数据库",
            parsed_config_json={},
            start_date=task_date,
            end_date=task_date,
            daily_available_minutes=60,
            status="active",
        )
    )
    db.add(
        StudyTask(
            id=task_id,
            plan_id=plan_id,
            course_id=course_id,
            title="数据库设计",
            task_date=task_date,
            status="in_progress" if any(status == "completed" for status in subtask_statuses) else "not_started",
            sort_order=1,
        )
    )
    for index, status in enumerate(subtask_statuses, start=1):
        db.add(
            StudySubTask(
                id=f"{task_id}_sub_{index}",
                task_id=task_id,
                plan_id=plan_id,
                course_id=course_id,
                title=f"二级任务 {index}",
                subtask_type="learn",
                description="学习内容",
                related_material_ids_json=[],
                status=status,
                completed_at=datetime.now(timezone.utc) if status == "completed" else None,
                sort_order=index,
            )
        )


def _count_checkin_records(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(CheckinRecord)) or 0)


def test_get_single_checkin_returns_snapshot_without_creating_record(api: ApiHarness) -> None:
    headers = _register_and_headers(api.client)
    user_id = _user_id(api.db)
    _seed_course(api.db, user_id=user_id)
    _seed_plan_day(api.db, user_id=user_id)
    api.db.commit()
    before = _count_checkin_records(api.db)

    response = api.client.get("/api/v1/checkins/2026-07-11", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["checkin_date"] == "2026-07-11"
    assert body["data"]["total_subtask_count"] == 2
    assert body["data"]["completed_subtask_count"] == 0
    assert body["data"]["completion_ratio"] == "0.0000"
    assert body["data"]["color_level"] == 1
    assert body["data"]["has_tasks"] is True
    assert _count_checkin_records(api.db) == before


def test_get_checkin_range_returns_persisted_records_and_streak(api: ApiHarness) -> None:
    headers = _register_and_headers(api.client)
    user_id = _user_id(api.db)
    _seed_course(api.db, user_id=user_id)
    _seed_plan_day(api.db, user_id=user_id, plan_id="sp_1", task_id="task_1", task_date=date(2026, 7, 1), subtask_statuses=("not_started",))
    _seed_plan_day(api.db, user_id=user_id, plan_id="sp_2", task_id="task_2", task_date=date(2026, 7, 2), subtask_statuses=("completed", "not_started"))
    _seed_plan_day(api.db, user_id=user_id, plan_id="sp_3", task_id="task_3", task_date=date(2026, 7, 3), subtask_statuses=("completed",))
    _seed_plan_day(api.db, user_id=user_id, plan_id="sp_4", task_id="task_4", task_date=date(2026, 7, 5), subtask_statuses=("completed",))
    api.db.commit()
    for day in [date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3), date(2026, 7, 5)]:
        recalculate_checkin(api.db, user_id=user_id, checkin_date=day, flush_only=False)

    response = api.client.get("/api/v1/checkins?start_date=2026-07-01&end_date=2026-07-31", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["start_date"] == "2026-07-01"
    assert data["end_date"] == "2026-07-31"
    assert len(data["items"]) == 4
    assert data["summary"] == {
        "task_days": 4,
        "completed_days": 3,
        "current_streak_days": 1,
        "longest_streak_days": 2,
    }


def test_get_checkin_requires_auth(api: ApiHarness) -> None:
    response = api.client.get("/api/v1/checkins/2026-07-11")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_get_checkin_range_rejects_invalid_date_order(api: ApiHarness) -> None:
    headers = _register_and_headers(api.client)

    response = api.client.get("/api/v1/checkins?start_date=2026-07-31&end_date=2026-07-01", headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_checkin_range_rejects_more_than_366_days(api: ApiHarness) -> None:
    headers = _register_and_headers(api.client)

    response = api.client.get("/api/v1/checkins?start_date=2026-01-01&end_date=2027-01-02", headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"