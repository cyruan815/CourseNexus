from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.integrations.rag.base import RagIndex
from app.modules.checkins.service import recalculate_checkin
from app.modules.course_qa.models import SourceCitation
from app.modules.course_qa.schemas import CourseAnswerRead, CourseQuestionCreate
from app.modules.course_qa.service import ask_course_question
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generated_content.schemas import GeneratedContentRead
from app.modules.generated_content.service import build_generated_content_read
from app.modules.generation.generators.handout import build_generator as build_handout_generator
from app.modules.generation.generators.handout.generator import (
    _assert_no_mermaid,
    _handout_has_visual,
    ensure_handout_header,
)
from app.modules.generation.generators.task_test import build_generator as build_task_test_generator
from app.modules.generation.generators.task_test.schemas import TaskTestContent, TaskTestGenerationParameters
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.generation.orchestrator.registry import GeneratorRegistry
from app.modules.learning_execution import repository
from app.modules.learning_execution.schemas import (
    CompletionPlanRead,
    CompletionSubTaskRead,
    CompletionTaskRead,
    ExecutionContextRead,
    ExecutionCourseRead,
    ExecutionMaterialRead,
    ExecutionPlanRead,
    ExecutionSubTaskRead,
    ExecutionTaskRead,
    SubTaskCompletionResult,
)
from app.modules.material_context.coverage import run_material_coverage
from app.modules.material_context.schemas import MaterialContextBatch, MaterialScope, build_material_scope_snapshot
from app.modules.material_context.service import iter_material_context_batches
from app.modules.study_plans.models import StudySubTask


VALID_TASK_STATUSES = {"not_started", "in_progress", "completed"}
HANDOUT_SUBTASK_TYPES = {"learn", "review"}
TASK_TEST_SUBTASK_TYPES = {"quiz", "test"}


def derive_task_status(subtask_statuses: list[str]) -> str:
    if not subtask_statuses or all(status == "not_started" for status in subtask_statuses):
        return "not_started"
    if all(status == "completed" for status in subtask_statuses):
        return "completed"
    return "in_progress"


def derive_plan_status(task_statuses: list[str]) -> str:
    if task_statuses and all(status == "completed" for status in task_statuses):
        return "completed"
    return "active"


def get_execution_context(db: Session, *, user_id: str, subtask_id: str) -> ExecutionContextRead:
    target = repository.get_execution_target(db, user_id=user_id, subtask_id=subtask_id)
    tasks = repository.list_tasks_for_plan_date(db, plan_id=target.plan.id, task_date=target.task.task_date)
    subtasks = repository.list_subtasks_for_tasks(db, task_ids=[task.id for task in tasks])
    subtasks_by_task: dict[str, list[StudySubTask]] = defaultdict(list)
    for subtask in subtasks:
        subtasks_by_task[subtask.task_id].append(subtask)

    return ExecutionContextRead(
        course=ExecutionCourseRead(course_id=target.course.id, name=target.course.name),
        plan=ExecutionPlanRead(plan_id=target.plan.id, title=target.plan.title, status=target.plan.status),
        execution_date=target.task.task_date,
        tasks=[
            ExecutionTaskRead(
                task_id=task.id,
                title=task.title,
                task_date=task.task_date,
                status=_as_task_status(task.status),
                sort_order=task.sort_order,
                subtasks=[_subtask_read(subtask) for subtask in subtasks_by_task[task.id]],
            )
            for task in tasks
        ],
        current_subtask_id=target.subtask.id,
        related_materials=_related_materials(db, user_id=user_id, course_id=target.course.id, subtask=target.subtask),
        handout_content_id=_latest_content_id(db, user_id=user_id, subtask_id=target.subtask.id, content_type="handout"),
        task_test_content_id=_latest_content_id(db, user_id=user_id, subtask_id=target.subtask.id, content_type="task_test"),
    )


def generate_handout_for_subtask(
    db: Session,
    *,
    user_id: str,
    subtask_id: str,
    parameters: dict[str, object],
    force_regenerate: bool,
    model_provider: ModelProvider,
    max_tokens: int,
) -> GeneratedContentRead:
    return _generate_task_content(
        db,
        user_id=user_id,
        subtask_id=subtask_id,
        content_type="handout",
        allowed_subtask_types=HANDOUT_SUBTASK_TYPES,
        parameters=parameters,
        force_regenerate=force_regenerate,
        model_provider=model_provider,
        max_tokens=max_tokens,
    )


def generate_task_test_for_subtask(
    db: Session,
    *,
    user_id: str,
    subtask_id: str,
    parameters: dict[str, object],
    force_regenerate: bool,
    model_provider: ModelProvider,
    max_tokens: int,
) -> GeneratedContentRead:
    return _generate_task_content(
        db,
        user_id=user_id,
        subtask_id=subtask_id,
        content_type="task_test",
        allowed_subtask_types=TASK_TEST_SUBTASK_TYPES,
        parameters=parameters,
        force_regenerate=force_regenerate,
        model_provider=model_provider,
        max_tokens=max_tokens,
    )


