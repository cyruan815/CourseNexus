from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.errors import CourseNexusError
from app.core.config import get_settings
from app.integrations.markmap.preprocessor import MarkmapLibPreprocessor
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.mindmap.markdown import serialize_markmap_markdown
from app.modules.generation.generators.mindmap.prompts import build_mindmap_prompt
from app.modules.generation.generators.mindmap.schemas import (
    MindmapContent,
    MindmapEdge,
    MindmapGenerationResult,
    MindmapNode,
    MindmapParameters,
)
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.schemas import MaterialGenerationContext


class MarkmapPreprocessor(Protocol):
    def transform(self, markdown: str) -> dict[str, object]: ...


def _derive_child_levels(result: MindmapGenerationResult, *, max_depth: int) -> dict[str, int]:
    node_ids = {node.id for node in result.nodes}
    children: dict[str, list[str]] = defaultdict(list)
    parent_by_child: dict[str, str] = {}
    for edge in result.edges:
        if edge.relation != "child":
            continue
        if edge.from_ not in node_ids or edge.to not in node_ids or edge.from_ == edge.to:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Mindmap child edge is invalid")
        if edge.to in parent_by_child:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Mindmap child has multiple parents")
        parent_by_child[edge.to] = edge.from_
        children[edge.from_].append(edge.to)

    if result.root_node_id in parent_by_child or set(parent_by_child) != node_ids - {result.root_node_id}:
        raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Mindmap child tree is incomplete")

    levels = {result.root_node_id: 1}
    queue = deque([result.root_node_id])
    while queue:
        parent = queue.popleft()
        for child in children[parent]:
            if child in levels:
                raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Mindmap child graph contains a cycle")
            levels[child] = levels[parent] + 1
            if levels[child] > max_depth:
                raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Mindmap exceeds requested limits")
            queue.append(child)
    if set(levels) != node_ids:
        raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Mindmap nodes must be reachable")
    return levels


class MindmapGenerator:
    content_type = "mindmap"

    def __init__(
        self,
        *,
        model_provider: ModelProvider,
        markmap_preprocessor: MarkmapPreprocessor | None = None,
    ) -> None:
        self.model_provider = model_provider
        self.markmap_preprocessor = markmap_preprocessor or MarkmapLibPreprocessor()

    def generate(self, *, context: MaterialGenerationContext, parameters: dict[str, Any]) -> GeneratorOutput:
        try:
            params = MindmapParameters.model_validate(parameters)
        except ValidationError as exc:
            raise CourseNexusError(code="VALIDATION_ERROR", message="Invalid mindmap parameters", status_code=422) from exc
        result = self.model_provider.generate_structured(
            prompt=build_mindmap_prompt(context, parameters=params),
            output_schema=MindmapGenerationResult,
        )
        if len(result.nodes) > params.max_nodes:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Mindmap exceeds requested limits")

        id_map = {node.id: f"node_{index:03d}" for index, node in enumerate(result.nodes, start=1)}
        if len(id_map) != len(result.nodes) or result.root_node_id not in id_map:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Mindmap node IDs are invalid")
        levels = _derive_child_levels(result, max_depth=params.max_depth)
        nodes = [
            MindmapNode(id=id_map[node.id], label=node.label, summary=node.summary, level=levels[node.id])
            for node in result.nodes
        ]
        edges = [
            MindmapEdge.model_validate(
                {"from": id_map.get(edge.from_, edge.from_), "to": id_map.get(edge.to, edge.to), "relation": edge.relation}
            )
            for edge in result.edges
            if params.include_cross_links or edge.relation == "child"
        ]
        root_node_id = id_map[result.root_node_id]
        root_node = next(node for node in nodes if node.id == root_node_id)
        markdown = serialize_markmap_markdown(root_node_id=root_node_id, nodes=nodes, edges=edges)
        markmap_data = self.markmap_preprocessor.transform(markdown)
        try:
            content = MindmapContent(
                root_node_id=root_node_id,
                nodes=nodes,
                edges=edges,
                markmap_markdown=markdown,
                markmap_data=markmap_data,
            )
        except ValidationError as exc:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Mindmap graph is invalid") from exc
        return GeneratorOutput(
            title=f"Knowledge Mindmap: {root_node.label}",
            content_json=content.model_dump(mode="json", by_alias=True),
        )


def build_generator(model_provider: ModelProvider) -> MindmapGenerator:
    settings = get_settings()
    return MindmapGenerator(
        model_provider=model_provider,
        markmap_preprocessor=MarkmapLibPreprocessor(
            node_command=settings.markmap_node_command,
            timeout_seconds=settings.markmap_transform_timeout_seconds,
        ),
    )
