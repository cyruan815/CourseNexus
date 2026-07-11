from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CheckinRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    checkin_date: date
    total_subtask_count: int
    completed_subtask_count: int
    completion_ratio: Decimal = Field(max_digits=5, decimal_places=4)
    color_level: int
    has_tasks: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CheckinRangeSummaryRead(BaseModel):
    task_days: int
    completed_days: int
    current_streak_days: int
    longest_streak_days: int


class CheckinRangeRead(BaseModel):
    start_date: date
    end_date: date
    items: list[CheckinRead]
    summary: CheckinRangeSummaryRead
