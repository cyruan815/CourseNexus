from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from app.modules.checkins.schemas import CheckinRangeSummaryRead, CheckinRead


def calculate_completion_ratio(total: int, completed: int) -> Decimal:
    if total <= 0:
        return Decimal("0.0000")
    return (Decimal(completed) / Decimal(total)).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)


def calculate_color_level(total: int, completed: int) -> int:
    if total <= 0:
        return 0
    if completed <= 0:
        return 1
    ratio = calculate_completion_ratio(total, completed)
    if ratio < Decimal("0.4000"):
        return 2
    if ratio < Decimal("0.8000"):
        return 3
    if ratio < Decimal("1.0000"):
        return 4
    return 5


def calculate_streak_summary(items: list[CheckinRead]) -> CheckinRangeSummaryRead:
    ordered = sorted(items, key=lambda item: item.checkin_date)
    task_days = sum(1 for item in ordered if item.total_subtask_count > 0)
    completed_days = sum(1 for item in ordered if item.total_subtask_count > 0 and item.completed_subtask_count > 0)
    longest = 0
    current_run = 0
    previous_date = None
    last_run = 0
    for item in ordered:
        counts_for_streak = item.total_subtask_count > 0 and item.completed_subtask_count > 0
        if not counts_for_streak:
            current_run = 0
            previous_date = item.checkin_date
            continue
        if previous_date is not None and (item.checkin_date - previous_date).days == 1:
            current_run += 1
        else:
            current_run = 1
        longest = max(longest, current_run)
        last_run = current_run
        previous_date = item.checkin_date
    return CheckinRangeSummaryRead(
        task_days=task_days,
        completed_days=completed_days,
        current_streak_days=last_run,
        longest_streak_days=longest,
    )
