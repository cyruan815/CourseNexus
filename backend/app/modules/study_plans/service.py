from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from time import perf_counter
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.core.logging import get_logger
from app.integrations.model_provider.base import ModelProvider
from app.modules.courses.service import assert_course_owner
from app.modules.material_context.coverage import run_material_coverage
from app.modules.material_context.schemas import ContextChunk
from app.modules.material_context.service import iter_material_context_batches
from app.modules.study_plans import repository as study_plan_repository
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask
from app.modules.study_plans.planner import map_material_batch, make_coverage, reduce_plan_batches, validate_preview
from app.modules.study_plans.repository import StudyPlanBundle
from app.modules.study_plans.schemas import (
    StudyPlanBuildRequest,
    StudyPlanConfigParseRequest,
    StudyPlanParsedConfig,
    StudyPlanPreview,
    StudyPlanSaveRequest,
    StudySubTaskPreview,
    StudyTaskPreview,
)


logger = get_logger("study_plan.build")


def _new_plan_id() -> str:
    return f"sp_{uuid4().hex}"


def _new_task_id() -> str:
    return f"tsk_{uuid4().hex}"


def _new_subtask_id() -> str:
    return f"sub_{uuid4().hex}"


def parse_study_plan_config(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: StudyPlanConfigParseRequest,
    model_provider: ModelProvider,
) -> StudyPlanParsedConfig:
    course = assert_course_owner(db, user_id, course_id)
    parsed = model_provider.generate_structured(
        prompt=_build_config_parse_prompt(course_name=course.name, payload=payload),
        output_schema=StudyPlanParsedConfig,
    )
    return parsed.model_copy(update={"material_scope": payload.material_scope})


def preview_study_plan(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: StudyPlanBuildRequest,
    model_provider: ModelProvider,
    max_tokens: int,
) -> StudyPlanPreview:
    started_at = perf_counter()
    assert_course_owner(db, user_id, course_id)
    batches = list(
        iter_material_context_batches(
            db,
            user_id=user_id,
            course_id=course_id,
            material_scope=payload.material_scope,
            max_tokens=max_tokens,
        )
    )
    if not batches:
        raise CourseNexusError(code="NO_PARSED_MATERIAL", message="当前范围没有已解析资料", status_code=400)

    expected_material_ids = {material_id for batch in batches for material_id in batch.material_ids}
    coverage_result = run_material_coverage(
        batches=batches,
        expected_material_ids=expected_material_ids,
        map_batch=lambda batch: map_material_batch(batch=batch, payload=payload, model_provider=model_provider),
        reduce_results=lambda mapped_batches: reduce_plan_batches(
            mapped_batches=mapped_batches,
            payload=payload,
            expected_material_ids=expected_material_ids,
            model_provider=model_provider,
        ),
    )
    preview = StudyPlanPreview(
        course_id=course_id,
        title=coverage_result.value.title,
        goal_text=payload.goal_text,
        start_date=payload.start_date,
        end_date=payload.end_date,
        daily_available_minutes=payload.daily_available_minutes,
        material_scope=payload.material_scope,
        coverage=make_coverage(
            expected_material_ids=expected_material_ids,
            processed_material_ids=coverage_result.processed_material_ids,
            batch_count=len(batches),
        ),
        tasks=coverage_result.value.tasks,
    )
    validate_preview(preview=preview, scoped_material_ids=expected_material_ids)
    logger.info(
        "计划预览成功 | course=%s tasks=%d subtasks=%d cost_ms=%.2f",
        course_id,
        len(preview.tasks),
        sum(len(task.subtasks) for task in preview.tasks),
        (perf_counter() - started_at) * 1000,
    )
    return preview


def save_study_plan(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: StudyPlanBuildRequest | StudyPlanSaveRequest,
    model_provider: ModelProvider,
    max_tokens: int,
    idempotency_key: str | None = None,
) -> StudyPlanBundle:
    started_at = perf_counter()
    assert_course_owner(db, user_id, course_id)
    save_payload = _coerce_save_request(payload)
    key_hash = _hash_value(idempotency_key) if idempotency_key else None
    request_hash = _hash_request(save_payload)
    if key_hash:
        existing_plan = study_plan_repository.get_active_study_plan_for_idempotency_key(
            db,
            user_id=user_id,
            course_id=course_id,
            key_hash=key_hash,
        )
        if existing_plan is not None:
            config = existing_plan.parsed_config_json if isinstance(existing_plan.parsed_config_json, dict) else {}
            idempotency = config.get("idempotency") if isinstance(config, dict) else {}
            if isinstance(idempotency, dict) and idempotency.get("request_hash") == request_hash:
                return _bundle_for_plan(db, existing_plan)
            raise CourseNexusError(code="IDEMPOTENCY_CONFLICT", message="幂等键已用于不同请求", status_code=409)

    if save_payload.tasks is None:
        preview = preview_study_plan(
            db,
            user_id=user_id,
            course_id=course_id,
            payload=save_payload,
            model_provider=model_provider,
            max_tokens=max_tokens,
        )
        title = save_payload.title or preview.title
        tasks_preview = preview.tasks
        coverage = preview.coverage.model_dump(mode="json")
    else:
        title = save_payload.title or "学习计划"
        tasks_preview = save_payload.tasks
        coverage = None

    plan_id = _new_plan_id()
    plan = StudyPlan(
        id=plan_id,
        user_id=user_id,
        course_id=course_id,
        title=title,
        goal_text=save_payload.goal_text,
        parsed_config_json=_saved_config(save_payload, coverage=coverage, key_hash=key_hash, request_hash=request_hash),
        start_date=save_payload.start_date,
        end_date=save_payload.end_date,
        daily_available_minutes=save_payload.daily_available_minutes,
        status="active",
    )
    tasks, subtasks = _rows_from_task_previews(plan_id=plan_id, course_id=course_id, task_previews=tasks_preview)
    try:
        study_plan_repository.add_study_plan_bundle(db, plan=plan, tasks=tasks, subtasks=subtasks)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(plan)
    logger.info(
        "计划保存成功 | plan=%s course=%s tasks=%d subtasks=%d cost_ms=%.2f",
        plan_id,
        course_id,
        len(tasks),
        len(subtasks),
        (perf_counter() - started_at) * 1000,
    )
    return _bundle_for_plan(db, plan)


