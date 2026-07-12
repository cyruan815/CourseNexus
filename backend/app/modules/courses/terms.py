from __future__ import annotations

from typing import Literal


CourseTerm = Literal[
    "2027-2028-autumn",
    "2027-2028-spring",
    "2026-2027-autumn",
    "2026-2027-spring",
    "2025-2026-autumn",
    "2025-2026-spring",
    "2024-2025-autumn",
    "2024-2025-spring",
]

COURSE_TERM_OPTIONS: tuple[tuple[CourseTerm, str], ...] = (
    ("2027-2028-autumn", "2027-2028 秋季"),
    ("2027-2028-spring", "2027-2028 春季"),
    ("2026-2027-autumn", "2026-2027 秋季"),
    ("2026-2027-spring", "2026-2027 春季"),
    ("2025-2026-autumn", "2025-2026 秋季"),
    ("2025-2026-spring", "2025-2026 春季"),
    ("2024-2025-autumn", "2024-2025 秋季"),
    ("2024-2025-spring", "2024-2025 春季"),
)
