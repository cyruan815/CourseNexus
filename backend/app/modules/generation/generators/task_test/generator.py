from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.task_test.schemas import TaskTestContent, TaskTestGenerationParameters
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.schemas import MaterialContextBatch, MaterialContextResult


_CHOICE_OPTION_IDS = ("A", "B", "C", "D")
_CHOICE_QUESTION_TYPES = {"single_choice", "multiple_choice"}


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
        _normalize_choice_question_options(content)
        _validate_task_test_content(content=content, params=params)
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
        "请先在内部汇总下方所有 chunk 的候选考点，再只输出最终题目。"
        "题数是最终硬约束，questions 长度必须严格等于题数，不能多也不能少。"
        "question_type 只能来自上面的题型白名单。"
        "题目 id 必须连续使用 q_1、q_2 ... q_N，sort_order 必须连续使用 1..N。"
        "单选和多选题的 options[].id 必须唯一，正确答案必须精确命中 options[].id；"
        "单选和多选题必须恰好 4 个选项，最终选项必须按顺序使用 A、B、C、D；"
        "多选题 correct_answer 必须是无重复字符串数组；判断题 correct_answer 必须是 boolean。"
        "不得输出重复或高度相似的题干。"
        "每道题必须有答案、解析和 source_citation_ids；source_citation_ids 必须使用下方 chunk_id。\n\n"
        f"{chunks}"
    )


def _validate_task_test_content(*, content: TaskTestContent, params: TaskTestGenerationParameters) -> None:
    expected_question_ids = [f"q_{index}" for index in range(1, params.question_count + 1)]
    expected_sort_orders = list(range(1, params.question_count + 1))
    questions = sorted(content.questions, key=lambda item: item.sort_order)

    if len(questions) != params.question_count:
        _raise_schema_invalid(
            "测试题数量不符合请求",
            details={"expected": params.question_count, "actual": len(questions)},
        )

    question_ids = [question.id for question in questions]
    sort_orders = [question.sort_order for question in questions]
    if question_ids != expected_question_ids or sort_orders != expected_sort_orders:
        _raise_schema_invalid(
            "测试题 id 或 sort_order 不连续",
            details={"question_ids": question_ids, "sort_orders": sort_orders},
        )

    allowed_question_types = set(params.question_types)
    invalid_types = sorted(
        {question.question_type for question in questions if question.question_type not in allowed_question_types}
    )
    if invalid_types:
        _raise_schema_invalid("测试题题型不在请求白名单内", details={"invalid_question_types": invalid_types})

    normalized_texts: list[str] = []
    for question in questions:
        _validate_question_contract(question)
        normalized_text = _normalize_question_text(question.question_text)
        if any(_is_duplicate_or_highly_similar(normalized_text, existing) for existing in normalized_texts):
            _raise_schema_invalid("测试题题干重复或高度相似", details={"question_id": question.id})
        normalized_texts.append(normalized_text)


def _normalize_choice_question_options(content: TaskTestContent) -> None:
    for question in sorted(content.questions, key=lambda item: item.sort_order):
        if question.question_type not in _CHOICE_QUESTION_TYPES:
            continue
        if len(question.options) != len(_CHOICE_OPTION_IDS):
            _raise_schema_invalid(
                "选择题必须恰好包含 4 个选项",
                details={"question_id": question.id, "actual": len(question.options)},
            )

        original_to_normalized: dict[str, str] = {}
        for normalized_id, option in zip(_CHOICE_OPTION_IDS, question.options, strict=True):
            original_id = option.id
            if not original_id.strip() or original_id != original_id.strip():
                _raise_schema_invalid("选项 id 必须为无首尾空白的非空字符串", details={"question_id": question.id})
            if original_id in original_to_normalized:
                _raise_schema_invalid("选择题选项 id 必须唯一", details={"question_id": question.id})
            original_to_normalized[original_id] = normalized_id
            option.id = normalized_id

        if question.question_type == "single_choice":
            answer = question.correct_answer
            if not isinstance(answer, str) or answer != answer.strip() or answer not in original_to_normalized:
                _raise_schema_invalid("单选题答案必须精确命中选项 id", details={"question_id": question.id})
            question.correct_answer = original_to_normalized[answer]
        elif question.question_type == "multiple_choice":
            answers = question.correct_answer
            if not isinstance(answers, list):
                _raise_schema_invalid("多选题答案必须是字符串数组", details={"question_id": question.id})
            normalized_answers: list[str] = []
            for answer in answers:
                if not isinstance(answer, str) or answer != answer.strip() or answer not in original_to_normalized:
                    _raise_schema_invalid("多选题答案必须精确命中选项 id", details={"question_id": question.id})
                normalized_answers.append(original_to_normalized[answer])
            if len(normalized_answers) != len(set(normalized_answers)):
                _raise_schema_invalid("多选题答案不得重复", details={"question_id": question.id})
            question.correct_answer = normalized_answers


def _validate_question_contract(question: object) -> None:
    question_type = getattr(question, "question_type")
    options = getattr(question, "options")
    correct_answer = getattr(question, "correct_answer")

    option_ids: list[str] = []
    for option in options:
        option_id = option.id
        if not option_id.strip() or option_id != option_id.strip():
            _raise_schema_invalid("选项 id 必须为无首尾空白的非空字符串", details={"question_id": question.id})
        option_ids.append(option_id)
    if len(option_ids) != len(set(option_ids)):
        _raise_schema_invalid("选择题选项 id 必须唯一", details={"question_id": question.id})

    option_id_set = set(option_ids)
    if question_type == "single_choice":
        if not isinstance(correct_answer, str) or correct_answer != correct_answer.strip() or correct_answer not in option_id_set:
            _raise_schema_invalid("单选题答案必须精确命中选项 id", details={"question_id": question.id})
    elif question_type == "multiple_choice":
        if not isinstance(correct_answer, list):
            _raise_schema_invalid("多选题答案必须是字符串数组", details={"question_id": question.id})
        if any(answer != answer.strip() for answer in correct_answer):
            _raise_schema_invalid("多选题答案不得包含首尾空白", details={"question_id": question.id})
        if len(correct_answer) != len(set(correct_answer)):
            _raise_schema_invalid("多选题答案不得重复", details={"question_id": question.id})
        if not set(correct_answer).issubset(option_id_set):
            _raise_schema_invalid("多选题答案必须精确命中选项 id", details={"question_id": question.id})


def _normalize_question_text(value: str) -> str:
    return "".join(value.lower().split())


def _is_duplicate_or_highly_similar(left: str, right: str) -> bool:
    if left == right:
        return True
    if min(len(left), len(right)) < 8:
        return False
    return SequenceMatcher(None, left, right).ratio() >= 0.95


def _raise_schema_invalid(message: str, *, details: dict[str, object] | None = None) -> None:
    raise CourseNexusError(
        code="GENERATION_SCHEMA_INVALID",
        message=message,
        status_code=500,
        details=details,
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
