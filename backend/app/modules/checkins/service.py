from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_DOWN
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.modules.checkins import repository
from app.modules.checkins.models import CheckinRecord
from app.modules.checkins.schemas import CheckinRangeRead, CheckinRangeSummaryRead, CheckinRead


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


def _new_checkin_id() -> str:
    return f"chkrec_{uuid4().hex}"


def _read_from_record(record: CheckinRecord) -> CheckinRead:
    return CheckinRead(
        id=record.id,
        checkin_date=record.checkin_date,
        total_subtask_count=record.total_subtask_count,
        completed_subtask_count=record.completed_subtask_count,
        completion_ratio=record.completion_ratio,
        color_level=record.color_level,
        has_tasks=record.total_subtask_count > 0,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def compute_checkin_snapshot(db: Session, *, user_id: str, checkin_date: date) -> CheckinRead:
    counts = repository.count_subtasks_for_date(db, user_id=user_id, checkin_date=checkin_date)
    ratio = calculate_completion_ratio(counts.total_subtask_count, counts.completed_subtask_count)
    return CheckinRead(
        id=None,
        checkin_date=checkin_date,
        total_subtask_count=counts.total_subtask_count,
        completed_subtask_count=counts.completed_subtask_count,
        completion_ratio=ratio,
        color_level=calculate_color_level(counts.total_subtask_count, counts.completed_subtask_count),
        has_tasks=counts.total_subtask_count > 0,
        created_at=None,
        updated_at=None,
    )


def recalculate_checkin(db: Session, *, user_id: str, checkin_date: date, flush_only: bool) -> CheckinRead:
    snapshot = compute_checkin_snapshot(db, user_id=user_id, checkin_date=checkin_date)
    record = repository.get_checkin_record(db, user_id=user_id, checkin_date=checkin_date)
    now = datetime.now(timezone.utc)
    if record is None:
        record = CheckinRecord(id=_new_checkin_id(), user_id=user_id, checkin_date=checkin_date, created_at=now)
        db.add(record)
    record.total_subtask_count = snapshot.total_subtask_count
    record.completed_subtask_count = snapshot.completed_subtask_count
    record.completion_ratio = snapshot.completion_ratio
    record.color_level = snapshot.color_level
    record.updated_at = now
    db.flush()
    if not flush_only:
        db.commit()
        db.refresh(record)
    return _read_from_record(record)


def get_checkin_day(db: Session, *, user_id: str, target_date: date) -> CheckinRead:
    record = repository.get_checkin_record(db, user_id=user_id, checkin_date=target_date)
    if record is not None:
        return _read_from_record(record)
    return compute_checkin_snapshot(db, user_id=user_id, checkin_date=target_date)


def get_checkin_range(db: Session, *, user_id: str, start_date: date, end_date: date) -> CheckinRangeRead:
    if end_date < start_date:
        raise CourseNexusError(code="VALIDATION_ERROR", message="结束日期不能早于开始日期", status_code=422)
    if (end_date - start_date).days > 365:
        raise CourseNexusError(code="VALIDATION_ERROR", message="查询范围不能超过 366 天", status_code=422)
    records = repository.list_checkin_records(db, user_id=user_id, start_date=start_date, end_date=end_date)
    items = [_read_from_record(record) for record in records]
    return CheckinRangeRead(start_date=start_date, end_date=end_date, items=items, summary=calculate_streak_summary(items))