def ask_subtask_question(
    db: Session,
    *,
    user_id: str,
    subtask_id: str,
    conversation_id: str | None,
    question: str,
    model_provider: ModelProvider,
    rag_index: RagIndex,
    top_k: int,
) -> CourseAnswerRead:
    target = repository.get_execution_target(db, user_id=user_id, subtask_id=subtask_id)
    material_ids = _material_ids(target.subtask)
    material_scope = MaterialScope(include_all_parsed_materials=False, material_ids=material_ids)
    payload = CourseQuestionCreate(
        conversation_id=conversation_id,
        question=question,
        material_scope=material_scope,
        source_page="task_execution",
    )
    return ask_course_question(
        db,
        user_id=user_id,
        course_id=target.course.id,
        payload=payload,
        model_provider=model_provider,
        rag_index=rag_index,
        top_k=top_k,
        allowed_conversation_source_pages={"task_execution"},
        material_scope_metadata={"subtask_id": target.subtask.id, "task_id": target.task.id},
        model_question_context=_task_qa_context(target),
    )


def _generate_task_content(
    db: Session,
    *,
    user_id: str,
    subtask_id: str,
    content_type: str,
    allowed_subtask_types: set[str],
    parameters: dict[str, object],
    force_regenerate: bool,
    model_provider: ModelProvider,
    max_tokens: int,
) -> GeneratedContentRead:
    target = repository.get_execution_target(db, user_id=user_id, subtask_id=subtask_id)
    if target.subtask.subtask_type not in allowed_subtask_types:
        raise CourseNexusError(
            code="STATE_CONFLICT",
            message="二级任务类型不允许生成该内容",
            status_code=409,
            details={"subtask_type": target.subtask.subtask_type, "content_type": content_type},
        )

    if not force_regenerate:
        existing_content = repository.get_latest_successful_task_content(
            db,
            user_id=user_id,
            subtask_id=target.subtask.id,
            content_type=content_type,
        )
        if existing_content is not None:
            return build_generated_content_read(db, existing_content)

    material_ids = _material_ids(target.subtask)
    material_scope = MaterialScope(include_all_parsed_materials=False, material_ids=material_ids)
    material_scope_json: dict[str, object] = material_scope.model_dump(mode="json")
    content_id = f"gen_{uuid4().hex}"

    try:
        effective_parameters = _merge_task_content_parameters(content_type=content_type, target=target, parameters=parameters)
        if not material_ids:
            raise CourseNexusError(code="NO_PARSED_MATERIAL", message="当前任务没有关联已解析资料", status_code=400)

        registry = _task_content_registry()
        generator = registry.create(content_type, model_provider)
        batches = list(
            iter_material_context_batches(
                db,
                user_id=user_id,
                course_id=target.course.id,
                material_scope=material_scope,
                max_tokens=max_tokens,
            )
        )
        if not batches:
            raise CourseNexusError(code="NO_PARSED_MATERIAL", message="当前任务没有已解析资料上下文", status_code=400)

        if content_type == "handout":
            citation_scope = _stored_subtask_citation_chunk_ids(target)
            if citation_scope:
                batches = _filter_batches_by_citation_scope(batches=batches, citation_chunk_ids=citation_scope)
            effective_parameters = {
                **effective_parameters,
                "handout_title": _generated_task_content_title(content_type=content_type, target=target),
                "source_note": _handout_source_note(batches=batches, subtask_title=target.subtask.title),
            }

        material_scope_json = build_material_scope_snapshot(
            material_scope,
            [chunk for batch in batches for chunk in batch.chunks],
        )

        if content_type == "task_test":
            output = generator.generate(
                batches=tuple(batches),
                expected_material_ids=frozenset(material_ids),
                parameters=effective_parameters,
            )
        else:
            expected_material_ids = {material_id for batch in batches for material_id in batch.material_ids}
            output = run_material_coverage(
                batches=batches,
                expected_material_ids=expected_material_ids,
                map_batch=lambda batch: generator.generate(
                    batches=(batch,),
                    expected_material_ids=frozenset(batch.material_ids),
                    parameters=effective_parameters,
                ),
                reduce_results=lambda outputs: _reduce_task_content_outputs(
                    content_type=content_type,
                    outputs=outputs,
                    model_provider=model_provider,
                    parameters=effective_parameters,
                ),
            ).value
        content = _new_task_generated_content(
            content_id=content_id,
            user_id=user_id,
            course_id=target.course.id,
            subtask_id=target.subtask.id,
            content_type=content_type,
            material_scope_json=material_scope_json,
        )
        content.title = _generated_task_content_title(content_type=content_type, target=target)
        content.content = output.content
        content.content_json = output.content_json
        content.generation_status = "success"
        content.error_code = None
        db.add(content)
        db.flush()
        if output.item_citation_chunk_ids:
            citation_ids_by_item = _save_task_content_citations(
                db,
                generated_content_id=content.id,
                batches=batches,
                item_citation_chunk_ids=output.item_citation_chunk_ids,
            )
            content.content_json = _bind_source_citation_ids(
                output.content_json,
                citation_ids_by_item,
                is_handout_root=False,
            )
        db.add(content)
        db.flush()
        db.commit()
    except CourseNexusError as exc:
        db.rollback()
        _save_failed_task_content(
            db,
            content_id=content_id,
            user_id=user_id,
            course_id=target.course.id,
            subtask_id=target.subtask.id,
            content_type=content_type,
            material_scope_json=material_scope_json,
            error_code=exc.code,
        )
        raise
    except Exception as exc:
        db.rollback()
        _save_failed_task_content(
            db,
            content_id=content_id,
            user_id=user_id,
            course_id=target.course.id,
            subtask_id=target.subtask.id,
            content_type=content_type,
            material_scope_json=material_scope_json,
            error_code="GENERATION_FAILED",
        )
        raise CourseNexusError(code="GENERATION_FAILED", message="任务内容生成失败", status_code=502) from exc

    db.refresh(content)
    return build_generated_content_read(db, content)


