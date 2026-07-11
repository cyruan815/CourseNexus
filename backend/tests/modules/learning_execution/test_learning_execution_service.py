from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import CourseNexusError
from app.db.base import Base
import app.db.models  # noqa: F401
from app.modules.courses.models import Course
from app.modules.learning_execution.service import get_execution_context, set_subtask_completion
from app.modules.materials.models import CourseMaterial
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask
from app.modules.users.models import User


@dataclass(frozen=True)
class ExecutionFixture:
    plan_id: str
    today_task_ids: set[str]
    today_subtask_id: str


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


def _seed_base(db: Session) -> None:
    db.add_all(
        [
            User(id="usr_a", username="alice", password_hash="hash", status="active"),
            User(id="usr_b", username="bob", password_hash="hash", status="active"),
            Course(id="crs_a", user_id="usr_a", name="数据库", status="active"),
            Course(id="crs_b", user_id="usr_b", name="其他课", status="active"),
            Course(id="crs_other_a", user_id="usr_a", name="同用户另一课", status="active"),
            CourseMaterial(
                id="mat_a",
                user_id="usr_a",
                course_id="crs_a",
                name="数据库设计.pdf",
                material_type="pdf",
                source_type="file",
                file_url="/materials/db.pdf",
                parse_status="parsed",
            ),
            CourseMaterial(
                id="mat_other_course",
                user_id="usr_a",
                course_id="crs_other_a",
                name="另一课.pdf",
                material_type="pdf",
                source_type="file",
                file_url="/materials/other.pdf",
                parse_status="parsed",
            ),
        ]
    )


def _seed_plan(db: Session, *, related_material_ids: list[str] | None = None, plan_status: str = "active") -> ExecutionFixture:
    related_material_ids = ["mat_a"] if related_material_ids is None else related_material_ids
    db.add(
        StudyPlan(
            id="sp_exec",
            user_id="usr_a",
            course_id="crs_a",
            title="数据库计划",
            goal_text="学习数据库设计",
            parsed_config_json={},
            start_date=date(2026, 7, 11),
            end_date=date(2026, 7, 12),
            daily_available_minutes=60,
            status=plan_status,
            deleted_at=datetime.now(timezone.utc) if plan_status == "deleted" else None,
        )
    )
    db.add_all(
        [
            StudyTask(id="task_today_1", plan_id="sp_exec", course_id="crs_a", title="数据库设计概述", task_date=date(2026, 7, 11), status="not_started", sort_order=1),
            StudyTask(id="task_today_2", plan_id="sp_exec", course_id="crs_a", title="需求分析", task_date=date(2026, 7, 11), status="not_started", sort_order=2),
            StudyTask(id="task_tomorrow", plan_id="sp_exec", course_id="crs_a", title="概念结构设计", task_date=date(2026, 7, 12), status="not_started", sort_order=3),
        ]
    )
    db.add_all(
        [
            StudySubTask(
                id="sub_current",
                task_id="task_today_1",
                plan_id="sp_exec",
                course_id="crs_a",
                title="阅读数据库设计概述",
                subtask_type="learn",
                description="阅读 PPT",
                related_material_ids_json=related_material_ids,
                status="not_started",
                sort_order=1,
            ),
            StudySubTask(id="sub_today_2", task_id="task_today_2", plan_id="sp_exec", course_id="crs_a", title="整理需求分析", subtask_type="review", description="复盘", related_material_ids_json=[], status="not_started", sort_order=1),
            StudySubTask(id="sub_tomorrow", task_id="task_tomorrow", plan_id="sp_exec", course_id="crs_a", title="画 E-R 图", subtask_type="test", description="练习", related_material_ids_json=[], status="not_started", sort_order=1),
        ]
    )
    return ExecutionFixture(plan_id="sp_exec", today_task_ids={"task_today_1", "task_today_2"}, today_subtask_id="sub_current")


