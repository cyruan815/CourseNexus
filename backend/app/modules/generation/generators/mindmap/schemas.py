from __future__ import annotations

from collections import defaultdict, deque
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MindmapParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    center_topic: str | None = Field(default=None, min_length=1, max_length=120)
    max_depth: int = Field(default=4, ge=2, le=6)
    max_nodes: int = Field(default=80, ge=3, le=200)
    include_cross_links: bool = True


class ConceptCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=160)
    summary: str = Field(default="", max_length=500)
    parent_local_key: str | None = Field(default=None, max_length=120)
    source_chunk_ids: list[str] = Field(default_factory=list)


class RelationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_local_key: str = Field(min_length=1, max_length=120)
    to_local_key: str = Field(min_length=1, max_length=120)
    relation: Literal["child", "related"]


class MindmapMapResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concepts: list[ConceptCandidate] = Field(default_factory=list)
    relations: list[RelationCandidate] = Field(default_factory=list)


class MindmapNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^node_\d{3}$")
    label: str = Field(min_length=1, max_length=160)
    summary: str = Field(default="", max_length=500)
    level: int = Field(ge=1, le=6)
    source_citation_ids: list[str] = Field(default_factory=list)


class MindmapEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_: str = Field(alias="from", serialization_alias="from")
    to: str
    relation: Literal["child", "related"]


class MindmapContent(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: Literal["1.0"] = "1.0"
    renderer: Literal["markmap"] = "markmap"
    root_node_id: str
    nodes: list[MindmapNode] = Field(min_length=1)
    edges: list[MindmapEdge] = Field(default_factory=list)
    markmap_markdown: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_graph(self) -> "MindmapContent":
        node_by_id = {node.id: node for node in self.nodes}
        if len(node_by_id) != len(self.nodes) or self.root_node_id not in node_by_id:
            raise ValueError("Mindmap node IDs and root must be valid")
        roots = [node for node in self.nodes if node.level == 1]
        if len(roots) != 1 or roots[0].id != self.root_node_id:
            raise ValueError("Mindmap must have exactly one root")

        children: dict[str, list[str]] = defaultdict(list)
        parents: dict[str, str] = {}
        edge_keys: set[tuple[str, str, str]] = set()
        for edge in self.edges:
            if edge.from_ not in node_by_id or edge.to not in node_by_id or edge.from_ == edge.to:
                raise ValueError("Mindmap edge endpoint is invalid")
            key = (edge.from_, edge.to, edge.relation)
            if key in edge_keys:
                raise ValueError("Mindmap edge is duplicated")
            edge_keys.add(key)
            if edge.relation == "child":
                if edge.to in parents:
                    raise ValueError("Mindmap child has multiple parents")
                parents[edge.to] = edge.from_
                children[edge.from_].append(edge.to)

        if set(parents) != set(node_by_id) - {self.root_node_id}:
            raise ValueError("Every non-root node must have one parent")
        seen = {self.root_node_id}
        queue = deque([self.root_node_id])
        while queue:
            parent = queue.popleft()
            for child in children[parent]:
                if child in seen:
                    raise ValueError("Mindmap child graph contains a cycle")
                if node_by_id[child].level != node_by_id[parent].level + 1:
                    raise ValueError("Mindmap levels must be continuous")
                seen.add(child)
                queue.append(child)
            labels = [node_by_id[child].label.casefold() for child in children[parent]]
            if len(labels) != len(set(labels)):
                raise ValueError("Mindmap sibling labels must be unique")
        if seen != set(node_by_id):
            raise ValueError("Mindmap nodes must be reachable")
        return self
