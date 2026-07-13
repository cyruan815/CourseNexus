from app.modules.generation.generators.mindmap.generator import MindmapGenerator
from app.modules.generation.generators.mindmap.schemas import MindmapGenerationResult
from app.modules.material_context.schemas import MaterialGenerationContext
from tests.modules.generation.conftest import RecordingStructuredModelProvider


class FakePreprocessor:
    def transform(self, markdown: str) -> dict[str, object]:
        return {
            "root": {"content": "Root", "children": []},
            "features": {},
            "assets": {"styles": [], "scripts": []},
        }


def test_mindmap_validates_complete_graph_and_persists_markmap_data() -> None:
    provider = RecordingStructuredModelProvider({
        "root_node_id": "root",
        "nodes": [
            {"id": "root", "label": "Root", "summary": "Root summary", "level": 1},
            {"id": "child", "label": "Child", "summary": "Child summary", "level": 2},
        ],
        "edges": [{"from": "root", "to": "child", "relation": "child"}],
    })
    context = MaterialGenerationContext(chunks=[], material_ids=["m1"], text="COMPLETE", estimated_tokens=4)
    output = MindmapGenerator(model_provider=provider, markmap_preprocessor=FakePreprocessor()).generate(
        context=context, parameters={"max_nodes": 10, "max_depth": 4}
    )
    assert len(provider.calls) == 1
    assert provider.calls[0][1] is MindmapGenerationResult
    assert output.content_json["nodes"][0]["id"] == "node_001"
    assert output.content_json["markmap_data"]["root"]["content"] == "Root"
    assert "source_citation_ids" not in output.content_json["nodes"][0]
    assert "generic meta nodes" in provider.calls[0][0]
    assert "concise labels" in provider.calls[0][0]


def test_mindmap_uses_the_actual_root_for_title_when_model_order_differs() -> None:
    provider = RecordingStructuredModelProvider({
        "root_node_id": "root",
        "nodes": [
            {"id": "child", "label": "Child", "summary": "Child summary", "level": 2},
            {"id": "root", "label": "Root", "summary": "Root summary", "level": 1},
        ],
        "edges": [{"from": "root", "to": "child", "relation": "child"}],
    })
    context = MaterialGenerationContext(chunks=[], material_ids=["m1"], text="COMPLETE", estimated_tokens=4)

    output = MindmapGenerator(model_provider=provider, markmap_preprocessor=FakePreprocessor()).generate(
        context=context, parameters={"max_nodes": 10, "max_depth": 4}
    )

    assert output.title == "Knowledge Mindmap: Root"
    assert output.content_json["root_node_id"] == "node_002"


def test_mindmap_derives_levels_from_child_edges_instead_of_model_levels() -> None:
    provider = RecordingStructuredModelProvider({
        "root_node_id": "root",
        "nodes": [
            {"id": "root", "label": "Root", "summary": "", "level": 1},
            {"id": "child", "label": "Child", "summary": "", "level": 4},
            {"id": "grandchild", "label": "Grandchild", "summary": "", "level": 2},
        ],
        "edges": [
            {"from": "root", "to": "child", "relation": "child"},
            {"from": "child", "to": "grandchild", "relation": "child"},
        ],
    })
    context = MaterialGenerationContext(chunks=[], material_ids=["m1"], text="COMPLETE", estimated_tokens=4)

    output = MindmapGenerator(model_provider=provider, markmap_preprocessor=FakePreprocessor()).generate(
        context=context, parameters={"max_nodes": 10, "max_depth": 3}
    )

    assert [node["level"] for node in output.content_json["nodes"]] == [1, 2, 3]
