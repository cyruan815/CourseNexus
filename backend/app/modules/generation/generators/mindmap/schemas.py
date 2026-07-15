from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.generation.generators.topic import TopicTitle


class MindmapParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    center_topic: str | None = Field(default=None, min_length=1, max_length=120)
    max_depth: int = Field(default=4, ge=2, le=6)
    max_nodes: int = Field(default=80, ge=3, le=200)
    include_cross_links: bool = True


class MindmapDraftNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=160)
    summary: str = Field(default="", max_length=500)
    level: int = Field(ge=1, le=6)

    @field_validator("id", "label")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        result = value.strip()
        if not result:
            raise ValueError("Mindmap fields cannot be blank")
        return result

    @field_validator("summary")
    @classmethod
    def trim_summary(cls, value: str) -> str:
        return value.strip()


class MindmapDraftEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    from_: str = Field(alias="from", serialization_alias="from", min_length=1)
    to: str = Field(min_length=1)
    relation: Literal["child", "related"]


class MindmapGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    topic_title: TopicTitle
    root_node_id: str = Field(min_length=1)
    nodes: list[MindmapDraftNode] = Field(min_length=1)
    edges: list[MindmapDraftEdge] = Field(default_factory=list)


class MindmapNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^node_\d{3}$")
    label: str = Field(min_length=1, max_length=160)
    summary: str = Field(default="", max_length=500)
    level: int = Field(ge=1, le=6)


class MindmapEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    from_: str = Field(alias="from", serialization_alias="from")
    to: str
    relation: Literal["child", "related"]


class MarkmapAssets(BaseModel):
    model_config = ConfigDict(extra="forbid")
    styles: list[Any] = Field(default_factory=list)
    scripts: list[Any] = Field(default_factory=list)


class MarkmapData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root: dict[str, Any]
    features: dict[str, Any]
    assets: MarkmapAssets


class MindmapContent(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_version: Literal["1.0"] = "1.0"
    renderer: Literal["markmap"] = "markmap"
    root_node_id: str
    nodes: list[MindmapNode] = Field(min_length=1)
    edges: list[MindmapEdge] = Field(default_factory=list)
    markmap_markdown: str = Field(min_length=1)
    markmap_data: MarkmapData

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
        if seen != set(node_by_id):
            raise ValueError("Mindmap nodes must be reachable")
        return self
