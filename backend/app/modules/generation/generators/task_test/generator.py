from __future__ import annotations

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.task_test.schemas import TaskTestContent, TaskTestGenerationParameters
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.schemas import MaterialContextResult


class TaskTestGenerator:
    def __init__(self, model_provider: ModelProvider) -> None:
        self.model_provider = model_provider

    def generate(self, *, context: MaterialContextResult, parameters: dict[str, object]) -> GeneratorOutput:
        params = TaskTestGenerationParameters.model_validate(parameters)
        allowed_chunk_ids = {chunk.chunk_id for chunk in context.chunks}
        prompt = _build_prompt(context=context, params=params)
        content = self.model_provider.generate_structured(prompt=prompt, output_schema=TaskTestContent)
        citation_chunk_ids = _collect_citation_chunk_ids(content)
        if not citation_chunk_ids or not set(citation_chunk_ids).issubset(allowed_chunk_ids):
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="测试题引用不属于本次材料上下文", status_code=500)
        return GeneratorOutput(
            title="任务测试题",
            content_json=content.model_dump(mode="json"),
            citation_chunk_ids=citation_chunk_ids,
        )


def build_generator(model_provider: ModelProvider) -> TaskTestGenerator:
    return TaskTestGenerator(model_provider=model_provider)


def _build_prompt(*, context: MaterialContextResult, params: TaskTestGenerationParameters) -> str:
    chunks = "\n\n".join(
        f"[chunk_id={chunk.chunk_id}; material={chunk.material_name}; page={chunk.page or chunk.page_index}]\n{chunk.content_text}"
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


def _collect_citation_chunk_ids(content: TaskTestContent) -> list[str]:
    ordered: list[str] = []
    for question in sorted(content.questions, key=lambda item: item.sort_order):
        for chunk_id in question.source_citation_ids:
            if chunk_id not in ordered:
                ordered.append(chunk_id)
    return ordered
