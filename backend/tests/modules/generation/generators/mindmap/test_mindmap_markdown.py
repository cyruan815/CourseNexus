from __future__ import annotations

from app.modules.generation.generators.mindmap.markdown import serialize_markmap_markdown
from app.modules.generation.generators.mindmap.schemas import MindmapEdge, MindmapNode


def test_serializer_uses_nested_lists_and_ignores_related_edges() -> None:
    nodes = [
        MindmapNode(id="node_001", label="Root", level=1),
        MindmapNode(id="node_002", label="Child", level=2),
        MindmapNode(id="node_003", label="Leaf", level=3),
    ]
    edges = [
        MindmapEdge.model_validate({"from": "node_001", "to": "node_002", "relation": "child"}),
        MindmapEdge.model_validate({"from": "node_002", "to": "node_003", "relation": "child"}),
        MindmapEdge.model_validate({"from": "node_003", "to": "node_001", "relation": "related"}),
    ]
    assert serialize_markmap_markdown(root_node_id="node_001", nodes=nodes, edges=edges) == (
        "- Root\n  - Child\n    - Leaf"
    )


def test_serializer_normalizes_whitespace_and_escapes_markdown() -> None:
    nodes = [MindmapNode(id="node_001", label="A   *topic*", level=1)]
    assert serialize_markmap_markdown(root_node_id="node_001", nodes=nodes, edges=[]) == "- A \\*topic\\*"
