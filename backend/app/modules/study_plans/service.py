from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone, timedelta
from math import ceil
from time import perf_counter
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.core.logging import get_logger
from app.integrations.model_provider.base import ModelProvider
from app.modules.checkins.service import recalculate_checkin
from app.modules.courses.service import assert_course_owner
from app.modules.generation.generators.task_test.schemas import TaskTestGenerationParameters
from app.modules.material_context.coverage import run_material_coverage
from app.modules.material_context.schemas import ContextChunk, MaterialContextBatch
from app.modules.material_context.service import (
    iter_material_context_batches,
    resolve_material_scope_ids,
    summarize_material_quality_for_scope,
)
from app.modules.study_plans import repository as study_plan_repository
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask
from app.modules.study_plans.planner import (
    derive_planner_strategy,
    map_material_batch,
    make_coverage,
    reduce_plan_batches,
    validate_preview,
)
from app.modules.study_plans.repository import StudyPlanBundle
from app.modules.study_plans.schemas import (
    DIAGNOSTIC_QUESTION_VERSION,
    MIN_DAILY_AVAILABLE_MINUTES,
    PlanBatchExtraction,
    StudyPlanDiagnosticProfileRequest,
    StudyPlanDiagnosticProfileResponse,
    StudyPlanDiagnosticQuestion,
    StudyPlanDiagnosticQuestionOption,
    StudyPlanDiagnosticQuestionRequest,
    StudyPlanDiagnosticQuestionsResponse,
    StudyPlanBuildRequest,
    StudyPlanConfigExtraction,
    StudyPlanConfigParseRequest,
    StudyPlanParsedConfig,
    StudyPlanPreview,
    StudyPlanRegenerationPreviewRequest,
    StudyPlanReplaceRequest,
    StudyPlanSaveRequest,
    StudyPreferenceOverrides,
    StudySubTaskPreview,
    StudyTaskPreview,
)


logger = get_logger("study_plan.build")

_CONFIG_PARSE_REFERENCE_TIMEZONE = "Asia/Shanghai"
_CONFIG_PARSE_SYSTEM_FIELDS = {
    "recommended_daily_minutes",
    "daily_minutes_source",
    "diagnostic_profile",
    "material_snapshot",
    "coverage",
    "capacity",
    "generation_metadata",
    "material_scope",
}


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
    extraction = model_provider.generate_structured(
        prompt=_build_config_parse_prompt(course_name=course.name, payload=payload),
        output_schema=StudyPlanConfigExtraction,
    )
    return _assemble_parsed_config(extraction=extraction, payload=payload, model_provider=model_provider)


def build_study_plan_diagnostic_questions(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: StudyPlanDiagnosticQuestionRequest,
    max_tokens: int,
) -> StudyPlanDiagnosticQuestionsResponse:
    topics = _diagnostic_topics_for_scope(
        db,
        user_id=user_id,
        course_id=course_id,
        material_scope=payload.material_scope,
        max_tokens=max_tokens,
    )
    questions: list[StudyPlanDiagnosticQuestion] = []
    for index, topic in enumerate(topics, start=1):
        questions.append(
            StudyPlanDiagnosticQuestion(
                question_id=f"topic_mastery_{topic['topic_id']}",
                question_type="topic_mastery",
                question_text=f"你对「{topic['topic_title']}」了解多少？",
                topic_id=topic["topic_id"],
                topic_title=topic["topic_title"],
                options=_mastery_question_options(),
                sort_order=index,
            )
        )

    weak_area_order = len(questions) + 1
    questions.append(
        StudyPlanDiagnosticQuestion(
            question_id="weak_area",
            question_type="weak_area",
            question_text="你最担心哪类内容？",
            options=_weak_area_question_options(),
            sort_order=weak_area_order,
        )
    )
    questions.append(
        StudyPlanDiagnosticQuestion(
            question_id="diagnostic_note",
            question_type="diagnostic_note",
            question_text="还有什么想特别补的地方？",
            required=False,
            options=[],
            placeholder="可选填写",
            sort_order=weak_area_order + 1,
        )
    )
    return StudyPlanDiagnosticQuestionsResponse(
        question_version=DIAGNOSTIC_QUESTION_VERSION,
        questions=questions,
    )


