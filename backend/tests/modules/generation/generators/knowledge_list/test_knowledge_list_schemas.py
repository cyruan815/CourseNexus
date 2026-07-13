import pytest
from pydantic import ValidationError

from app.modules.generation.generators.knowledge_list.schemas import KnowledgeDraft, KnowledgeListParameters


def test_knowledge_parameters_validate_count() -> None:
    assert KnowledgeListParameters().item_count == 50
    with pytest.raises(ValidationError):
        KnowledgeListParameters(item_count=0)


def test_knowledge_draft_trims_and_rejects_blank_text() -> None:
    item = KnowledgeDraft(name=" Process ", definition=" Running program ", importance="high", related_section=" OS ")
    assert item.name == "Process"
    with pytest.raises(ValidationError):
        KnowledgeDraft(name=" ", definition="D", importance="low", related_section="S")
