import pytest
from pydantic import ValidationError

from app.modules.generation.generators.outline.schemas import OutlineDraft, OutlineParameters


def test_outline_parameters_validate_ranges() -> None:
    assert OutlineParameters().section_count == 12
    with pytest.raises(ValidationError):
        OutlineParameters(section_count=0)


def test_outline_rejects_blank_business_text() -> None:
    with pytest.raises(ValidationError):
        OutlineDraft(title=" ", summary="Summary", review_suggestion="Review")
