from __future__ import annotations

import re

from app.core.config import MODEL_PURPOSES, Settings


REDACTED_VALUE = "[REDACTED]"
_BEARER_TOKEN_PATTERN = re.compile(
    r"\bBearer\s+[A-Za-z0-9._~+/=-]+",
    flags=re.IGNORECASE,
)
_LABELED_SECRET_PATTERN = re.compile(
    r"\b(?P<label>(?:[A-Za-z0-9]+_)*api_key|secret_key)"
    r"(?P<separator>\s*[:=]\s*)"
    r"(?P<value>[^\s,;|]+)",
    flags=re.IGNORECASE,
)
_AUTHORIZATION_VALUE_PATTERN = re.compile(
    r"\b(?P<label>authorization)(?P<separator>\s*[:=]\s*)"
    r"(?!Bearer\b)(?P<value>[^\s,;|]+)",
    flags=re.IGNORECASE,
)


class SensitiveDataRedactor:
    def __init__(self, settings: Settings) -> None:
        values = {
            settings.secret_key,
            settings.openai_api_key,
            settings.study_plan_map_api_key,
            *(settings.model_endpoint(purpose).api_key for purpose in MODEL_PURPOSES),
        }
        self._configured_values = tuple(
            sorted(
                (value for value in values if value),
                key=len,
                reverse=True,
            )
        )

    def redact(self, text: str) -> str:
        redacted = _BEARER_TOKEN_PATTERN.sub(f"Bearer {REDACTED_VALUE}", text)
        redacted = _LABELED_SECRET_PATTERN.sub(
            lambda match: (
                f"{match.group('label')}{match.group('separator')}{REDACTED_VALUE}"
            ),
            redacted,
        )
        redacted = _AUTHORIZATION_VALUE_PATTERN.sub(
            lambda match: (
                f"{match.group('label')}{match.group('separator')}{REDACTED_VALUE}"
            ),
            redacted,
        )
        for value in self._configured_values:
            redacted = redacted.replace(value, REDACTED_VALUE)
        return redacted
