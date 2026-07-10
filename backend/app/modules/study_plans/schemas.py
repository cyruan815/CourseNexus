from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.material_context.schemas import MaterialScope


PlanPreference = Literal["balanced", "fast_track", "mastery", "advanced"]
SubTaskType = Literal["learn", "review", "quiz", "test"]


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


class StudyPlanConfigParseRequest(BaseModel):
    goal_text: str = Field(min_length=1)
    material_scope: MaterialScope = Field(default_factory=MaterialScope)


class StudyPlanParsedConfig(BaseModel):
    goal_text: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    daily_available_minutes: int | None = Field(default=None, gt=0)
    preference: PlanPreference | None = None
    material_scope: MaterialScope = Field(default_factory=MaterialScope)
    unresolved_fields: list[str] = Field(default_factory=list)


class StudyPlanConfigParseResponse(StudyPlanParsedConfig):
    pass


class PlanMaterialUnit(BaseModel):
    topic: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    estimated_minutes: int = Field(gt=0)
    related_material_ids: list[str] = Field(min_length=1)
    citation_chunk_ids: list[str] = Field(default_factory=list)


class PlanBatchExtraction(BaseModel):
    units: list[PlanMaterialUnit] = Field(min_length=1)
    citation_chunk_ids: list[str] = Field(default_factory=list)


class StudySubTaskPreview(BaseModel):
    title: str
    subtask_type: SubTaskType
    description: str | None = None
    related_material_ids: list[str] = Field(min_length=1)
    estimated_minutes: int = Field(default=1, gt=0)
    citation_chunk_ids: list[str] = Field(default_factory=list)
    sort_order: int


class StudyTaskPreview(BaseModel):
    title: str
    task_date: date
    sort_order: int
    subtasks: list[StudySubTaskPreview]


class StudyPlanReduction(BaseModel):
    title: str = Field(min_length=1)
    tasks: list[StudyTaskPreview] = Field(min_length=1)
    citation_chunk_ids: list[str] = Field(default_factory=list)


class StudyPlanCoverage(BaseModel):
    expected_material_ids: list[str] = Field(default_factory=list)
    processed_material_ids: list[str] = Field(default_factory=list)
    batch_count: int = 0


class StudyPlanPreview(BaseModel):
    course_id: str
    title: str
    goal_text: str
    start_date: date
    end_date: date
    daily_available_minutes: int
    preference: PlanPreference = "balanced"
    material_scope: MaterialScope
    coverage: StudyPlanCoverage = Field(default_factory=StudyPlanCoverage)
    tasks: list[StudyTaskPreview]


class StudyPlanSaveRequest(StudyPlanBuildRequest):
    title: str | None = None
    preference: PlanPreference = "balanced"
    tasks: list[StudyTaskPreview] | None = None


class StudyPlanReplaceRequest(StudyPlanSaveRequest):
    expected_updated_at: datetime
    title: str
    tasks: list[StudyTaskPreview] = Field(min_length=1)


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
