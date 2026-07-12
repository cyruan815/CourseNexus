from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone, timedelta
from math import ceil
from time import perf_counter
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.core.logging import get_logger
from app.integrations.model_provider.base import ModelProvider
from app.modules.checkins.service import recalculate_checkin
from app.modules.courses.service import assert_course_owner
from app.modules.material_context.coverage import run_material_coverage
from app.modules.material_context.schemas import ContextChunk, MaterialContextBatch
from app.modules.material_context.service import iter_material_context_batches, resolve_material_scope_ids
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
    StudyPlanConfigParseRequest,
    StudyPlanParsedConfig,
    StudyPlanPreview,
    StudyPlanRegenerationPreviewRequest,
    StudyPlanReplaceRequest,
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
    normalized = _normalize_relative_config(parsed, goal_text=payload.goal_text)
    if normalized.daily_available_minutes is not None and normalized.daily_minutes_source is None:
        normalized = normalized.model_copy(update={"daily_minutes_source": "user_text"})
    return normalized.model_copy(update={"material_scope": payload.material_scope})



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

    task_previews = coverage_result.value.tasks
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
    )
    planner_strategy = derive_planner_strategy(payload.preference, payload.diagnostic_profile)
    generation_metadata = _with_planner_strategy(
        payload.generation_metadata or _build_generation_metadata(model_provider=model_provider),
        planner_strategy=planner_strategy,
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
    material_scope = payload.material_scope or _material_scope_from_config(config)
    build_payload = StudyPlanBuildRequest(
        goal_text=payload.goal_text or plan.goal_text,
        start_date=payload.start_date or plan.start_date,
        end_date=payload.end_date or plan.end_date,
        duration_days=payload.duration_days,
        daily_available_minutes=payload.daily_available_minutes or plan.daily_available_minutes,
        preference=payload.preference or config.get("preference", "balanced"),
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
    parsed_config = _saved_config(
        payload,
        coverage=None,
        capacity=None,
        generation_metadata=None,
        tasks_preview=payload.tasks,
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
        tasks, subtasks = _rows_from_task_previews(plan_id=plan_id, course_id=plan.course_id, task_previews=payload.tasks)
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
    raw = json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
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


def _build_capacity_summary(*, estimated_total_minutes: int, available_total_minutes: int) -> dict[str, object]:
    if estimated_total_minutes > available_total_minutes:
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


def _build_confirmed_config(*, payload: StudyPlanSaveRequest, duration_days: int, recommended_daily_minutes: int | None, daily_minutes_source: str | None) -> dict[str, object]:
    planner_strategy = derive_planner_strategy(payload.preference, payload.diagnostic_profile)
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
    planner_strategy = derive_planner_strategy(payload.preference, payload.diagnostic_profile)
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


def _material_scope_from_config(config: dict[str, object]) -> object:
    material_scope = config.get("material_scope")
    if isinstance(material_scope, dict):
        return material_scope
    return {"include_all_parsed_materials": True, "material_ids": []}

def _build_config_parse_prompt(*, course_name: str, payload: StudyPlanConfigParseRequest) -> str:
    return "\n".join(
        [
            "你是 CourseNexus 的学习计划配置解析器。",
            "只从用户目标中提取可编辑的学习计划字段，不创建计划，不编造无法确定的信息。",
            "无法可靠确定的字段填 null，并把字段名加入 unresolved_fields。",
            "相对日期解析规则：当用户写“今天是 YYYY年M月D日”时，可把该日期作为当前日期。",
            "当用户写“两天学完”且给出今天日期时，start_date 为当天，end_date 为当天 + 1 天。",
            "当用户写“N天学完/掌握/完成”且给出今天日期时，start_date 为当天，end_date 为当天 + (N - 1) 天。",
            f"课程名称：{course_name}",
            f"用户目标：{payload.goal_text}",
            f"资料范围：{payload.material_scope.model_dump(mode='json')}",
        ]
    )


def _normalize_relative_config(parsed: StudyPlanParsedConfig, *, goal_text: str) -> StudyPlanParsedConfig:
    explicit_today = _extract_explicit_today(goal_text)
    duration_days = _extract_duration_days(goal_text)
    if explicit_today is None or duration_days is None:
        return parsed

    start_date = parsed.start_date or explicit_today
    end_date = parsed.end_date or (start_date + timedelta(days=duration_days - 1))

    unresolved_fields = [
        field_name
        for field_name in parsed.unresolved_fields
        if field_name not in {"start_date", "end_date", "duration_days"}
    ]
    return parsed.model_copy(
        update={
            "start_date": start_date,
            "end_date": end_date,
            "duration_days": duration_days,
            "unresolved_fields": unresolved_fields,
        }
    )
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
    if not match:
        return None
    day_count = _parse_day_count(match.group(1))
    return day_count if day_count and day_count > 0 else None


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
