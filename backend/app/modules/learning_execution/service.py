from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.checkins.service import recalculate_checkin
from app.modules.course_qa.models import SourceCitation
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generated_content.schemas import GeneratedContentRead
from app.modules.generation.generators.handout import build_generator as build_handout_generator
from app.modules.generation.generators.handout.schemas import HandoutContent
from app.modules.generation.generators.task_test import build_generator as build_task_test_generator
from app.modules.generation.generators.task_test.schemas import TaskTestContent
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
from app.modules.material_context.schemas import MaterialContextBatch, MaterialContextResult, MaterialScope
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
        model_provider=model_provider,
        max_tokens=max_tokens,
    )


def generate_task_test_for_subtask(
    db: Session,
    *,
    user_id: str,
    subtask_id: str,
    parameters: dict[str, object],
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
        model_provider=model_provider,
        max_tokens=max_tokens,
    )


def _generate_task_content(
    db: Session,
    *,
    user_id: str,
    subtask_id: str,
    content_type: str,
    allowed_subtask_types: set[str],
    parameters: dict[str, object],
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

    material_ids = _material_ids(target.subtask)
    material_scope = MaterialScope(include_all_parsed_materials=False, material_ids=material_ids)
    content_id = f"gen_{uuid4().hex}"

    try:
        if not material_ids:
            raise CourseNexusError(code="NO_PARSED_MATERIAL", message="当前任务没有关联已解析资料", status_code=400)

        registry = _task_content_registry(model_provider)
        generator = registry.get(content_type)
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

        output = run_material_coverage(
            batches=batches,
            expected_material_ids=set(material_ids),
            map_batch=lambda batch: generator.generate(
                context=MaterialContextResult(chunks=batch.chunks, no_parsed_material=False),
                parameters=parameters,
            ),
            reduce_results=lambda outputs: _reduce_task_content_outputs(content_type=content_type, outputs=outputs),
        ).value

        content = _new_task_generated_content(
            content_id=content_id,
            user_id=user_id,
            course_id=target.course.id,
            subtask_id=target.subtask.id,
            content_type=content_type,
            material_scope=material_scope,
        )
        content.title = output.title
        content.content = output.content
        content.content_json = output.content_json
        content.generation_status = "success"
        content.error_code = None
        db.add(content)
        db.flush()
        _save_task_content_citations(db, generated_content_id=content.id, batches=batches, citation_chunk_ids=output.citation_chunk_ids)
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
            material_scope=material_scope,
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
            material_scope=material_scope,
            error_code="GENERATION_FAILED",
        )
        raise CourseNexusError(code="GENERATION_FAILED", message="任务内容生成失败", status_code=502) from exc

    db.refresh(content)
    return GeneratedContentRead.model_validate(content)


def _task_content_registry(model_provider: ModelProvider) -> GeneratorRegistry:
    registry = GeneratorRegistry()
    registry.register("handout", build_handout_generator(model_provider))
    registry.register("task_test", build_task_test_generator(model_provider))
    return registry


def _new_task_generated_content(
    *,
    content_id: str,
    user_id: str,
    course_id: str,
    subtask_id: str,
    content_type: str,
    material_scope: MaterialScope,
) -> AIGeneratedContent:
    return AIGeneratedContent(
        id=content_id,
        user_id=user_id,
        course_id=course_id,
        study_subtask_id=subtask_id,
        content_type=content_type,
        title=content_type.replace("_", " ").title(),
        generation_status="pending",
        material_scope_json=material_scope.model_dump(mode="json"),
    )


def _save_failed_task_content(
    db: Session,
    *,
    content_id: str,
    user_id: str,
    course_id: str,
    subtask_id: str,
    content_type: str,
    material_scope: MaterialScope,
    error_code: str,
) -> None:
    failed = _new_task_generated_content(
        content_id=content_id,
        user_id=user_id,
        course_id=course_id,
        subtask_id=subtask_id,
        content_type=content_type,
        material_scope=material_scope,
    )
    failed.generation_status = "failed"
    failed.error_code = error_code
    db.add(failed)
    db.commit()


def _reduce_task_content_outputs(*, content_type: str, outputs: list[GeneratorOutput]) -> GeneratorOutput:
    if not outputs:
        raise CourseNexusError(code="NO_PARSED_MATERIAL", message="没有可生成的材料批次", status_code=400)
    if content_type == "handout":
        return _reduce_handout_outputs(outputs)
    if content_type == "task_test":
        return _reduce_task_test_outputs(outputs)
    raise CourseNexusError(code="VALIDATION_ERROR", message="生成类型不支持", status_code=422)


def _reduce_handout_outputs(outputs: list[GeneratorOutput]) -> GeneratorOutput:
    contents = [HandoutContent.model_validate(output.content_json) for output in outputs]
    objectives: list[str] = []
    sections: list[dict[str, object]] = []
    citation_chunk_ids: list[str] = []
    sort_order = 1
    for content in contents:
        for objective in content.learning_objectives:
            if objective not in objectives:
                objectives.append(objective)
        for section in sorted(content.sections, key=lambda item: item.sort_order):
            data = section.model_dump(mode="json")
            data["id"] = f"sec_{sort_order}"
            data["sort_order"] = sort_order
            sections.append(data)
            sort_order += 1
            for chunk_id in section.source_citation_ids:
                if chunk_id not in citation_chunk_ids:
                    citation_chunk_ids.append(chunk_id)

    content_json = {
        "overview": contents[0].overview,
        "learning_objectives": objectives,
        "sections": sections,
        "summary": contents[-1].summary,
    }
    return GeneratorOutput(title="今日讲义", content_json=content_json, citation_chunk_ids=citation_chunk_ids)


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
    return GeneratorOutput(title="任务测试题", content_json=content_json, citation_chunk_ids=citation_chunk_ids)


def _save_task_content_citations(
    db: Session,
    *,
    generated_content_id: str,
    batches: list[MaterialContextBatch],
    citation_chunk_ids: list[str],
) -> None:
    chunk_by_id = {chunk.chunk_id: chunk for batch in batches for chunk in batch.chunks}
    selected_chunks = [chunk_by_id[chunk_id] for chunk_id in citation_chunk_ids if chunk_id in chunk_by_id]
    if not selected_chunks:
        raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="生成结果没有有效引用", status_code=500)
    db.add_all(
        [
            SourceCitation(
                id=f"cit_{uuid4().hex}",
                generated_content_id=generated_content_id,
                material_id=chunk.material_id,
                chunk_id=chunk.chunk_id,
                material_name=chunk.material_name,
                page=chunk.page,
                page_index=chunk.page_index if chunk.page_index is not None else 0,
                hit_text=chunk.content_text[:500],
                sort_order=index,
            )
            for index, chunk in enumerate(selected_chunks)
        ]
    )
    db.flush()


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
