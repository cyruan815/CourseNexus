from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.modules.todos_calendar.repository import (
    TodoTaskRow,
    list_task_rows_for_course_date,
    list_task_rows_for_course_month,
    list_task_rows_for_date,
    list_task_rows_for_month,
)
from app.modules.todos_calendar.schemas import (
    CalendarDaySummaryRead,
    CalendarMonthRead,
    CourseCalendarMonthRead,
    CourseDayTodosRead,
    CourseTodoGroupRead,
    DayTodosRead,
    SubTaskTodoRead,
    TaskStatus,
    TaskSummaryRead,
    TaskTodoRead,
    TodayTodosRead,
)

TASK_SUMMARY_LIMIT = 3


def parse_month(month: str) -> tuple[date, date]:
    try:
        parts = month.split("-")
        if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
            raise ValueError
        year = int(parts[0])
        month_number = int(parts[1])
        start = date(year, month_number, 1)
    except ValueError as exc:
        raise CourseNexusError(code="VALIDATION_ERROR", message="月份格式必须为 YYYY-MM", status_code=422) from exc
    if month_number == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month_number + 1, 1)
    return start, end


def _derived_status(total: int, completed: int) -> TaskStatus:
    if total == 0 or completed == 0:
        return "not_started"
    if completed == total:
        return "completed"
    return "in_progress"


def _as_task_status(value: str | None) -> TaskStatus:
    if value in ("not_started", "in_progress", "completed"):
        return value
    raise CourseNexusError(code="STATE_CONFLICT", message="任务状态不合法", status_code=409, details={"status": value})


def _assert_task_status_matches(*, task_id: str, stored_status: str, derived_status: TaskStatus) -> None:
    if stored_status != derived_status:
        raise CourseNexusError(
            code="STATE_CONFLICT",
            message="一级任务状态与二级任务派生状态不一致",
            status_code=409,
            details={"task_id": task_id, "stored_status": stored_status, "derived_status": derived_status},
        )


def _task_sort_order(rows: list[TodoTaskRow], task_id: str) -> int:
    for row in rows:
        if row.task_id == task_id:
            return row.task_sort_order
    return 0


def build_task_reads(rows: list[TodoTaskRow]) -> list[TaskTodoRead]:
    grouped: dict[str, list[TodoTaskRow]] = defaultdict(list)
    for row in rows:
        grouped[row.task_id].append(row)

    tasks: list[TaskTodoRead] = []
    for task_rows in grouped.values():
        first = task_rows[0]
        subtasks = [
            SubTaskTodoRead(
                subtask_id=row.subtask_id,
                title=row.subtask_title or "",
                subtask_type=row.subtask_type or "",
                description=row.subtask_description,
                status=_as_task_status(row.subtask_status),
                sort_order=row.subtask_sort_order or 0,
                execution_url=None,
            )
            for row in task_rows
            if row.subtask_id is not None
        ]
        subtasks.sort(key=lambda subtask: (subtask.sort_order, subtask.subtask_id))
        completed = sum(1 for subtask in subtasks if subtask.status == "completed")
        derived_status = _derived_status(len(subtasks), completed)
        _assert_task_status_matches(task_id=first.task_id, stored_status=first.task_status, derived_status=derived_status)
        first_incomplete_subtask_id = next(
            (subtask.subtask_id for subtask in subtasks if subtask.status != "completed"),
            None,
        )
        tasks.append(
            TaskTodoRead(
                task_id=first.task_id,
                plan_id=first.plan_id,
                course_id=first.course_id,
                course_name=first.course_name,
                title=first.task_title,
                task_date=first.task_date,
                status=_as_task_status(first.task_status),
                derived_status=derived_status,
                completed_subtask_count=completed,
                total_subtask_count=len(subtasks),
                first_incomplete_subtask_id=first_incomplete_subtask_id,
                subtasks=subtasks,
            )
        )

    tasks.sort(key=lambda task: (task.course_name, _task_sort_order(rows, task.task_id), task.title, task.task_id))
    return tasks


