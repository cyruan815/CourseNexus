from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.mindmap.markdown import serialize_markmap_markdown
from app.modules.generation.generators.mindmap.prompts import build_mindmap_map_prompt
from app.modules.generation.generators.mindmap.schemas import (
    ConceptCandidate,
    MindmapContent,
    MindmapEdge,
    MindmapMapResult,
    MindmapNode,
    MindmapParameters,
)
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.coverage import run_material_coverage
from app.modules.material_context.schemas import MaterialContextBatch


def _normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


@dataclass
class _Concept:
    label: str
    summary: str
    chunk_ids: list[str] = field(default_factory=list)
    material_ids: set[str] = field(default_factory=set)
    parent_labels: list[str] = field(default_factory=list)


class MindmapGenerator:
    content_type = "mindmap"

    def __init__(self, *, model_provider: ModelProvider) -> None:
        self.model_provider = model_provider

    def generate(
        self,
        *,
        batches: tuple[MaterialContextBatch, ...],
        expected_material_ids: frozenset[str],
        parameters: dict[str, Any],
    ) -> GeneratorOutput:
        try:
            params = MindmapParameters.model_validate(parameters)
        except ValidationError as exc:
            raise CourseNexusError(code="VALIDATION_ERROR", message="Invalid mindmap parameters", status_code=422) from exc

        result = run_material_coverage(
            batches=batches,
            expected_material_ids=set(expected_material_ids),
            map_batch=lambda batch: self.model_provider.generate_structured(
                prompt=build_mindmap_map_prompt(batch, center_topic=params.center_topic),
                output_schema=MindmapMapResult,
            ),
            reduce_results=lambda mapped: self._reduce(mapped, batches=batches, params=params),
        ).value
        return result

    def _reduce(
        self,
        mapped: list[MindmapMapResult],
        *,
        batches: tuple[MaterialContextBatch, ...],
        params: MindmapParameters,
    ) -> GeneratorOutput:
        allowed_chunk_ids = {chunk.chunk_id for batch in batches for chunk in batch.chunks}
        material_by_chunk = {chunk.chunk_id: chunk.material_id for batch in batches for chunk in batch.chunks}
        concepts: dict[str, _Concept] = {}
        key_to_label: dict[str, str] = {}
        relations: list[tuple[str, str, str]] = []
        for map_result in mapped:
            local: dict[str, str] = {}
            for candidate in map_result.concepts:
                label_key = _normalized(candidate.label)
                local[candidate.local_key] = label_key
                key_to_label[candidate.local_key] = label_key
                concept = concepts.setdefault(label_key, _Concept(candidate.label.strip(), candidate.summary.strip()))
                if not concept.summary and candidate.summary.strip():
                    concept.summary = candidate.summary.strip()
                for chunk_id in candidate.source_chunk_ids:
                    if chunk_id in allowed_chunk_ids and chunk_id not in concept.chunk_ids:
                        concept.chunk_ids.append(chunk_id)
                        concept.material_ids.add(material_by_chunk[chunk_id])
                if candidate.parent_local_key:
                    concept.parent_labels.append(candidate.parent_local_key)
            for relation in map_result.relations:
                relations.append((relation.from_local_key, relation.to_local_key, relation.relation))

        if not concepts:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Mindmap contains no concepts")
        root_key = self._select_root(concepts, params.center_topic)
        parent_by_child: dict[str, str] = {}
        for child_key, concept in concepts.items():
            if child_key == root_key:
                continue
            for parent_local_key in concept.parent_labels:
                parent_key = key_to_label.get(parent_local_key)
                if parent_key in concepts and parent_key != child_key:
                    parent_by_child[child_key] = parent_key
                    break
            parent_by_child.setdefault(child_key, root_key)

        children: dict[str, list[str]] = defaultdict(list)
        for child, parent in parent_by_child.items():
            children[parent].append(child)
        ordered_keys: list[str] = []
        levels = {root_key: 1}
        queue = deque([root_key])
        while queue and len(ordered_keys) < params.max_nodes:
            current = queue.popleft()
            ordered_keys.append(current)
            if levels[current] >= params.max_depth:
                continue
            for child in children[current]:
                if child not in levels:
                    levels[child] = levels[current] + 1
                    queue.append(child)
        if len(ordered_keys) < min(3, len(concepts)):
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Mindmap has too few connected concepts")

        id_by_key = {key: f"node_{index:03d}" for index, key in enumerate(ordered_keys, start=1)}
        nodes = [
            MindmapNode(
                id=id_by_key[key], label=concepts[key].label, summary=concepts[key].summary,
                level=levels[key], source_citation_ids=[]
            )
            for key in ordered_keys
        ]
        edges = [
            MindmapEdge.model_validate({"from": id_by_key[parent], "to": id_by_key[child], "relation": "child"})
            for child, parent in parent_by_child.items()
            if child in id_by_key and parent in id_by_key
        ]
        if params.include_cross_links:
            seen = {(edge.from_, edge.to, edge.relation) for edge in edges}
            for source_local, target_local, relation in relations:
                if relation != "related":
                    continue
                source = key_to_label.get(source_local)
                target = key_to_label.get(target_local)
                if source in id_by_key and target in id_by_key and source != target:
                    key = (id_by_key[source], id_by_key[target], "related")
                    if key not in seen:
                        edges.append(MindmapEdge.model_validate({"from": key[0], "to": key[1], "relation": key[2]}))
                        seen.add(key)
        markdown = serialize_markmap_markdown(root_node_id=id_by_key[root_key], nodes=nodes, edges=edges)
        try:
            content = MindmapContent(
                root_node_id=id_by_key[root_key], nodes=nodes, edges=edges, markmap_markdown=markdown
            )
        except ValidationError as exc:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Mindmap graph is invalid") from exc
        bindings = {id_by_key[key]: concepts[key].chunk_ids for key in ordered_keys}
        for key in ordered_keys:
            if key != root_key and not bindings[id_by_key[key]]:
                raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Mindmap node citation is missing")
        return GeneratorOutput(
            title=f"知识导图：{concepts[root_key].label}", content=None,
            content_json=content.model_dump(mode="json", by_alias=True),
            item_citation_chunk_ids=bindings,
        )

    @staticmethod
    def _select_root(concepts: dict[str, _Concept], center_topic: str | None) -> str:
        if center_topic:
            wanted = _normalized(center_topic)
            if wanted in concepts:
                return wanted
        return max(concepts, key=lambda key: (len(concepts[key].material_ids), -list(concepts).index(key)))


def build_generator(model_provider: ModelProvider) -> MindmapGenerator:
    return MindmapGenerator(model_provider=model_provider)
