from __future__ import annotations

from collections.abc import Generator
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.db.models  # noqa: F401
from app.modules.checkins.models import CheckinRecord
from app.modules.checkins.schemas import CheckinRead
from app.modules.checkins.service import calculate_color_level, calculate_completion_ratio, calculate_streak_summary, recalculate_checkin
from app.modules.courses.models import Course
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask
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


def _checkin(day: int, total: int, completed: int) -> CheckinRead:
    return CheckinRead(
        id=f"chk_{day}",
        checkin_date=date(2026, 7, day),
        total_subtask_count=total,
        completed_subtask_count=completed,
        completion_ratio=calculate_completion_ratio(total, completed),
        color_level=calculate_color_level(total, completed),
        has_tasks=total > 0,
        created_at=datetime(2026, 7, day, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, day, tzinfo=timezone.utc),
    )


def test_completion_ratio_uses_four_decimal_places() -> None:
    assert calculate_completion_ratio(0, 0) == Decimal("0.0000")
    assert calculate_completion_ratio(5, 1) == Decimal("0.2000")
    assert calculate_completion_ratio(3, 1) == Decimal("0.3333")


def test_color_level_distinguishes_no_tasks_from_not_started_tasks() -> None:
    assert calculate_color_level(0, 0) == 0
    assert calculate_color_level(4, 0) == 1
    assert calculate_color_level(5, 1) == 2
    assert calculate_color_level(5, 2) == 3
    assert calculate_color_level(5, 4) == 4
    assert calculate_color_level(5, 5) == 5


def test_streak_counts_any_completed_subtask_day() -> None:
    summary = calculate_streak_summary(
        [
            _checkin(1, total=0, completed=0),
            _checkin(2, total=3, completed=0),
            _checkin(3, total=3, completed=1),
            _checkin(4, total=3, completed=2),
            _checkin(6, total=3, completed=1),
        ]
    )

    assert summary.task_days == 4
    assert summary.completed_days == 3
    assert summary.current_streak_days == 1
    assert summary.longest_streak_days == 2


def test_streak_returns_zero_when_last_task_day_is_incomplete() -> None:
    summary = calculate_streak_summary(
        [
            _checkin(10, total=1, completed=1),
            _checkin(11, total=1, completed=0),
        ]
    )

    assert summary.task_days == 2
    assert summary.completed_days == 1
    assert summary.current_streak_days == 0
    assert summary.longest_streak_days == 1


def test_streak_no_task_day_breaks_current_run() -> None:
    summary = calculate_streak_summary(
        [
            _checkin(1, total=1, completed=1),
            _checkin(2, total=0, completed=0),
        ]
    )

    assert summary.task_days == 1
    assert summary.completed_days == 1
    assert summary.current_streak_days == 0
    assert summary.longest_streak_days == 1


def test_streak_missing_record_breaks_adjacent_run() -> None:
    summary = calculate_streak_summary(
        [
            _checkin(1, total=1, completed=1),
            _checkin(3, total=1, completed=1),
        ]
    )

    assert summary.current_streak_days == 1
    assert summary.longest_streak_days == 1


def test_streak_counts_new_run_after_interruption() -> None:
    summary = calculate_streak_summary(
        [
            _checkin(1, total=1, completed=1),
            _checkin(2, total=1, completed=0),
            _checkin(3, total=1, completed=1),
            _checkin(4, total=1, completed=1),
        ]
    )

    assert summary.current_streak_days == 2
    assert summary.longest_streak_days == 2


def test_streak_empty_result_returns_zeroes() -> None:
    summary = calculate_streak_summary([])

    assert summary.task_days == 0
    assert summary.completed_days == 0
    assert summary.current_streak_days == 0
    assert summary.longest_streak_days == 0


def _seed_user(db: Session, user_id: str = "usr_a", username: str = "alice") -> None:
    db.add(User(id=user_id, username=username, password_hash="hash", status="active"))


def _seed_course(
    db: Session,
    *,
    course_id: str = "crs_a",
    user_id: str = "usr_a",
    status: str = "active",
) -> None:
    db.add(
        Course(
            id=course_id,
            user_id=user_id,
            name=f"Course {course_id}",
            status=status,
            deleted_at=datetime.now(timezone.utc) if status == "deleted" else None,
        )
    )


def _seed_plan_tree(
    db: Session,
    *,
    user_id: str = "usr_a",
    course_id: str = "crs_a",
    plan_id: str = "sp_a",
    plan_status: str = "active",
    task_id: str = "task_a",
    task_date: date = date(2026, 7, 11),
    subtask_statuses: tuple[str, ...] = ("completed", "not_started"),
) -> None:
    db.add(
        StudyPlan(
            id=plan_id,
            user_id=user_id,
            course_id=course_id,
            title=f"Plan {plan_id}",
            goal_text="复习",
            parsed_config_json={},
            start_date=task_date,
            end_date=task_date,
            daily_available_minutes=60,
            status=plan_status,
            deleted_at=datetime.now(timezone.utc) if plan_status == "deleted" else None,
        )
    )
    db.add(
        StudyTask(
            id=task_id,
            plan_id=plan_id,
            course_id=course_id,
            title=f"Task {task_id}",
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
                title=f"Subtask {index}",
                subtask_type="learn",
                description="学习内容",
                related_material_ids_json=[],
                status=status,
                completed_at=datetime.now(timezone.utc) if status == "completed" else None,
                sort_order=index,
            )
        )


def test_recalculate_checkin_creates_one_record_for_user_date(db: Session) -> None:
    _seed_user(db)
    _seed_course(db)
    _seed_plan_tree(db, subtask_statuses=("completed", "not_started"))
    db.commit()

    first = recalculate_checkin(db, user_id="usr_a", checkin_date=date(2026, 7, 11), flush_only=False)
    second = recalculate_checkin(db, user_id="usr_a", checkin_date=date(2026, 7, 11), flush_only=False)

    assert first.id == second.id
    assert second.total_subtask_count == 2
    assert second.completed_subtask_count == 1
    assert second.completion_ratio == Decimal("0.5000")
    assert second.color_level == 3
    assert second.has_tasks is True
    assert db.scalar(select(func.count()).select_from(CheckinRecord).where(CheckinRecord.user_id == "usr_a")) == 1


def test_recalculate_checkin_ignores_deleted_courses_and_deleted_plans(db: Session) -> None:
    _seed_user(db)
    _seed_course(db, course_id="crs_deleted", status="deleted")
    _seed_course(db, course_id="crs_active")
    _seed_plan_tree(db, course_id="crs_deleted", plan_id="sp_deleted_course", task_id="task_deleted_course")
    _seed_plan_tree(db, course_id="crs_active", plan_id="sp_deleted_plan", plan_status="deleted", task_id="task_deleted_plan")
    db.commit()

    result = recalculate_checkin(db, user_id="usr_a", checkin_date=date(2026, 7, 11), flush_only=False)

    assert result.total_subtask_count == 0
    assert result.completed_subtask_count == 0
    assert result.completion_ratio == Decimal("0.0000")
    assert result.color_level == 0
    assert result.has_tasks is False