from app.modules.generation.generators.flashcard.generator import FlashcardGenerator
from app.modules.generation.generators.flashcard.schemas import FlashcardGenerationResult
from app.modules.material_context.schemas import MaterialGenerationContext
from tests.modules.generation.conftest import RecordingStructuredModelProvider


def test_flashcard_uses_one_final_model_result() -> None:
    provider = RecordingStructuredModelProvider({"cards": [{"front": "Process", "back": "Running program", "tags": ["OS"]}]})
    context = MaterialGenerationContext(chunks=[], material_ids=["m1"], text="COMPLETE", estimated_tokens=4)
    output = FlashcardGenerator(model_provider=provider).generate(context=context, parameters={"card_count": 1})
    assert len(provider.calls) == 1
    assert provider.calls[0][1] is FlashcardGenerationResult
    assert output.content_json["cards"] == [{
        "id": "card_001", "front": "Process", "back": "Running program", "tags": ["OS"],
        "mastery_status": "unknown", "sort_order": 1,
    }]
    assert "one atomic concept" in provider.calls[0][0]
