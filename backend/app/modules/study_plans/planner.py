from __future__ import annotations

from math import ceil
import re

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.material_context.schemas import MaterialContextBatch
from app.modules.study_plans.schemas import (
    PlanBatchExtraction,
    StudyPlanBuildRequest,
    StudyPlanCoverage,
    StudyPlanPreview,
    StudyPlanReduction,
)
from app.modules.study_plans.task_tree_rules import is_assessment_subtask, validate_daily_assessment_contract


_WEAK_AREA_STRATEGY_RULES = {
    "concept": "加强概念解释：先用通俗语言说清概念含义、边界、因果关系和易混点，再安排检查产出。",
    "calculation": "加强公式、步骤推导、计算练习：任务要写明公式含义、适用条件、推导或代入步骤，并安排计算练习。",
    "application": "加强例题和应用任务：用典型例题或真实应用场景引入，再要求学生迁移到新题或新场景。",
    "memorization": "加强重点记忆、回顾、检查：标出必记结论、易错点和复述或默写检查任务。",
    "other": "根据 diagnostic_note 和 weak_topics 调整讲解顺序和任务颗粒度。",
}

_EXPLANATION_STYLE_RULES = {
    "plain_language": "plain_language：任务描述风格要用通俗短句解释术语，避免只给结论。",
    "step_by_step": "step_by_step：任务描述风格要按含义 -> 条件 -> 步骤 -> 练习检查的顺序写。",
    "example_first": "example_first：任务描述风格要先给例题或场景，再抽象概念和规则。",
    "exam_focused": "exam_focused：任务描述风格要突出重点记忆、易错回顾和可检查产出。",
}

_PREFERENCE_PLANNER_STRATEGIES = {
    "fast_track": {
        "content_depth": "concise",
        "example_intensity": "low",
        "assessment_intensity": "low",
        "review_intensity": "low",
    },
    "balanced": {
        "content_depth": "standard",
        "example_intensity": "standard",
        "assessment_intensity": "standard",
        "review_intensity": "standard",
    },
    "mastery": {
        "content_depth": "detailed",
        "example_intensity": "high",
        "assessment_intensity": "high",
        "review_intensity": "high",
    },
    "sprint": {
        "content_depth": "focused",
        "example_intensity": "standard",
        "assessment_intensity": "high",
        "review_intensity": "high",
    },
}


def derive_planner_strategy(
    preference: object,
    diagnostic_profile: dict[str, object] | None = None,
    preference_overrides: object | None = None,
) -> dict[str, object]:
    normalized_preference = _normalize_strategy_preference(preference)
    base_strategy = dict(_PREFERENCE_PLANNER_STRATEGIES[normalized_preference])
    base_strategy.update(_planner_preference_overrides(preference_overrides))
    profile = diagnostic_profile if isinstance(diagnostic_profile, dict) else {}
    return {
        "preference": normalized_preference,
        "content_depth": base_strategy["content_depth"],
        "example_intensity": base_strategy["example_intensity"],
        "assessment_intensity": base_strategy["assessment_intensity"],
        "review_intensity": base_strategy["review_intensity"],
        "foundation_required": _diagnostic_bool(profile.get("foundation_needed")),
        "weak_topics": _diagnostic_string_list(profile.get("weak_topics")),
        "weak_area": _diagnostic_string(profile.get("weak_area"), default="other"),
        "explanation_style": _diagnostic_string(profile.get("explanation_style"), default="plain_language"),
    }



def _planner_preference_overrides(preference_overrides: object | None) -> dict[str, object]:
    if preference_overrides is None:
        return {}
    if isinstance(preference_overrides, dict):
        raw = preference_overrides
    elif hasattr(preference_overrides, "model_dump"):
        raw = preference_overrides.model_dump(mode="json")
    else:
        raw = {
            key: getattr(preference_overrides, key, None)
            for key in ("content_depth", "example_intensity", "assessment_intensity", "review_intensity")
        }
    return {
        key: raw[key]
        for key in ("content_depth", "example_intensity", "assessment_intensity", "review_intensity")
        if isinstance(raw, dict) and raw.get(key) is not None
    }
def _normalize_strategy_preference(preference: object) -> str:
    if preference is None:
        return "balanced"
    value = str(preference).strip()
    if value == "advanced":
        value = "sprint"
    return value if value in _PREFERENCE_PLANNER_STRATEGIES else "balanced"


