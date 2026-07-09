from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CheckinRecord(Base):
    __tablename__ = "checkin_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    checkin_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_subtask_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completed_subtask_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completion_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=0, server_default="0")
    color_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "checkin_date", name="uq_checkin_records_user_date"),
        CheckConstraint("total_subtask_count >= 0", name="checkin_total_count_non_negative"),
        CheckConstraint("completed_subtask_count >= 0", name="checkin_completed_count_non_negative"),
        CheckConstraint("completed_subtask_count <= total_subtask_count", name="checkin_completed_not_greater_total"),
        CheckConstraint("completion_ratio >= 0 and completion_ratio <= 1", name="checkin_completion_ratio_range"),
        CheckConstraint("color_level >= 0 and color_level <= 5", name="checkin_color_level_range"),
        Index("ix_checkin_records_color_level", "color_level"),
        Index("ix_checkin_records_user_date", "user_id", "checkin_date"),
    )
