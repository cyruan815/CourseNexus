from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.material_context.schemas import MaterialScope


class StudyPlanBuildRequest(BaseModel):
    goal_text: str = Field(min_length=1)
    start_date: date
    end_date: date
    daily_available_minutes: int = Field(gt=0)
    material_scope: MaterialScope = Field(default_factory=MaterialScope)

    @model_validator(mode="after")
    def validate_date_range(self) -> "StudyPlanBuildRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class StudySubTaskPreview(BaseModel):
    title: str
    subtask_type: str
    description: str | None = None
    related_material_ids: list[str]
    sort_order: int


class StudyTaskPreview(BaseModel):
    title: str
    task_date: date
    sort_order: int
    subtasks: list[StudySubTaskPreview]


class StudyPlanPreview(BaseModel):
    course_id: str
    title: str
    goal_text: str
    start_date: date
    end_date: date
    daily_available_minutes: int
    material_scope: MaterialScope
    tasks: list[StudyTaskPreview]


class StudyPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    course_id: str
    title: str
    goal_text: str
    parsed_config_json: dict | list | None
    start_date: date
    end_date: date
    daily_available_minutes: int
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class StudyTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    plan_id: str
    course_id: str
    title: str
    task_date: date
    status: str
    sort_order: int
    created_at: datetime
    updated_at: datetime


class StudySubTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    plan_id: str
    course_id: str
    title: str
    subtask_type: str
    description: str | None
    related_material_ids_json: dict | list | None
    status: str
    completed_at: datetime | None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class StudyPlanBundleRead(BaseModel):
    plan: StudyPlanRead
    tasks: list[StudyTaskRead]
    subtasks: list[StudySubTaskRead]