def _planner_strategy_prompt_lines(strategy: dict[str, object]) -> list[str]:
    preference = str(strategy.get("preference") or "balanced")
    foundation_required = bool(strategy.get("foundation_required"))
    weak_topics = strategy.get("weak_topics") if isinstance(strategy.get("weak_topics"), list) else []
    weak_topics_value = ", ".join(str(topic) for topic in weak_topics) if weak_topics else "none"
    lines = [
        "planner_strategy:",
        f"preference: {preference}",
        f"content_depth: {strategy['content_depth']}",
        f"example_intensity: {strategy['example_intensity']}",
        f"assessment_intensity: {strategy['assessment_intensity']}",
        f"review_intensity: {strategy['review_intensity']}",
        f"foundation_required: {_format_prompt_bool(foundation_required)}",
        f"strategy_weak_topics: {weak_topics_value}",
        f"strategy_weak_area: {strategy['weak_area']}",
        f"strategy_explanation_style: {strategy['explanation_style']}",
        "合并优先级：",
        "1. 用户时间约束：必须尊重 daily_available_minutes；容量不足时先压缩额外例题、测试和 review，并通过 capacity warning 暴露，不静默加重计划。",
        "2. 诊断得出的必要补基础：foundation_required=true 时必须保留补基础任务，优先排在第一天或最早可行日期，即使 preference=fast_track。",
        "3. 学习方式 preference 派生配置：planner 必须显式使用 content_depth、example_intensity、assessment_intensity、review_intensity 控制任务描述、例题、自测和复习强度。",
        "4. 额外例题、测试、review：只在前三级约束满足且时间允许时，根据对应 intensity 增补。",
    ]
    lines.append("上述最终有效策略已经包含用户局部覆盖；不得再次使用学习方式的默认值覆盖 content_depth、example_intensity、assessment_intensity 或 review_intensity。")
    if preference == "fast_track":
        lines.append(
            "fast_track 以最终有效策略控制计划轻重；除必要补基础外，优先压缩拓展讲解和重复练习，"
            f"但必须保留当前 content_depth={strategy['content_depth']}。"
        )
    elif preference == "mastery":
        lines.append(
            "mastery 以最终有效策略安排讲义、例题、review 和阶段测评；"
            f"当前 content_depth={strategy['content_depth']}，example_intensity={strategy['example_intensity']}。"
        )
    elif preference == "sprint":
        lines.append(
            "sprint 以最终有效策略偏向回顾和测试，压缩铺垫但保留必要补基础；"
            f"当前 assessment_intensity={strategy['assessment_intensity']}，review_intensity={strategy['review_intensity']}。"
        )
    else:
        lines.append("balanced 使用最终有效策略保持日常学习节奏。")
    return lines


def _diagnostic_profile_prompt_lines(diagnostic_profile: dict[str, object]) -> list[str]:
    if not diagnostic_profile:
        return [
            "diagnostic_profile: none",
            "诊断生成策略：未提供学前诊断时，按 goal_text、preference、资料难度和每日时间生成。",
        ]

    foundation_needed = _diagnostic_bool(diagnostic_profile.get("foundation_needed"))
    weak_topics = _diagnostic_string_list(diagnostic_profile.get("weak_topics"))
    weak_area = _diagnostic_string(diagnostic_profile.get("weak_area"), default="other")
    explanation_style = _diagnostic_string(diagnostic_profile.get("explanation_style"), default="plain_language")
    prior_knowledge_level = _diagnostic_string(diagnostic_profile.get("prior_knowledge_level"), default="unknown")
    question_version = _diagnostic_string(diagnostic_profile.get("question_version"), default="unknown")
    diagnostic_note = _diagnostic_string(diagnostic_profile.get("diagnostic_note"), default="")
    weak_topics_value = ", ".join(weak_topics) if weak_topics else "none"

    lines = [
        "diagnostic_profile:",
        f"question_version: {question_version}",
        f"prior_knowledge_level: {prior_knowledge_level}",
        f"foundation_needed: {_format_prompt_bool(foundation_needed)}",
        f"weak_topics: {weak_topics_value}",
        f"weak_area: {weak_area}",
        f"explanation_style: {explanation_style}",
        "诊断生成策略：diagnostic_profile 是 planner 约束，不是仅用于 preview/save 追溯。",
    ]
    if diagnostic_note:
        lines.append(f"diagnostic_note: {diagnostic_note}")
    if foundation_needed:
        lines.append("foundation_needed=true 时：计划必须前置安排补基础任务，优先放在第一天或最早可行日期；因现有 schema 的 subtask_type 不新增 foundation，请用 learn/review 类型并在标题或 description 中写明“补基础”。")
    else:
        lines.append("foundation_needed=false 时：不强制补基础，但仍要根据 weak_topics 调整顺序和粒度。")
    lines.extend(
        [
            "weak_topics 策略：weak_topics 对应主题必须更靠前、更细，能在任务标题、description 或排序中体现；不要只合并进泛泛章节。",
            f"weak_area 策略：{_WEAK_AREA_STRATEGY_RULES.get(weak_area, _WEAK_AREA_STRATEGY_RULES['other'])}",
            f"explanation_style 策略：{_EXPLANATION_STYLE_RULES.get(explanation_style, _EXPLANATION_STYLE_RULES['plain_language'])}",
        ]
    )
    return lines


