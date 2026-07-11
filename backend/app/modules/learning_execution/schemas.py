from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ExecutionCourseRead(BaseModel):
    course_id: str
    name: str


class ExecutionPlanRead(BaseModel):
    plan_id: str
    title: str
    status: str


class ExecutionMaterialRead(BaseModel):
    material_id: str
    name: str | None
    material_type: str | None
    parse_status: str | None
    availability: str


class ExecutionSubTaskRead(BaseModel):
    subtask_id: str
    title: str
    subtask_type: str
    description: str | None
    status: str
    completed_at: datetime | None
    sort_order: int


class ExecutionTaskRead(BaseModel):
    task_id: str
    title: str
    task_date: date
    status: str
    sort_order: int
    subtasks: list[ExecutionSubTaskRead]


class ExecutionContextRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    course: ExecutionCourseRead
    plan: ExecutionPlanRead
    execution_date: date
    tasks: list[ExecutionTaskRead]
    current_subtask_id: str
    related_materials: list[ExecutionMaterialRead]
    handout_content_id: str | None
    task_test_content_id: str | None