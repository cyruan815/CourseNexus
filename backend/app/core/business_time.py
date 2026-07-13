from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo


SHANGHAI_TIMEZONE = ZoneInfo("Asia/Shanghai")


def today_shanghai() -> date:
    return datetime.now(SHANGHAI_TIMEZONE).date()
