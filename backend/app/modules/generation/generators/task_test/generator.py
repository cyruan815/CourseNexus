from __future__ import annotations

from typing import Any

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.task_test.schemas import TaskTestContent, TaskTestGenerationParameters
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.schemas import MaterialContextBatch, MaterialContextResult


class TaskTestGenerator:
    content_type = "task_test"

    def __init__(self, model_provider: ModelProvider) -> None:
        self.model_provider = model_provider

    def generate(
        self,
        *,
        batches: tuple[MaterialContextBatch, ...],
        expected_material_ids: frozenset[str],
        parameters: dict[str, Any],
    ) -> GeneratorOutput:
        context = _context_from_batches(batches)
        _assert_material_coverage(context=context, expected_material_ids=expected_material_ids)
        params = TaskTestGenerationParameters.model_validate(parameters)
        allowed_chunk_ids = {chunk.chunk_id for chunk in context.chunks}
        prompt = _build_prompt(context=context, params=params)
        content = self.model_provider.generate_structured(prompt=prompt, output_schema=TaskTestContent)
        item_citation_chunk_ids = _collect_item_citation_chunk_ids(content)
        citation_chunk_ids = {chunk_id for chunk_ids in item_citation_chunk_ids.values() for chunk_id in chunk_ids}
        if not citation_chunk_ids or not citation_chunk_ids.issubset(allowed_chunk_ids):
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="测试题引用不属于本次材料上下文", status_code=500)
        return GeneratorOutput(
            title="任务测试题",
            content_json=content.model_dump(mode="json"),
            item_citation_chunk_ids=item_citation_chunk_ids,
        )


def build_generator(model_provider: ModelProvider) -> TaskTestGenerator:
    return TaskTestGenerator(model_provider=model_provider)


def _context_from_batches(batches: tuple[MaterialContextBatch, ...]) -> MaterialContextResult:
    chunks = [chunk for batch in batches for chunk in batch.chunks]
    return MaterialContextResult(chunks=chunks, no_parsed_material=not chunks)


def _assert_material_coverage(*, context: MaterialContextResult, expected_material_ids: frozenset[str]) -> None:
    represented_material_ids = {chunk.material_id for chunk in context.chunks}
    if represented_material_ids != set(expected_material_ids):
        raise CourseNexusError(
            code="MATERIAL_COVERAGE_INCOMPLETE",
            message="材料覆盖不完整",
            status_code=409,
            details={
                "expected_material_ids": sorted(expected_material_ids),
                "processed_material_ids": sorted(represented_material_ids),
            },
        )


def _build_prompt(*, context: MaterialContextResult, params: TaskTestGenerationParameters) -> str:
    chunks = "\n\n".join(
        f"[chunk_id={chunk.chunk_id}; material={chunk.material_name}; page={_page_label(chunk)}]\n{chunk.content_text}"
        for chunk in context.chunks
    )
    return (
        "你是 CourseNexus 的计划学习任务测试题生成器。"
        "只能使用给定资料，不得编造来源。"
        "输出必须符合 TaskTestContent schema。"
        f"题数：{params.question_count}；题型：{', '.join(params.question_types)}；难度：{params.difficulty}。\n\n"
        "每道题必须有答案、解析和 source_citation_ids；source_citation_ids 必须使用下方 chunk_id。\n\n"
        f"{chunks}"
    )


def _collect_item_citation_chunk_ids(content: TaskTestContent) -> dict[str, list[str]]:
    return {
        question.id: list(dict.fromkeys(question.source_citation_ids))
        for question in sorted(content.questions, key=lambda item: item.sort_order)
    }


def _page_label(chunk: object) -> str | int | None:
    page = getattr(chunk, "page", None)
    if page is not None:
        return page
    return getattr(chunk, "page_index", None)
