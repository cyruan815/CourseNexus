from __future__ import annotations

from datetime import date, timedelta
from time import perf_counter
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.core.logging import get_logger
from app.integrations.model_provider.base import ModelProvider
from app.modules.courses.service import assert_course_owner
from app.modules.material_context.schemas import ContextChunk
from app.modules.material_context.service import resolve_context
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask
from app.modules.study_plans.repository import (
    StudyPlanBundle,
    get_active_study_plan_for_user,
    list_active_study_plans_for_course,
    list_subtasks_for_plan,
    list_tasks_for_plan,
    save_study_plan_bundle,
)
from app.modules.study_plans.schemas import (
    StudyPlanBuildRequest,
    StudyPlanConfigParseRequest,
    StudyPlanParsedConfig,
    StudyPlanPreview,
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
) -> StudyPlanPreview:
    started_at = perf_counter()
    preview = _build_study_plan_preview(db, user_id=user_id, course_id=course_id, payload=payload)
    logger.info(
        "计划预览成功 | course=%s tasks=%d subtasks=%d cost_ms=%.2f",
        course_id,
        len(preview.tasks),
        sum(len(task.subtasks) for task in preview.tasks),
        (perf_counter() - started_at) * 1000,
    )
    return preview


def _build_study_plan_preview(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: StudyPlanBuildRequest,
) -> StudyPlanPreview:
    course = assert_course_owner(db, user_id, course_id)
    context = resolve_context(db, user_id, course_id, payload.material_scope)
    if context.no_parsed_material:
        raise CourseNexusError(code="NO_PARSED_MATERIAL", message="当前范围没有已解析资料", status_code=400)

    return StudyPlanPreview(
        course_id=course_id,
        title=f"{course.name} 学习计划",
        goal_text=payload.goal_text,
        start_date=payload.start_date,
        end_date=payload.end_date,
        daily_available_minutes=payload.daily_available_minutes,
        material_scope=payload.material_scope,
        tasks=_build_task_previews(payload.start_date, payload.end_date, context.chunks),
    )


def save_study_plan(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: StudyPlanBuildRequest,
) -> StudyPlanBundle:
    started_at = perf_counter()
    preview = _build_study_plan_preview(db, user_id=user_id, course_id=course_id, payload=payload)
    plan_id = _new_plan_id()
    plan = StudyPlan(
        id=plan_id,
        user_id=user_id,
        course_id=course_id,
        title=preview.title,
        goal_text=payload.goal_text,
        parsed_config_json={
            "material_scope": payload.material_scope.model_dump(mode="json"),
            "daily_available_minutes": payload.daily_available_minutes,
        },
        start_date=payload.start_date,
        end_date=payload.end_date,
        daily_available_minutes=payload.daily_available_minutes,
        status="active",
    )
    tasks: list[StudyTask] = []
    subtasks: list[StudySubTask] = []
    for task_preview in preview.tasks:
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
    bundle = save_study_plan_bundle(db, plan=plan, tasks=tasks, subtasks=subtasks)
    logger.info(
        "计划保存成功 | plan=%s course=%s tasks=%d subtasks=%d cost_ms=%.2f",
        plan_id,
        course_id,
        len(tasks),
        len(subtasks),
        (perf_counter() - started_at) * 1000,
    )
    return bundle


def list_study_plans(db: Session, *, user_id: str, course_id: str) -> list[StudyPlan]:
    assert_course_owner(db, user_id, course_id)
    return list_active_study_plans_for_course(db, user_id=user_id, course_id=course_id)


def get_study_plan_detail(db: Session, *, user_id: str, plan_id: str) -> StudyPlanBundle:
    plan = get_active_study_plan_for_user(db, user_id=user_id, plan_id=plan_id)
    if plan is None:
        raise CourseNexusError(code="NOT_FOUND", message="学习计划不存在", status_code=404)
    return StudyPlanBundle(
        plan=plan,
        tasks=list_tasks_for_plan(db, plan_id=plan_id),
        subtasks=list_subtasks_for_plan(db, plan_id=plan_id),
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