def list_study_plans(db: Session, *, user_id: str, course_id: str) -> list[StudyPlan]:
    assert_course_owner(db, user_id, course_id)
    return study_plan_repository.list_active_study_plans_for_course(db, user_id=user_id, course_id=course_id)


def get_study_plan_detail(db: Session, *, user_id: str, plan_id: str) -> StudyPlanBundle:
    plan = study_plan_repository.get_active_study_plan_for_user(db, user_id=user_id, plan_id=plan_id)
    if plan is None:
        raise CourseNexusError(code="NOT_FOUND", message="学习计划不存在", status_code=404)
    return _bundle_for_plan(db, plan)


def _coerce_save_request(payload: StudyPlanBuildRequest | StudyPlanSaveRequest) -> StudyPlanSaveRequest:
    if isinstance(payload, StudyPlanSaveRequest):
        return payload
    return StudyPlanSaveRequest.model_validate(payload.model_dump(mode="json"))


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_request(payload: StudyPlanSaveRequest) -> str:
    raw = json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _hash_value(raw)


def _saved_config(
    payload: StudyPlanSaveRequest,
    *,
    coverage: dict[str, object] | None,
    key_hash: str | None,
    request_hash: str,
) -> dict[str, object]:
    config: dict[str, object] = {
        "material_scope": payload.material_scope.model_dump(mode="json"),
        "daily_available_minutes": payload.daily_available_minutes,
        "preference": payload.preference,
        "tasks_source": "confirmed" if payload.tasks is not None else "generated",
    }
    if coverage is not None:
        config["coverage"] = coverage
    if key_hash is not None:
        config["idempotency"] = {"key_hash": key_hash, "request_hash": request_hash}
    return config


def _rows_from_task_previews(
    *,
    plan_id: str,
    course_id: str,
    task_previews: list[StudyTaskPreview],
) -> tuple[list[StudyTask], list[StudySubTask]]:
    tasks: list[StudyTask] = []
    subtasks: list[StudySubTask] = []
    for task_preview in task_previews:
        task_id = _new_task_id()
        tasks.append(
            StudyTask(
                id=task_id,
                plan_id=plan_id,
                course_id=course_id,
                title=task_preview.title,
                task_date=task_preview.task_date,
                status="not_started",
                sort_order=task_preview.sort_order,
            )
        )
        for subtask_preview in task_preview.subtasks:
            subtasks.append(
                StudySubTask(
                    id=_new_subtask_id(),
                    task_id=task_id,
                    plan_id=plan_id,
                    course_id=course_id,
                    title=subtask_preview.title,
                    subtask_type=subtask_preview.subtask_type,
                    description=subtask_preview.description,
                    related_material_ids_json=subtask_preview.related_material_ids,
                    status="not_started",
                    sort_order=subtask_preview.sort_order,
                )
            )
    return tasks, subtasks


def _bundle_for_plan(db: Session, plan: StudyPlan) -> StudyPlanBundle:
    return StudyPlanBundle(
        plan=plan,
        tasks=study_plan_repository.list_tasks_for_plan(db, plan_id=plan.id),
        subtasks=study_plan_repository.list_subtasks_for_plan(db, plan_id=plan.id),
    )


def _build_config_parse_prompt(*, course_name: str, payload: StudyPlanConfigParseRequest) -> str:
    return "\n".join(
        [
            "你是 CourseNexus 的学习计划配置解析器。",
            "只从用户目标中提取可编辑的学习计划字段，不创建计划，不编造无法确定的信息。",
            "无法可靠确定的字段填 null，并把字段名加入 unresolved_fields。",
            f"课程名称：{course_name}",
            f"用户目标：{payload.goal_text}",
            f"资料范围：{payload.material_scope.model_dump(mode='json')}",
        ]
    )


def _build_task_previews(start_date: date, end_date: date, chunks: list[ContextChunk]) -> list[StudyTaskPreview]:
    days = _date_range(start_date, end_date)
    return [
        StudyTaskPreview(
            title=f"第 {index + 1} 天学习任务",
            task_date=task_date,
            sort_order=index + 1,
            subtasks=_build_subtask_previews(chunks, offset=index),
        )
        for index, task_date in enumerate(days)
    ]


def _build_subtask_previews(chunks: list[ContextChunk], *, offset: int) -> list[StudySubTaskPreview]:
    subtask_types = ["learn", "review", "quiz"]
    selected_chunks = [chunks[(offset + index) % len(chunks)] for index in range(min(3, len(chunks)))]
    return [
        StudySubTaskPreview(
            title=f"{_subtask_label(subtask_types[index])}: {chunk.heading or chunk.material_name}",
            subtask_type=subtask_types[index],
            description=chunk.content_text[:200],
            related_material_ids=[chunk.material_id],
            sort_order=index + 1,
        )
        for index, chunk in enumerate(selected_chunks)
    ]


def _date_range(start_date: date, end_date: date) -> list[date]:
    day_count = (end_date - start_date).days + 1
    return [start_date + timedelta(days=offset) for offset in range(day_count)]


def _subtask_label(subtask_type: str) -> str:
    return {"learn": "学习", "review": "复习", "quiz": "自测"}[subtask_type]
