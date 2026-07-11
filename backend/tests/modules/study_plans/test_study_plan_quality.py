from __future__ import annotations

from datetime import date

import pytest

from app.core.errors import CourseNexusError
from app.modules.material_context.schemas import ContextChunk, MaterialContextBatch, MaterialScope
from app.modules.study_plans import planner
from app.modules.study_plans import service as study_plan_service
from app.modules.study_plans.schemas import (
    PlanBatchExtraction,
    StudyPlanBuildRequest,
    StudyPlanConfigParseRequest,
    StudyPlanCoverage,
    StudyPlanParsedConfig,
    StudyPlanPreview,
    StudySubTaskPreview,
    StudyTaskPreview,
)


def _build_request(goal_text: str = "我要两天学完计网这门课的第七章节") -> StudyPlanBuildRequest:
    return StudyPlanBuildRequest(
        goal_text=goal_text,
        start_date=date(2026, 7, 12),
        end_date=date(2026, 7, 13),
        daily_available_minutes=180,
        material_scope=MaterialScope(),
    )


def _context_batch() -> MaterialContextBatch:
    return MaterialContextBatch(
        material_ids=["mat_net"],
        estimated_tokens=120,
        chunks=[
            ContextChunk(
                material_id="mat_net",
                chunk_id="chk_001",
                chunk_index=1,
                material_name="Chap7 物理层.pdf",
                page="8",
                page_index=7,
                heading="7.2 数据通信的基础知识",
                content_text="奈奎斯特公式：<!-- formula-not-decoded -->；香农公式用于噪声信道。",
            ),
            ContextChunk(
                material_id="mat_net",
                chunk_id="chk_002",
                chunk_index=2,
                material_name="Chap7 物理层.pdf",
                page="18",
                page_index=17,
                heading="7.4 调制技术和编码技术",
                content_text="调制包括 ASK、FSK、PSK；编码包括 PCM 流程。",
            ),
        ],
    )


def _mapped_batch() -> PlanBatchExtraction:
    return PlanBatchExtraction.model_validate(
        {
            "units": [
                {
                    "topic": "数据通信公式",
                    "summary": "奈奎斯特和香农公式，需要复核公式占位。",
                    "difficulty": "medium",
                    "estimated_minutes": 45,
                    "related_material_ids": ["mat_net"],
                    "citation_chunk_ids": ["chk_001"],
                },
                {
                    "topic": "调制编码技术",
                    "summary": "ASK、FSK、PSK 与 PCM 编码流程。",
                    "difficulty": "medium",
                    "estimated_minutes": 45,
                    "related_material_ids": ["mat_net"],
                    "citation_chunk_ids": ["chk_002"],
                },
            ],
            "citation_chunk_ids": ["chk_001", "chk_002"],
        }
    )


def _subtask(**overrides: object) -> StudySubTaskPreview:
    data = {
        "title": "学习数据通信公式",
        "subtask_type": "learn",
        "description": "学习公式含义和使用条件",
        "related_material_ids": ["mat_net"],
        "estimated_minutes": 80,
        "citation_chunk_ids": ["chk_001"],
        "sort_order": 1,
    }
    data.update(overrides)
    return StudySubTaskPreview.model_validate(data)


def _preview(*, goal_text: str = "我要两天学完计网这门课的第七章节", tasks: list[StudyTaskPreview]) -> StudyPlanPreview:
    return StudyPlanPreview(
        course_id="crs_net",
        title="计算机网络第七章学习计划",
        goal_text=goal_text,
        start_date=date(2026, 7, 12),
        end_date=date(2026, 7, 13),
        daily_available_minutes=180,
        material_scope=MaterialScope(),
        coverage=StudyPlanCoverage(expected_material_ids=["mat_net"], processed_material_ids=["mat_net"], batch_count=1),
        tasks=tasks,
    )


def test_map_prompt_requires_ordered_detailed_coverage_and_formula_review() -> None:
    prompt = planner._build_map_prompt(batch=_context_batch(), payload=_build_request())

    assert "章节/页码顺序" in prompt
    assert "不要只输出章节级摘要" in prompt
    assert "formula-not-decoded" in prompt
    assert "需人工复核" in prompt
    assert "citation_chunk_ids" in prompt
    assert "ASK、FSK、PSK" in prompt


def test_reduce_prompt_uses_exact_course_name_and_quality_rules() -> None:
    prompt = planner._build_reduce_prompt(
        mapped_batches=[_mapped_batch()],
        payload=_build_request(),
        expected_material_ids={"mat_net"},
        course_name="计算机网络",
    )

    assert "课程名称：计算机网络" in prompt
    assert "标题必须使用课程名称的原文" in prompt
    assert "至少使用每日可用时间的 80%" in prompt
    assert "练习" in prompt
    assert "输出" in prompt
    assert "quiz/test" in prompt
    assert "最后一个二级任务" in prompt