def _diagnostic_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def _format_prompt_bool(value: bool) -> str:
    return "true" if value else "false"


def _diagnostic_string(value: object, *, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _diagnostic_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item).strip())]


def map_material_batch(
    *,
    batch: MaterialContextBatch,
    payload: StudyPlanBuildRequest,
    model_provider: ModelProvider,
) -> PlanBatchExtraction:
    return model_provider.generate_structured(
        prompt=_build_map_prompt(batch=batch, payload=payload),
        output_schema=PlanBatchExtraction,
    )


def reduce_plan_batches(
    *,
    mapped_batches: list[PlanBatchExtraction],
    payload: StudyPlanBuildRequest,
    expected_material_ids: set[str],
    model_provider: ModelProvider,
    course_name: str | None = None,
    retry_feedback: str | None = None,
) -> StudyPlanReduction:
    return model_provider.generate_structured(
        prompt=_build_reduce_prompt(
            mapped_batches=mapped_batches,
            payload=payload,
            expected_material_ids=expected_material_ids,
            course_name=course_name,
            retry_feedback=retry_feedback,
        ),
        output_schema=StudyPlanReduction,
    )


def make_coverage(*, expected_material_ids: set[str], processed_material_ids: set[str], batch_count: int) -> StudyPlanCoverage:
    return StudyPlanCoverage(
        expected_material_ids=sorted(expected_material_ids),
        processed_material_ids=sorted(processed_material_ids),
        batch_count=batch_count,
    )


def repair_daily_assessment_coverage(tasks: list[StudyTaskPreview]) -> list[StudyTaskPreview]:
    if not tasks:
        return tasks

    final_task_date = max(task.task_date for task in tasks)
    full_plan_material_ids: list[str] = []
    full_plan_chunk_ids: list[str] = []
    for task in tasks:
        for subtask in task.subtasks:
            if is_assessment_subtask(subtask):
                continue
            full_plan_material_ids = _ordered_unique([*full_plan_material_ids, *subtask.related_material_ids])
            full_plan_chunk_ids = _ordered_unique([*full_plan_chunk_ids, *subtask.citation_chunk_ids])

    repaired_tasks: list[StudyTaskPreview] = []
    for task in tasks:
        assessments = [subtask for subtask in task.subtasks if is_assessment_subtask(subtask)]
        if len(assessments) != 1 or not task.subtasks or task.subtasks[-1] is not assessments[0]:
            repaired_tasks.append(task)
            continue

        assessment = assessments[0]
        if task.task_date == final_task_date:
            required_material_ids = full_plan_material_ids
            required_chunk_ids = full_plan_chunk_ids
        else:
            required_material_ids = []
            required_chunk_ids = []
            for subtask in task.subtasks:
                if subtask is assessment:
                    break
                if is_assessment_subtask(subtask):
                    continue
                required_material_ids = _ordered_unique([*required_material_ids, *subtask.related_material_ids])
                required_chunk_ids = _ordered_unique([*required_chunk_ids, *subtask.citation_chunk_ids])

        repaired_assessment = assessment.model_copy(
            update={
                "related_material_ids": _ordered_unique([*assessment.related_material_ids, *required_material_ids]),
                "citation_chunk_ids": _ordered_unique([*assessment.citation_chunk_ids, *required_chunk_ids]),
            }
        )
        repaired_subtasks = [
            repaired_assessment if subtask is assessment else subtask
            for subtask in task.subtasks
        ]
        repaired_tasks.append(task.model_copy(update={"subtasks": repaired_subtasks}))

    return repaired_tasks


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result

