from __future__ import annotations

from datetime import date

import pytest

from app.core.errors import CourseNexusError
from app.modules.todos_calendar.repository import TodoTaskRow
from app.modules.todos_calendar.service import build_course_groups, build_task_reads, summarize_calendar_days


def _row(
    *,
    course_name: str = "Computer Networks",
    course_id: str = "crs_net",
    plan_id: str = "sp_net",
    task_id: str = "task_transport",
    task_title: str = "可靠传输",
    task_status: str = "not_started",
    task_sort_order: int = 1,
    subtask_id: str | None = "sub_window",
    subtask_title: str | None = "学习滑动窗口",
    subtask_status: str | None = "not_started",
    subtask_sort_order: int | None = 1,
) -> TodoTaskRow:
    return TodoTaskRow(
        course_id=course_id,
        course_name=course_name,
        plan_id=plan_id,
        plan_title="期末复习计划",
        plan_start_date=date(2026, 7, 10),
        plan_end_date=date(2026, 7, 20),
        task_id=task_id,
        task_title=task_title,
        task_date=date(2026, 7, 11),
        task_status=task_status,
        task_sort_order=task_sort_order,
        subtask_id=subtask_id,
        subtask_title=subtask_title,
        subtask_type="learn" if subtask_id else None,
        subtask_description="学习内容" if subtask_id else None,
        subtask_status=subtask_status,
        subtask_sort_order=subtask_sort_order,
    )


def test_build_task_reads_sorts_by_course_task_and_subtask_order() -> None:
    rows = [
        _row(
            course_name="Math",
            task_id="task_b",
            task_title="极限复习",
            task_sort_order=2,
            subtask_id="sub_b2",
            subtask_sort_order=2,
        ),
        _row(
            course_name="Computer Networks",
            task_id="task_a",
            task_title="可靠传输",
            task_sort_order=1,
            subtask_id="sub_a1",
            subtask_sort_order=1,
        ),
        _row(
            course_name="Math",
            task_id="task_b",
            task_title="极限复习",
            task_sort_order=2,
            subtask_id="sub_b1",
            subtask_sort_order=1,
        ),
    ]

    tasks = build_task_reads(rows)

    assert [task.course_name for task in tasks] == ["Computer Networks", "Math"]
    assert [sub.subtask_id for sub in tasks[1].subtasks] == ["sub_b1", "sub_b2"]


def test_build_task_reads_derived_status_and_first_incomplete_subtask() -> None:
    rows = [
        _row(task_status="in_progress", subtask_id="sub_done", subtask_status="completed", subtask_sort_order=1),
        _row(task_status="in_progress", subtask_id="sub_next", subtask_status="not_started", subtask_sort_order=2),
    ]

    task = build_task_reads(rows)[0]

    assert task.derived_status == "in_progress"
    assert task.completed_subtask_count == 1
    assert task.total_subtask_count == 2
    assert task.first_incomplete_subtask_id == "sub_next"


def test_build_task_reads_rejects_status_mismatch() -> None:
    rows = [_row(task_status="completed", subtask_id="sub_next", subtask_status="not_started")]

    with pytest.raises(CourseNexusError) as exc_info:
        build_task_reads(rows)

    assert exc_info.value.code == "STATE_CONFLICT"


def test_build_course_groups_keeps_plan_ids_but_does_not_require_plan_title() -> None:
    tasks = build_task_reads(
        [
            _row(course_id="crs_net", course_name="Computer Networks", plan_id="sp_a", task_id="task_a"),
            _row(
                course_id="crs_net",
                course_name="Computer Networks",
                plan_id="sp_b",
                task_id="task_b",
                task_sort_order=2,
            ),
        ]
    )

    groups = build_course_groups(tasks)

    assert len(groups) == 1
    assert groups[0].course_name == "Computer Networks"
    assert groups[0].plan_ids == ["sp_a", "sp_b"]
    assert [task.plan_id for task in groups[0].tasks] == ["sp_a", "sp_b"]


def test_summarize_calendar_days_limits_task_summaries_to_three() -> None:
    rows = [
        _row(task_id=f"task_{index}", task_title=f"任务 {index}", task_sort_order=index, subtask_id=f"sub_{index}")
        for index in range(1, 6)
    ]

    month = summarize_calendar_days(rows, month="2026-07")

    day = month.days[0]
    assert day.task_count == 5
    assert [summary.title for summary in day.task_summaries] == ["任务 1", "任务 2", "任务 3"]
    assert day.hidden_task_count == 2

from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.db.models  # noqa: F401
from app.modules.courses.models import Course
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask
from app.modules.todos_calendar.service import (
    get_course_day_todos,
    get_course_month_calendar,
    get_global_day_todos,
    get_global_month_calendar,
    get_today_todos,
)
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


def _seed_user(db: Session, user_id: str, username: str) -> None:
    db.add(User(id=user_id, username=username, password_hash="hash", status="active"))


def _seed_course(db: Session, *, course_id: str, user_id: str, name: str, status: str = "active") -> None:
    db.add(Course(id=course_id, user_id=user_id, name=name, status=status, deleted_at=datetime.now(timezone.utc) if status == "deleted" else None))


