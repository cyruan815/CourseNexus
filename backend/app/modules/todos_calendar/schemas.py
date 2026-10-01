from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["not_started", "in_progress", "completed"]


class SubTaskTodoRead(BaseModel):
    subtask_id: str
    title: str
    subtask_type: str
    description: str | None = None
    status: TaskStatus
    sort_order: int
    execution_url: str | None = None


class TaskTodoRead(BaseModel):
    task_id: str
    plan_id: str
    plan_title: str
    course_id: str
    course_name: str
    title: str
    task_date: date
    status: TaskStatus
    derived_status: TaskStatus
    completed_subtask_count: int
    total_subtask_count: int
    first_incomplete_subtask_id: str | None = None
    subtasks: list[SubTaskTodoRead] = Field(default_factory=list)


class CourseTodoGroupRead(BaseModel):
    course_id: str
    course_name: str
    plan_ids: list[str]
    tasks: list[TaskTodoRead]


class TodayTodosRead(BaseModel):
    date: date
    tasks: list[TaskTodoRead]


class DayTodosRead(BaseModel):
    date: date
    courses: list[CourseTodoGroupRead]


class TaskSummaryRead(BaseModel):
    task_id: str
    plan_id: str
    plan_title: str
    course_id: str
    course_name: str
    title: str
    status: TaskStatus
    derived_status: TaskStatus
    sort_order: int


class CalendarDaySummaryRead(BaseModel):
    date: date
    course_count: int
    task_count: int
    subtask_count: int
    completed_subtask_count: int
    status: TaskStatus
    task_summaries: list[TaskSummaryRead] = Field(default_factory=list)
    hidden_task_count: int = 0


class CalendarMonthRead(BaseModel):
    month: str
    days: list[CalendarDaySummaryRead]


class CourseCalendarMonthRead(BaseModel):
    course_id: str
    course_name: str
    month: str
    days: list[CalendarDaySummaryRead]


class CourseDayTodosRead(BaseModel):
    course_id: str
    course_name: str
    date: date
    tasks: list[TaskTodoRead]