def _task_qa_context(target: repository.ExecutionTarget) -> str:
    lines = [
        f"Course: {target.course.name}",
        f"Plan: {target.plan.title}",
        f"Plan goal: {target.plan.goal_text}",
        f"Task: {target.task.title}",
        f"Subtask: {target.subtask.title}",
        f"Subtask type: {target.subtask.subtask_type}",
    ]
    if target.subtask.description:
        lines.append(f"Subtask description: {target.subtask.description}")
    return "\n".join(lines)


def _task_content_registry() -> GeneratorRegistry:
    registry = GeneratorRegistry()
    registry.register("handout", build_handout_generator)
    registry.register("task_test", build_task_test_generator)
    return registry


def _merge_task_content_parameters(
    *,
    content_type: str,
    target: repository.ExecutionTarget,
    parameters: dict[str, object],
) -> dict[str, object]:
    if content_type == "handout":
        return {**dict(parameters), **_handout_task_context_parameters(target)}
    if content_type != "task_test":
        return dict(parameters)
    stored_parameters = _stored_task_generation_parameters(target=target, content_type=content_type)
    merged = _merge_task_test_parameters(
        stored_parameters=stored_parameters,
        request_parameters=dict(parameters),
    )
    try:
        return TaskTestGenerationParameters.model_validate(merged).model_dump(mode="json")
    except ValidationError as exc:
        if parameters:
            raise CourseNexusError(
                code="VALIDATION_ERROR",
                message="任务测试题请求参数无效",
                status_code=422,
                details={"field": "parameters", "errors": exc.errors()},
            ) from exc
        raise CourseNexusError(
            code="GENERATION_SCHEMA_INVALID",
            message="任务测试题生成参数无效",
            status_code=500,
            details={"field": "generation_parameters.task_test", "errors": exc.errors()},
        ) from exc


def _merge_task_test_parameters(
    *,
    stored_parameters: dict[str, object],
    request_parameters: dict[str, object],
) -> dict[str, object]:
    stored = dict(stored_parameters)
    request = dict(request_parameters)
    if _has_request_question_type_counts(request):
        stored.pop("question_type_counts", None)
        stored.pop("question_count", None)
        stored.pop("question_types", None)
    elif "types" in request:
        stored.pop("question_type_counts", None)
        stored.pop("question_types", None)
    elif "question_count" in request or "question_types" in request:
        stored.pop("question_type_counts", None)
    return {**stored, **request}


def _has_request_question_type_counts(parameters: dict[str, object]) -> bool:
    if isinstance(parameters.get("question_type_counts"), list):
        return True
    for key in ("items", "questions", "question_types"):
        raw_items = parameters.get(key)
        if isinstance(raw_items, list) and raw_items and all(isinstance(item, dict) for item in raw_items):
            return True
    if any(key in parameters for key in ("single_choice", "multiple_choice", "true_false", "short_answer")):
        return True
    return any(isinstance(key, str) and "道" in key for key in parameters)

