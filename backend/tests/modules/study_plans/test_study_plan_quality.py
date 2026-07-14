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
    StudyPlanConfigExtraction,
    StudyPlanCoverage,
    StudyPlanParsedConfig,
    PlanPreference,
    StudyPlanPreview,
    StudyPlanSaveRequest,
    StudyPreferenceOverrides,
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


def _context_chunk(*, heading: str | None, content_text: str) -> ContextChunk:
    return ContextChunk(
        material_id="mat_net",
        chunk_id="chk_meta_case",
        chunk_index=1,
        material_name="Chap7 物理层.pdf",
        page="1",
        page_index=0,
        heading=heading,
        content_text=content_text,
    )


@pytest.mark.parametrize(
    ("heading", "content_text"),
    [
        ("第 7 章 小结", "复习本章要点。"),
        ("目录", "第 1 章 基础"),
        (None, "# Summary\nThis chapter reviews the main ideas."),
        ("Acknowledgements", "Thank you to the contributors."),
    ],
)
def test_meta_citation_detection_accepts_structural_labels(
    heading: str | None,
    content_text: str,
) -> None:
    assert study_plan_service._is_meta_citation_chunk(
        _context_chunk(heading=heading, content_text=content_text)
    )


@pytest.mark.parametrize(
    ("heading", "content_text"),
    [
        ("Summary Statistics", "Summary Statistics describes numerical data."),
        ("数据总结方法", "总结变量之间的关系是统计分析的一部分。"),
        (None, "总结变量之间的关系，并计算均值与方差。"),
        ("Outline Algorithms", "Outline Algorithms are used in rendering."),
    ],
)
def test_meta_citation_detection_keeps_normal_body_content(
    heading: str | None,
    content_text: str,
) -> None:
    assert not study_plan_service._is_meta_citation_chunk(
        _context_chunk(heading=heading, content_text=content_text)
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


class _ConfigParseTestProvider:
    pass


def _assemble_config_from_goal(
    goal_text: str,
    *,
    preference: str | None = None,
    preference_overrides: StudyPreferenceOverrides | None = None,
) -> StudyPlanParsedConfig:
    return study_plan_service._assemble_parsed_config(
        extraction=StudyPlanConfigExtraction(
            preference=preference,
            preference_overrides=preference_overrides or StudyPreferenceOverrides(),
        ),
        payload=StudyPlanConfigParseRequest(goal_text=goal_text, material_scope=MaterialScope()),
        model_provider=_ConfigParseTestProvider(),
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


def test_subtask_type_normalizes_model_aliases() -> None:
    practice = _subtask(subtask_type="practice")
    final_test = _subtask(subtask_type="final-test")

    assert practice.subtask_type == "quiz"
    assert final_test.subtask_type == "test"

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


def test_reduce_prompt_uses_effective_preference_overrides_without_default_conflict() -> None:
    payload = _build_request().model_copy(
        update={
            "preference": "fast_track",
            "preference_overrides": StudyPreferenceOverrides(content_depth="detailed"),
        }
    )

    prompt = planner._build_reduce_prompt(
        mapped_batches=[_mapped_batch()],
        payload=payload,
        expected_material_ids={"mat_net"},
        course_name="计算机网络",
    )

    assert "content_depth: detailed" in prompt
    assert "example_intensity: low" in prompt
    assert "assessment_intensity: low" in prompt
    assert "review_intensity: low" in prompt
    assert "content_depth=concise" not in prompt
    assert "局部覆盖" in prompt


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
    assert "fast_track 以最终有效策略控制计划轻重" in prompt
    assert "不得再次使用学习方式的默认值覆盖" in prompt
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



def test_validate_preview_requires_exactly_one_assessment_per_day() -> None:
    missing_assessment_preview = _preview(
        goal_text="review for final",
        tasks=[
            StudyTaskPreview(
                title="day 1",
                task_date=date(2026, 7, 12),
                sort_order=1,
                subtasks=[_subtask(estimated_minutes=90, sort_order=1)],
            ),
            StudyTaskPreview(
                title="day 2",
                task_date=date(2026, 7, 13),
                sort_order=2,
                subtasks=[_subtask(title="final test", subtask_type="test", estimated_minutes=90, sort_order=1)],
            ),
        ],
    )

    with pytest.raises(CourseNexusError) as missing_exc:
        planner.validate_preview(preview=missing_assessment_preview, scoped_material_ids={"mat_net"})

    assert missing_exc.value.code == "GENERATION_SCHEMA_INVALID"
    assert missing_exc.value.details["assessment_count"] == 0

    duplicated_assessment_preview = _preview(
        goal_text="review for final",
        tasks=[
            StudyTaskPreview(
                title="day 1",
                task_date=date(2026, 7, 12),
                sort_order=1,
                subtasks=[
                    _subtask(estimated_minutes=60, sort_order=1),
                    _subtask(title="daily quiz", subtask_type="quiz", estimated_minutes=20, sort_order=2),
                    _subtask(title="extra test", subtask_type="test", estimated_minutes=20, sort_order=3),
                ],
            ),
            StudyTaskPreview(
                title="day 2",
                task_date=date(2026, 7, 13),
                sort_order=2,
                subtasks=[_subtask(title="final test", subtask_type="test", estimated_minutes=90, sort_order=1)],
            ),
        ],
    )

    with pytest.raises(CourseNexusError) as duplicated_exc:
        planner.validate_preview(preview=duplicated_assessment_preview, scoped_material_ids={"mat_net"})

    assert duplicated_exc.value.code == "GENERATION_SCHEMA_INVALID"
    assert duplicated_exc.value.details["assessment_count"] == 2


def test_validate_preview_requires_daily_assessment_to_cover_same_day_learning_scope() -> None:
    preview = _preview(
        goal_text="review for final",
        tasks=[
            StudyTaskPreview(
                title="day 1",
                task_date=date(2026, 7, 12),
                sort_order=1,
                subtasks=[
                    _subtask(title="learn formula", estimated_minutes=50, citation_chunk_ids=["chk_001"], sort_order=1),
                    _subtask(title="review coding", subtask_type="review", estimated_minutes=40, citation_chunk_ids=["chk_002"], sort_order=2),
                    _subtask(title="daily quiz", subtask_type="quiz", estimated_minutes=30, citation_chunk_ids=["chk_001"], sort_order=3),
                ],
            ),
            StudyTaskPreview(
                title="day 2",
                task_date=date(2026, 7, 13),
                sort_order=2,
                subtasks=[_subtask(title="final test", subtask_type="test", estimated_minutes=90, citation_chunk_ids=["chk_001", "chk_002"], sort_order=1)],
            ),
        ],
    )

    with pytest.raises(CourseNexusError) as exc_info:
        planner.validate_preview(preview=preview, scoped_material_ids={"mat_net"})

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"
    assert exc_info.value.details["missing_chunk_ids"] == ["chk_002"]


def test_validate_preview_requires_final_assessment_to_cover_full_plan_learning_scope() -> None:
    preview = _preview(
        goal_text="review for final",
        tasks=[
            StudyTaskPreview(
                title="day 1",
                task_date=date(2026, 7, 12),
                sort_order=1,
                subtasks=[
                    _subtask(title="learn formula", estimated_minutes=60, citation_chunk_ids=["chk_001"], sort_order=1),
                    _subtask(title="daily quiz", subtask_type="quiz", estimated_minutes=30, citation_chunk_ids=["chk_001"], sort_order=2),
                ],
            ),
            StudyTaskPreview(
                title="day 2",
                task_date=date(2026, 7, 13),
                sort_order=2,
                subtasks=[
                    _subtask(title="review coding", subtask_type="review", estimated_minutes=60, citation_chunk_ids=["chk_002"], sort_order=1),
                    _subtask(title="final test", subtask_type="test", estimated_minutes=30, citation_chunk_ids=["chk_001"], sort_order=2),
                ],
            ),
        ],
    )

    with pytest.raises(CourseNexusError) as exc_info:
        planner.validate_preview(preview=preview, scoped_material_ids={"mat_net"})

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"
    assert exc_info.value.details["missing_chunk_ids"] == ["chk_002"]


def test_validate_preview_accepts_daily_and_final_assessment_contract() -> None:
    preview = _preview(
        goal_text="review for final",
        tasks=[
            StudyTaskPreview(
                title="day 1",
                task_date=date(2026, 7, 12),
                sort_order=1,
                subtasks=[
                    _subtask(title="learn formula", estimated_minutes=60, citation_chunk_ids=["chk_001"], sort_order=1),
                    _subtask(title="daily quiz", subtask_type="quiz", estimated_minutes=30, citation_chunk_ids=["chk_001"], sort_order=2),
                ],
            ),
            StudyTaskPreview(
                title="day 2",
                task_date=date(2026, 7, 13),
                sort_order=2,
                subtasks=[
                    _subtask(title="review coding", subtask_type="review", estimated_minutes=60, citation_chunk_ids=["chk_002"], sort_order=1),
                    _subtask(title="final test", subtask_type="test", estimated_minutes=30, citation_chunk_ids=["chk_001", "chk_002"], sort_order=2),
                ],
            ),
        ],
    )

    planner.validate_preview(preview=preview, scoped_material_ids={"mat_net"})


def test_validate_preview_requires_subtask_citations() -> None:
    preview = _preview(
        goal_text="review for final",
        tasks=[
            StudyTaskPreview(
                title="day 1",
                task_date=date(2026, 7, 12),
                sort_order=1,
                subtasks=[
                    _subtask(citation_chunk_ids=[]),
                    _subtask(title="daily quiz", subtask_type="quiz", estimated_minutes=30, sort_order=2),
                ],
            ),
            StudyTaskPreview(
                title="day 2",
                task_date=date(2026, 7, 13),
                sort_order=2,
                subtasks=[_subtask(title="final test", subtask_type="test", estimated_minutes=120, sort_order=1)],
            ),
        ],
    )

    with pytest.raises(CourseNexusError, match="\u4e8c\u7ea7\u4efb\u52a1\u5fc5\u987b\u5f15\u7528\u8d44\u6599 chunk"):
        planner.validate_preview(preview=preview, scoped_material_ids={"mat_net"})


def test_validate_preview_rejects_completion_goal_with_underused_daily_time() -> None:
    preview = _preview(
        tasks=[
            StudyTaskPreview(
                title="\u7b2c\u4e00\u5929",
                task_date=date(2026, 7, 12),
                sort_order=1,
                subtasks=[
                    _subtask(estimated_minutes=50, sort_order=1),
                    _subtask(title="\u9636\u6bb5\u81ea\u6d4b", subtask_type="quiz", estimated_minutes=30, sort_order=2),
                ],
            ),
            StudyTaskPreview(
                title="\u7b2c\u4e8c\u5929",
                task_date=date(2026, 7, 13),
                sort_order=2,
                subtasks=[_subtask(title="\u7efc\u5408\u81ea\u6d4b", subtask_type="test", estimated_minutes=120, sort_order=1)],
            ),
        ]
    )

    with pytest.raises(CourseNexusError, match="\u6bcf\u65e5\u4efb\u52a1\u65f6\u957f\u5229\u7528\u4e0d\u8db3"):
        planner.validate_preview(preview=preview, scoped_material_ids={"mat_net"})


def test_validate_preview_completion_goal_requires_final_assessment() -> None:
    preview = _preview(
        tasks=[
            StudyTaskPreview(
                title="\u7b2c\u4e00\u5929",
                task_date=date(2026, 7, 12),
                sort_order=1,
                subtasks=[
                    _subtask(estimated_minutes=90, sort_order=1),
                    _subtask(title="daily quiz", subtask_type="quiz", estimated_minutes=30, sort_order=2),
                ],
            ),
            StudyTaskPreview(
                title="\u7b2c\u4e8c\u5929",
                task_date=date(2026, 7, 13),
                sort_order=2,
                subtasks=[_subtask(title="\u7efc\u5408\u590d\u4e60", subtask_type="review", estimated_minutes=120)],
            ),
        ]
    )

    with pytest.raises(CourseNexusError) as exc_info:
        planner.validate_preview(preview=preview, scoped_material_ids={"mat_net"})

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"
    assert exc_info.value.details["assessment_count"] == 0

def test_config_parse_schema_normalizes_nullable_trace_fields() -> None:
    parsed = StudyPlanParsedConfig.model_validate(
        {
            "goal_text": "两天学习物理层",
            "diagnostic_profile": None,
            "material_snapshot": None,
            "coverage": None,
            "capacity": None,
            "generation_metadata": None,
        }
    )

    assert parsed.diagnostic_profile == {}
    assert parsed.material_snapshot == {}
    assert parsed.coverage == {}
    assert parsed.capacity == {}
    assert parsed.generation_metadata == {}
def test_config_parse_guardrail_keeps_detail_examples_as_local_overrides() -> None:
    parsed = _assemble_config_from_goal("讲义详细一点，多给例题")

    assert parsed.preference is None
    assert parsed.preference_overrides.content_depth == "detailed"
    assert parsed.preference_overrides.example_intensity == "high"
    assert parsed.generation_metadata["config_parse"]["preference_resolution"] == "unresolved"
    assert parsed.generation_metadata["config_parse"]["preference_overrides_resolution"] == "rule_guardrail"


def test_config_parse_guardrail_keeps_overall_mastery_and_local_detail() -> None:
    parsed = _assemble_config_from_goal("深入掌握整个章节，讲义详细一点")

    assert parsed.preference == "mastery"
    assert parsed.preference_overrides.content_depth == "detailed"


def test_config_parse_guardrail_supports_fast_track_with_local_detail_override() -> None:
    parsed = _assemble_config_from_goal("快速过一遍，但公式部分详细讲")

    assert parsed.preference == "fast_track"
    assert parsed.preference_overrides.content_depth == "detailed"
    assert parsed.preference_overrides.example_intensity is None


@pytest.mark.parametrize("goal_text", ["不需要详细讲", "不是考前冲刺"])
def test_config_parse_guardrail_ignores_negated_preference_signals(goal_text: str) -> None:
    parsed = _assemble_config_from_goal(goal_text)

    assert parsed.preference is None
    assert parsed.preference_overrides.content_depth is None
    assert parsed.preference_overrides.assessment_intensity is None


def test_config_parse_prompt_explains_relative_day_rules() -> None:
    prompt = study_plan_service._build_config_parse_prompt(
        course_name="计算机网络",
        payload=StudyPlanConfigParseRequest(
            goal_text="我要两天学完计网这门课的第七章节，今天是2026年7月12日",
            material_scope=MaterialScope(),
        ),
    )

    assert "reference_date:" in prompt
    assert "timezone: Asia/Shanghai" in prompt
    assert "持续 N 天时，开始日算第 1 天" in prompt
    assert "如果已知 start_date 和 duration_days，请计算 end_date" in prompt
    assert "不得计算推荐每日学习时间" in prompt
    assert "preference_overrides 用于提取局部要求" in prompt


def test_assemble_parsed_config_resolves_two_day_goal_from_explicit_today() -> None:
    parsed = _assemble_config_from_goal("我要两天学完计网这门课的第七章节，今天是2026年7月12日")

    assert parsed.start_date == date(2026, 7, 12)
    assert parsed.end_date == date(2026, 7, 13)
    assert parsed.duration_days == 2
    assert "start_date" not in parsed.unresolved_fields
    assert "duration_days" not in parsed.unresolved_fields

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
    assert request.client_flow == "legacy"
    assert request.preference == "sprint"
    assert request.diagnostic_profile["question_version"] == "study_plan_diagnostic_v1"
    assert request.tasks is None



def test_save_request_accepts_wizard_v1_client_flow_without_changing_task_optional_contract() -> None:
    request = StudyPlanSaveRequest.model_validate(
        {
            "client_flow": "wizard_v1",
            "goal_text": "我要两天学完计网这门课的第七章节",
            "start_date": "2026-07-12",
            "duration_days": 2,
            "daily_available_minutes": 60,
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        }
    )

    assert request.client_flow == "wizard_v1"
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





def test_capacity_marks_over_capacity_when_any_day_exceeds_daily_minutes() -> None:
    capacity = study_plan_service._build_capacity_summary(
        estimated_total_minutes=100,
        available_total_minutes=120,
        daily_over_capacity=True,
    )

    assert capacity["feasibility_status"] == "over_capacity"
    assert capacity["warnings"] == ["PLAN_OVER_CAPACITY"]
def test_normalizes_quiz_subtasks_to_day_end() -> None:
    task = StudyTaskPreview(
        title="第一天任务",
        task_date=date(2026, 7, 13),
        sort_order=1,
        subtasks=[
            StudySubTaskPreview(
                title="阶段自测",
                subtask_type="quiz",
                related_material_ids=["mat_net"],
                estimated_minutes=20,
                citation_chunk_ids=["chk_001"],
                sort_order=1,
            ),
            StudySubTaskPreview(
                title="公式复习",
                subtask_type="review",
                related_material_ids=["mat_net"],
                estimated_minutes=30,
                citation_chunk_ids=["chk_001"],
                sort_order=2,
            ),
        ],
    )

    normalized = study_plan_service._normalize_quiz_subtasks_to_day_end([task])

    assert [subtask.subtask_type for subtask in normalized[0].subtasks] == ["review", "quiz"]
    assert [subtask.sort_order for subtask in normalized[0].subtasks] == [1, 2]
def test_enriches_quiz_subtask_generation_parameters_from_task_text() -> None:
    task = StudyTaskPreview(
        title="第二天综合测试",
        task_date=date(2026, 7, 13),
        sort_order=1,
        subtasks=[
            StudySubTaskPreview(
                title="物理层综合测试",
                subtask_type="test",
                description="完成 10 道选择题和 3 道计算题，覆盖 Nyquist/Shannon 公式。",
                related_material_ids=["mat_net"],
                estimated_minutes=90,
                citation_chunk_ids=["chk_001"],
                sort_order=1,
            )
        ],
    )

    enriched = study_plan_service._with_subtask_generation_parameters([task])

    params = enriched[0].subtasks[0].generation_parameters["task_test"]
    assert params == {
        "question_count": 13,
        "question_types": ["single_choice", "short_answer"],
        "question_type_counts": [
            {"question_type": "single_choice", "question_count": 10},
            {"question_type": "short_answer", "question_count": 3},
        ],
        "difficulty": "medium",
    }




def test_normalizes_model_question_type_count_generation_parameters() -> None:
    task = StudyTaskPreview(
        title="第二天综合测试",
        task_date=date(2026, 7, 13),
        sort_order=1,
        subtasks=[
            StudySubTaskPreview(
                title="物理层综合测试",
                subtask_type="test",
                description="包括10道选择题和3道计算题。",
                related_material_ids=["mat_net"],
                estimated_minutes=90,
                citation_chunk_ids=["chk_001"],
                generation_parameters={"task_test": {"single_choice": 10, "short_answer": 3, "question_count": 13}},
                sort_order=1,
            )
        ],
    )

    enriched = study_plan_service._with_subtask_generation_parameters([task])

    assert enriched[0].subtasks[0].generation_parameters["task_test"] == {
        "question_count": 13,
        "question_types": ["single_choice", "short_answer"],
        "question_type_counts": [
            {"question_type": "single_choice", "question_count": 10},
            {"question_type": "short_answer", "question_count": 3},
        ],
        "difficulty": "medium",
    }


def test_normalizes_model_question_type_list_generation_parameters() -> None:
    task = StudyTaskPreview(
        title="第二天综合测试",
        task_date=date(2026, 7, 13),
        sort_order=1,
        subtasks=[
            StudySubTaskPreview(
                title="最终测试：10道选择题和3道计算题",
                subtask_type="test",
                description="10道选择题覆盖物理层功能；3道计算题应用Nyquist/Shannon公式。",
                related_material_ids=["mat_net"],
                estimated_minutes=90,
                citation_chunk_ids=["chk_001"],
                generation_parameters={
                    "task_test": [
                        {"question_count": 10, "question_type": "single_choice"},
                        {"question_count": 3, "question_type": "short_answer"},
                    ]
                },
                sort_order=1,
            )
        ],
    )

    enriched = study_plan_service._with_subtask_generation_parameters([task])

    assert enriched[0].subtasks[0].generation_parameters["task_test"] == {
        "question_count": 13,
        "question_types": ["single_choice", "short_answer"],
        "question_type_counts": [
            {"question_type": "single_choice", "question_count": 10},
            {"question_type": "short_answer", "question_count": 3},
        ],
        "difficulty": "medium",
    }


def test_normalizes_model_question_label_map_generation_parameters() -> None:
    task = StudyTaskPreview(
        title="第二天综合测试",
        task_date=date(2026, 7, 13),
        sort_order=1,
        subtasks=[
            StudySubTaskPreview(
                title="最终测试：10道选择题和3道计算题",
                subtask_type="test",
                description="10道选择题覆盖物理层功能；3道计算题应用Nyquist/Shannon公式。",
                related_material_ids=["mat_net"],
                estimated_minutes=90,
                citation_chunk_ids=["chk_001"],
                generation_parameters={"task_test": {"10道选择题": "single_choice", "3道计算题": "short_answer"}},
                sort_order=1,
            )
        ],
    )

    enriched = study_plan_service._with_subtask_generation_parameters([task])

    assert enriched[0].subtasks[0].generation_parameters["task_test"] == {
        "question_count": 13,
        "question_types": ["single_choice", "short_answer"],
        "question_type_counts": [
            {"question_type": "single_choice", "question_count": 10},
            {"question_type": "short_answer", "question_count": 3},
        ],
        "difficulty": "medium",
    }

def test_normalizes_model_question_type_objects_generation_parameters() -> None:
    task = StudyTaskPreview(
        title="第二天综合测试",
        task_date=date(2026, 7, 13),
        sort_order=1,
        subtasks=[
            StudySubTaskPreview(
                title="最终测试：10道选择题和3道计算题",
                subtask_type="test",
                description="10道选择题覆盖物理层功能；3道计算题应用Nyquist/Shannon公式。",
                related_material_ids=["mat_net"],
                estimated_minutes=90,
                citation_chunk_ids=["chk_001"],
                generation_parameters={
                    "task_test": {
                        "question_types": [
                            {"type": "single_choice", "count": 10},
                            {"type": "short_answer", "count": 3},
                        ],
                        "total_question_count": 13,
                    }
                },
                sort_order=1,
            )
        ],
    )

    enriched = study_plan_service._with_subtask_generation_parameters([task])

    assert enriched[0].subtasks[0].generation_parameters["task_test"] == {
        "question_count": 13,
        "question_types": ["single_choice", "short_answer"],
        "question_type_counts": [
            {"question_type": "single_choice", "question_count": 10},
            {"question_type": "short_answer", "question_count": 3},
        ],
        "difficulty": "medium",
    }

def test_normalizes_model_items_generation_parameters() -> None:
    task = StudyTaskPreview(
        title="第二天综合测试",
        task_date=date(2026, 7, 13),
        sort_order=1,
        subtasks=[
            StudySubTaskPreview(
                title="最终测试：10道选择题和3道计算题",
                subtask_type="test",
                description="10道选择题覆盖物理层功能；3道计算题应用Nyquist/Shannon公式。",
                related_material_ids=["mat_net"],
                estimated_minutes=90,
                citation_chunk_ids=["chk_001"],
                generation_parameters={
                    "task_test": {
                        "items": [
                            {"question_type": "single_choice", "question_count": 10},
                            {"question_type": "short_answer", "question_count": 3},
                        ]
                    }
                },
                sort_order=1,
            )
        ],
    )

    enriched = study_plan_service._with_subtask_generation_parameters([task])

    assert enriched[0].subtasks[0].generation_parameters["task_test"] == {
        "question_count": 13,
        "question_types": ["single_choice", "short_answer"],
        "question_type_counts": [
            {"question_type": "single_choice", "question_count": 10},
            {"question_type": "short_answer", "question_count": 3},
        ],
        "difficulty": "medium",
    }


def test_rejects_conflicting_question_type_count_generation_parameters() -> None:
    task = StudyTaskPreview(
        title="第二天综合测试",
        task_date=date(2026, 7, 13),
        sort_order=1,
        subtasks=[
            StudySubTaskPreview(
                title="物理层综合测试",
                subtask_type="test",
                description="完成测试题。",
                related_material_ids=["mat_net"],
                estimated_minutes=90,
                citation_chunk_ids=["chk_001"],
                generation_parameters={
                    "task_test": {
                        "question_count": 12,
                        "question_type_counts": [
                            {"question_type": "single_choice", "question_count": 10},
                            {"question_type": "short_answer", "question_count": 3},
                        ],
                    }
                },
                sort_order=1,
            )
        ],
    )

    with pytest.raises(CourseNexusError) as exc_info:
        study_plan_service._with_subtask_generation_parameters([task])

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.details["field"] == "generation_parameters.task_test"


def test_rejects_invalid_quiz_subtask_generation_parameters() -> None:
    task = StudyTaskPreview(
        title="第二天综合测试",
        task_date=date(2026, 7, 13),
        sort_order=1,
        subtasks=[
            StudySubTaskPreview(
                title="物理层综合测试",
                subtask_type="test",
                description="完成测试题。",
                related_material_ids=["mat_net"],
                estimated_minutes=90,
                citation_chunk_ids=["chk_001"],
                generation_parameters={"task_test": {"question_count": 0}},
                sort_order=1,
            )
        ],
    )

    with pytest.raises(CourseNexusError) as exc_info:
        study_plan_service._with_subtask_generation_parameters([task])

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.details["field"] == "generation_parameters.task_test"