def build_study_plan_diagnostic_profile(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: StudyPlanDiagnosticProfileRequest,
    max_tokens: int,
) -> StudyPlanDiagnosticProfileResponse:
    if payload.question_version != DIAGNOSTIC_QUESTION_VERSION:
        raise CourseNexusError(
            code="DIAGNOSTIC_STALE",
            message="诊断问题版本已失效，请重新诊断",
            status_code=409,
            details={"question_version": payload.question_version, "expected_question_version": DIAGNOSTIC_QUESTION_VERSION},
        )

    topics = _diagnostic_topics_for_scope(
        db,
        user_id=user_id,
        course_id=course_id,
        material_scope=payload.material_scope,
        max_tokens=max_tokens,
    )
    valid_topic_ids = {topic["topic_id"] for topic in topics}
    invalid_topic_ids = [answer.topic_id for answer in payload.topic_mastery if answer.topic_id not in valid_topic_ids]
    if invalid_topic_ids:
        raise CourseNexusError(
            code="DIAGNOSTIC_STALE",
            message="诊断答案和当前资料范围不匹配，请重新诊断",
            status_code=409,
            details={"invalid_topic_ids": invalid_topic_ids, "valid_topic_ids": sorted(valid_topic_ids)},
        )

    weak_topics = [answer.topic_id for answer in payload.topic_mastery if answer.mastery_level in {"none", "heard"}]
    foundation_needed = len(weak_topics) > len(payload.topic_mastery) / 2
    return StudyPlanDiagnosticProfileResponse(
        question_version=DIAGNOSTIC_QUESTION_VERSION,
        prior_knowledge_level=_prior_knowledge_level(payload.topic_mastery, foundation_needed=foundation_needed),
        foundation_needed=foundation_needed,
        weak_topics=weak_topics,
        weak_area=payload.weak_area,
        explanation_style=_explanation_style_for_weak_area(payload.weak_area),
        diagnostic_note=payload.diagnostic_note,
    )


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
    course = assert_course_owner(db, user_id, course_id)
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

    material_quality = summarize_material_quality_for_scope(
        db,
        user_id=user_id,
        course_id=course_id,
        material_scope=payload.material_scope,
    )
    expected_material_ids = {material_id for batch in batches for material_id in batch.material_ids}
    duration_days = payload.duration_days or _duration_days_between(payload.start_date, payload.end_date)
    resolved_payload: StudyPlanBuildRequest | None = None
    mapped_estimated_total_minutes = 0

    def reduce_results(mapped_batches: list[PlanBatchExtraction]):
        nonlocal mapped_estimated_total_minutes, resolved_payload
        mapped_estimated_total_minutes = _mapped_batches_total_minutes(mapped_batches)
        daily_available_minutes, recommended_daily_minutes, daily_minutes_source = _resolve_daily_minutes(
            payload=payload,
            estimated_total_minutes=mapped_estimated_total_minutes,
            duration_days=duration_days,
            use_payload_recommendation=False,
        )
        resolved_payload = payload.model_copy(
            update={
                "daily_available_minutes": daily_available_minutes,
                "recommended_daily_minutes": recommended_daily_minutes,
                "daily_minutes_source": daily_minutes_source,
            }
        )
        return reduce_plan_batches(
            mapped_batches=mapped_batches,
            payload=resolved_payload,
            expected_material_ids=expected_material_ids,
            model_provider=model_provider,
            course_name=course.name,
        )

    coverage_result = run_material_coverage(
        batches=batches,
        expected_material_ids=expected_material_ids,
        map_batch=lambda batch: map_material_batch(batch=batch, payload=payload, model_provider=model_provider),
        reduce_results=reduce_results,
    )
    if resolved_payload is None:
        raise CourseNexusError(code="GENERATION_FAILED", message="学习计划生成失败", status_code=500)

    task_previews = _normalize_task_sort_orders(_normalize_quiz_subtasks_to_day_end(coverage_result.value.tasks))
    estimated_total_minutes = _task_previews_total_minutes(task_previews)
    daily_available_minutes = _require_resolved_daily_minutes(resolved_payload.daily_available_minutes)
    recommended_daily_minutes = resolved_payload.recommended_daily_minutes or _recommended_daily_minutes(
        estimated_total_minutes=mapped_estimated_total_minutes or estimated_total_minutes,
        duration_days=duration_days,
    )
    daily_minutes_source = resolved_payload.daily_minutes_source or "system_estimated"
    available_total_minutes = daily_available_minutes * duration_days
    material_snapshot = payload.material_snapshot or _build_material_snapshot(
        material_scope=payload.material_scope,
        expected_material_ids=expected_material_ids,
    )
    capacity = _build_capacity_summary(
        estimated_total_minutes=estimated_total_minutes,
        available_total_minutes=available_total_minutes,
        daily_over_capacity=_has_daily_over_capacity(tasks_preview=task_previews, daily_available_minutes=daily_available_minutes),
    )
    planner_strategy = derive_planner_strategy(payload.preference, payload.diagnostic_profile, payload.preference_overrides)
    generation_metadata = _with_material_quality(
        _with_planner_strategy(
            payload.generation_metadata or _build_generation_metadata(model_provider=model_provider),
            planner_strategy=planner_strategy,
        ),
        material_quality=material_quality.model_dump(mode="json"),
    )
    preview = StudyPlanPreview(
        course_id=course_id,
        title=coverage_result.value.title,
        goal_text=payload.goal_text,
        start_date=payload.start_date,
        end_date=payload.end_date,
        duration_days=duration_days,
        daily_available_minutes=daily_available_minutes,
        recommended_daily_minutes=recommended_daily_minutes,
        daily_minutes_source=daily_minutes_source,
        preference=payload.preference,
        diagnostic_profile=payload.diagnostic_profile,
        material_snapshot=material_snapshot,
        material_scope=payload.material_scope,
        coverage=make_coverage(
            expected_material_ids=expected_material_ids,
            processed_material_ids=coverage_result.processed_material_ids,
            batch_count=len(batches),
        ),
        capacity=capacity,
        generation_metadata=generation_metadata,
        tasks=task_previews,
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
    if save_payload.client_flow == "wizard_v1" and not save_payload.tasks:
        raise CourseNexusError(
            code="PREVIEW_TASKS_REQUIRED",
            message="新向导保存必须提交预览中的 tasks",
            status_code=422,
        )
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

    preview: StudyPlanPreview | None = None
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
        save_payload = save_payload.model_copy(
            update={
                "daily_available_minutes": preview.daily_available_minutes,
                "recommended_daily_minutes": preview.recommended_daily_minutes,
                "daily_minutes_source": preview.daily_minutes_source,
                "material_snapshot": preview.material_snapshot,
                "coverage": preview.coverage.model_dump(mode="json"),
                "capacity": preview.capacity,
                "generation_metadata": preview.generation_metadata,
            }
        )
    else:
        title = save_payload.title or "学习计划"
        tasks_preview = save_payload.tasks
        _validate_confirmed_task_tree(
            db,
            user_id=user_id,
            course_id=course_id,
            payload=save_payload,
            task_previews=tasks_preview,
        )
        save_payload = _resolve_save_payload_daily_minutes(save_payload, tasks_preview=tasks_preview)

    tasks_preview = _with_subtask_generation_parameters(tasks_preview)

    plan_id = _new_plan_id()
    now = datetime.now(timezone.utc)
    plan = StudyPlan(
        id=plan_id,
        user_id=user_id,
        course_id=course_id,
        title=title,
        goal_text=save_payload.goal_text,
        idempotency_key_hash=key_hash,
        parsed_config_json=_saved_config(
            save_payload,
            coverage=preview.coverage.model_dump(mode="json") if preview is not None else None,
            capacity=preview.capacity if preview is not None else None,
            generation_metadata=preview.generation_metadata if preview is not None else None,
            tasks_preview=tasks_preview,
            tasks_source="generated" if save_payload.tasks is None else "confirmed",
            key_hash=key_hash,
            request_hash=request_hash,
        ),
        start_date=save_payload.start_date,
        end_date=save_payload.end_date,
        daily_available_minutes=_require_resolved_daily_minutes(save_payload.daily_available_minutes),
        status="active",
        created_at=now,
        updated_at=now,
    )
    tasks, subtasks = _rows_from_task_previews(plan_id=plan_id, course_id=course_id, task_previews=tasks_preview)
    try:
        study_plan_repository.add_study_plan_bundle(db, plan=plan, tasks=tasks, subtasks=subtasks)
        _recalculate_checkins_for_dates(db, user_id=user_id, dates=_task_dates(tasks))
        db.commit()
    except IntegrityError:
        db.rollback()
        if key_hash:
            return _resolve_idempotency_write_conflict(
                db,
                user_id=user_id,
                course_id=course_id,
                key_hash=key_hash,
                request_hash=request_hash,
            )
        raise
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




def preview_study_plan_regeneration(
    db: Session,
    *,
    user_id: str,
    plan_id: str,
    payload: StudyPlanRegenerationPreviewRequest,
    model_provider: ModelProvider,
    max_tokens: int,
) -> StudyPlanPreview:
    plan = _get_active_plan_or_404(db, user_id=user_id, plan_id=plan_id)
    _assert_replace_allowed(db, plan_id=plan_id)

    config = plan.parsed_config_json if isinstance(plan.parsed_config_json, dict) else {}
    confirmed_config = _config_dict(config, "confirmed_config") or {}
    saved_duration_days = (
        _config_int(confirmed_config, "duration_days")
        or _config_int(config, "duration_days")
        or _duration_days_between(plan.start_date, plan.end_date)
    )
    start_date = payload.start_date or plan.start_date
    if payload.duration_days is not None:
        end_date = payload.end_date
        duration_days = payload.duration_days
    elif payload.end_date is not None:
        end_date = payload.end_date
        duration_days = None
    elif payload.start_date is not None:
        end_date = None
        duration_days = saved_duration_days
    else:
        end_date = plan.end_date
        duration_days = saved_duration_days

    material_scope = (
        payload.material_scope
        or _config_dict(confirmed_config, "material_scope")
        or _config_dict(config, "material_scope")
        or {"include_all_parsed_materials": True, "material_ids": []}
    )
    saved_diagnostic_profile = _config_dict(confirmed_config, "diagnostic_profile") or _config_dict(config, "diagnostic_profile") or {}
    diagnostic_profile = payload.diagnostic_profile if payload.diagnostic_profile is not None else saved_diagnostic_profile
    daily_available_minutes = (
        payload.daily_available_minutes
        or _config_int(confirmed_config, "daily_available_minutes")
        or _config_int(config, "daily_available_minutes")
        or plan.daily_available_minutes
    )
    preference = payload.preference or confirmed_config.get("preference") or config.get("preference") or "balanced"
    build_payload = StudyPlanBuildRequest(
        goal_text=payload.goal_text or plan.goal_text,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration_days,
        daily_available_minutes=daily_available_minutes,
        preference=preference,
        diagnostic_profile=diagnostic_profile,
        material_scope=material_scope,
    )
    preview = preview_study_plan(
        db,
        user_id=user_id,
        course_id=plan.course_id,
        payload=build_payload,
        model_provider=model_provider,
        max_tokens=max_tokens,
    )
    return preview


def replace_study_plan(db: Session, *, user_id: str, plan_id: str, payload: StudyPlanReplaceRequest) -> StudyPlanBundle:
    plan = _get_active_plan_or_404(db, user_id=user_id, plan_id=plan_id)
    _assert_expected_updated_at(plan.updated_at, payload.expected_updated_at)
    _assert_replace_allowed(db, plan_id=plan_id)
    _validate_confirmed_task_tree(
        db,
        user_id=user_id,
        course_id=plan.course_id,
        payload=payload,
        task_previews=payload.tasks,
    )
    payload = _resolve_save_payload_daily_minutes(payload, tasks_preview=payload.tasks)
    tasks_preview = _with_subtask_generation_parameters(payload.tasks)
    parsed_config = _saved_config(
        payload,
        coverage=None,
        capacity=None,
        generation_metadata=None,
        tasks_preview=tasks_preview,
        tasks_source="confirmed",
        key_hash=None,
        request_hash=_hash_request(payload),
    )
    updated_at = datetime.now(timezone.utc)
    try:
        claimed = study_plan_repository.claim_study_plan_replace(
            db,
            user_id=user_id,
            plan_id=plan_id,
            expected_updated_at=_db_expected_updated_at(plan.updated_at, payload.expected_updated_at),
            title=payload.title,
            goal_text=payload.goal_text,
            start_date=payload.start_date,
            end_date=payload.end_date,
            daily_available_minutes=_require_resolved_daily_minutes(payload.daily_available_minutes),
            parsed_config_json=parsed_config,
            updated_at=updated_at,
        )
        if not claimed:
            db.rollback()
            raise CourseNexusError(code="STATE_CONFLICT", message="学习计划已被更新", status_code=409)

        old_dates = _task_dates(study_plan_repository.list_tasks_for_plan(db, plan_id=plan_id))
        study_plan_repository.delete_tasks_for_plan(db, plan_id=plan_id)
        plan.title = payload.title
        plan.goal_text = payload.goal_text
        plan.start_date = payload.start_date
        plan.end_date = payload.end_date
        plan.daily_available_minutes = _require_resolved_daily_minutes(payload.daily_available_minutes)
        plan.status = "active"
        plan.updated_at = updated_at
        plan.parsed_config_json = parsed_config
        tasks, subtasks = _rows_from_task_previews(plan_id=plan_id, course_id=plan.course_id, task_previews=tasks_preview)
        db.add_all(tasks)
        db.add_all(subtasks)
        db.flush()
        _recalculate_checkins_for_dates(db, user_id=user_id, dates=old_dates | _task_dates(tasks))
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(plan)
    return _bundle_for_plan(db, plan)


def delete_study_plan(db: Session, *, user_id: str, plan_id: str) -> StudyPlan:
    plan = _get_active_plan_or_404(db, user_id=user_id, plan_id=plan_id)
    dates = _task_dates(study_plan_repository.list_tasks_for_plan(db, plan_id=plan_id))
    now = datetime.now(timezone.utc)
    plan.status = "deleted"
    plan.deleted_at = now
    plan.updated_at = now
    db.add(plan)
    db.flush()
    _recalculate_checkins_for_dates(db, user_id=user_id, dates=dates)
    db.commit()
    db.refresh(plan)
    return plan


def _resolve_idempotency_write_conflict(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    key_hash: str,
    request_hash: str,
) -> StudyPlanBundle:
    existing_plan = study_plan_repository.get_active_study_plan_for_idempotency_key(
        db,
        user_id=user_id,
        course_id=course_id,
        key_hash=key_hash,
    )
    if existing_plan is None:
        raise CourseNexusError(code="IDEMPOTENCY_CONFLICT", message="幂等键已被已删除或不可复用计划占用", status_code=409)

    config = existing_plan.parsed_config_json if isinstance(existing_plan.parsed_config_json, dict) else {}
    idempotency = config.get("idempotency") if isinstance(config, dict) else {}
    if isinstance(idempotency, dict) and idempotency.get("request_hash") == request_hash:
        return _bundle_for_plan(db, existing_plan)
    raise CourseNexusError(code="IDEMPOTENCY_CONFLICT", message="幂等键已用于不同请求", status_code=409)


def _task_dates(tasks: list[StudyTask]) -> set[date]:
    return {task.task_date for task in tasks}


def _recalculate_checkins_for_dates(db: Session, *, user_id: str, dates: set[date]) -> None:
    for checkin_date in sorted(dates):
        recalculate_checkin(db, user_id=user_id, checkin_date=checkin_date, flush_only=True)

def _coerce_save_request(payload: StudyPlanBuildRequest | StudyPlanSaveRequest) -> StudyPlanSaveRequest:
    if isinstance(payload, StudyPlanSaveRequest):
        return payload
    return StudyPlanSaveRequest.model_validate(payload.model_dump(mode="json"))

def _resolve_save_payload_daily_minutes(
    payload: StudyPlanSaveRequest,
    *,
    tasks_preview: list[StudyTaskPreview],
) -> StudyPlanSaveRequest:
    duration_days = payload.duration_days or _duration_days_between(payload.start_date, payload.end_date)
    estimated_total_minutes = _task_previews_total_minutes(tasks_preview)
    daily_available_minutes, recommended_daily_minutes, daily_minutes_source = _resolve_daily_minutes(
        payload=payload,
        estimated_total_minutes=estimated_total_minutes,
        duration_days=duration_days,
        use_payload_recommendation=True,
    )
    capacity = _build_capacity_summary(
        estimated_total_minutes=estimated_total_minutes,
        available_total_minutes=daily_available_minutes * duration_days,
        daily_over_capacity=_has_daily_over_capacity(tasks_preview=tasks_preview, daily_available_minutes=daily_available_minutes),
    )
    return payload.model_copy(
        update={
            "daily_available_minutes": daily_available_minutes,
            "recommended_daily_minutes": recommended_daily_minutes,
            "daily_minutes_source": daily_minutes_source,
            "capacity": capacity,
        }
    )


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_request(payload: StudyPlanSaveRequest) -> str:
    data = payload.model_dump(mode="json")
    if data.get("client_flow") == "legacy":
        data.pop("client_flow", None)
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _hash_value(raw)


def _duration_days_between(start_date: date, end_date: date) -> int:
    return (end_date - start_date).days + 1


def _normalize_preference_value(value: str | None) -> str | None:
    return "sprint" if value == "advanced" else value



def _diagnostic_topics_for_scope(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_scope: object,
    max_tokens: int,
) -> list[dict[str, str]]:
    batches = list(
        iter_material_context_batches(
            db,
            user_id=user_id,
            course_id=course_id,
            material_scope=material_scope,
            max_tokens=max_tokens,
        )
    )
    if not batches:
        raise CourseNexusError(code="NO_PARSED_MATERIAL", message="当前范围没有已解析资料", status_code=400)

    topics = _extract_diagnostic_topics(batches)
    if not topics:
        raise CourseNexusError(code="NO_PARSED_MATERIAL", message="当前范围没有可用于诊断的资料主题", status_code=400)
    return topics


def _extract_diagnostic_topics(batches: list[MaterialContextBatch]) -> list[dict[str, str]]:
    topics: list[dict[str, str]] = []
    seen_titles: set[str] = set()
    for batch in batches:
        for chunk in batch.chunks:
            topic_title = _diagnostic_topic_title(chunk)
            normalized_title = _normalize_topic_title(topic_title)
            if not normalized_title or normalized_title in seen_titles:
                continue
            seen_titles.add(normalized_title)
            topics.append(
                {
                    "topic_id": _diagnostic_topic_id(chunk=chunk, topic_title=normalized_title),
                    "topic_title": normalized_title,
                }
            )
            if len(topics) >= 3:
                return topics
    return topics


def _diagnostic_topic_title(chunk: ContextChunk) -> str:
    if chunk.heading and chunk.heading.strip():
        return chunk.heading.strip()
    material_name = re.sub(r"\.[^.]+$", "", chunk.material_name).strip()
    if material_name:
        return material_name
    first_line = next((line.strip() for line in chunk.content_text.splitlines() if line.strip()), "")
    return first_line[:40].strip() or "核心知识点"


def _normalize_topic_title(topic_title: str) -> str:
    return re.sub(r"\s+", " ", topic_title.strip().lstrip("#").strip())


def _diagnostic_topic_id(*, chunk: ContextChunk, topic_title: str) -> str:
    basis = f"{chunk.material_id}:{chunk.chunk_id}:{topic_title}"
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return f"topic_{digest}"


def _mastery_question_options() -> list[StudyPlanDiagnosticQuestionOption]:
    return [
        StudyPlanDiagnosticQuestionOption(value="none", label="完全不了解"),
        StudyPlanDiagnosticQuestionOption(value="heard", label="听说过，但不清楚"),
        StudyPlanDiagnosticQuestionOption(value="some", label="了解一些"),
        StudyPlanDiagnosticQuestionOption(value="familiar", label="比较熟悉"),
    ]


def _weak_area_question_options() -> list[StudyPlanDiagnosticQuestionOption]:
    return [
        StudyPlanDiagnosticQuestionOption(value="concept", label="概念理解"),
        StudyPlanDiagnosticQuestionOption(value="calculation", label="计算推导"),
        StudyPlanDiagnosticQuestionOption(value="application", label="做题应用"),
        StudyPlanDiagnosticQuestionOption(value="memorization", label="记忆重点"),
        StudyPlanDiagnosticQuestionOption(value="other", label="其他"),
    ]


def _prior_knowledge_level(topic_mastery: list[object], *, foundation_needed: bool) -> str:
    levels = [getattr(answer, "mastery_level") for answer in topic_mastery]
    if levels and all(level == "none" for level in levels):
        return "none"
    if foundation_needed:
        return "little"
    familiar_count = sum(1 for level in levels if level == "familiar")
    if levels and familiar_count >= ceil(len(levels) / 2):
        return "solid"
    return "some"


def _explanation_style_for_weak_area(weak_area: str) -> str:
    return {
        "calculation": "step_by_step",
        "application": "example_first",
        "memorization": "exam_focused",
    }.get(weak_area, "plain_language")


def _task_previews_total_minutes(task_previews: list[StudyTaskPreview]) -> int:
    return sum(subtask.estimated_minutes for task in task_previews for subtask in task.subtasks)

def _mapped_batches_total_minutes(mapped_batches: list[PlanBatchExtraction]) -> int:
    return sum(unit.estimated_minutes for batch in mapped_batches for unit in batch.units)


def _recommended_daily_minutes(*, estimated_total_minutes: int, duration_days: int) -> int:
    return max(MIN_DAILY_AVAILABLE_MINUTES, ceil(estimated_total_minutes / max(duration_days, 1)))


def _resolve_daily_minutes(
    *,
    payload: StudyPlanBuildRequest,
    estimated_total_minutes: int,
    duration_days: int,
    use_payload_recommendation: bool,
) -> tuple[int, int, str]:
    recommended_daily_minutes = (
        payload.recommended_daily_minutes
        if use_payload_recommendation and payload.recommended_daily_minutes is not None
        else _recommended_daily_minutes(estimated_total_minutes=estimated_total_minutes, duration_days=duration_days)
    )
    if payload.daily_available_minutes is None:
        return recommended_daily_minutes, recommended_daily_minutes, "system_estimated"
    return payload.daily_available_minutes, recommended_daily_minutes, payload.daily_minutes_source or "user_text"




def _normalize_quiz_subtasks_to_day_end(tasks: list[StudyTaskPreview]) -> list[StudyTaskPreview]:
    normalized_tasks: list[StudyTaskPreview] = []
    for task in tasks:
        subtasks = sorted(
            task.subtasks,
            key=lambda subtask: (subtask.subtask_type in {"quiz", "test"}, subtask.sort_order),
        )
        normalized_subtasks = [
            subtask.model_copy(update={"sort_order": sort_order})
            for sort_order, subtask in enumerate(subtasks, start=1)
        ]
        normalized_tasks.append(task.model_copy(update={"subtasks": normalized_subtasks}))
    return normalized_tasks


def _normalize_task_sort_orders(tasks: list[StudyTaskPreview]) -> list[StudyTaskPreview]:
    normalized_tasks: list[StudyTaskPreview] = []
    for task_index, task in enumerate(tasks, start=1):
        normalized_subtasks = [
            subtask.model_copy(update={"sort_order": subtask_index})
            for subtask_index, subtask in enumerate(task.subtasks, start=1)
        ]
        normalized_tasks.append(
            task.model_copy(
                update={
                    "sort_order": task_index,
                    "subtasks": normalized_subtasks,
                }
            )
        )
    return normalized_tasks


def _with_subtask_generation_parameters(tasks: list[StudyTaskPreview]) -> list[StudyTaskPreview]:
    enriched_tasks: list[StudyTaskPreview] = []
    for task in tasks:
        enriched_subtasks: list[StudySubTaskPreview] = []
        for subtask in task.subtasks:
            if subtask.subtask_type in {"quiz", "test"}:
                generation_parameters = dict(subtask.generation_parameters)
                has_task_test_parameters = "task_test" in generation_parameters
                raw_task_test_parameters = generation_parameters.get("task_test")
                if has_task_test_parameters:
                    raw_task_test_was_string = isinstance(raw_task_test_parameters, str)
                    raw_task_test_parameters = _coerce_task_test_parameters_shorthand(
                        generation_parameters=generation_parameters,
                        raw_task_test_parameters=raw_task_test_parameters,
                    )
                    if not isinstance(raw_task_test_parameters, (dict, list)):
                        raise CourseNexusError(
                            code="VALIDATION_ERROR",
                            message="任务测试题生成参数无效",
                            status_code=422,
                            details={"field": "generation_parameters.task_test"},
                        )
                    try:
                        task_test_parameters = TaskTestGenerationParameters.model_validate(raw_task_test_parameters)
                    except ValidationError as exc:
                        raise CourseNexusError(
                            code="VALIDATION_ERROR",
                            message="任务测试题生成参数无效",
                            status_code=422,
                            details={"field": "generation_parameters.task_test", "errors": exc.errors()},
                        ) from exc
                    if raw_task_test_was_string:
                        for consumed_key in ("question_count", "total_question_count", "question_types", "difficulty"):
                            generation_parameters.pop(consumed_key, None)
                else:
                    try:
                        task_test_parameters = _infer_task_test_generation_parameters_from_text(
                            " ".join(part for part in [subtask.title, subtask.description or ""] if part)
                        )
                    except ValidationError as exc:
                        raise CourseNexusError(
                            code="VALIDATION_ERROR",
                            message="任务测试题生成参数无效",
                            status_code=422,
                            details={"field": "generation_parameters.task_test", "errors": exc.errors()},
                        ) from exc
                generation_parameters["task_test"] = task_test_parameters.model_dump(mode="json")
                subtask = subtask.model_copy(update={"generation_parameters": generation_parameters})
            enriched_subtasks.append(subtask)
        enriched_tasks.append(task.model_copy(update={"subtasks": enriched_subtasks}))
    return enriched_tasks


def _coerce_task_test_parameters_shorthand(
    *,
    generation_parameters: dict[str, object],
    raw_task_test_parameters: object,
) -> object:
    if not isinstance(raw_task_test_parameters, str):
        return raw_task_test_parameters
    question_type = TaskTestGenerationParameters._normalize_question_type_value(raw_task_test_parameters)
    if question_type is None:
        return raw_task_test_parameters

    normalized: dict[str, object] = {"question_types": [question_type]}
    for key in ("question_count", "total_question_count", "difficulty"):
        if key in generation_parameters:
            normalized[key] = generation_parameters[key]
    return normalized


def _infer_task_test_generation_parameters_from_text(text: str) -> TaskTestGenerationParameters:
    counts_by_type: dict[str, int] = {}
    question_types: list[str] = []
    for match in re.finditer(r"([一二两三四五六七八九十\d]+)\s*道\s*(单选题|多选题|选择题|判断题|简答题|问答题|计算题|证明题)", text):
        count = _parse_day_count(match.group(1))
        if count is None:
            continue
        question_type = _question_type_for_plan_label(match.group(2))
        counts_by_type[question_type] = counts_by_type.get(question_type, 0) + count
        if question_type not in question_types:
            question_types.append(question_type)
    if not counts_by_type:
        return TaskTestGenerationParameters()
    return TaskTestGenerationParameters(
        question_type_counts=[
            {"question_type": question_type, "question_count": counts_by_type[question_type]}
            for question_type in question_types
        ],
        difficulty="medium",
    )


def _question_type_for_plan_label(label: str) -> str:
    if label == "多选题":
        return "multiple_choice"
    if label == "判断题":
        return "true_false"
    if label in {"简答题", "问答题", "计算题", "证明题"}:
        return "short_answer"
    return "single_choice"


def _require_resolved_daily_minutes(value: int | None) -> int:
    if value is None:
        raise CourseNexusError(code="VALIDATION_ERROR", message="每日学习时间未解析", status_code=422)
    return value


def _task_previews_material_ids(task_previews: list[StudyTaskPreview]) -> list[str]:
    material_ids: list[str] = []
    for task in task_previews:
        for subtask in task.subtasks:
            for material_id in subtask.related_material_ids:
                if material_id not in material_ids:
                    material_ids.append(material_id)
    return material_ids


def _build_material_snapshot(*, material_scope: object, expected_material_ids: set[str]) -> dict[str, object]:
    scope = material_scope if hasattr(material_scope, "include_all_parsed_materials") else None
    include_all = bool(getattr(scope, "include_all_parsed_materials", False)) if scope is not None else False
    material_ids = sorted(expected_material_ids)
    snapshot_basis = {
        "mode": "all_parsed" if include_all else "selected",
        "material_ids": material_ids,
    }
    snapshot_hash = hashlib.sha256(json.dumps(snapshot_basis, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        **snapshot_basis,
        "snapshot_hash": f"sha256:{snapshot_hash}",
    }




def _has_daily_over_capacity(*, tasks_preview: list[StudyTaskPreview], daily_available_minutes: int) -> bool:
    return any(
        sum(subtask.estimated_minutes for subtask in task.subtasks) > daily_available_minutes
        for task in tasks_preview
    )

def _build_capacity_summary(*, estimated_total_minutes: int, available_total_minutes: int, daily_over_capacity: bool = False) -> dict[str, object]:
    if daily_over_capacity or estimated_total_minutes > available_total_minutes:
        feasibility_status = "over_capacity"
        warnings = ["PLAN_OVER_CAPACITY"]
    elif estimated_total_minutes >= max(1, round(available_total_minutes * 0.8)):
        feasibility_status = "tight"
        warnings = []
    else:
        feasibility_status = "ok"
        warnings = []
    return {
        "estimated_total_minutes": estimated_total_minutes,
        "available_total_minutes": available_total_minutes,
        "feasibility_status": feasibility_status,
        "warnings": warnings,
    }


def _build_generation_metadata(*, model_provider: ModelProvider) -> dict[str, object]:
    return {
        "schema_version": 1,
        "model_provider": model_provider.__class__.__name__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _with_planner_strategy(metadata: dict[str, object], *, planner_strategy: dict[str, object]) -> dict[str, object]:
    return {**metadata, "planner_strategy": planner_strategy}


def _with_material_quality(metadata: dict[str, object], *, material_quality: dict[str, object]) -> dict[str, object]:
    return {**metadata, "material_quality": material_quality}


def _build_confirmed_config(*, payload: StudyPlanSaveRequest, duration_days: int, recommended_daily_minutes: int | None, daily_minutes_source: str | None) -> dict[str, object]:
    planner_strategy = derive_planner_strategy(payload.preference, payload.diagnostic_profile, payload.preference_overrides)
    config: dict[str, object] = {
        "goal_text": payload.goal_text,
        "start_date": payload.start_date.isoformat(),
        "end_date": payload.end_date.isoformat(),
        "duration_days": duration_days,
        "daily_available_minutes": _require_resolved_daily_minutes(payload.daily_available_minutes),
        "preference": _normalize_preference_value(payload.preference),
        "planner_strategy": planner_strategy,
        "material_scope": payload.material_scope.model_dump(mode="json"),
    }
    if recommended_daily_minutes is not None:
        config["recommended_daily_minutes"] = recommended_daily_minutes
    if daily_minutes_source is not None:
        config["daily_minutes_source"] = daily_minutes_source
    if payload.recommended_daily_minutes is not None:
        config.setdefault("recommended_daily_minutes", payload.recommended_daily_minutes)
    if payload.diagnostic_profile:
        config["diagnostic_profile"] = payload.diagnostic_profile
    if payload.material_snapshot:
        config["material_snapshot"] = payload.material_snapshot
    if payload.coverage:
        config["coverage"] = payload.coverage
    if payload.capacity:
        config["capacity"] = payload.capacity
    if payload.generation_metadata:
        config["generation_metadata"] = payload.generation_metadata
    return config


def _build_coverage_summary(task_previews: list[StudyTaskPreview]) -> dict[str, object]:
    material_ids = _task_previews_material_ids(task_previews)
    return {
        "expected_material_ids": material_ids,
        "processed_material_ids": material_ids,
        "batch_count": 0,
    }


def _saved_config(
    payload: StudyPlanSaveRequest,
    *,
    coverage: dict[str, object] | None,
    capacity: dict[str, object] | None,
    generation_metadata: dict[str, object] | None,
    tasks_preview: list[StudyTaskPreview],
    tasks_source: str,
    key_hash: str | None,
    request_hash: str,
) -> dict[str, object]:
    duration_days = payload.duration_days or _duration_days_between(payload.start_date, payload.end_date)
    estimated_total_minutes = _task_previews_total_minutes(tasks_preview)
    planner_strategy = derive_planner_strategy(payload.preference, payload.diagnostic_profile, payload.preference_overrides)
    daily_available_minutes, recommended_daily_minutes, daily_minutes_source = _resolve_daily_minutes(
        payload=payload,
        estimated_total_minutes=estimated_total_minutes,
        duration_days=duration_days,
        use_payload_recommendation=True,
    )
    available_total_minutes = daily_available_minutes * duration_days
    confirmed_config = _build_confirmed_config(
        payload=payload,
        duration_days=duration_days,
        recommended_daily_minutes=recommended_daily_minutes,
        daily_minutes_source=daily_minutes_source,
    )
    material_snapshot = payload.material_snapshot or _build_material_snapshot(
        material_scope=payload.material_scope,
        expected_material_ids=set(_task_previews_material_ids(tasks_preview)),
    )
    coverage_value = coverage or _build_coverage_summary(tasks_preview)
    capacity_value = _build_capacity_summary(
        estimated_total_minutes=estimated_total_minutes,
        available_total_minutes=available_total_minutes,
        daily_over_capacity=_has_daily_over_capacity(tasks_preview=tasks_preview, daily_available_minutes=daily_available_minutes),
    )
    generation_metadata_value = _with_planner_strategy(
        generation_metadata or {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat()},
        planner_strategy=planner_strategy,
    )
    data: dict[str, object] = {
        "schema_version": 1,
        "confirmed_config": confirmed_config,
        "diagnostic_profile": payload.diagnostic_profile,
        "material_snapshot": material_snapshot,
        "coverage": coverage_value,
        "capacity": capacity_value,
        "generation_metadata": generation_metadata_value,
        "tasks_source": tasks_source,
        "task_snapshot": [task.model_dump(mode="json") for task in tasks_preview],
        "material_scope": payload.material_scope.model_dump(mode="json"),
        "daily_available_minutes": daily_available_minutes,
        "preference": _normalize_preference_value(payload.preference),
        "planner_strategy": planner_strategy,
        "start_date": payload.start_date.isoformat(),
        "end_date": payload.end_date.isoformat(),
        "duration_days": duration_days,
    }
    if recommended_daily_minutes is not None:
        data["recommended_daily_minutes"] = recommended_daily_minutes
    if daily_minutes_source is not None:
        data["daily_minutes_source"] = daily_minutes_source
    if key_hash is not None:
        data["idempotency"] = {"key_hash": key_hash, "request_hash": request_hash}
    return data
def _validate_confirmed_task_tree(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: StudyPlanBuildRequest,
    task_previews: list[StudyTaskPreview],
) -> None:
    if not task_previews:
        _raise_invalid_confirmed_task_tree("计划至少需要一个一级任务")

    end_date = payload.end_date
    if end_date is None:
        _raise_invalid_confirmed_task_tree("计划结束日期未解析")

    task_orders = [task.sort_order for task in task_previews]
    expected_task_orders = list(range(1, len(task_previews) + 1))
    if task_orders != expected_task_orders:
        _raise_invalid_confirmed_task_tree(
            "一级任务排序不连续",
            details={"sort_orders": task_orders, "expected_sort_orders": expected_task_orders},
        )

    scoped_material_ids = set(
        resolve_material_scope_ids(
            db,
            user_id=user_id,
            course_id=course_id,
            material_scope=payload.material_scope,
        )
    )

    for task in task_previews:
        if task.task_date < payload.start_date or task.task_date > end_date:
            _raise_invalid_confirmed_task_tree(
                "计划任务日期超出请求范围",
                details={
                    "task_date": task.task_date.isoformat(),
                    "start_date": payload.start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )
        if not task.subtasks:
            _raise_invalid_confirmed_task_tree(
                "每个一级任务至少需要一个二级任务",
                details={"task_sort_order": task.sort_order},
            )

        subtask_orders = [subtask.sort_order for subtask in task.subtasks]
        expected_subtask_orders = list(range(1, len(task.subtasks) + 1))
        if subtask_orders != expected_subtask_orders:
            _raise_invalid_confirmed_task_tree(
                "二级任务排序不连续",
                details={
                    "task_sort_order": task.sort_order,
                    "sort_orders": subtask_orders,
                    "expected_sort_orders": expected_subtask_orders,
                },
            )

        for subtask in task.subtasks:
            related_material_ids = set(subtask.related_material_ids)
            if not related_material_ids:
                _raise_invalid_confirmed_task_tree(
                    "二级任务必须关联资料",
                    details={"task_sort_order": task.sort_order, "subtask_sort_order": subtask.sort_order},
                )
            if not related_material_ids.issubset(scoped_material_ids):
                _raise_invalid_confirmed_task_tree(
                    "二级任务关联了范围外或不可用资料",
                    details={
                        "task_sort_order": task.sort_order,
                        "subtask_sort_order": subtask.sort_order,
                        "related_material_ids": sorted(related_material_ids),
                        "scoped_material_ids": sorted(scoped_material_ids),
                    },
                )


def _raise_invalid_confirmed_task_tree(message: str, *, details: dict[str, object] | None = None) -> None:
    raise CourseNexusError(code="VALIDATION_ERROR", message=message, status_code=422, details=details)

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




def _get_active_plan_or_404(db: Session, *, user_id: str, plan_id: str) -> StudyPlan:
    plan = study_plan_repository.get_active_study_plan_for_user(db, user_id=user_id, plan_id=plan_id)
    if plan is None:
        raise CourseNexusError(code="NOT_FOUND", message="学习计划不存在", status_code=404)
    return plan


def _assert_replace_allowed(db: Session, *, plan_id: str) -> None:
    if study_plan_repository.has_started_subtasks(db, plan_id=plan_id):
        raise CourseNexusError(code="STATE_CONFLICT", message="已有学习进度，不能替换计划", status_code=409)
    if study_plan_repository.has_bound_generated_content(db, plan_id=plan_id):
        raise CourseNexusError(code="STATE_CONFLICT", message="已有绑定生成内容，不能替换计划", status_code=409)


def _assert_expected_updated_at(actual: datetime, expected: datetime) -> None:
    actual_value = actual.replace(tzinfo=timezone.utc) if actual.tzinfo is None else actual.astimezone(timezone.utc)
    expected_value = expected.replace(tzinfo=timezone.utc) if expected.tzinfo is None else expected.astimezone(timezone.utc)
    if actual_value != expected_value:
        raise CourseNexusError(code="STATE_CONFLICT", message="学习计划已被更新", status_code=409)


def _db_expected_updated_at(actual: datetime, expected: datetime) -> datetime:
    expected_value = expected.replace(tzinfo=timezone.utc) if expected.tzinfo is None else expected.astimezone(timezone.utc)
    if actual.tzinfo is None:
        return expected_value.replace(tzinfo=None)
    return expected_value


def _config_dict(config: dict[str, object], key: str) -> dict[str, object] | None:
    value = config.get(key)
    return value if isinstance(value, dict) else None


def _config_int(config: dict[str, object], key: str) -> int | None:
    value = config.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _preference_overrides_from_config(config: dict[str, object]) -> StudyPreferenceOverrides | None:
    value = config.get("preference_overrides")
    if isinstance(value, dict):
        return StudyPreferenceOverrides.model_validate(value)
    return None
def _material_scope_from_config(config: dict[str, object]) -> object:
    material_scope = config.get("material_scope")
    if isinstance(material_scope, dict):
        return material_scope
    return {"include_all_parsed_materials": True, "material_ids": []}

def _build_config_parse_prompt(*, course_name: str, payload: StudyPlanConfigParseRequest) -> str:
    reference_date = _config_parse_reference_date().isoformat()
    tomorrow_date = (_config_parse_reference_date() + timedelta(days=1)).isoformat()
    prompt = """
你是 CourseNexus 的学习计划配置解析器。

你的唯一任务是从用户的自然语言学习目标中提取可编辑配置。
你不生成学习计划、学习任务、讲义、测试题或推荐学习时间。

当前日期上下文：
- reference_date: {reference_date}
- timezone: {timezone}

课程名称：
{course_name}

用户原始输入：
{goal_text}

资料范围仅供理解上下文，不要改写或输出：
{material_scope}

请输出符合 StudyPlanConfigExtraction Schema 的 JSON。

你只能提取以下字段：
1. start_date
2. end_date
3. duration_days
4. daily_available_minutes
5. preference
6. preference_overrides
7. ambiguous_fields

不要输出或推断以下系统字段：
- recommended_daily_minutes
- daily_minutes_source
- material_scope
- diagnostic_profile
- material_snapshot
- coverage
- capacity
- generation_metadata
- unresolved_fields
- needs_confirmation_fields

日期规则：
- “今天、明天、后天、下周”等相对日期必须以 reference_date 和 timezone 为基准。
- 持续 N 天时，开始日算第 1 天。
- “一周、1周、一个星期、一星期、一个礼拜”表示 duration_days=7；N 周/星期/礼拜表示 N*7 天。
- 如果已知 start_date 和 duration_days，请计算 end_date。
- 如果已知 start_date 和 end_date，请计算 duration_days。
- 如果用户明确给出的日期互相冲突，不要自行覆盖，把相关字段加入 ambiguous_fields。
- 无法可靠确定时返回 null，不要猜测。

每日学习时间规则：
- 只有用户明确表达“每天、每日、一天学习 X 分钟或小时”时，才填写 daily_available_minutes。
- “两天总共学习三小时”不是每日学习时间，不得填写 daily_available_minutes。
- 用户没有说明每日学习时间时返回 null。
- 不得计算推荐每日学习时间。

preference 只能是：fast_track、balanced、mastery、sprint、null。

整体学习方式映射：
- “速通、快速过一遍、时间紧、先建立框架、少讲一点、抓重点” -> fast_track
- “正常节奏、均衡学习、日常学习” -> balanced
- “深入掌握、深度掌握、系统掌握、真正理解、讲透、扎实掌握” -> mastery
- “考前冲刺、查漏补缺、强化复习、重点回顾、易错点复盘” -> sprint

注意：
- 用户只是要求最后安排测试题，不等于 sprint。
- 用户没有明确整体学习方式时，preference 返回 null。
- 不得因为缺少学习方式就默认 balanced。
- “深度学习”可能是学习方式，也可能是课程主题，必须结合句子语义判断。
- “快速学习深度学习基础”中的“深度学习”是课程主题，整体方式应为 fast_track。
- “用两天深度学习物理层”中的“深度学习”表示深入学习方式，可倾向 mastery。
- 出现否定表达时，不得使用被否定的偏好，例如“不需要详细讲”“不要多给例题”“不是考前冲刺”。
- 如果两个整体模式明确冲突且无法通过局部覆盖表达，将 preference 返回 null，并把 preference 加入 ambiguous_fields。

preference_overrides 用于提取局部要求：

content_depth:
- “讲义详细、讲细、展开讲解” -> detailed
- “简洁一点、少讲、只讲重点” -> concise
- 没有明确表达 -> null

example_intensity:
- “多给例题、多举例、多做示范” -> high
- “少一点例题、不需要太多例题” -> low
- 没有明确表达 -> null

assessment_intensity:
- “多安排测试、加强练习、强化检测” -> high
- “不要太多测试、少做题” -> low
- 没有明确表达 -> null

review_intensity:
- “多复习、多回顾、重复巩固” -> high
- “不用重复复习、少安排回顾” -> low
- 没有明确表达 -> null

局部覆盖和整体 preference 可以同时存在。

示例一：
输入：今天是 2026 年 7 月 13 日。我想用 2 天深入掌握物理层，讲义详细一点，多给公式例题。
输出：
{
  "start_date": "2026-07-13",
  "end_date": "2026-07-14",
  "duration_days": 2,
  "daily_available_minutes": null,
  "preference": "mastery",
  "preference_overrides": {
    "content_depth": "detailed",
    "example_intensity": "high",
    "assessment_intensity": null,
    "review_intensity": null
  },
  "ambiguous_fields": []
}

示例二：
输入：我想明天快速过一遍第七章，公式部分详细讲，不要太多测试。
输出：
{
  "start_date": "{tomorrow_date}",
  "end_date": null,
  "duration_days": null,
  "daily_available_minutes": null,
  "preference": "fast_track",
  "preference_overrides": {
    "content_depth": "detailed",
    "example_intensity": null,
    "assessment_intensity": "low",
    "review_intensity": null
  },
  "ambiguous_fields": []
}

示例三：
输入：考前冲刺两天，每天学习 90 分钟，重点查漏补缺并多安排测试。
输出：
{
  "start_date": null,
  "end_date": null,
  "duration_days": 2,
  "daily_available_minutes": 90,
  "preference": "sprint",
  "preference_overrides": {
    "content_depth": null,
    "example_intensity": null,
    "assessment_intensity": "high",
    "review_intensity": "high"
  },
  "ambiguous_fields": []
}

示例四：
输入：我想快速学习深度学习基础。
输出：
{
  "start_date": null,
  "end_date": null,
  "duration_days": null,
  "daily_available_minutes": null,
  "preference": "fast_track",
  "preference_overrides": {
    "content_depth": null,
    "example_intensity": null,
    "assessment_intensity": null,
    "review_intensity": null
  },
  "ambiguous_fields": []
}
""".strip()
    return (
        prompt.replace("{reference_date}", reference_date)
        .replace("{timezone}", _CONFIG_PARSE_REFERENCE_TIMEZONE)
        .replace("{course_name}", course_name)
        .replace("{goal_text}", payload.goal_text)
        .replace("{material_scope}", str(payload.material_scope.model_dump(mode="json")))
        .replace("{tomorrow_date}", tomorrow_date)
    )


def _assemble_parsed_config(
    *,
    extraction: StudyPlanConfigExtraction,
    payload: StudyPlanConfigParseRequest,
    model_provider: ModelProvider,
) -> StudyPlanParsedConfig:
    ambiguous_fields = set(extraction.ambiguous_fields)
    start_date, end_date, duration_days = _resolve_config_dates(
        extraction=extraction,
        goal_text=payload.goal_text,
        ambiguous_fields=ambiguous_fields,
    )
    preference, preference_resolution = _resolve_config_preference(
        preference=extraction.preference,
        goal_text=payload.goal_text,
        ambiguous_fields=ambiguous_fields,
    )
    preference_overrides, preference_overrides_resolution = _resolve_config_preference_overrides(
        preference_overrides=extraction.preference_overrides,
    )
    unresolved_fields = _resolve_config_unresolved_fields(
        start_date=start_date,
        end_date=end_date,
        duration_days=duration_days,
        ambiguous_fields=ambiguous_fields,
    )
    needs_confirmation_fields = _resolve_config_confirmation_fields(ambiguous_fields=ambiguous_fields)
    return StudyPlanParsedConfig(
        goal_text=payload.goal_text,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration_days,
        daily_available_minutes=extraction.daily_available_minutes,
        recommended_daily_minutes=None,
        daily_minutes_source="user_text" if extraction.daily_available_minutes is not None else None,
        preference=preference,
        preference_overrides=preference_overrides,
        diagnostic_profile={},
        material_snapshot={},
        coverage={},
        capacity={},
        generation_metadata=_build_config_parse_metadata(
            model_provider=model_provider,
            preference_resolution=preference_resolution,
            preference_overrides_resolution=preference_overrides_resolution,
        ),
        material_scope=payload.material_scope,
        unresolved_fields=unresolved_fields,
        needs_confirmation_fields=needs_confirmation_fields,
    )

def _config_parse_reference_date() -> date:
    return datetime.now(timezone(timedelta(hours=8))).date()


def _resolve_config_dates(
    *,
    extraction: StudyPlanConfigExtraction,
    goal_text: str,
    ambiguous_fields: set[str],
) -> tuple[date | None, date | None, int | None]:
    start_date = extraction.start_date
    end_date = extraction.end_date
    duration_days = extraction.duration_days

    explicit_today = _extract_explicit_today(goal_text)
    if explicit_today is not None and start_date is None:
        start_date = explicit_today
    elif explicit_today is None and start_date is None and _mentions_today(goal_text):
        start_date = _config_parse_reference_date()

    text_duration_days = _extract_duration_days(goal_text)
    if text_duration_days is not None:
        if duration_days is not None and duration_days != text_duration_days:
            _raise_config_parse_validation_error(
                "自然语言天数和模型解析天数不一致",
                details={"duration_days": duration_days, "text_duration_days": text_duration_days},
            )
        duration_days = text_duration_days
        ambiguous_fields.discard("duration_days")

    if (
        start_date is None
        and end_date is None
        and duration_days is not None
        and {"start_date", "end_date"} & ambiguous_fields
        and not _mentions_explicit_date_signal(goal_text)
    ):
        ambiguous_fields.difference_update({"start_date", "end_date"})

    has_date_ambiguity = bool({"start_date", "end_date", "duration_days"} & ambiguous_fields)
    if not has_date_ambiguity and start_date is None and end_date is None and duration_days is not None:
        start_date = _config_parse_reference_date()

    if start_date is not None and duration_days is not None:
        expected_end_date = start_date + timedelta(days=duration_days - 1)
        if end_date is not None and end_date != expected_end_date:
            _raise_config_parse_validation_error(
                "日期范围和天数不一致",
                details={
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "duration_days": duration_days,
                    "expected_end_date": expected_end_date.isoformat(),
                },
            )
        end_date = expected_end_date
    elif start_date is not None and end_date is not None:
        duration_days = (end_date - start_date).days + 1
    elif end_date is not None and duration_days is not None:
        start_date = end_date - timedelta(days=duration_days - 1)

    if start_date is not None and end_date is not None:
        if end_date < start_date:
            _raise_config_parse_validation_error(
                "结束日期不能早于开始日期",
                details={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            )
        if duration_days is None:
            duration_days = (end_date - start_date).days + 1
        elif duration_days != (end_date - start_date).days + 1:
            _raise_config_parse_validation_error(
                "日期范围和天数不一致",
                details={
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "duration_days": duration_days,
                },
            )
    return start_date, end_date, duration_days

def _mentions_today(goal_text: str) -> bool:
    return bool(re.search(r"今天|今日|当天|从今天", goal_text))


def _mentions_explicit_date_signal(goal_text: str) -> bool:
    return bool(
        re.search(
            r"\d{4}\s*年|\d{1,2}\s*月\s*\d{1,2}\s*[日号]|\d{1,2}\s*号|今天|今日|明天|后天|本周|下周|周[一二三四五六日天]|星期[一二三四五六日天]",
            goal_text,
        )
    )


def _raise_config_parse_validation_error(message: str, *, details: dict[str, object]) -> None:
    raise CourseNexusError(code="VALIDATION_ERROR", message=message, status_code=422, details=details)


def _resolve_config_preference(
    *,
    preference: str | None,
    goal_text: str,
    ambiguous_fields: set[str],
) -> tuple[str | None, str]:
    if "preference" in ambiguous_fields:
        return None, "unresolved"
    if preference is not None:
        return preference, "model"
    guardrail_preference = _guardrail_preference(goal_text)
    if guardrail_preference is not None:
        return guardrail_preference, "rule_guardrail"
    return None, "unresolved"

def _resolve_config_preference_overrides(
    *,
    preference_overrides: StudyPreferenceOverrides,
) -> tuple[StudyPreferenceOverrides, str]:
    if _has_preference_overrides(preference_overrides):
        return preference_overrides, "model"
    return preference_overrides, "none"
def _guardrail_preference(goal_text: str) -> str | None:
    signals = {
        "mastery": (
            "深度学习",
            "深入学习",
            "深入掌握",
            "深度掌握",
            "真正掌握",
            "系统掌握",
            "扎实掌握",
            "讲义详细",
            "讲详细",
            "讲细",
            "详细一点",
            "多给例题",
            "多给公式",
            "公式适用条件",
            "多讲公式",
            "多讲例题",
            "讲透",
        ),
        "fast_track": (
            "速通",
            "快速过一遍",
            "快速通关",
            "快速学完",
            "快速复习",
            "时间紧",
            "抓重点即可",
            "少讲一点",
            "先建立框架",
            "先抓框架",
        ),
        "sprint": (
            "考前冲刺",
            "考试冲刺",
            "冲刺复习",
            "查漏补缺",
            "强化测试",
            "强化复习",
            "易错点",
            "考前最后检验",
        ),
        "balanced": ("正常节奏", "均衡", "日常学习"),
    }
    matched_preferences = {
        preference
        for preference, phrases in signals.items()
        if any(_contains_non_negated_phrase(goal_text, phrase) for phrase in phrases)
    }
    if len(matched_preferences) == 1:
        return next(iter(matched_preferences))
    return None


def _contains_non_negated_phrase(goal_text: str, phrase: str) -> bool:
    for match in re.finditer(re.escape(phrase), goal_text):
        prefix = goal_text[max(0, match.start() - 4) : match.start()]
        if any(negator in prefix for negator in ("不", "不是", "不要", "无需", "不用", "别")):
            continue
        return True
    return False


def _resolve_config_unresolved_fields(
    *,
    start_date: date | None,
    end_date: date | None,
    duration_days: int | None,
    ambiguous_fields: set[str],
) -> list[str]:
    unresolved_fields: list[str] = []
    if start_date is None or "start_date" in ambiguous_fields:
        unresolved_fields.append("start_date")
    if (duration_days is None and end_date is None) or "duration_days" in ambiguous_fields or "end_date" in ambiguous_fields:
        unresolved_fields.append("duration_days")
    if "preference" in ambiguous_fields:
        unresolved_fields.append("preference")
    return _without_system_or_duplicate_fields(unresolved_fields)


def _resolve_config_confirmation_fields(*, ambiguous_fields: set[str]) -> list[str]:
    fields = ["preference"]
    if "daily_available_minutes" in ambiguous_fields:
        fields.append("daily_available_minutes")
    return _without_system_or_duplicate_fields(fields)


def _without_system_or_duplicate_fields(fields: list[str]) -> list[str]:
    result: list[str] = []
    for field in fields:
        if field in _CONFIG_PARSE_SYSTEM_FIELDS or field in result:
            continue
        result.append(field)
    return result


def _build_config_parse_metadata(
    *,
    model_provider: ModelProvider,
    preference_resolution: str,
    preference_overrides_resolution: str,
) -> dict[str, object]:
    metadata = _build_generation_metadata(model_provider=model_provider)
    metadata["config_parse"] = {
        "preference_resolution": preference_resolution,
        "preference_overrides_resolution": preference_overrides_resolution,
    }
    return metadata

def _has_preference_overrides(preference_overrides: StudyPreferenceOverrides) -> bool:
    return any(value is not None for value in preference_overrides.model_dump(mode="json").values())


def _extract_explicit_today(goal_text: str) -> date | None:
    patterns = (
        r"今天是\s*(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日",
        r"今天\s*(?:是|为|[:：])?\s*(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
    )
    for pattern in patterns:
        match = re.search(pattern, goal_text)
        if match:
            year, month, day = (int(part) for part in match.groups())
            return date(year, month, day)
    return None


def _extract_duration_days(goal_text: str) -> int | None:
    match = re.search(r"([一二两三四五六七八九十\d]+)\s*天", goal_text)
    if match:
        day_count = _parse_day_count(match.group(1))
        return day_count if day_count and day_count > 0 else None

    match = re.search(r"([一二两三四五六七八九十\d]+|一个)\s*(?:周|星期|礼拜)", goal_text)
    if match:
        week_count = _parse_day_count(match.group(1).removesuffix("个"))
        return week_count * 7 if week_count and week_count > 0 else None

    return None


def _parse_day_count(raw_value: str) -> int | None:
    if raw_value.isdigit():
        return int(raw_value)
    digits = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if raw_value in digits:
        return digits[raw_value]
    if raw_value == "十":
        return 10
    if "十" in raw_value:
        tens_raw, ones_raw = raw_value.split("十", 1)
        tens = 1 if tens_raw == "" else digits.get(tens_raw)
        ones = 0 if ones_raw == "" else digits.get(ones_raw)
        if tens is None or ones is None:
            return None
        return tens * 10 + ones
    return None

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