def _handout_task_context_parameters(target: repository.ExecutionTarget) -> dict[str, object]:
    diagnostic_profile = _stored_diagnostic_profile(target)
    planner_strategy = _stored_planner_strategy(target)
    weak_area = _optional_string(diagnostic_profile.get("weak_area"))
    weak_topics = _optional_string_list(diagnostic_profile.get("weak_topics"))
    return {
        "course_name": target.course.name,
        "plan_goal": target.plan.goal_text or "",
        "task_title": target.task.title,
        "subtask_title": target.subtask.title,
        "subtask_type": target.subtask.subtask_type,
        "subtask_description": target.subtask.description or "",
        "estimated_minutes": _stored_subtask_estimated_minutes(target),
        "content_depth": _content_depth_for_handout(planner_strategy),
        "example_intensity": _intensity_for_handout(planner_strategy, "example_intensity"),
        "assessment_intensity": _intensity_for_handout(planner_strategy, "assessment_intensity"),
        "review_intensity": _intensity_for_handout(planner_strategy, "review_intensity"),
        "diagnostic_foundation_needed": diagnostic_profile.get("foundation_needed")
        if isinstance(diagnostic_profile.get("foundation_needed"), bool)
        else None,
        "diagnostic_weak_area": weak_area,
        "diagnostic_weak_topics": weak_topics,
        "diagnostic_note": _optional_string(diagnostic_profile.get("diagnostic_note")),
        "teaching_strategy_hint": _teaching_strategy_hint(weak_area),
    }


def _stored_diagnostic_profile(target: repository.ExecutionTarget) -> dict[str, object]:
    config = target.plan.parsed_config_json
    if not isinstance(config, dict):
        return {}
    profile = config.get("diagnostic_profile")
    if isinstance(profile, dict):
        return profile
    confirmed_config = config.get("confirmed_config")
    if isinstance(confirmed_config, dict):
        confirmed_profile = confirmed_config.get("diagnostic_profile")
        if isinstance(confirmed_profile, dict):
            return confirmed_profile
    return {}


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _optional_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    strings = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return list(dict.fromkeys(strings))


def _stored_planner_strategy(target: repository.ExecutionTarget) -> dict[str, object]:
    config = target.plan.parsed_config_json
    if not isinstance(config, dict):
        return {}
    generation_metadata = config.get("generation_metadata")
    if isinstance(generation_metadata, dict):
        planner_strategy = generation_metadata.get("planner_strategy")
        if isinstance(planner_strategy, dict):
            return planner_strategy
    planner_strategy = config.get("planner_strategy")
    return planner_strategy if isinstance(planner_strategy, dict) else {}


def _stored_subtask_estimated_minutes(target: repository.ExecutionTarget) -> int | None:
    subtask_snapshot = _stored_subtask_snapshot(target)
    value = subtask_snapshot.get("estimated_minutes")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _stored_subtask_snapshot(target: repository.ExecutionTarget) -> dict[str, object]:
    config = target.plan.parsed_config_json
    if not isinstance(config, dict):
        return {}
    task_snapshot = config.get("task_snapshot")
    if not isinstance(task_snapshot, list):
        return {}
    for task in task_snapshot:
        if not isinstance(task, dict) or task.get("sort_order") != target.task.sort_order:
            continue
        subtasks = task.get("subtasks")
        if not isinstance(subtasks, list):
            return {}
        for subtask in subtasks:
            if isinstance(subtask, dict) and subtask.get("sort_order") == target.subtask.sort_order:
                return subtask
    return {}


def _content_depth_for_handout(planner_strategy: dict[str, object]) -> str:
    value = planner_strategy.get("content_depth")
    if value in {"concise", "standard", "detailed"}:
        return str(value)
    return {"brief": "concise", "focused": "concise", "deep": "detailed"}.get(str(value), "standard")


def _intensity_for_handout(planner_strategy: dict[str, object], key: str) -> str:
    value = planner_strategy.get(key)
    return str(value) if value in {"low", "standard", "high"} else "standard"


def _teaching_strategy_hint(weak_area: object) -> str:
    return {
        "concept": "加强概念边界、直觉解释和相似概念对比。",
        "calculation": "加强公式变量、单位、适用条件、代入步骤和计算例题。",
        "application": "加强场景例子、输入输出、实际应用和迁移题。",
        "memorization": "加强核心结论、易错判断、口诀式总结和快速自测。",
    }.get(str(weak_area), "保持清晰、专业、耐心的一对一讲解风格。")

def _stored_task_generation_parameters(
    *,
    target: repository.ExecutionTarget,
    content_type: str,
) -> dict[str, object]:
    config = target.plan.parsed_config_json
    if not isinstance(config, dict):
        return {}
    task_snapshot = config.get("task_snapshot")
    if not isinstance(task_snapshot, list):
        return {}
    for task in task_snapshot:
        if not isinstance(task, dict) or task.get("sort_order") != target.task.sort_order:
            continue
        subtasks = task.get("subtasks")
        if not isinstance(subtasks, list):
            return {}
        for subtask in subtasks:
            if not isinstance(subtask, dict) or subtask.get("sort_order") != target.subtask.sort_order:
                continue
            generation_parameters = subtask.get("generation_parameters")
            if not isinstance(generation_parameters, dict):
                return {}
            content_parameters = generation_parameters.get(content_type)
            return dict(content_parameters) if isinstance(content_parameters, dict) else {}
    return {}


