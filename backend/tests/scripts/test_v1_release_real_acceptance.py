from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings
from scripts.run_v1_release_acceptance import (
    REQUIRED_MODEL_PURPOSES,
    ValidationLog,
    _missing_model_purposes,
)


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
