from __future__ import annotations

from collections.abc import Generator
from datetime import date

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.db.models  # noqa: F401
from app.modules.checkins.models import CheckinRecord
from app.modules.courses.models import Course
from app.modules.learning_execution.service import set_subtask_completion
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask
from app.modules.todos_calendar.service import get_today_todos
from app.modules.users.models import User


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


def _seed_execution(db: Session) -> None:
    db.add(User(id="usr_tx", username="tx", password_hash="hash", status="active"))
    db.add(Course(id="crs_tx", user_id="usr_tx", name="数据库", status="active"))
    db.add(
        StudyPlan(
            id="sp_tx",
            user_id="usr_tx",
            course_id="crs_tx",
            title="数据库计划",
            goal_text="学习数据库",
            parsed_config_json={},
            start_date=date(2026, 7, 11),
            end_date=date(2026, 7, 11),
            daily_available_minutes=60,
            status="active",
        )
    )
    db.add(StudyTask(id="task_tx", plan_id="sp_tx", course_id="crs_tx", title="数据库设计", task_date=date(2026, 7, 11), status="not_started", sort_order=1))
    db.add_all(
        [
            StudySubTask(id="sub_tx", task_id="task_tx", plan_id="sp_tx", course_id="crs_tx", title="阅读 PPT", subtask_type="learn", description="阅读", related_material_ids_json=[], status="not_started", sort_order=1),
            StudySubTask(id="sub_tx_2", task_id="task_tx", plan_id="sp_tx", course_id="crs_tx", title="复盘", subtask_type="review", description="复盘", related_material_ids_json=[], status="not_started", sort_order=2),
        ]
    )
    db.commit()


def _subtask(db: Session) -> StudySubTask:
    return db.get(StudySubTask, "sub_tx")


def _task(db: Session) -> StudyTask:
    return db.get(StudyTask, "task_tx")


def _plan(db: Session) -> StudyPlan:
    return db.get(StudyPlan, "sp_tx")


def _checkin_count(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(CheckinRecord)) or 0)


def test_completion_failure_rolls_back_subtask_task_plan_and_checkin(monkeypatch: pytest.MonkeyPatch, db: Session) -> None:
    _seed_execution(db)

    def fail_recalculate(*args: object, **kwargs: object) -> object:
        raise RuntimeError("forced checkin failure")

    monkeypatch.setattr("app.modules.learning_execution.service.recalculate_checkin", fail_recalculate)

    with pytest.raises(RuntimeError):
        set_subtask_completion(db, user_id="usr_tx", subtask_id="sub_tx", completed=True)

    db.expire_all()
    assert _subtask(db).status == "not_started"
    assert _task(db).status == "not_started"
    assert _plan(db).status == "active"
    assert _checkin_count(db) == 0


def test_s03_queries_reflect_completion_after_commit(db: Session) -> None:
    _seed_execution(db)

    set_subtask_completion(db, user_id="usr_tx", subtask_id="sub_tx", completed=True)

    today = get_today_todos(db, user_id="usr_tx", target_date=date(2026, 7, 11))
    assert today.tasks[0].completed_subtask_count == 1
    assert today.tasks[0].derived_status == "in_progress"
    assert _checkin_count(db) == 1