def _stored_subtask_citation_chunk_ids(target: repository.ExecutionTarget) -> list[str]:
    config = target.plan.parsed_config_json
    if not isinstance(config, dict):
        return []
    task_snapshot = config.get("task_snapshot")
    if not isinstance(task_snapshot, list):
        return []
    for task in task_snapshot:
        if not isinstance(task, dict) or task.get("sort_order") != target.task.sort_order:
            continue
        subtasks = task.get("subtasks")
        if not isinstance(subtasks, list):
            return []
        for subtask in subtasks:
            if not isinstance(subtask, dict) or subtask.get("sort_order") != target.subtask.sort_order:
                continue
            citation_chunk_ids = subtask.get("citation_chunk_ids")
            if not isinstance(citation_chunk_ids, list) or not all(
                isinstance(chunk_id, str) for chunk_id in citation_chunk_ids
            ):
                return []
            return list(dict.fromkeys(citation_chunk_ids))
    return []


def _filter_batches_by_citation_scope(
    *,
    batches: list[MaterialContextBatch],
    citation_chunk_ids: list[str],
) -> list[MaterialContextBatch]:
    allowed_chunk_ids = set(citation_chunk_ids)
    scoped_batches: list[MaterialContextBatch] = []
    for batch in batches:
        scoped_chunks = [chunk for chunk in batch.chunks if chunk.chunk_id in allowed_chunk_ids]
        if not scoped_chunks:
            continue
        scoped_batches.append(
            MaterialContextBatch(
                chunks=scoped_chunks,
                material_ids=list(dict.fromkeys(chunk.material_id for chunk in scoped_chunks)),
                estimated_tokens=batch.estimated_tokens,
            )
        )
    if not scoped_batches:
        raise CourseNexusError(
            code="NO_PARSED_MATERIAL",
            message="当前任务没有匹配任务引用范围的已解析资料上下文",
            status_code=400,
        )
    return scoped_batches


def _new_task_generated_content(
    *,
    content_id: str,
    user_id: str,
    course_id: str,
    subtask_id: str,
    content_type: str,
    material_scope_json: dict[str, object],
) -> AIGeneratedContent:
    return AIGeneratedContent(
        id=content_id,
        user_id=user_id,
        course_id=course_id,
        study_subtask_id=subtask_id,
        content_type=content_type,
        title=content_type.replace("_", " ").title(),
        generation_status="pending",
        material_scope_json=material_scope_json,
    )


def _save_failed_task_content(
    db: Session,
    *,
    content_id: str,
    user_id: str,
    course_id: str,
    subtask_id: str,
    content_type: str,
    material_scope_json: dict[str, object],
    error_code: str,
) -> None:
    failed = _new_task_generated_content(
        content_id=content_id,
        user_id=user_id,
        course_id=course_id,
        subtask_id=subtask_id,
        content_type=content_type,
        material_scope_json=material_scope_json,
    )
    failed.generation_status = "failed"
    failed.error_code = error_code
    db.add(failed)
    db.commit()


def _generated_task_content_title(*, content_type: str, target: repository.ExecutionTarget) -> str:
    base_title = target.subtask.title.strip() or target.task.title.strip() or "任务内容"
    if content_type == "handout":
        return f"{base_title}讲义"
    if content_type == "task_test":
        return f"{base_title}测试题"
    return base_title


def _handout_source_note(*, batches: list[MaterialContextBatch], subtask_title: str) -> str:
    material_names: list[str] = []
    for batch in batches:
        for chunk in batch.chunks:
            name = chunk.material_name.strip() if isinstance(chunk.material_name, str) else ""
            if name and name not in material_names:
                material_names.append(name)
    quoted_materials = "".join(f"《{name}》" for name in material_names) or "当前资料"
    topic = subtask_title.strip() if isinstance(subtask_title, str) and subtask_title.strip() else "当前知识点"
    return f"本讲义基于{quoted_materials}中“{topic}”相关内容生成。"


def _reduce_task_content_outputs(
    *,
    content_type: str,
    outputs: list[GeneratorOutput],
    model_provider: ModelProvider | None = None,
    parameters: dict[str, object] | None = None,
) -> GeneratorOutput:
    if not outputs:
        raise CourseNexusError(code="NO_PARSED_MATERIAL", message="没有可生成的材料批次", status_code=400)
    if content_type == "handout":
        return _reduce_handout_outputs(outputs, model_provider=model_provider, parameters=parameters)
    if content_type == "task_test":
        return _reduce_task_test_outputs(outputs)
    raise CourseNexusError(code="VALIDATION_ERROR", message="生成类型不支持", status_code=422)


