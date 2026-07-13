from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HandoutGenerationParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str = "zh-CN"
    detail_level: Literal["brief", "standard", "deep"] = "standard"
    subtask_title: str | None = None
    subtask_description: str | None = None
    plan_goal: str | None = None
    diagnostic_weak_area: str | None = None
    diagnostic_explanation_style: str | None = None


class CitationBoundModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_citation_ids: list[str] = Field(min_length=1, max_length=4)

    @field_validator("source_citation_ids")
    @classmethod
    def _citation_ids_non_empty(cls, value: list[str]) -> list[str]:
        stripped = [item.strip() for item in value]
        if any(not item for item in stripped):
            raise ValueError("source_citation_ids must contain non-empty strings")
        return list(dict.fromkeys(stripped))


class FormulaVariable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    meaning: str = Field(min_length=1)
    unit: str | None = None


class FormulaBlock(CitationBoundModel):
    type: Literal["formula"] = "formula"
    title: str = Field(min_length=1)
    latex: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    variables: list[FormulaVariable] = Field(min_length=1)
    conditions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @field_validator("conditions", "limitations")
    @classmethod
    def _optional_lists_non_empty(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("items must be non-empty strings")
        return value


class ParagraphBlock(CitationBoundModel):
    type: Literal["paragraph"] = "paragraph"
    role: Literal["lead", "definition", "intuition", "why", "process", "summary"] = "definition"
    text: str = Field(min_length=1)


class ExampleBlock(CitationBoundModel):
    type: Literal["example"] = "example"
    title: str = Field(min_length=1)
    problem: str = Field(min_length=1)
    steps: list[str] = Field(min_length=1)
    answer: str = Field(min_length=1)
    explanation: str = Field(min_length=1)

    @field_validator("steps")
    @classmethod
    def _steps_non_empty(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("steps must contain non-empty strings")
        return value


class TableColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    label: str = Field(min_length=1)


class TableBlock(CitationBoundModel):
    type: Literal["table"] = "table"
    title: str = Field(min_length=1)
    columns: list[TableColumn] = Field(min_length=2, max_length=6)
    rows: list[dict[str, str | int | float | bool | None]] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def _row_keys_match_columns(self) -> "TableBlock":
        column_keys = {column.key for column in self.columns}
        if len(column_keys) != len(self.columns):
            raise ValueError("table column keys must be unique")
        for row in self.rows:
            if set(row) != column_keys:
                raise ValueError("table rows must match column keys")
        return self


class StepsBlock(CitationBoundModel):
    type: Literal["steps"] = "steps"
    title: str = Field(min_length=1)
    steps: list[str] = Field(min_length=1, max_length=12)

    @field_validator("steps")
    @classmethod
    def _steps_non_empty(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("steps must contain non-empty strings")
        return value


class CalloutBlock(CitationBoundModel):
    type: Literal["callout"] = "callout"
    tone: Literal["key", "tip", "warning", "mistake"] = "key"
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)


class MindmapNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    children: list[MindmapNode] = Field(default_factory=list, max_length=12)


class MindmapBlock(CitationBoundModel):
    type: Literal["mindmap"] = "mindmap"
    title: str = Field(min_length=1)
    root: MindmapNode


class MermaidBlock(CitationBoundModel):
    type: Literal["mermaid"] = "mermaid"
    title: str = Field(min_length=1)
    diagram_type: Literal["flowchart", "sequence", "class", "state", "er"] = "flowchart"
    code: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class ChartPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    value: float


class ChartSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    points: list[ChartPoint] = Field(min_length=1, max_length=24)


class ChartBlock(CitationBoundModel):
    type: Literal["chart"] = "chart"
    title: str = Field(min_length=1)
    chart_type: Literal["bar", "line", "pie"] = "bar"
    unit: str | None = None
    series: list[ChartSeries] = Field(min_length=1, max_length=6)
    explanation: str = Field(min_length=1)


HandoutBlock = Annotated[
    ParagraphBlock
    | FormulaBlock
    | ExampleBlock
    | TableBlock
    | StepsBlock
    | CalloutBlock
    | MindmapBlock
    | MermaidBlock
    | ChartBlock,
    Field(discriminator="type"),
]


class PrerequisiteItem(CitationBoundModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    example: str | None = None
    sort_order: int = Field(ge=1)


class ExamFocusItem(CitationBoundModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    sort_order: int = Field(ge=1)


class SelfCheckItem(CitationBoundModel):
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    explanation: str | None = None
    sort_order: int = Field(ge=1)


class HandoutSection(CitationBoundModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str | None = Field(default=None, min_length=1)
    lead: str | None = Field(default=None, min_length=1)
    blocks: list[HandoutBlock] = Field(default_factory=list, max_length=16)
    key_points: list[str] = Field(min_length=1, max_length=8)
    sort_order: int = Field(ge=1)

    @field_validator("key_points")
    @classmethod
    def _key_points_non_empty(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("key_points must contain non-empty strings")
        return value

    @model_validator(mode="after")
    def _has_legacy_body_or_structured_blocks(self) -> "HandoutSection":
        if self.body is None and not self.blocks:
            raise ValueError("section requires body or blocks")
        return self


class HandoutContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1, 2] = 1
    title: str | None = Field(default=None, min_length=1, max_length=255)
    overview: str = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    estimated_minutes: int | None = Field(default=None, ge=1, le=480)
    learning_objectives: list[str] = Field(min_length=1, max_length=8)
    prerequisites: list[PrerequisiteItem] = Field(default_factory=list, max_length=12)
    sections: list[HandoutSection] = Field(min_length=1, max_length=12)
    knowledge_map: MindmapBlock | MermaidBlock | None = None
    formula_cards: list[FormulaBlock] = Field(default_factory=list, max_length=12)
    exam_focus: list[ExamFocusItem] = Field(default_factory=list, max_length=12)
    self_check: list[SelfCheckItem] = Field(default_factory=list, max_length=20)
    summary: str = Field(min_length=1)

    @field_validator("learning_objectives")
    @classmethod
    def _objectives_non_empty(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("learning objectives must be non-empty")
        return value

    @model_validator(mode="after")
    def _v2_requires_title_and_blocks(self) -> "HandoutContent":
        if self.schema_version == 2:
            if self.title is None:
                raise ValueError("schema_version 2 handout requires title")
            if any(not section.blocks for section in self.sections):
                raise ValueError("schema_version 2 sections require blocks")
        return self