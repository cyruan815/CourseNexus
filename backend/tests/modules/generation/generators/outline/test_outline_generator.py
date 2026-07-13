from app.modules.generation.generators.outline.generator import OutlineGenerator
from app.modules.generation.generators.outline.schemas import OutlineGenerationResult
from app.modules.material_context.schemas import MaterialGenerationContext
from tests.modules.generation.conftest import RecordingStructuredModelProvider


def test_outline_preserves_model_order_and_assigns_ids() -> None:
    provider = RecordingStructuredModelProvider({"sections": [
        {"title": "First", "summary": "Summary 1", "review_suggestion": "Review 1"},
        {"title": "Second", "summary": "Summary 2", "review_suggestion": "Review 2"},
    ]})
    context = MaterialGenerationContext(chunks=[], material_ids=["m1"], text="COMPLETE", estimated_tokens=4)
    output = OutlineGenerator(model_provider=provider).generate(context=context, parameters={"section_count": 2})
    assert len(provider.calls) == 1
    assert provider.calls[0][1] is OutlineGenerationResult
    assert [item["title"] for item in output.content_json["sections"]] == ["1. First", "2. Second"]
    assert "source_citation_ids" not in output.content_json["sections"][0]