def _reduce_handout_outputs(
    outputs: list[GeneratorOutput],
    *,
    model_provider: ModelProvider | None = None,
    parameters: dict[str, object] | None = None,
) -> GeneratorOutput:
    markdown_parts = [str(output.content or "").strip() for output in outputs if str(output.content or "").strip()]
    if not markdown_parts:
        raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="模型未返回可保存的 Markdown 讲义", status_code=500)

    params = dict(parameters or {})
    title = str(params.get("handout_title") or outputs[0].title or "讲义").strip() or "讲义"
    source_note = _optional_string(params.get("source_note"))
    if len(markdown_parts) == 1:
        markdown = ensure_handout_header(markdown=markdown_parts[0], title=title, source_note=source_note)
    else:
        if model_provider is None:
            raise CourseNexusError(code="GENERATION_FAILED", message="多批次讲义缺少最终合成模型", status_code=502)
        synthesis_prompt = _build_handout_synthesis_prompt(
            title=title,
            source_note=source_note,
            markdown_parts=markdown_parts,
        )
        markdown = ensure_handout_header(
            markdown=model_provider.generate_text(prompt=synthesis_prompt),
            title=title,
            source_note=source_note,
        )
    if not markdown:
        raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="模型未返回可保存的 Markdown 讲义", status_code=500)
    _assert_no_mermaid(markdown)
    if not _handout_has_visual(markdown):
        raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="讲义必须至少包含一张安全 SVG 图示", status_code=500)
    return GeneratorOutput(
        title=title,
        content=markdown,
        content_json={"format": "markdown", "schema_version": 1},
        item_citation_chunk_ids={},
    )


def _build_handout_synthesis_prompt(*, title: str, source_note: str | None, markdown_parts: list[str]) -> str:
    draft_sections = "\n\n".join(
        f"## 批次草稿 {index}\n\n{markdown}"
        for index, markdown in enumerate(markdown_parts, start=1)
    )
    source_rule = f"一级标题下一段必须原样写入来源说明：{source_note}" if source_note else "不需要额外来源说明。"
    return "\n\n".join(
        [
            "你是 CourseNexus 的讲义终稿编辑。下面是同一个二级任务在不同资料批次上生成的 Markdown 草稿。",
            "请把它们合成为一整篇上下连贯、去重后的最终 Markdown 讲义，不要简单拼接，不要保留批次标题。",
            f"最终讲义一级标题必须是：{title}",
            source_rule,
            "最终讲义必须保留或重画至少一张安全内联 SVG 图示，不要输出 Mermaid 代码块或 Mermaid 语法。",
            "只输出 Markdown 正文，不要输出 JSON，不要输出非 SVG HTML，不要包裹代码块，不要写逐条 citation 或 source_citation_ids。",
            draft_sections,
        ]
    )


def _extend_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)




