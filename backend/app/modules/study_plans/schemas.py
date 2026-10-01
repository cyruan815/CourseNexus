from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, BeforeValidator, field_validator, model_validator

from app.modules.material_context.schemas import MaterialScope


PlanPreferenceLiteral = Literal["balanced", "fast_track", "mastery", "advanced", "sprint"]
StudyPreference = Literal["fast_track", "balanced", "mastery", "sprint"]
ContentDepth = Literal["concise", "standard", "detailed"]
IntensityLevel = Literal["low", "standard", "high"]
AmbiguousConfigField = Literal["start_date", "end_date", "duration_days", "daily_available_minutes", "preference"]
DailyMinutesSource = Literal["user_text", "system_estimated", "user_modified"]
StudyPlanClientFlow = Literal["legacy", "wizard_v1"]
SubTaskTypeLiteral = Literal["learn", "review", "quiz", "test"]
MIN_DAILY_AVAILABLE_MINUTES = 30
DIAGNOSTIC_QUESTION_VERSION = "study_plan_diagnostic_v2"
MAX_STUDY_PLAN_TITLE_LENGTH = 255
MasteryLevel = Literal["none", "heard", "some", "familiar"]
WeakArea = Literal["concept", "calculation", "application", "memorization", "other"]
DiagnosticQuestionType = Literal["topic_mastery", "weak_area", "diagnostic_note"]
PriorKnowledgeLevel = Literal["none", "little", "some", "solid"]
ExplanationStyle = Literal["plain_language", "step_by_step", "example_first", "exam_focused"]

def _normalize_preference_value(value: str | None) -> str | None:
    if value == "advanced":
        return "sprint"
    return value
PlanPreference = Annotated[PlanPreferenceLiteral, BeforeValidator(_normalize_preference_value)]


def _normalize_subtask_type(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "study": "learn",
        "learning": "learn",
        "read": "learn",
        "recap": "review",
        "revision": "review",
        "practice": "quiz",
        "exercise": "quiz",
        "exercises": "quiz",
        "drill": "quiz",
        "self_test": "quiz",
        "assessment": "quiz",
        "exam": "test",
        "final": "test",
        "final_test": "test",
        "comprehensive_test": "test",
    }
    return aliases.get(normalized, normalized)


SubTaskType = Annotated[SubTaskTypeLiteral, BeforeValidator(_normalize_subtask_type)]

class StudyPreferenceOverrides(BaseModel):
    content_depth: ContentDepth | None = None
    example_intensity: IntensityLevel | None = None
    assessment_intensity: IntensityLevel | None = None
    review_intensity: IntensityLevel | None = None

class StudyPlanBuildRequest(BaseModel):
    goal_text: str = Field(min_length=1)
    start_date: date
    end_date: date | None = None
    duration_days: int | None = Field(default=None, gt=0)
    daily_available_minutes: int | None = None
    recommended_daily_minutes: int | None = Field(default=None, gt=0)
    daily_minutes_source: DailyMinutesSource | None = None
    preference: PlanPreference = "balanced"
    preference_overrides: StudyPreferenceOverrides = Field(default_factory=StudyPreferenceOverrides)
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

    @field_validator("preference_overrides", mode="before")
    @classmethod
    def normalize_nullable_preference_overrides(cls, value: object) -> object:
        return {} if value is None else value

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



