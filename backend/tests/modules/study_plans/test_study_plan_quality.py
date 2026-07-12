from __future__ import annotations

from datetime import date

import pytest
from pydantic import TypeAdapter, ValidationError

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
    PlanPreference,
    StudyPlanPreview,
    StudyPlanSaveRequest,
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


def test_build_request_derives_end_date_from_duration_days() -> None:
    request = StudyPlanBuildRequest.model_validate(
        {
            "goal_text": "两天学完物理层",
            "start_date": "2026-07-12",
            "duration_days": 2,
            "daily_available_minutes": 90,
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        }
    )

    assert request.end_date == date(2026, 7, 13)
    assert request.duration_days == 2

    with pytest.raises(ValidationError):
        StudyPlanBuildRequest.model_validate(
            {
                "goal_text": "两天学完物理层",
                "start_date": "2026-07-12",
                "daily_available_minutes": 90,
                "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
            }
        )


def test_build_request_allows_missing_daily_minutes_for_auto_estimate() -> None:
    request = StudyPlanBuildRequest.model_validate(
        {
            "goal_text": "两天学完物理层",
            "start_date": "2026-07-12",
            "duration_days": 2,
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        }
    )

    assert request.daily_available_minutes is None
    assert request.end_date == date(2026, 7, 13)
    assert request.duration_days == 2


def test_build_request_rejects_daily_minutes_below_minimum() -> None:
    with pytest.raises(ValidationError):
        StudyPlanBuildRequest.model_validate(
            {
                "goal_text": "两天学完物理层",
                "start_date": "2026-07-12",
                "duration_days": 2,
                "daily_available_minutes": 20,
                "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
            }
        )
def test_study_plan_preview_carries_wizard_metadata() -> None:
    preview = StudyPlanPreview.model_validate(
        {
            "course_id": "crs_net",
            "title": "物理层学习计划",
            "goal_text": "两天学完物理层",
            "start_date": "2026-07-12",
            "end_date": "2026-07-13",
            "duration_days": 2,
            "daily_available_minutes": 90,
            "recommended_daily_minutes": 90,
            "daily_minutes_source": "system_estimated",
            "preference": "balanced",
            "material_scope": {"include_all_parsed_materials": False, "material_ids": ["mat_net"]},
            "coverage": {"expected_material_ids": ["mat_net"], "processed_material_ids": ["mat_net"], "batch_count": 1},
            "diagnostic_profile": {"question_version": "study_plan_diagnostic_v1"},
            "material_snapshot": {"mode": "selected"},
            "capacity": {"feasibility_status": "ok"},
            "generation_metadata": {"schema_version": 1},
            "tasks": [
                {
                    "title": "第一天",
                    "task_date": "2026-07-12",
                    "sort_order": 1,
                    "subtasks": [
                        {
                            "title": "补基础",
                            "subtask_type": "learn",
                            "description": "补物理层基础",
                            "related_material_ids": ["mat_net"],
                            "estimated_minutes": 90,
                            "citation_chunk_ids": ["chk_001"],
                            "sort_order": 1,
                        }
                    ],
                }
            ],
        }
    )

    assert preview.duration_days == 2
    assert preview.recommended_daily_minutes == 90
    assert preview.daily_minutes_source == "system_estimated"
    assert preview.diagnostic_profile == {"question_version": "study_plan_diagnostic_v1"}
    assert preview.material_snapshot == {"mode": "selected"}
    assert preview.capacity == {"feasibility_status": "ok"}
    assert preview.generation_metadata == {"schema_version": 1}


def test_plan_preference_accepts_sprint_and_normalizes_legacy_advanced() -> None:
    preference_adapter = TypeAdapter(PlanPreference)

    assert preference_adapter.validate_python("sprint") == "sprint"
    assert preference_adapter.validate_python("advanced") == "sprint"


