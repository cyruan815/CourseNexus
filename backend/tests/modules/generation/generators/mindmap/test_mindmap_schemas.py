from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.generation.generators.mindmap.schemas import MindmapContent, MindmapParameters


def test_parameters_use_defaults_and_forbid_unknown_fields() -> None:
    params = MindmapParameters.model_validate({})
    assert (params.max_depth, params.max_nodes, params.include_cross_links) == (4, 80, True)
    with pytest.raises(ValidationError):
        MindmapParameters.model_validate({"unknown": True})


@pytest.mark.parametrize("payload", [{"max_depth": 1}, {"max_depth": 7}, {"max_nodes": 2}, {"max_nodes": 201}])
def test_parameters_reject_out_of_range_values(payload: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        MindmapParameters.model_validate(payload)


def _content(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "root_node_id": "node_001",
        "nodes": [
            {"id": "node_001", "label": "Root", "summary": "", "level": 1},
            {"id": "node_002", "label": "Child", "summary": "", "level": 2},
        ],
        "edges": [{"from": "node_001", "to": "node_002", "relation": "child"}],
        "markmap_markdown": "- Root\n  - Child",
        "markmap_data": {
            "root": {"content": "Root", "children": []},
            "features": {},
            "assets": {"styles": [], "scripts": []},
        },
    }
    value.update(updates)
    return value


def test_final_graph_accepts_valid_tree() -> None:
    assert MindmapContent.model_validate(_content()).root_node_id == "node_001"


def test_final_graph_rejects_multiple_parents() -> None:
    nodes = _content()["nodes"] + [
        {"id": "node_003", "label": "Other", "summary": "", "level": 2}
    ]
    edges = [
        {"from": "node_001", "to": "node_002", "relation": "child"},
        {"from": "node_003", "to": "node_002", "relation": "child"},
        {"from": "node_001", "to": "node_003", "relation": "child"},
    ]
    with pytest.raises(ValidationError):
        MindmapContent.model_validate(_content(nodes=nodes, edges=edges))
