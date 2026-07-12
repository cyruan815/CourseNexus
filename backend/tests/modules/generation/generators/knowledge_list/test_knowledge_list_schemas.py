from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.generation.generators.knowledge_list.schemas import (
    KnowledgeCandidate,
    KnowledgeListParameters,
)


def test_parameters_use_defaults() -> None:
    params = KnowledgeListParameters.model_validate({})
    assert (params.item_count, params.extraction_focus, params.minimum_importance) == (
        50,
        "balanced",
        "low",
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"item_count": 0},
        {"item_count": 201},
        {"extraction_focus": "bad"},
        {"minimum_importance": "critical"},
        {"unknown": 1},
    ],
)
def test_parameters_reject_invalid_values(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        KnowledgeListParameters.model_validate(payload)


def test_candidate_requires_grounded_fields() -> None:
    candidate = KnowledgeCandidate(
        name="Process",
        definition="A program in execution.",
        importance="high",
        related_section="Process management",
        source_chunk_ids=["c1"],
    )
    assert candidate.name == "Process"
    with pytest.raises(ValidationError):
        KnowledgeCandidate(
            name="Process",
            definition="Definition",
            importance="high",
            related_section="Section",
            source_chunk_ids=[],
        )