def test_validate_preview_requires_quiz_or_test_to_be_last() -> None:
    preview = _preview(
        tasks=[
            StudyTaskPreview(
                title="第一天",
                task_date=date(2026, 7, 12),
                sort_order=1,
                subtasks=[
                    _subtask(title="阶段自测", subtask_type="quiz", estimated_minutes=30, sort_order=1),
                    _subtask(title="继续学习", subtask_type="learn", estimated_minutes=90, sort_order=2),
                ],
            ),
            StudyTaskPreview(
                title="第二天",
                task_date=date(2026, 7, 13),
                sort_order=2,
                subtasks=[_subtask(title="综合自测", subtask_type="test", estimated_minutes=120, sort_order=1)],
            ),
        ]
    )

    with pytest.raises(CourseNexusError, match="自测任务必须排在当天最后"):
        planner.validate_preview(preview=preview, scoped_material_ids={"mat_net"})


def test_validate_preview_requires_subtask_citations() -> None:
    preview = _preview(
        goal_text="期末复习",
        tasks=[
            StudyTaskPreview(
                title="第一天",
                task_date=date(2026, 7, 12),
                sort_order=1,
                subtasks=[_subtask(citation_chunk_ids=[])],
            ),
            StudyTaskPreview(
                title="第二天",
                task_date=date(2026, 7, 13),
                sort_order=2,
                subtasks=[_subtask()],
            ),
        ],
    )

    with pytest.raises(CourseNexusError, match="二级任务必须引用资料 chunk"):
        planner.validate_preview(preview=preview, scoped_material_ids={"mat_net"})


def test_validate_preview_rejects_completion_goal_with_underused_daily_time() -> None:
    preview = _preview(
        tasks=[
            StudyTaskPreview(
                title="第一天",
                task_date=date(2026, 7, 12),
                sort_order=1,
                subtasks=[
                    _subtask(estimated_minutes=50, sort_order=1),
                    _subtask(title="阶段自测", subtask_type="quiz", estimated_minutes=30, sort_order=2),
                ],
            ),
            StudyTaskPreview(
                title="第二天",
                task_date=date(2026, 7, 13),
                sort_order=2,
                subtasks=[_subtask(title="综合自测", subtask_type="test", estimated_minutes=120, sort_order=1)],
            ),
        ]
    )

    with pytest.raises(CourseNexusError, match="每日任务时长利用不足"):
        planner.validate_preview(preview=preview, scoped_material_ids={"mat_net"})


def test_validate_preview_completion_goal_requires_final_assessment() -> None:
    preview = _preview(
        tasks=[
            StudyTaskPreview(
                title="第一天",
                task_date=date(2026, 7, 12),
                sort_order=1,
                subtasks=[_subtask(estimated_minutes=120)],
            ),
            StudyTaskPreview(
                title="第二天",
                task_date=date(2026, 7, 13),
                sort_order=2,
                subtasks=[_subtask(title="综合复习", subtask_type="review", estimated_minutes=120)],
            ),
        ]
    )

    with pytest.raises(CourseNexusError, match="最后一天必须包含综合自测"):
        planner.validate_preview(preview=preview, scoped_material_ids={"mat_net"})


def test_config_parse_prompt_explains_relative_day_rules() -> None:
    prompt = study_plan_service._build_config_parse_prompt(
        course_name="计算机网络",
        payload=StudyPlanConfigParseRequest(
            goal_text="我要两天学完计网这门课的第七章节，今天是2026年7月12日",
            material_scope=MaterialScope(),
        ),
    )

    assert "今天是 YYYY年M月D日" in prompt
    assert "两天学完" in prompt
    assert "start_date 为当天" in prompt
    assert "end_date 为当天 + 1 天" in prompt


def test_normalize_relative_config_resolves_two_day_goal_from_explicit_today() -> None:
    parsed = StudyPlanParsedConfig(
        goal_text="我要两天学完计网这门课的第七章节",
        start_date=None,
        end_date=None,
        daily_available_minutes=None,
        preference=None,
        unresolved_fields=["start_date", "end_date", "daily_available_minutes"],
    )

    normalized = study_plan_service._normalize_relative_config(
        parsed,
        goal_text="我要两天学完计网这门课的第七章节，今天是2026年7月12日",
    )

    assert normalized.start_date == date(2026, 7, 12)
    assert normalized.end_date == date(2026, 7, 13)
    assert "start_date" not in normalized.unresolved_fields
    assert "end_date" not in normalized.unresolved_fields
    assert "daily_available_minutes" in normalized.unresolved_fields