def validate_preview(*, preview: StudyPlanPreview, scoped_material_ids: set[str]) -> None:
    allowed_types = {"learn", "review", "quiz", "test"}
    completion_quality_required = _requires_completion_quality(preview.goal_text)
    for task in preview.tasks:
        if task.task_date < preview.start_date or task.task_date > preview.end_date:
            raise _invalid_generation("计划任务日期超出请求范围")
        if not task.subtasks:
            raise _invalid_generation("每天至少需要一个二级任务")

        daily_minutes = sum(subtask.estimated_minutes for subtask in task.subtasks)
        if daily_minutes > preview.daily_available_minutes and not _has_over_capacity_warning(preview):
            raise _invalid_generation("每日任务时长超过用户可用时间")
        if completion_quality_required and daily_minutes < _minimum_required_minutes(preview.daily_available_minutes):
            raise _invalid_generation("每日任务时长利用不足")

        for subtask in task.subtasks:
            if subtask.subtask_type not in allowed_types:
                raise _invalid_generation("二级任务类型无效")
            if not is_assessment_subtask(subtask):
                if "task_test" in subtask.generation_parameters:
                    raise _invalid_generation("学习或复习任务不能携带测试题生成参数")
                if _has_assessment_quantity_text(subtask.title, subtask.description):
                    raise _invalid_generation("学习或复习任务不能包含测试题量要求")
            if not subtask.citation_chunk_ids:
                raise _invalid_generation("二级任务必须引用资料 chunk")
            related_material_ids = set(subtask.related_material_ids)
            if not related_material_ids:
                raise _invalid_generation("二级任务必须关联资料")
            if not related_material_ids.issubset(scoped_material_ids):
                raise _invalid_generation("二级任务关联了范围外资料")

    validate_daily_assessment_contract(preview.tasks)


def _build_map_prompt(*, batch: MaterialContextBatch, payload: StudyPlanBuildRequest) -> str:
    daily_minutes = payload.daily_available_minutes if payload.daily_available_minutes is not None else "auto"
    chunk_lines = [
        (
            f"chunk_id={chunk.chunk_id} material_id={chunk.material_id} "
            f"page={chunk.page or ''} heading={chunk.heading or ''} text={chunk.content_text}"
        )
        for chunk in batch.chunks
    ]
    return "\n".join(
        [
            "你是 CourseNexus 的学习计划材料分析器。",
            "请把本批资料提炼为可排入学习计划的知识单元。",
            "按 chunk 出现顺序、章节/页码顺序覆盖资料，不要只输出章节级摘要。",
            "把公式、标准、接口示例、典型设备、调制/编码/复用方法和安全隐患拆成可学习的细粒度知识点。",
            "每个有实质内容的 chunk 必须被至少一个知识单元引用，或在相邻知识单元 summary 中说明已合并。",
            "遇到 <!-- formula-not-decoded -->、图片、表格或图示缺失时，在 summary 中写明需人工复核。",
            "每个 PlanMaterialUnit 的 citation_chunk_ids 必须来自输入 chunk_id，不能留空。",
            "网络类资料要特别保留 10BaseT/RJ45、ASK、FSK、PSK、PCM、WDM、STDM、HUB、冲突域等具体术语。",
            f"goal_text: {payload.goal_text}",
            f"date_range: {payload.start_date.isoformat()} to {payload.end_date.isoformat()}",
            f"daily_available_minutes: {daily_minutes}",
            "material_ids: " + " ".join(batch.material_ids),
            "chunks:",
            *chunk_lines,
        ]
    )


