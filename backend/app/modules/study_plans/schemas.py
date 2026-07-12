from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, BeforeValidator, field_validator, model_validator

from app.modules.material_context.schemas import MaterialScope


PlanPreferenceLiteral = Literal["balanced", "fast_track", "mastery", "advanced", "sprint"]
DailyMinutesSource = Literal["user_text", "system_estimated", "user_modified"]
SubTaskType = Literal["learn", "review", "quiz", "test"]
MIN_DAILY_AVAILABLE_MINUTES = 30


def _normalize_preference_value(value: str | None) -> str | None:
    if value == "advanced":
        return "sprint"
    return value
PlanPreference = Annotated[PlanPreferenceLiteral, BeforeValidator(_normalize_preference_value)]


class StudyPlanBuildRequest(BaseModel):
    goal_text: str = Field(min_length=1)
    start_date: date
    end_date: date | None = None
    duration_days: int | None = Field(default=None, gt=0)
    daily_available_minutes: int | None = None
    recommended_daily_minutes: int | None = Field(default=None, gt=0)
    daily_minutes_source: DailyMinutesSource | None = None
    preference: PlanPreference = "balanced"
    diagnostic_profile: dict[str, object] = Field(default_factory=dict)
    material_snapshot: dict[str, object] = Field(default_factory=dict)
    coverage: dict[str, object] = Field(default_factory=dict)
    capacity: dict[str, object] = Field(default_factory=dict)
    generation_metadata: dict[str, object] = Field(default_factory=dict)
    material_scope: MaterialScope = Field(default_factory=MaterialScope)

    @field_validator("daily_available_minutes")
    @classmethod
    def validate_daily_available_minutes(cls, value: int | None) -> int | None:
        if value is not None and value < MIN_DAILY_AVAILABLE_MINUTES:
            raise ValueError("daily_available_minutes must be at least 30")
        return value

    @field_validator("preference", mode="after")
    @classmethod
    def normalize_preference(cls, value: PlanPreference) -> PlanPreference:
        normalized = _normalize_preference_value(value)
        return normalized if normalized is not None else value

    @model_validator(mode="after")
    def validate_date_range(self) -> "StudyPlanBuildRequest":
        if self.end_date is None and self.duration_days is None:
            raise ValueError("either end_date or duration_days must be provided")

        if self.end_date is None and self.duration_days is not None:
            self.end_date = self.start_date + timedelta(days=self.duration_days - 1)
        elif self.end_date is not None and self.duration_days is None:
            self.duration_days = (self.end_date - self.start_date).days + 1
        elif self.end_date is not None and self.duration_days is not None:
            expected_end_date = self.start_date + timedelta(days=self.duration_days - 1)
            if expected_end_date != self.end_date:
                raise ValueError("end_date and duration_days must describe the same date range")

        if self.end_date is None or self.duration_days is None:
            raise ValueError("end_date and duration_days must be resolvable")
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
    duration_days: int | None = Field(default=None, gt=0)
    daily_available_minutes: int | None = Field(default=None, gt=0)
    recommended_daily_minutes: int | None = Field(default=None, gt=0)
    daily_minutes_source: DailyMinutesSource | None = None
    preference: PlanPreference | None = None
    diagnostic_profile: dict[str, object] = Field(default_factory=dict)
    material_snapshot: dict[str, object] = Field(default_factory=dict)
    coverage: dict[str, object] = Field(default_factory=dict)
    capacity: dict[str, object] = Field(default_factory=dict)
    generation_metadata: dict[str, object] = Field(default_factory=dict)
    material_scope: MaterialScope = Field(default_factory=MaterialScope)
    unresolved_fields: list[str] = Field(default_factory=list)

    @field_validator("daily_available_minutes")
    @classmethod
    def validate_daily_available_minutes(cls, value: int | None) -> int | None:
        if value is not None and value < MIN_DAILY_AVAILABLE_MINUTES:
            raise ValueError("daily_available_minutes must be at least 30")
        return value

    @field_validator("preference", mode="after")
    @classmethod
    def normalize_preference(cls, value: PlanPreference | None) -> PlanPreference | None:
        return _normalize_preference_value(value)

    @model_validator(mode="after")
    def validate_date_range(self) -> "StudyPlanParsedConfig":
        if self.start_date is not None and self.end_date is not None and self.duration_days is None:
            self.duration_days = (self.end_date - self.start_date).days + 1
        elif self.start_date is not None and self.duration_days is not None and self.end_date is None:
            self.end_date = self.start_date + timedelta(days=self.duration_days - 1)
        elif self.start_date is not None and self.end_date is not None and self.duration_days is not None:
            expected_end_date = self.start_date + timedelta(days=self.duration_days - 1)
            if expected_end_date != self.end_date:
                raise ValueError("end_date and duration_days must describe the same date range")
        return self


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
    duration_days: int | None = None
    daily_available_minutes: int
    recommended_daily_minutes: int | None = None
    daily_minutes_source: DailyMinutesSource | None = None
    preference: PlanPreference = "balanced"
    diagnostic_profile: dict[str, object] = Field(default_factory=dict)
    material_snapshot: dict[str, object] = Field(default_factory=dict)
    material_scope: MaterialScope
    coverage: StudyPlanCoverage = Field(default_factory=StudyPlanCoverage)
    capacity: dict[str, object] = Field(default_factory=dict)
    generation_metadata: dict[str, object] = Field(default_factory=dict)
    tasks: list[StudyTaskPreview]

    @field_validator("daily_available_minutes")
    @classmethod
    def validate_daily_available_minutes(cls, value: int | None) -> int | None:
        if value is not None and value < MIN_DAILY_AVAILABLE_MINUTES:
            raise ValueError("daily_available_minutes must be at least 30")
        return value

    @field_validator("preference", mode="after")
    @classmethod
    def normalize_preference(cls, value: PlanPreference) -> PlanPreference:
        normalized = _normalize_preference_value(value)
        return normalized if normalized is not None else value


class StudyPlanSaveRequest(StudyPlanBuildRequest):
    title: str | None = None
    tasks: list[StudyTaskPreview] | None = None


class StudyPlanRegenerationPreviewRequest(BaseModel):
    goal_text: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = Field(default=None, gt=0)
    daily_available_minutes: int | None = Field(default=None, gt=0)
    preference: PlanPreference | None = None
    material_scope: MaterialScope | None = None

    @field_validator("daily_available_minutes")
    @classmethod
    def validate_daily_available_minutes(cls, value: int | None) -> int | None:
        if value is not None and value < MIN_DAILY_AVAILABLE_MINUTES:
            raise ValueError("daily_available_minutes must be at least 30")
        return value

    @field_validator("preference", mode="after")
    @classmethod
    def normalize_preference(cls, value: PlanPreference | None) -> PlanPreference | None:
        return _normalize_preference_value(value)

    @model_validator(mode="after")
    def validate_optional_date_range(self) -> "StudyPlanRegenerationPreviewRequest":
        if self.start_date is not None and self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if self.start_date is not None and self.duration_days is not None and self.end_date is None:
            self.end_date = self.start_date + timedelta(days=self.duration_days - 1)
        if self.start_date is not None and self.end_date is not None and self.duration_days is None:
            self.duration_days = (self.end_date - self.start_date).days + 1
        return self


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