def test_execution_context_returns_only_same_plan_same_day_tasks(db: Session) -> None:
    _seed_base(db)
    fixture = _seed_plan(db)
    db.commit()

    context = get_execution_context(db, user_id="usr_a", subtask_id=fixture.today_subtask_id)

    assert context.execution_date == date(2026, 7, 11)
    assert {task.task_date for task in context.tasks} == {date(2026, 7, 11)}
    assert {task.task_id for task in context.tasks} == fixture.today_task_ids
    assert context.current_subtask_id == "sub_current"
    assert context.related_materials[0].availability == "available"
    assert context.handout_content_id is None
    assert context.task_test_content_id is None


def test_execution_context_rejects_cross_user_and_deleted_plan(db: Session) -> None:
    _seed_base(db)
    _seed_plan(db)
    db.commit()

    with pytest.raises(CourseNexusError) as exc_info:
        get_execution_context(db, user_id="usr_b", subtask_id="sub_current")

    assert exc_info.value.code == "NOT_FOUND"


def test_execution_context_rejects_cross_course_related_material(db: Session) -> None:
    _seed_base(db)
    _seed_plan(db, related_material_ids=["mat_other_course"])
    db.commit()

    with pytest.raises(CourseNexusError) as exc_info:
        get_execution_context(db, user_id="usr_a", subtask_id="sub_current")

    assert exc_info.value.code == "STATE_CONFLICT"


def test_execution_context_marks_missing_material_as_deleted(db: Session) -> None:
    _seed_base(db)
    _seed_plan(db, related_material_ids=["mat_missing"])
    db.commit()

    context = get_execution_context(db, user_id="usr_a", subtask_id="sub_current")

    assert context.related_materials[0].material_id == "mat_missing"
    assert context.related_materials[0].availability == "deleted"

def test_complete_subtask_updates_subtask_parent_task_plan_and_checkin(db: Session) -> None:
    _seed_base(db)
    fixture = _seed_plan(db)
    db.add(
        StudySubTask(
            id="sub_sibling",
            task_id="task_today_1",
            plan_id="sp_exec",
            course_id="crs_a",
            title="补充练习",
            subtask_type="review",
            description="复习",
            related_material_ids_json=[],
            status="not_started",
            sort_order=2,
        )
    )
    db.commit()

    result = set_subtask_completion(db, user_id="usr_a", subtask_id=fixture.today_subtask_id, completed=True)

    assert result.changed is True
    assert result.subtask.status == "completed"
    assert result.subtask.completed_at is not None
    assert result.task.status == "in_progress"
    assert result.task.completed_subtask_count == 1
    assert result.task.total_subtask_count == 2
    assert result.plan.status == "active"
    assert result.checkin.total_subtask_count == 3
    assert result.checkin.completed_subtask_count == 1


def test_repeated_complete_is_idempotent_but_recalculates_checkin(db: Session) -> None:
    _seed_base(db)
    fixture = _seed_plan(db)
    db.commit()

    first = set_subtask_completion(db, user_id="usr_a", subtask_id=fixture.today_subtask_id, completed=True)
    second = set_subtask_completion(db, user_id="usr_a", subtask_id=fixture.today_subtask_id, completed=True)

    assert first.changed is True
    assert second.changed is False
    assert second.subtask.status == "completed"
    assert second.subtask.completed_at == first.subtask.completed_at
    assert second.checkin.completed_subtask_count == first.checkin.completed_subtask_count


def test_cancel_completion_returns_subtask_to_not_started(db: Session) -> None:
    _seed_base(db)
    fixture = _seed_plan(db)
    db.commit()
    set_subtask_completion(db, user_id="usr_a", subtask_id=fixture.today_subtask_id, completed=True)

    result = set_subtask_completion(db, user_id="usr_a", subtask_id=fixture.today_subtask_id, completed=False)

    assert result.changed is True
    assert result.subtask.status == "not_started"
    assert result.subtask.completed_at is None
    assert result.checkin.completed_subtask_count == 0