def _build_reduce_prompt(
    *,
    mapped_batches: list[PlanBatchExtraction],
    payload: StudyPlanBuildRequest,
    expected_material_ids: set[str],
    course_name: str | None = None,
    retry_feedback: str | None = None,
) -> str:
    mapped_json = [batch.model_dump(mode="json") for batch in mapped_batches]
    course_line = f"课程名称：{course_name}" if course_name else "课程名称：未提供，标题必须忠实使用 goal_text 中的课程名"
    planner_strategy = derive_planner_strategy(payload.preference, payload.diagnostic_profile, getattr(payload, "preference_overrides", None))
    strategy_prompt_lines = _planner_strategy_prompt_lines(planner_strategy)
    diagnostic_prompt_lines = _diagnostic_profile_prompt_lines(payload.diagnostic_profile)
    return "\n".join(
        [
            "你是 CourseNexus 的学习计划排程器。",
            "请把所有材料单元归并为日期连续、可执行的单课程学习计划预览。",
            course_line,
            "标题必须使用课程名称的原文，不要改写、错写或自行造简称。",
            "如果目标包含“学完/掌握/精通/冲刺”等完成型意图，且材料足够，至少使用每日可用时间的 80%。",
            "学习任务时长不足时，用复习、练习、输出任务或自测补足，而不是留下大段空闲。",
            "所有 mapped units 都必须进入某个二级任务；可合并相近单元，但 description 里要说明覆盖内容。",
            "每天任务要具体可执行，包含可检查产出，例如公式默写、要点回顾、对比表、错题回顾或口头复述。",
            "任务类型边界：learn 是学习讲义任务，用于学习新内容；review 是复习讲义任务，只能回顾此前已经安排学习过的内容，不能引入新知识点；quiz/test 是测试题任务。",
            "learn/review 不得填写 generation_parameters.task_test，也不得在 title 或 description 中写“几道选择题、几道计算题”等明确测试题量。",
            "目录页、主要内容页、版权页、感谢页、章节小结页不能作为普通 learn 任务的 citation_chunk_ids；小结页只可作为 review 或 quiz/test 的辅助引用。",
            "如果 learn 任务已引用正文 chunk，必须排除目录、小结、版权、感谢等元信息 chunk，避免第一天讲义提前混入后续主题。",
            "每天一级任务必须且只能有一个 quiz/test。",
            "quiz/test 必须是当天最后一个二级任务。",
            "非最后一天 quiz/test 是当日测试，related_material_ids 和 citation_chunk_ids 必须覆盖当天前面所有 learn/review。",
            "最后一天 quiz/test 是全计划综合测试，related_material_ids 和 citation_chunk_ids 必须覆盖全计划所有 learn/review；最后一天不再额外安排当天测试。",
            "如果 goal_text、diagnostic_note 或任务描述要求具体测试题量，例如 10 道选择题和 3 道计算题，quiz/test subtask 必须在 description 保留题量文字，并填写 generation_parameters.task_test；选择题映射 single_choice，计算题映射 short_answer，question_count 为总题数。",
            "每个 subtask 的 citation_chunk_ids 必须来自 mapped units，不能留空。",
            *(
                [
                    f"上次输出错误：{retry_feedback}",
                    "请修正后重新返回完整计划 JSON；不要只返回补丁。",
                    "如果 learn/review 出现明确测试题量，请把题量文字和 generation_parameters.task_test 移到当天最后一个 quiz/test。",
                ]
                if retry_feedback
                else []
            ),
            f"goal_text: {payload.goal_text}",
            f"date_range: {payload.start_date.isoformat()} to {payload.end_date.isoformat()}",
            f"daily_available_minutes: {payload.daily_available_minutes}",
            *strategy_prompt_lines,
            *diagnostic_prompt_lines,
            "expected_material_ids: " + " ".join(sorted(expected_material_ids)),
            f"mapped_batches: {mapped_json}",
        ]
    )


def _has_over_capacity_warning(preview: StudyPlanPreview) -> bool:
    warnings = preview.capacity.get("warnings")
    return (
        preview.capacity.get("feasibility_status") == "over_capacity"
        and isinstance(warnings, list)
        and "PLAN_OVER_CAPACITY" in warnings
    )



def _has_assessment_quantity_text(title: str, description: str | None) -> bool:
    text = " ".join(part for part in (title, description or "") if part)
    return bool(re.search(r"([一二两三四五六七八九十\d]+)\s*道\s*(单选题|多选题|选择题|判断题|简答题|问答题|计算题|证明题)", text))


def _requires_completion_quality(goal_text: str) -> bool:
    completion_keywords = ("学完", "掌握", "精通", "冲刺", "备考", "完成")
    return any(keyword in goal_text for keyword in completion_keywords)


def _minimum_required_minutes(daily_available_minutes: int) -> int:
    return ceil(daily_available_minutes * 0.6)


def invalid_generation_message(error: CourseNexusError) -> str | None:
    if error.code != "GENERATION_SCHEMA_INVALID":
        return None
    return error.message


def _invalid_generation(message: str) -> CourseNexusError:
    return CourseNexusError(code="GENERATION_SCHEMA_INVALID", message=message, status_code=500)