def test_derive_planner_strategy_maps_each_preference() -> None:
    assert planner.derive_planner_strategy("fast_track") == {
        "preference": "fast_track",
        "content_depth": "concise",
        "example_intensity": "low",
        "assessment_intensity": "low",
        "review_intensity": "low",
        "foundation_required": False,
        "weak_topics": [],
        "weak_area": "other",
        "explanation_style": "plain_language",
    }
    assert planner.derive_planner_strategy("balanced")["content_depth"] == "standard"
    assert planner.derive_planner_strategy("balanced")["example_intensity"] == "standard"
    assert planner.derive_planner_strategy("balanced")["assessment_intensity"] == "standard"
    assert planner.derive_planner_strategy("balanced")["review_intensity"] == "standard"
    assert planner.derive_planner_strategy("mastery")["content_depth"] == "detailed"
    assert planner.derive_planner_strategy("mastery")["example_intensity"] == "high"
    assert planner.derive_planner_strategy("mastery")["assessment_intensity"] == "high"
    assert planner.derive_planner_strategy("mastery")["review_intensity"] == "high"
    assert planner.derive_planner_strategy("sprint")["content_depth"] == "focused"
    assert planner.derive_planner_strategy("sprint")["example_intensity"] == "standard"
    assert planner.derive_planner_strategy("sprint")["assessment_intensity"] == "high"
    assert planner.derive_planner_strategy("sprint")["review_intensity"] == "high"


def test_derive_planner_strategy_defaults_unknown_preference_to_balanced() -> None:
    assert planner.derive_planner_strategy(None)["preference"] == "balanced"
    assert planner.derive_planner_strategy("unknown")["preference"] == "balanced"
    assert planner.derive_planner_strategy("advanced")["preference"] == "sprint"


def test_derive_planner_strategy_keeps_foundation_for_fast_track_diagnostic() -> None:
    strategy = planner.derive_planner_strategy(
        "fast_track",
        {
            "foundation_needed": True,
            "weak_topics": ["nyquist_shannon"],
            "weak_area": "calculation",
            "explanation_style": "step_by_step",
        },
    )

    assert strategy["preference"] == "fast_track"
    assert strategy["content_depth"] == "concise"
    assert strategy["example_intensity"] == "low"
    assert strategy["assessment_intensity"] == "low"
    assert strategy["review_intensity"] == "low"
    assert strategy["foundation_required"] is True
    assert strategy["weak_topics"] == ["nyquist_shannon"]
    assert strategy["weak_area"] == "calculation"
    assert strategy["explanation_style"] == "step_by_step"


def test_derive_planner_strategy_marks_mastery_and_sprint_intensity() -> None:
    mastery_strategy = planner.derive_planner_strategy("mastery")
    sprint_strategy = planner.derive_planner_strategy("sprint")

    assert mastery_strategy["content_depth"] == "detailed"
    assert mastery_strategy["example_intensity"] == "high"
    assert mastery_strategy["assessment_intensity"] == "high"
    assert mastery_strategy["review_intensity"] == "high"
    assert sprint_strategy["content_depth"] == "focused"
    assert sprint_strategy["assessment_intensity"] == "high"
    assert sprint_strategy["review_intensity"] == "high"


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

def test_reduce_prompt_includes_diagnostic_profile_strategy() -> None:
    payload = _build_request().model_copy(
        update={
            "preference": "fast_track",
            "diagnostic_profile": {
                "question_version": "study_plan_diagnostic_v1",
                "prior_knowledge_level": "little",
                "foundation_needed": True,
                "weak_topics": ["nyquist_shannon", "modulation_coding"],
                "weak_area": "calculation",
                "explanation_style": "step_by_step",
                "diagnostic_note": "希望多讲公式怎么用",
            }
        }
    )

    prompt = planner._build_reduce_prompt(
        mapped_batches=[_mapped_batch()],
        payload=payload,
        expected_material_ids={"mat_net"},
        course_name="计算机网络",
    )

    assert "diagnostic_profile" in prompt
    assert "planner_strategy" in prompt
    assert "content_depth: concise" in prompt
    assert "example_intensity: low" in prompt
    assert "assessment_intensity: low" in prompt
    assert "review_intensity: low" in prompt
    assert "合并优先级" in prompt
    assert "1. 用户时间约束" in prompt
    assert "2. 诊断得出的必要补基础" in prompt
    assert "3. 学习方式 preference 派生配置" in prompt
    assert "4. 额外例题、测试、review" in prompt
    assert "foundation_needed: true" in prompt
    assert "foundation_required: true" in prompt
    assert "第一天或最早可行日期" in prompt
    assert "即使 preference=fast_track" in prompt
    assert "fast_track 不能生成过重计划" in prompt
    assert "weak_topics: nyquist_shannon, modulation_coding" in prompt
    assert "更靠前、更细" in prompt
    assert "weak_area: calculation" in prompt
    assert "公式、步骤推导、计算练习" in prompt
    assert "explanation_style: step_by_step" in prompt
    assert "任务描述风格" in prompt
    assert "希望多讲公式怎么用" in prompt


