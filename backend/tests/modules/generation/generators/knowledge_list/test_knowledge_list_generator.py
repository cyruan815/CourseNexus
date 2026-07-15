from app.modules.generation.generators.knowledge_list.generator import KnowledgeListGenerator
from app.modules.generation.generators.knowledge_list.schemas import KnowledgeGenerationResult
from app.modules.material_context.schemas import MaterialGenerationContext
from tests.modules.generation.conftest import RecordingStructuredModelProvider


def test_knowledge_list_filters_importance_and_preserves_model_order() -> None:
    provider = RecordingStructuredModelProvider({"topic_title": "第一章 进程管理", "items": [
        {"name": "Low", "definition": "Low item", "importance": "low", "related_section": "A"},
        {"name": "High", "definition": "High item", "importance": "high", "related_section": "B"},
        {"name": "Medium", "definition": "Medium item", "importance": "medium", "related_section": "C"},
    ]})
    context = MaterialGenerationContext(chunks=[], material_ids=["m1"], text="COMPLETE", estimated_tokens=4)
    output = KnowledgeListGenerator(model_provider=provider).generate(
        context=context, parameters={"minimum_importance": "medium", "item_count": 5}
    )
    assert len(provider.calls) == 1
    assert provider.calls[0][1] is KnowledgeGenerationResult
    assert [item["name"] for item in output.content_json["items"]] == ["High", "Medium"]
    assert "source_citation_ids" not in output.content_json["items"][0]
    assert output.title == "第一章 进程管理"
    assert "formula conditions" in provider.calls[0][0]
    assert "ordinary headings" in provider.calls[0][0]
    assert "Simplified Chinese topic_title" in provider.calls[0][0]