def build_course_groups(tasks: list[TaskTodoRead]) -> list[CourseTodoGroupRead]:
    grouped: dict[str, list[TaskTodoRead]] = defaultdict(list)
    course_names: dict[str, str] = {}
    for task in tasks:
        grouped[task.course_id].append(task)
        course_names[task.course_id] = task.course_name

    groups: list[CourseTodoGroupRead] = []
    for course_id, course_tasks in grouped.items():
        plan_ids = list(dict.fromkeys(task.plan_id for task in course_tasks))
        groups.append(
            CourseTodoGroupRead(
                course_id=course_id,
                course_name=course_names[course_id],
                plan_ids=plan_ids,
                tasks=course_tasks,
            )
        )
    groups.sort(key=lambda group: group.course_name)
    return groups


def summarize_calendar_days(rows: list[TodoTaskRow], *, month: str) -> CalendarMonthRead:
    rows_by_date: dict[date, list[TodoTaskRow]] = defaultdict(list)
    for row in rows:
        rows_by_date[row.task_date].append(row)

    days: list[CalendarDaySummaryRead] = []
    for task_date, date_rows in rows_by_date.items():
        tasks = build_task_reads(date_rows)
        subtask_count = sum(task.total_subtask_count for task in tasks)
        completed_subtask_count = sum(task.completed_subtask_count for task in tasks)
        status = _derived_status(subtask_count, completed_subtask_count)
        summaries = [
            TaskSummaryRead(
                task_id=task.task_id,
                plan_id=task.plan_id,
                course_id=task.course_id,
                course_name=task.course_name,
                title=task.title,
                status=task.status,
                derived_status=task.derived_status,
                sort_order=_task_sort_order(date_rows, task.task_id),
            )
            for task in tasks[:TASK_SUMMARY_LIMIT]
        ]
        days.append(
            CalendarDaySummaryRead(
                date=task_date,
                course_count=len({task.course_id for task in tasks}),
                task_count=len(tasks),
                subtask_count=subtask_count,
                completed_subtask_count=completed_subtask_count,
                status=status,
                task_summaries=summaries,
                hidden_task_count=max(len(tasks) - TASK_SUMMARY_LIMIT, 0),
            )
        )

    days.sort(key=lambda day: day.date)
    return CalendarMonthRead(month=month, days=days)


def get_today_todos(db: Session, *, user_id: str, target_date: date) -> TodayTodosRead:
    rows = list_task_rows_for_date(db, user_id=user_id, target_date=target_date)
    return TodayTodosRead(date=target_date, tasks=build_task_reads(rows))


def get_global_day_todos(db: Session, *, user_id: str, target_date: date) -> DayTodosRead:
    rows = list_task_rows_for_date(db, user_id=user_id, target_date=target_date)
    return DayTodosRead(date=target_date, courses=build_course_groups(build_task_reads(rows)))


def get_global_month_calendar(db: Session, *, user_id: str, month: str) -> CalendarMonthRead:
    start, end = parse_month(month)
    rows = list_task_rows_for_month(db, user_id=user_id, month_start=start, month_end=end)
    return summarize_calendar_days(rows, month=month)


def get_course_day_todos(db: Session, *, user_id: str, course_id: str, target_date: date) -> CourseDayTodosRead:
    course, rows = list_task_rows_for_course_date(db, user_id=user_id, course_id=course_id, target_date=target_date)
    return CourseDayTodosRead(course_id=course.id, course_name=course.name, date=target_date, tasks=build_task_reads(rows))


def get_course_month_calendar(db: Session, *, user_id: str, course_id: str, month: str) -> CourseCalendarMonthRead:
    start, end = parse_month(month)
    course, rows = list_task_rows_for_course_month(db, user_id=user_id, course_id=course_id, month_start=start, month_end=end)
    month_read = summarize_calendar_days(rows, month=month)
    days = [day.model_copy(update={"course_count": 1}) for day in month_read.days]
    return CourseCalendarMonthRead(course_id=course.id, course_name=course.name, month=month, days=days)