from __future__ import annotations

import re
from collections import defaultdict

from app.modules.generation.generators.mindmap.schemas import MindmapEdge, MindmapNode


def _escape_label(label: str) -> str:
    normalized = " ".join(label.split())
    return re.sub(r"([\\`*_[\]<>#])", r"\\\1", normalized)


def serialize_markmap_markdown(
    *, root_node_id: str, nodes: list[MindmapNode], edges: list[MindmapEdge]
) -> str:
    node_by_id = {node.id: node for node in nodes}
    if root_node_id not in node_by_id:
        raise ValueError("Mindmap root does not exist")
    order = {node.id: position for position, node in enumerate(nodes)}
    children: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.relation == "child":
            if edge.from_ not in node_by_id or edge.to not in node_by_id:
                raise ValueError("Mindmap child endpoint does not exist")
            children[edge.from_].append(edge.to)
    for child_ids in children.values():
        child_ids.sort(key=order.__getitem__)

    lines: list[str] = []

    def visit(node_id: str, depth: int) -> None:
        lines.append(f"{'  ' * depth}- {_escape_label(node_by_id[node_id].label)}")
        for child_id in children[node_id]:
            visit(child_id, depth + 1)

    visit(root_node_id, 0)
    return "\n".join(lines)