def _merge_by_id(items: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in items:
        key = str(item.get("id") or item.get("title") or item)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def _collect_source_citation_ids(value: object) -> list[str]:
    chunk_ids: list[str] = []
    if isinstance(value, dict):
        source_ids = value.get("source_citation_ids")
        if isinstance(source_ids, list):
            for source_id in source_ids:
                if isinstance(source_id, str) and source_id.strip() and source_id not in chunk_ids:
                    chunk_ids.append(source_id)
        for child in value.values():
            _extend_unique(chunk_ids, _collect_source_citation_ids(child))
    elif isinstance(value, list):
        for child in value:
            _extend_unique(chunk_ids, _collect_source_citation_ids(child))
    return chunk_ids


def _reduce_task_test_outputs(outputs: list[GeneratorOutput]) -> GeneratorOutput:
    contents = [TaskTestContent.model_validate(output.content_json) for output in outputs]
    questions: list[dict[str, object]] = []
    citation_chunk_ids: list[str] = []
    sort_order = 1
    for content in contents:
        for question in sorted(content.questions, key=lambda item: item.sort_order):
            data = question.model_dump(mode="json")
            data["id"] = f"q_{sort_order}"
            data["sort_order"] = sort_order
            questions.append(data)
            sort_order += 1
            for chunk_id in question.source_citation_ids:
                if chunk_id not in citation_chunk_ids:
                    citation_chunk_ids.append(chunk_id)

    content_json = {
        "instructions": contents[0].instructions,
        "questions": questions,
    }
    return GeneratorOutput(
        title="任务测试题",
        content_json=content_json,
        item_citation_chunk_ids=_item_citation_chunk_ids(content_json=content_json, citation_chunk_ids=citation_chunk_ids),
    )


def _item_citation_chunk_ids(*, content_json: dict[str, object], citation_chunk_ids: list[str]) -> dict[str, list[str]]:
    bindings: dict[str, list[str]] = {}
    for item_id in _collect_content_item_ids(content_json):
        bindings[item_id] = list(citation_chunk_ids)
    return bindings


def _collect_content_item_ids(value: object) -> list[str]:
    item_ids: list[str] = []
    if isinstance(value, dict):
        item_id = value.get("id")
        if isinstance(item_id, str):
            item_ids.append(item_id)
        for child in value.values():
            item_ids.extend(_collect_content_item_ids(child))
    elif isinstance(value, list):
        for child in value:
            item_ids.extend(_collect_content_item_ids(child))
    return list(dict.fromkeys(item_ids))


def _ordered_unique_chunk_ids(item_citation_chunk_ids: dict[str, list[str]]) -> list[str]:
    chunk_ids: list[str] = []
    for item_chunk_ids in item_citation_chunk_ids.values():
        for chunk_id in item_chunk_ids:
            if chunk_id not in chunk_ids:
                chunk_ids.append(chunk_id)
    return chunk_ids


def _save_task_content_citations(
    db: Session,
    *,
    generated_content_id: str,
    batches: list[MaterialContextBatch],
    item_citation_chunk_ids: dict[str, list[str]],
) -> dict[str, list[str]]:
    chunk_by_id = {chunk.chunk_id: chunk for batch in batches for chunk in batch.chunks}
    citation_chunk_ids = _ordered_unique_chunk_ids(item_citation_chunk_ids)
    selected_chunks = [chunk_by_id[chunk_id] for chunk_id in citation_chunk_ids if chunk_id in chunk_by_id]
    if not selected_chunks:
        raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="生成结果没有有效引用", status_code=500)

    citation_ids_by_chunk_id: dict[str, str] = {}
    citations: list[SourceCitation] = []
    for sort_order, chunk in enumerate(selected_chunks, start=1):
        citation_id = f"cit_{uuid4().hex}"
        citation_ids_by_chunk_id[chunk.chunk_id] = citation_id
        citations.append(
            SourceCitation(
                id=citation_id,
                generated_content_id=generated_content_id,
                material_id=chunk.material_id,
                material_version_id=chunk.material_version_id,
                chunk_id=chunk.chunk_id,
                material_name=chunk.material_name,
                page=chunk.page,
                page_index=chunk.page_index if chunk.page_index is not None else 0,
                hit_text=chunk.content_text[:500],
                sort_order=sort_order,
            )
        )
    db.add_all(citations)
    db.flush()
    bindings = {
        item_id: [citation_ids_by_chunk_id[chunk_id] for chunk_id in chunk_ids if chunk_id in citation_ids_by_chunk_id]
        for item_id, chunk_ids in item_citation_chunk_ids.items()
    }
    for chunk_id, citation_id in citation_ids_by_chunk_id.items():
        bindings[f"__chunk__:{chunk_id}"] = [citation_id]
    return bindings


def _bind_source_citation_ids(
    value: object,
    bindings: dict[str, list[str]],
    inherited_citation_ids: list[str] | None = None,
    *,
    allow_raw_block_citations: bool = False,
    is_handout_root: bool = False,
    suppress_source_citations: bool = False,
) -> object:
    if isinstance(value, dict):
        if suppress_source_citations:
            return {
                key: _bind_source_citation_ids(
                    child,
                    bindings,
                    None,
                    suppress_source_citations=True,
                )
                for key, child in value.items()
            }

        item_id = value.get("id")
        block_type = value.get("type")
        is_block = isinstance(block_type, str)
        item_citation_ids = bindings.get(item_id, []) if isinstance(item_id, str) else []
        source_citation_ids = (
            _citation_ids_for_raw_sources(value.get("source_citation_ids"), bindings)
            if not is_block or allow_raw_block_citations
            else []
        )
        current_citation_ids = source_citation_ids or item_citation_ids or list(inherited_citation_ids or [])
        bound = {
            key: _bind_source_citation_ids(
                child,
                bindings,
                current_citation_ids,
                allow_raw_block_citations=is_handout_root and key in {"knowledge_map", "formula_cards"},
                suppress_source_citations=key == "rows",
            )
            for key, child in value.items()
        }
        if "source_citation_ids" in value or (is_block and current_citation_ids):
            bound["source_citation_ids"] = list(dict.fromkeys(current_citation_ids))
        return bound
    if isinstance(value, list):
        return [
            _bind_source_citation_ids(
                child,
                bindings,
                inherited_citation_ids,
                allow_raw_block_citations=allow_raw_block_citations,
                suppress_source_citations=suppress_source_citations,
            )
            for child in value
        ]
    return value


