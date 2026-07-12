from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.generation.generators.outline.schemas import OutlineCandidate, OutlineParameters


def test_parameters_use_defaults() -> None:
    params = OutlineParameters.model_validate({})
    assert (params.organization, params.section_count, params.detail_level) == ("review_path", 12, "standard")


@pytest.mark.parametrize("payload", [{"section_count": 0}, {"section_count": 31}, {"organization": "bad"}, {"detail_level": "bad"}, {"unknown": 1}])
def test_parameters_reject_invalid_values(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        OutlineParameters.model_validate(payload)


def test_candidate_requires_grounded_non_empty_fields() -> None:
    candidate = OutlineCandidate(title="Processes", summary="Core concepts", review_suggestion="Review states", source_order_key="001", source_chunk_ids=["c1"])
    assert candidate.title == "Processes"
    with pytest.raises(ValidationError):
        OutlineCandidate(title="", summary="Core", review_suggestion="Review", source_order_key="001", source_chunk_ids=["c1"])
    with pytest.raises(ValidationError):
        OutlineCandidate(title="Title", summary="Core", review_suggestion="Review", source_order_key="001", source_chunk_ids=[])