class StudyPlanConfigExtraction(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = Field(default=None, ge=1)
    daily_available_minutes: int | None = Field(default=None, ge=1)
    preference: StudyPreference | None = None
    preference_overrides: StudyPreferenceOverrides = Field(default_factory=StudyPreferenceOverrides)
    ambiguous_fields: list[AmbiguousConfigField] = Field(default_factory=list)

    @field_validator("preference_overrides", mode="before")
    @classmethod
    def normalize_nullable_preference_overrides(cls, value: object) -> object:
        return {} if value is None else value

    @field_validator("ambiguous_fields", mode="before")
    @classmethod
    def normalize_nullable_ambiguous_fields(cls, value: object) -> object:
        return [] if value is None else value

class StudyPlanDiagnosticConfirmedConfig(BaseModel):
    start_date: date | None = None
    duration_days: int | None = Field(default=None, gt=0)
    preference: PlanPreference | None = None
    daily_available_minutes: int | None = None
    daily_minutes_source: DailyMinutesSource | None = None

    @field_validator("daily_available_minutes")
    @classmethod
    def validate_daily_available_minutes(cls, value: int | None) -> int | None:
        if value is not None and value < MIN_DAILY_AVAILABLE_MINUTES:
            raise ValueError("daily_available_minutes must be at least 30")
        return value


class StudyPlanDiagnosticTopicCandidate(BaseModel):
    topic_title: str = Field(min_length=1)
    diagnostic_value: str | None = None
    question_text: str | None = None
    source_chunk_id: str | None = None


class StudyPlanDiagnosticTopicExtraction(BaseModel):
    topics: list[StudyPlanDiagnosticTopicCandidate] = Field(default_factory=list)


class StudyPlanDiagnosticQuestionRequest(BaseModel):
    goal_text: str = Field(min_length=1)
    material_scope: MaterialScope = Field(default_factory=MaterialScope)
    confirmed_config: StudyPlanDiagnosticConfirmedConfig = Field(default_factory=StudyPlanDiagnosticConfirmedConfig)


class StudyPlanDiagnosticQuestionOption(BaseModel):
    value: str
    label: str


class StudyPlanDiagnosticQuestion(BaseModel):
    question_id: str
    question_type: DiagnosticQuestionType
    question_type_label: str | None = None
    question_text: str
    sort_order: int = Field(gt=0)
    required: bool = True
    topic_id: str | None = None
    topic_title: str | None = None
    options: list[StudyPlanDiagnosticQuestionOption] = Field(default_factory=list)
    placeholder: str | None = None


class StudyPlanDiagnosticQuestionsResponse(BaseModel):
    question_version: str = DIAGNOSTIC_QUESTION_VERSION
    questions: list[StudyPlanDiagnosticQuestion]
    generation_metadata: dict[str, object] = Field(default_factory=dict)


class TopicMasteryAnswer(BaseModel):
    topic_id: str = Field(min_length=1)
    topic_title: str = Field(min_length=1)
    mastery_level: MasteryLevel


class StudyPlanDiagnosticProfileRequest(BaseModel):
    question_version: str = DIAGNOSTIC_QUESTION_VERSION
    topic_mastery: list[TopicMasteryAnswer] = Field(min_length=3, max_length=3)
    weak_area: WeakArea
    diagnostic_note: str | None = None
    material_scope: MaterialScope = Field(default_factory=MaterialScope)


    @model_validator(mode="after")
    def validate_unique_topic_mastery(self) -> "StudyPlanDiagnosticProfileRequest":
        topic_ids = [answer.topic_id for answer in self.topic_mastery]
        if len(set(topic_ids)) != len(topic_ids):
            raise ValueError("topic_mastery topic_id values must be unique")
        return self

class StudyPlanDiagnosticProfileResponse(BaseModel):
    question_version: str = DIAGNOSTIC_QUESTION_VERSION
    prior_knowledge_level: PriorKnowledgeLevel
    foundation_needed: bool
    weak_topics: list[str] = Field(default_factory=list)
    weak_area: WeakArea
    explanation_style: ExplanationStyle
    diagnostic_note: str | None = None


class StudyPlanParsedConfig(BaseModel):
    goal_text: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = Field(default=None, gt=0)
    daily_available_minutes: int | None = Field(default=None, gt=0)
    recommended_daily_minutes: int | None = Field(default=None, gt=0)
    daily_minutes_source: DailyMinutesSource | None = None
    preference: PlanPreference | None = None
    preference_overrides: StudyPreferenceOverrides = Field(default_factory=StudyPreferenceOverrides)
    diagnostic_profile: dict[str, object] = Field(default_factory=dict)
    material_snapshot: dict[str, object] = Field(default_factory=dict)
    coverage: dict[str, object] = Field(default_factory=dict)
    capacity: dict[str, object] = Field(default_factory=dict)
    generation_metadata: dict[str, object] = Field(default_factory=dict)
    material_scope: MaterialScope = Field(default_factory=MaterialScope)
    unresolved_fields: list[str] = Field(default_factory=list)
    needs_confirmation_fields: list[str] = Field(default_factory=list)
    field_labels: dict[str, str] = Field(default_factory=dict)
    unresolved_field_prompts: list[dict[str, str]] = Field(default_factory=list)
    needs_confirmation_field_prompts: list[dict[str, str]] = Field(default_factory=list)
    field_options: dict[str, list[dict[str, str]]] = Field(default_factory=dict)

    @field_validator("diagnostic_profile", "material_snapshot", "coverage", "capacity", "generation_metadata", mode="before")
    @classmethod
    def normalize_nullable_dict_fields(cls, value: object) -> object:
        return {} if value is None else value


    @field_validator("preference_overrides", mode="before")
    @classmethod
    def normalize_nullable_overrides(cls, value: object) -> object:
        return {} if value is None else value
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
    generation_parameters: dict[str, object] = Field(default_factory=dict)
    sort_order: int


class StudyTaskPreview(BaseModel):
    title: str
    task_date: date
    sort_order: int
    subtasks: list[StudySubTaskPreview]


class StudyPlanReduction(BaseModel):
    title: str = Field(min_length=1, max_length=MAX_STUDY_PLAN_TITLE_LENGTH)
    tasks: list[StudyTaskPreview] = Field(min_length=1)
    citation_chunk_ids: list[str] = Field(default_factory=list)


class StudyPlanCoverage(BaseModel):
    expected_material_ids: list[str] = Field(default_factory=list)
    processed_material_ids: list[str] = Field(default_factory=list)
    batch_count: int = 0


class StudyPlanPreview(BaseModel):
    course_id: str
    title: str = Field(min_length=1, max_length=MAX_STUDY_PLAN_TITLE_LENGTH)
    goal_text: str
    start_date: date
    end_date: date
    duration_days: int | None = None
    daily_available_minutes: int
    recommended_daily_minutes: int | None = None
    daily_minutes_source: DailyMinutesSource | None = None
    preference: PlanPreference = "balanced"
    preference_overrides: StudyPreferenceOverrides = Field(default_factory=StudyPreferenceOverrides)
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

    @field_validator("preference_overrides", mode="before")
    @classmethod
    def normalize_nullable_preference_overrides(cls, value: object) -> object:
        return {} if value is None else value

    @field_validator("preference", mode="after")
    @classmethod
    def normalize_preference(cls, value: PlanPreference) -> PlanPreference:
        normalized = _normalize_preference_value(value)
        return normalized if normalized is not None else value


class StudyPlanSaveRequest(StudyPlanBuildRequest):
    client_flow: StudyPlanClientFlow = "legacy"
    title: str | None = Field(default=None, min_length=1, max_length=MAX_STUDY_PLAN_TITLE_LENGTH)
    tasks: list[StudyTaskPreview] | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("title must not be blank")
        return normalized


class StudyPlanRegenerationPreviewRequest(BaseModel):
    goal_text: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = Field(default=None, gt=0)
    daily_available_minutes: int | None = Field(default=None, gt=0)
    preference: PlanPreference | None = None
    preference_overrides: StudyPreferenceOverrides | None = None
    diagnostic_profile: dict[str, object] | None = None
    material_scope: MaterialScope | None = None

    @field_validator("daily_available_minutes")
    @classmethod
    def validate_daily_available_minutes(cls, value: int | None) -> int | None:
        if value is not None and value < MIN_DAILY_AVAILABLE_MINUTES:
            raise ValueError("daily_available_minutes must be at least 30")
        return value

    @field_validator("preference_overrides", mode="before")
    @classmethod
    def normalize_nullable_preference_overrides(cls, value: object) -> object:
        return None if value is None else value

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
    title: str = Field(min_length=1, max_length=MAX_STUDY_PLAN_TITLE_LENGTH)
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