def _citation_ids_for_raw_sources(value: object, bindings: dict[str, list[str]]) -> list[str]:
    citation_ids: list[str] = []
    if not isinstance(value, list):
        return citation_ids
    for source_id in value:
        if not isinstance(source_id, str):
            continue
        for citation_id in bindings.get(f"__chunk__:{source_id}", []):
            if citation_id not in citation_ids:
                citation_ids.append(citation_id)
    return citation_ids


def _latest_content_id(db: Session, *, user_id: str, subtask_id: str, content_type: str) -> str | None:
    content = repository.get_latest_successful_task_content(
        db,
        user_id=user_id,
        subtask_id=subtask_id,
        content_type=content_type,
    )
    return content.id if content is not None else None


def _as_task_status(value: str) -> str:
    if value not in VALID_TASK_STATUSES:
        raise CourseNexusError(code="STATE_CONFLICT", message="任务状态不合法", status_code=409, details={"status": value})
    return value


def _subtask_read(subtask: StudySubTask) -> ExecutionSubTaskRead:
    return ExecutionSubTaskRead(
        subtask_id=subtask.id,
        title=subtask.title,
        subtask_type=subtask.subtask_type,
        description=subtask.description,
        status=_as_task_status(subtask.status),
        completed_at=subtask.completed_at,
        sort_order=subtask.sort_order,
    )


def _material_ids(subtask: StudySubTask) -> list[str]:
    raw = subtask.related_material_ids_json
    if raw is None:
        return []
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        raise CourseNexusError(code="VALIDATION_ERROR", message="关联资料 ID 结构损坏", status_code=422)
    return list(dict.fromkeys(raw))


def _related_materials(db: Session, *, user_id: str, course_id: str, subtask: StudySubTask) -> list[ExecutionMaterialRead]:
    material_ids = _material_ids(subtask)
    materials = {material.id: material for material in repository.list_materials_by_ids(db, material_ids=material_ids)}
    reads: list[ExecutionMaterialRead] = []
    for material_id in material_ids:
        material = materials.get(material_id)
        if material is None:
            reads.append(ExecutionMaterialRead(material_id=material_id, name=None, material_type=None, parse_status=None, availability="deleted"))
            continue
        if material.user_id != user_id or material.course_id != course_id:
            raise CourseNexusError(code="STATE_CONFLICT", message="关联资料不属于当前课程", status_code=409, details={"material_id": material_id})
        availability = "deleted" if material.deleted_at is not None or material.parse_status == "deleted" else "available"
        reads.append(
            ExecutionMaterialRead(
                material_id=material.id,
                name=material.name,
                material_type=material.material_type,
                parse_status=material.parse_status,
                availability=availability,
            )
        )
    return reads


def set_subtask_completion(db: Session, *, user_id: str, subtask_id: str, completed: bool) -> SubTaskCompletionResult:
    target = repository.get_completion_target(db, user_id=user_id, subtask_id=subtask_id)
    expected_status = "completed" if completed else "not_started"
    changed = target.subtask.status != expected_status
    try:
        if changed:
            target.subtask.status = expected_status
            target.subtask.completed_at = datetime.now(timezone.utc) if completed else None
            db.add(target.subtask)
        db.flush()

        sibling_subtasks = repository.list_subtasks_for_task(db, task_id=target.task.id)
        target.task.status = derive_task_status([item.status for item in sibling_subtasks])
        target.task.updated_at = datetime.now(timezone.utc)
        db.add(target.task)
        db.flush()

        plan_tasks = repository.list_tasks_for_plan(db, plan_id=target.plan.id)
        target.plan.status = derive_plan_status([item.status for item in plan_tasks])
        target.plan.updated_at = datetime.now(timezone.utc)
        db.add(target.plan)
        db.flush()

        checkin = recalculate_checkin(db, user_id=user_id, checkin_date=target.task.task_date, flush_only=True)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(target.subtask)
    db.refresh(target.task)
    db.refresh(target.plan)
    sibling_subtasks = repository.list_subtasks_for_task(db, task_id=target.task.id)
    return SubTaskCompletionResult(
        changed=changed,
        subtask=CompletionSubTaskRead(
            subtask_id=target.subtask.id,
            status=target.subtask.status,
            completed_at=target.subtask.completed_at,
        ),
        task=CompletionTaskRead(
            task_id=target.task.id,
            status=target.task.status,
            completed_subtask_count=sum(1 for item in sibling_subtasks if item.status == "completed"),
            total_subtask_count=len(sibling_subtasks),
        ),
        plan=CompletionPlanRead(plan_id=target.plan.id, status=target.plan.status),
        checkin=checkin,
    )
