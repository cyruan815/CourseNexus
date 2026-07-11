from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from app.modules.checkins.schemas import CheckinRead
from app.modules.checkins.service import calculate_color_level, calculate_completion_ratio, calculate_streak_summary


def _checkin(day: int, total: int, completed: int) -> CheckinRead:
    return CheckinRead(
        id=f"chk_{day}",
        checkin_date=date(2026, 7, day),
        total_subtask_count=total,
        completed_subtask_count=completed,
        completion_ratio=calculate_completion_ratio(total, completed),
        color_level=calculate_color_level(total, completed),
        has_tasks=total > 0,
        created_at=datetime(2026, 7, day, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, day, tzinfo=timezone.utc),
    )


def test_completion_ratio_uses_four_decimal_places() -> None:
    assert calculate_completion_ratio(0, 0) == Decimal("0.0000")
    assert calculate_completion_ratio(5, 1) == Decimal("0.2000")
    assert calculate_completion_ratio(3, 1) == Decimal("0.3333")


def test_color_level_distinguishes_no_tasks_from_not_started_tasks() -> None:
    assert calculate_color_level(0, 0) == 0
    assert calculate_color_level(4, 0) == 1
    assert calculate_color_level(5, 1) == 2
    assert calculate_color_level(5, 2) == 3
    assert calculate_color_level(5, 4) == 4
    assert calculate_color_level(5, 5) == 5


def test_streak_counts_any_completed_subtask_day() -> None:
    summary = calculate_streak_summary(
        [
            _checkin(1, total=0, completed=0),
            _checkin(2, total=3, completed=0),
            _checkin(3, total=3, completed=1),
            _checkin(4, total=3, completed=2),
            _checkin(6, total=3, completed=1),
        ]
    )

    assert summary.task_days == 4
    assert summary.completed_days == 3
    assert summary.current_streak_days == 1
    assert summary.longest_streak_days == 2