@pytest.mark.parametrize(
    ("weak_area", "expected_rule"),
    [
        ("concept", "加强概念解释"),
        ("calculation", "加强公式、步骤推导、计算练习"),
        ("application", "加强例题和应用任务"),
        ("memorization", "加强重点记忆、回顾、检查"),
    ],
)
def test_reduce_prompt_covers_each_weak_area_rule(weak_area: str, expected_rule: str) -> None:
    payload = _build_request().model_copy(
        update={
            "diagnostic_profile": {
                "foundation_needed": False,
                "weak_topics": ["topic_a"],
                "weak_area": weak_area,
                "explanation_style": "plain_language",
            }
        }
    )

    prompt = planner._build_reduce_prompt(
        mapped_batches=[_mapped_batch()],
        payload=payload,
        expected_material_ids={"mat_net"},
        course_name="计算机网络",
    )

    assert f"weak_area: {weak_area}" in prompt
    assert expected_rule in prompt


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

def test_build_request_derives_end_date_from_duration_days_and_normalizes_preference() -> None:
    request = StudyPlanBuildRequest.model_validate(
        {
            "goal_text": "我要两天学完计网这门课的第七章节",
            "start_date": "2026-07-12",
            "duration_days": 2,
            "daily_available_minutes": 60,
            "preference": "advanced",
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        }
    )

    assert request.end_date == date(2026, 7, 13)
    assert request.duration_days == 2
    assert request.preference == "sprint"



def test_save_request_accepts_wizard_metadata_fields() -> None:
    request = StudyPlanSaveRequest.model_validate(
        {
            "goal_text": "我要两天学完计网这门课的第七章节",
            "start_date": "2026-07-12",
            "duration_days": 2,
            "daily_available_minutes": 60,
            "preference": "advanced",
            "recommended_daily_minutes": 90,
            "daily_minutes_source": "system_estimated",
            "diagnostic_profile": {"question_version": "study_plan_diagnostic_v1"},
            "material_snapshot": {"mode": "selected"},
            "coverage": {"expected_material_ids": ["mat_net"]},
            "capacity": {"feasibility_status": "ok"},
            "generation_metadata": {"schema_version": 1},
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        }
    )

    assert request.end_date == date(2026, 7, 13)
    assert request.duration_days == 2
    assert request.preference == "sprint"
    assert request.diagnostic_profile["question_version"] == "study_plan_diagnostic_v1"
    assert request.tasks is None



def test_preview_schema_carries_wizard_metadata_fields() -> None:
    preview = StudyPlanPreview.model_validate(
        {
            "course_id": "crs_net",
            "title": "Computer Networks 学习计划",
            "goal_text": "我要两天学完计网这门课的第七章节",
            "start_date": "2026-07-12",
            "end_date": "2026-07-13",
            "duration_days": 2,
            "daily_available_minutes": 60,
            "recommended_daily_minutes": 90,
            "daily_minutes_source": "system_estimated",
            "preference": "advanced",
            "diagnostic_profile": {"question_version": "study_plan_diagnostic_v1"},
            "material_snapshot": {"mode": "selected", "snapshot_hash": "sha256:abc"},
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
            "coverage": {"expected_material_ids": ["mat_net"], "processed_material_ids": ["mat_net"], "batch_count": 1},
            "capacity": {
                "estimated_total_minutes": 120,
                "available_total_minutes": 120,
                "feasibility_status": "ok",
                "warnings": [],
            },
            "generation_metadata": {"schema_version": 1},
            "tasks": [
                {
                    "title": "第 1 天学习任务",
                    "task_date": "2026-07-12",
                    "sort_order": 1,
                    "subtasks": [
                        {
                            "title": "理解可靠传输",
                            "subtask_type": "learn",
                            "description": "学习滑动窗口和确认机制",
                            "related_material_ids": ["mat_net"],
                            "estimated_minutes": 60,
                            "citation_chunk_ids": ["chk_net"],
                            "sort_order": 1,
                        }
                    ],
                }
            ],
        }
    )

    assert preview.duration_days == 2
    assert preview.preference == "sprint"
    assert preview.recommended_daily_minutes == 90
    assert preview.daily_minutes_source == "system_estimated"
    assert preview.diagnostic_profile["question_version"] == "study_plan_diagnostic_v1"
    assert preview.material_snapshot["mode"] == "selected"
    assert preview.capacity["feasibility_status"] == "ok"
    assert preview.generation_metadata["schema_version"] == 1
