from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.core.config import Settings
from scripts.run_v1_release_acceptance import (
    AcceptanceFailure,
    REQUIRED_MODEL_PURPOSES,
    ValidationLog,
    _missing_model_purposes,
    _request_json,
    _validate_parsed_material,
)


class _StubResponse:
    status_code = 200

    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def json(self) -> dict[str, object]:
        return {"data": self._data}


class _StubClient:
    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def request(self, *_args: object, **_kwargs: object) -> _StubResponse:
        return _StubResponse(self._data)


def test_validation_log_only_persists_release_safe_fields(tmp_path: Path) -> None:
    log = ValidationLog(tmp_path)

    log.record(
        "course_qa",
        "failed",
        elapsed_ms=12.5,
        resource_ids={"course_id": "crs_example"},
        error_code="MODEL_REQUEST_FAILED",
    )

    payload = json.loads((tmp_path / "events.jsonl").read_text(encoding="utf-8"))
    assert set(payload) == {
        "timestamp",
        "step",
        "status",
        "elapsed_ms",
        "resource_ids",
        "error_code",
    }
    assert "prompt" not in payload
    assert "content" not in payload
    assert "api_key" not in payload


def test_real_acceptance_requires_every_used_model_purpose() -> None:
    settings = Settings(_env_file=None)

    assert _missing_model_purposes(settings) == list(REQUIRED_MODEL_PURPOSES)

    configured = Settings(
        _env_file=None,
        embedding_api_key="configured",
        course_qa_api_key="configured",
        outline_api_key="configured",
        study_plan_generator_api_key="configured",
    )
    assert _missing_model_purposes(configured) == []


@pytest.mark.parametrize(
    ("data", "expected_code"),
    [
        (
            {"parse_status": "parse_failed", "is_learning_ready": False},
            "MATERIAL_NOT_LEARNING_READY",
        ),
        (
            {"parse_status": "parsed", "is_learning_ready": True},
            "ACTIVE_PARSE_VERSION_MISSING",
        ),
    ],
)
def test_parse_step_records_failed_when_material_is_not_ready(
    tmp_path: Path,
    data: dict[str, Any],
    expected_code: str,
) -> None:
    log = ValidationLog(tmp_path)

    with pytest.raises(AcceptanceFailure, match=expected_code):
        _request_json(
            _StubClient(data),
            log,
            step="parse_txt",
            method="POST",
            path="/api/v1/materials/example/parse-retries",
            validate=_validate_parsed_material,
        )

    assert [(event.status, event.error_code) for event in log.events] == [
        ("failed", expected_code)
    ]
