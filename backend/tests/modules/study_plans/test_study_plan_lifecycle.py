from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.modules.study_plans.schemas import (
    StudyPlanConfigParseRequest,
    StudyPlanParsedConfig,
    StudyPlanReplaceRequest,
    StudyPlanSaveRequest,
    StudySubTaskPreview,
)


def _subtask(**overrides: object) -> StudySubTaskPreview:
    data = {
        "title": "理解滑动窗口",
        "subtask_type": "learn",
        "description": "学习窗口推进、确认与重传关系",
        "related_material_ids": ["mat_1"],
        "estimated_minutes": 30,
        "citation_chunk_ids": ["chk_1"],
        "sort_order": 1,
    }
    data.update(overrides)
    return StudySubTaskPreview.model_validate(data)


def test_config_parse_schema_returns_unresolved_fields() -> None:
    request = StudyPlanConfigParseRequest.model_validate(
        {
            "goal_text": "从 2026-07-11 到 2026-07-24，每天 60 分钟精通传输层",
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        }
    )
    parsed = StudyPlanParsedConfig.model_validate(
        {
            "goal_text": "精通传输层",
            "start_date": None,
            "end_date": None,
            "daily_available_minutes": 60,
            "preference": "mastery",
            "material_scope": request.material_scope.model_dump(mode="json"),
            "unresolved_fields": ["start_date", "end_date"],
        }
    )

    assert parsed.unresolved_fields == ["start_date", "end_date"]
    assert parsed.material_scope.include_all_parsed_materials is True


def test_subtask_preview_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        _subtask(subtask_type="watch")


def test_subtask_preview_requires_positive_minutes() -> None:
    with pytest.raises(ValidationError):
        _subtask(estimated_minutes=0)


def test_save_request_accepts_old_body_without_tasks() -> None:
    request = StudyPlanSaveRequest.model_validate(
        {
            "goal_text": "两周掌握传输层",
            "start_date": "2026-07-11",
            "end_date": "2026-07-24",
            "daily_available_minutes": 60,
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        }
    )

    assert request.tasks is None
    assert request.preference == "balanced"


def test_replace_request_requires_tasks() -> None:
    with pytest.raises(ValidationError):
        StudyPlanReplaceRequest.model_validate(
            {
                "expected_updated_at": datetime.now(timezone.utc).isoformat(),
                "title": "传输层冲刺计划",
                "goal_text": "掌握传输层",
                "start_date": "2026-07-11",
                "end_date": "2026-07-20",
                "daily_available_minutes": 60,
                "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
                "tasks": [],
            }
        )