def _seed_plan_tree(
    db: Session,
    *,
    user_id: str = "usr_a",
    course_id: str = "crs_net",
    plan_id: str = "sp_net",
    plan_status: str = "active",
    task_id: str = "task_transport",
    task_title: str = "可靠传输",
    task_date: date = date(2026, 7, 11),
    task_status: str = "in_progress",
    task_sort_order: int = 1,
    subtask_statuses: tuple[str, ...] = ("completed", "not_started"),
) -> None:
    db.add(
        StudyPlan(
            id=plan_id,
            user_id=user_id,
            course_id=course_id,
            title="期末复习计划",
            goal_text="复习",
            parsed_config_json={},
            start_date=date(2026, 7, 10),
            end_date=date(2026, 7, 20),
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
            title=task_title,
            task_date=task_date,
            status=task_status,
            sort_order=task_sort_order,
        )
    )
    for index, status in enumerate(subtask_statuses, start=1):
        db.add(
            StudySubTask(
                id=f"{task_id}_sub_{index}",
                task_id=task_id,
                plan_id=plan_id,
                course_id=course_id,
                title=f"{task_title} 子任务 {index}",
                subtask_type="learn",
                description="学习内容",
                related_material_ids_json=[],
                status=status,
                sort_order=index,
            )
        )


def _seed_calendar_fixture(db: Session) -> None:
    _seed_user(db, "usr_a", "alice")
    _seed_user(db, "usr_b", "bob")
    _seed_course(db, course_id="crs_net", user_id="usr_a", name="Computer Networks")
    _seed_course(db, course_id="crs_math", user_id="usr_a", name="Math")
    _seed_course(db, course_id="crs_deleted", user_id="usr_a", name="Deleted", status="deleted")
    _seed_course(db, course_id="crs_other", user_id="usr_b", name="Other")
    _seed_plan_tree(db, course_id="crs_math", plan_id="sp_math", task_id="task_math", task_title="极限复习", task_status="not_started", task_sort_order=2, subtask_statuses=("not_started",))
    _seed_plan_tree(db, course_id="crs_net", plan_id="sp_net", task_id="task_transport", task_title="可靠传输", task_status="in_progress", task_sort_order=1)
    _seed_plan_tree(db, course_id="crs_net", plan_id="sp_net_two", task_id="task_congestion", task_title="拥塞控制", task_status="not_started", task_sort_order=2, subtask_statuses=("not_started",))
    _seed_plan_tree(db, course_id="crs_net", plan_id="sp_later", task_id="task_later", task_title="后续复习", task_date=date(2026, 7, 12), task_status="not_started", subtask_statuses=("not_started",))
    _seed_plan_tree(db, user_id="usr_b", course_id="crs_other", plan_id="sp_other", task_id="task_other", task_title="其他用户任务", task_status="not_started", subtask_statuses=("not_started",))
    _seed_plan_tree(db, course_id="crs_deleted", plan_id="sp_deleted_course", task_id="task_deleted_course", task_title="删除课程任务", task_status="not_started", subtask_statuses=("not_started",))
    _seed_plan_tree(db, course_id="crs_net", plan_id="sp_deleted_plan", plan_status="deleted", task_id="task_deleted_plan", task_title="删除计划任务", task_status="not_started", subtask_statuses=("not_started",))
    db.commit()


def test_get_today_todos_filters_user_and_returns_nested_subtasks(db: Session) -> None:
    _seed_calendar_fixture(db)

    result = get_today_todos(db, user_id="usr_a", target_date=date(2026, 7, 11))

    assert [task.course_name for task in result.tasks] == ["Computer Networks", "Computer Networks", "Math"]
    assert [task.title for task in result.tasks] == ["可靠传输", "拥塞控制", "极限复习"]
    assert result.tasks[0].subtasks
    assert all(task.title not in {"其他用户任务", "删除课程任务", "删除计划任务"} for task in result.tasks)


def test_get_global_month_calendar_limits_summaries_and_counts_unique_courses(db: Session) -> None:
    _seed_calendar_fixture(db)

    result = get_global_month_calendar(db, user_id="usr_a", month="2026-07")

    day = next(day for day in result.days if day.date == date(2026, 7, 11))
    assert day.course_count == 2
    assert day.task_count == 3
    assert [summary.title for summary in day.task_summaries] == ["可靠传输", "拥塞控制", "极限复习"]
    assert day.hidden_task_count == 0


def test_get_course_day_todos_returns_only_requested_course_without_plan_title(db: Session) -> None:
    _seed_calendar_fixture(db)

    result = get_course_day_todos(db, user_id="usr_a", course_id="crs_net", target_date=date(2026, 7, 11))

    assert result.course_name == "Computer Networks"
    assert [task.course_id for task in result.tasks] == ["crs_net", "crs_net"]
    assert [task.plan_id for task in result.tasks] == ["sp_net", "sp_net_two"]
    assert all(task.subtasks for task in result.tasks)


def test_get_course_day_todos_returns_empty_for_existing_course_empty_date(db: Session) -> None:
    _seed_calendar_fixture(db)

    result = get_course_day_todos(db, user_id="usr_a", course_id="crs_math", target_date=date(2026, 7, 12))

    assert result.tasks == []


def test_get_course_month_calendar_hides_cross_user_course(db: Session) -> None:
    _seed_calendar_fixture(db)

    with pytest.raises(CourseNexusError) as exc_info:
        get_course_month_calendar(db, user_id="usr_a", course_id="crs_other", month="2026-07")

    assert exc_info.value.code == "NOT_FOUND"


def test_calendar_queries_do_not_write_session_state(db: Session) -> None:
    _seed_calendar_fixture(db)

    get_today_todos(db, user_id="usr_a", target_date=date(2026, 7, 11))
    get_global_day_todos(db, user_id="usr_a", target_date=date(2026, 7, 11))
    get_global_month_calendar(db, user_id="usr_a", month="2026-07")

    assert list(db.new) == []
    assert list(db.dirty) == []
    assert list(db.deleted) == []