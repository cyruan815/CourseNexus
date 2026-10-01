from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.core.errors import CourseNexusError
from app.db.base import Base
from app.db.session import get_db
import app.db.models  # noqa: F401
from app.integrations.model_provider.mock import MockModelProvider
from tests.fixtures.study_mode_samples import SAFE_HANDOUT_SVG, handout_markdown
from app.main import app
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.models import Course
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generation.generators.task_test.schemas import TaskTestContent
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.learning_execution import router as learning_router
from app.modules.learning_execution.service import (
    _bind_source_citation_ids,
    _merge_task_test_parameters,
    _reduce_task_content_outputs,
    generate_handout_for_subtask,
    generate_task_test_for_subtask,
)
from app.modules.materials.models import CourseMaterial, MaterialChunk, MaterialParseVersion
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask
from app.modules.users.models import User


@dataclass(frozen=True)
class ApiHarness:
    client: TestClient
    db: Session


@pytest.fixture()
def api() -> Generator[ApiHarness, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = testing_session()

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[learning_router.get_handout_model_provider] = lambda: MockModelProvider(
        text_outputs=[handout_markdown(title="主键讲义", body="主键用于唯一标识表中的一行。")]
    )
    app.dependency_overrides[learning_router.get_task_test_model_provider] = lambda: MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [
                    {
                        "id": "q_1",
                        "question_type": "single_choice",
                        "question_text": "主键的作用是什么？",
                        "options": [{"id": "A", "text": "唯一标识一行"}, {"id": "B", "text": "存储图片"}, {"id": "C", "text": "表达外键"}, {"id": "D", "text": "删除数据"}],
                        "correct_answer": "A",
                        "explanation": "主键用于唯一标识表中的一行。",
                        "source_citation_ids": ["chunk_api_content"],
                        "sort_order": 1,
                    }
                ],
            }
        }
    )
    try:
        yield ApiHarness(client=TestClient(app), db=session)
    finally:
        app.dependency_overrides.clear()
        session.close()


def _register_and_headers(api: ApiHarness) -> tuple[str, dict[str, str]]:
    return _register_user_and_headers(api, username="alice")


def _register_user_and_headers(api: ApiHarness, *, username: str) -> tuple[str, dict[str, str]]:
    response = api.client.post("/api/v1/auth/register", json={"username": username, "password": "password123"})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    user_id = api.db.execute(select(User).where(User.username == username)).scalar_one().id
    return user_id, {"Authorization": f"Bearer {token}"}


def _seed_task_content_plan(
    db: Session,
    *,
    user_id: str,
    subtask_type: str,
    material_ids: list[str] | None = None,
) -> str:
    db.add(Course(id="crs_api_content", user_id=user_id, name="数据库", status="active"))
    db.add(
        CourseMaterial(
            id="mat_api_content",
            user_id=user_id,
            course_id="crs_api_content",
            name="数据库讲义.pdf",
            material_type="pdf",
            source_type="file",
            file_url="/uploads/db.pdf",
            parse_status="parsed",
            active_parse_version_id="mpv_api_content",
        )
    )
    db.add(
        MaterialParseVersion(
            id="mpv_api_content",
            material_id="mat_api_content",
            course_id="crs_api_content",
            user_id=user_id,
            status="active",
            parse_quality="complete",
        )
    )
    db.add(
        MaterialChunk(
            id="chunk_api_content",
            material_id="mat_api_content",
            parse_version_id="mpv_api_content",
            course_id="crs_api_content",
            chunk_index=0,
            page="1",
            page_index=0,
            heading="主键",
            content_text="主键用于唯一标识表中的一行。",
        )
    )
    db.add(
        StudyPlan(
            id="sp_api_content",
            user_id=user_id,
            course_id="crs_api_content",
            title="数据库计划",
            goal_text="学习数据库",
            parsed_config_json={},
            start_date=date(2026, 7, 12),
            end_date=date(2026, 7, 12),
            daily_available_minutes=60,
            status="active",
        )
    )
    db.add(
        StudyTask(
            id="task_api_content",
            plan_id="sp_api_content",
            course_id="crs_api_content",
            title="学习主键",
            task_date=date(2026, 7, 12),
            status="not_started",
            sort_order=1,
        )
    )
    subtask_id = f"sub_api_content_{subtask_type}"
    db.add(
        StudySubTask(
            id=subtask_id,
            task_id="task_api_content",
            plan_id="sp_api_content",
            course_id="crs_api_content",
            title="任务内容",
            subtask_type=subtask_type,
            description="生成任务内容",
            related_material_ids_json=["mat_api_content"] if material_ids is None else material_ids,
            status="not_started",
            sort_order=1,
        )
    )
    db.commit()
    return subtask_id


def _add_related_material_without_chunks(db: Session, *, user_id: str, subtask_id: str) -> None:
    db.add(
        CourseMaterial(
            id="mat_api_content_empty",
            user_id=user_id,
            course_id="crs_api_content",
            name="空资料.pdf",
            material_type="pdf",
            source_type="file",
            file_url="/uploads/empty.pdf",
            parse_status="parsed",
            active_parse_version_id="mpv_api_content_empty",
        )
    )
    db.add(
        MaterialParseVersion(
            id="mpv_api_content_empty",
            material_id="mat_api_content_empty",
            course_id="crs_api_content",
            user_id=user_id,
            status="active",
        )
    )
    subtask = db.get(StudySubTask, subtask_id)
    assert subtask is not None
    subtask.related_material_ids_json = ["mat_api_content", "mat_api_content_empty"]
    db.add(subtask)
    db.commit()


def _add_related_material_with_chunk(db: Session, *, user_id: str, subtask_id: str) -> None:
    db.add(
        CourseMaterial(
            id="mat_api_content_second",
            user_id=user_id,
            course_id="crs_api_content",
            name="索引讲义.pdf",
            material_type="pdf",
            source_type="file",
            file_url="/uploads/index.pdf",
            parse_status="parsed",
            active_parse_version_id="mpv_api_content_second",
        )
    )
    db.add(
        MaterialParseVersion(
            id="mpv_api_content_second",
            material_id="mat_api_content_second",
            course_id="crs_api_content",
            user_id=user_id,
            status="active",
            parse_quality="complete",
        )
    )
    db.add(
        MaterialChunk(
            id="chunk_api_content_second",
            material_id="mat_api_content_second",
            parse_version_id="mpv_api_content_second",
            course_id="crs_api_content",
            chunk_index=0,
            page="2",
            page_index=1,
            heading="索引",
            content_text="索引用于提高查询效率。",
        )
    )
    subtask = db.get(StudySubTask, subtask_id)
    assert subtask is not None
    subtask.related_material_ids_json = ["mat_api_content", "mat_api_content_second"]
    db.add(subtask)
    db.commit()


def _set_plan_subtask_citation_scope(db: Session, *, citation_chunk_ids: object) -> None:
    plan = db.get(StudyPlan, "sp_api_content")
    assert plan is not None
    plan.parsed_config_json = {
        "task_snapshot": [
            {
                "sort_order": 1,
                "subtasks": [
                    {
                        "sort_order": 1,
                        "citation_chunk_ids": citation_chunk_ids,
                    }
                ],
            }
        ]
    }
    db.add(plan)
    db.commit()


def _set_stored_task_test_generation_parameters(db: Session, *, parameters: dict[str, object]) -> None:
    plan = db.get(StudyPlan, "sp_api_content")
    assert plan is not None
    plan.parsed_config_json = {
        "task_snapshot": [
            {
                "sort_order": 1,
                "subtasks": [
                    {
                        "sort_order": 1,
                        "generation_parameters": {"task_test": parameters},
                    }
                ],
            }
        ]
    }
    db.add(plan)
    db.commit()

class CountingHandoutModelProvider:
    def __init__(self, *, markdown: str | None = None) -> None:
        self.prompts: list[str] = []
        # 讲义生成契约要求至少一张安全内联 SVG 图示，默认样本必须自带。
        self.markdown = markdown if markdown is not None else handout_markdown(
            title="任务知识点讲义", body="根据任务范围生成讲义。"
        )

    def answer_question(self, *, question, context_chunks):  # pragma: no cover - unused in S06 tests
        raise AssertionError("answer_question should not be called")

    def generate_text(self, *, prompt):
        self.prompts.append(prompt)
        return self.markdown

    def generate_structured(self, *, prompt, output_schema):  # pragma: no cover - handout no longer uses structured output
        raise AssertionError("generate_structured should not be called for handout")


class CountingTaskTestModelProvider:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def answer_question(self, *, question, context_chunks):  # pragma: no cover - unused in S06 tests
        raise AssertionError("answer_question should not be called")

    def generate_structured(self, *, prompt, output_schema):
        self.prompts.append(prompt)
        assert output_schema is TaskTestContent
        return TaskTestContent.model_validate(
            {
                "instructions": "完成下列题目。",
                "questions": [
                    {
                        "id": "q_1",
                        "question_type": "single_choice",
                        "question_text": "主键的作用是什么？",
                        "options": [{"id": "A", "text": "唯一标识一行"}, {"id": "B", "text": "存储图片"}, {"id": "C", "text": "表达外键"}, {"id": "D", "text": "删除数据"}],
                        "correct_answer": "A",
                        "explanation": "主键用于唯一标识表中的一行。",
                        "source_citation_ids": ["chunk_api_content"],
                        "sort_order": 1,
                    },
                    {
                        "id": "q_2",
                        "question_type": "single_choice",
                        "question_text": "索引的作用是什么？",
                        "options": [{"id": "A", "text": "提高查询效率"}, {"id": "B", "text": "删除主键"}, {"id": "C", "text": "降低查询效率"}, {"id": "D", "text": "清空数据"}],
                        "correct_answer": "A",
                        "explanation": "索引用于提高查询效率。",
                        "source_citation_ids": ["chunk_api_content_second"],
                        "sort_order": 2,
                    },
                ],
            }
        )


class FlexibleTaskTestModelProvider:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def answer_question(self, *, question, context_chunks):  # pragma: no cover - unused in S06 tests
        raise AssertionError("answer_question should not be called")

    def generate_structured(self, *, prompt, output_schema):
        self.prompts.append(prompt)
        assert output_schema is TaskTestContent
        question_count = 5
        if "题数：2" in prompt:
            question_count = 2
        elif "题数：3" in prompt:
            question_count = 3
        question_type = "short_answer" if "题型：short_answer" in prompt else "single_choice"
        questions = []
        for index in range(1, question_count + 1):
            if question_type == "short_answer":
                questions.append(
                    {
                        "id": f"q_{index}",
                        "question_type": "short_answer",
                        "question_text": f"请简述主键的作用 {index}。",
                        "options": [],
                        "correct_answer": "主键用于唯一标识表中的一行。",
                        "explanation": "主键用于唯一标识表中的一行。",
                        "source_citation_ids": ["chunk_api_content"],
                        "sort_order": index,
                    }
                )
            else:
                questions.append(
                    {
                        "id": f"q_{index}",
                        "question_type": "single_choice",
                        "question_text": f"主键的作用是什么 {index}？",
                        "options": [
                            {"id": "A", "text": "唯一标识一行"},
                            {"id": "B", "text": "存储图片"},
                            {"id": "C", "text": "表达外键"},
                            {"id": "D", "text": "删除数据"},
                        ],
                        "correct_answer": "A",
                        "explanation": "主键用于唯一标识表中的一行。",
                        "source_citation_ids": ["chunk_api_content"],
                        "sort_order": index,
                    }
                )
        return TaskTestContent.model_validate({"instructions": "完成下列题目。", "questions": questions})

class BrokenModelProvider:
    def answer_question(self, *, question, context_chunks):  # pragma: no cover - unused in S06 tests
        raise AssertionError("answer_question should not be called")

    def generate_structured(self, *, prompt, output_schema):
        raise RuntimeError("model unavailable")


def _successful_contents(db: Session, *, subtask_id: str, content_type: str) -> list[AIGeneratedContent]:
    return list(
        db.execute(
            select(AIGeneratedContent)
            .where(
                AIGeneratedContent.study_subtask_id == subtask_id,
                AIGeneratedContent.content_type == content_type,
                AIGeneratedContent.generation_status == "success",
            )
            .order_by(AIGeneratedContent.created_at, AIGeneratedContent.id)
        ).scalars()
    )



def test_reduce_handout_outputs_synthesizes_markdown_batches() -> None:
    synthesized = handout_markdown(
        title="任务内容讲义",
        body="## 综合讲解\n\n主键和索引需要放在同一条学习线里理解。",
    )
    # ensure_handout_header 会剥掉草稿 H1，并按参数重新写入标题与来源说明。
    expected_reduced = handout_markdown(
        title="任务内容讲义",
        body=(
            "本讲义基于《数据库讲义.pdf》《索引讲义.pdf》中“任务内容”相关内容生成。\n\n"
            "## 综合讲解\n\n主键和索引需要放在同一条学习线里理解。"
        ),
    )
    provider = CountingHandoutModelProvider(markdown=synthesized)

    reduced = _reduce_task_content_outputs(
        content_type="handout",
        outputs=[
            GeneratorOutput(
                title="任务内容讲义",
                content="# 第一部分\n\n主键用于唯一标识一行。",
                content_json={"format": "markdown", "schema_version": 1},
            ),
            GeneratorOutput(
                title="任务内容讲义",
                content="# 第二部分\n\n索引用于提高查询效率。",
                content_json={"format": "markdown", "schema_version": 1},
            ),
        ],
        model_provider=provider,
        parameters={
            "handout_title": "任务内容讲义",
            "source_note": "本讲义基于《数据库讲义.pdf》《索引讲义.pdf》中“任务内容”相关内容生成。",
        },
    )

    assert len(provider.prompts) == 1
    assert "不要简单拼接" in provider.prompts[0]
    assert "批次草稿 1" in provider.prompts[0]
    assert "批次草稿 2" in provider.prompts[0]
    assert reduced.title == "任务内容讲义"
    assert reduced.content == expected_reduced
    assert reduced.content_json == {"format": "markdown", "schema_version": 1}
    assert reduced.item_citation_chunk_ids == {}


def test_reduce_handout_outputs_rejects_empty_markdown_batches() -> None:
    with pytest.raises(CourseNexusError) as exc_info:
        _reduce_task_content_outputs(
            content_type="handout",
            outputs=[GeneratorOutput(title="今日讲义", content="   ", content_json={"format": "markdown", "schema_version": 1})],
        )

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"


def test_generate_handout_for_learn_subtask_saves_markdown_content_without_citations(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")

    response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/handouts",
        headers=headers,
        json={"parameters": {"language": "zh-CN", "detail_level": "standard"}},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["content_type"] == "handout"
    assert data["study_subtask_id"] == subtask_id
    assert data["generation_status"] == "success"
    assert data["title"] == "任务内容讲义"
    expected_content = (
        "# 任务内容讲义\n\n"
        "本讲义基于《数据库讲义.pdf》中“任务内容”相关内容生成。\n\n"
        "主键用于唯一标识表中的一行。\n\n" + SAFE_HANDOUT_SVG
    )
    assert data["content"] == expected_content
    assert data["content_json"] == {"format": "markdown", "schema_version": 1}
    assert data["source_citations"] == []
    content = api.db.get(AIGeneratedContent, data["id"])
    assert content is not None
    assert content.study_subtask_id == subtask_id
    assert content.title == "任务内容讲义"
    assert content.content == expected_content
    assert content.content_json == {"format": "markdown", "schema_version": 1}
    citations = api.db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == data["id"])).scalars().all()
    assert citations == []


def test_generate_task_test_for_quiz_subtask_saves_content(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")

    response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/task-tests",
        headers=headers,
        json={"parameters": {"question_count": 1, "question_types": ["single_choice"], "difficulty": "medium"}},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["content_type"] == "task_test"
    assert data["study_subtask_id"] == subtask_id
    assert data["generation_status"] == "success"
    assert data["title"] == "任务内容测试题"
    assert data["content_json"]["questions"][0]["question_type"] == "single_choice"
    content = api.db.get(AIGeneratedContent, data["id"])
    assert content is not None
    assert content.title == "任务内容测试题"


def test_generate_task_test_multi_batch_generates_requested_question_count_once(api: ApiHarness) -> None:
    user_id, _ = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")
    _add_related_material_with_chunk(api.db, user_id=user_id, subtask_id=subtask_id)
    _set_plan_subtask_citation_scope(api.db, citation_chunk_ids=["chunk_api_content"])
    provider = CountingTaskTestModelProvider()

    result = generate_task_test_for_subtask(
        api.db,
        user_id=user_id,
        subtask_id=subtask_id,
        parameters={"question_count": 2, "question_types": ["single_choice"], "difficulty": "medium"},
        force_regenerate=True,
        model_provider=provider,
        max_tokens=1,
    )

    assert len(provider.prompts) == 1
    assert "chunk_api_content" in provider.prompts[0]
    assert "chunk_api_content_second" in provider.prompts[0]
    assert len(result.content_json["questions"]) == 2
    assert [question["id"] for question in result.content_json["questions"]] == ["q_1", "q_2"]
    citations = api.db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == result.id)).scalars().all()
    assert {citation.chunk_id for citation in citations} == {"chunk_api_content", "chunk_api_content_second"}


def test_generate_handout_uses_stored_subtask_citation_scope(api: ApiHarness) -> None:
    user_id, _ = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")
    _add_related_material_with_chunk(api.db, user_id=user_id, subtask_id=subtask_id)
    _set_plan_subtask_citation_scope(api.db, citation_chunk_ids=["chunk_api_content"])
    provider = CountingHandoutModelProvider()

    result = generate_handout_for_subtask(
        api.db,
        user_id=user_id,
        subtask_id=subtask_id,
        parameters={"language": "zh-CN", "detail_level": "standard"},
        force_regenerate=True,
        model_provider=provider,
        max_tokens=10_000,
    )

    assert len(provider.prompts) == 1
    assert "chunk_id=chunk_api_content;" in provider.prompts[0]
    assert "chunk_api_content_second" not in provider.prompts[0]
    citations = api.db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == result.id)).scalars().all()
    assert citations == []


def test_generate_handout_preserves_markdown_math_and_brackets_verbatim(api: ApiHarness) -> None:
    user_id, _ = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")
    provider = CountingHandoutModelProvider(
        markdown=handout_markdown(
            title="信噪比讲义",
            body=(
                "从 dB 转换为线性比值：\n\n"
                "[\n"
                "\\frac{S}{N} = 10^{\\frac{\\text{SNR (dB)}}{10}}\n"
                "]\n\n"
                "标准块级公式：\n\n"
                "$$\nC = B \\log_2(1 + S/N)\n$$\n\n"
                "行内公式 $C = B \\log_2(1 + S/N)$ 用来说明信道容量。"
            ),
        )
    )

    result = generate_handout_for_subtask(
        api.db,
        user_id=user_id,
        subtask_id=subtask_id,
        parameters={"language": "zh-CN", "detail_level": "standard"},
        force_regenerate=True,
        model_provider=provider,
        max_tokens=10_000,
    )

    assert "[\n\\frac{S}{N}" in result.content
    assert "$$\nC = B \\log_2(1 + S/N)\n$$" in result.content
    assert "$C = B \\log_2(1 + S/N)$" in result.content
    stored = api.db.get(AIGeneratedContent, result.id)
    assert stored is not None
    assert stored.content == result.content
    assert stored.title == "任务内容讲义"
    assert stored.content.startswith("# 任务内容讲义\n\n本讲义基于《数据库讲义.pdf》中“任务内容”相关内容生成。")

def test_generate_handout_passes_planner_and_diagnostic_context_to_prompt(api: ApiHarness) -> None:
    user_id, _ = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")
    plan = api.db.get(StudyPlan, "sp_api_content")
    assert plan is not None
    plan.parsed_config_json = {
        "diagnostic_profile": {
            "foundation_needed": True,
            "weak_area": "calculation",
            "weak_topics": ["Nyquist / Shannon 公式"],
            "diagnostic_note": "希望多讲公式怎么用。",
            "explanation_style": "step_by_step",
        },
        "generation_metadata": {
            "planner_strategy": {
                "content_depth": "detailed",
                "example_intensity": "high",
                "assessment_intensity": "high",
                "review_intensity": "standard",
            }
        },
        "task_snapshot": [
            {
                "sort_order": 1,
                "subtasks": [
                    {
                        "sort_order": 1,
                        "estimated_minutes": 45,
                        "citation_chunk_ids": ["chunk_api_content"],
                    }
                ],
            }
        ],
    }
    api.db.add(plan)
    api.db.commit()
    provider = CountingHandoutModelProvider()

    generate_handout_for_subtask(
        api.db,
        user_id=user_id,
        subtask_id=subtask_id,
        parameters={"language": "zh-CN"},
        force_regenerate=True,
        model_provider=provider,
        max_tokens=10_000,
    )

    prompt = provider.prompts[0]
    assert "课程名称：数据库" in prompt
    assert "一级任务标题：学习主键" in prompt
    assert "当前二级任务类型：learn" in prompt
    assert "预计学习时间：45 分钟" in prompt
    assert "内容深度：detailed" in prompt
    assert "例题强度：high" in prompt
    assert "测试强度：high" in prompt
    assert "复习强度：standard" in prompt
    assert "诊断薄弱方向：calculation" in prompt
    assert "薄弱知识点：Nyquist / Shannon 公式" in prompt
    assert "诊断补充说明：希望多讲公式怎么用。" in prompt
    assert "教学策略提示：加强公式变量、单位、适用条件、代入步骤和计算例题。" in prompt
    assert "建议讲解风格" not in prompt
    assert "step_by_step" not in prompt


def test_generate_handout_without_stored_citation_scope_keeps_material_scope(api: ApiHarness) -> None:
    user_id, _ = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")
    _add_related_material_with_chunk(api.db, user_id=user_id, subtask_id=subtask_id)
    provider = CountingHandoutModelProvider()

    generate_handout_for_subtask(
        api.db,
        user_id=user_id,
        subtask_id=subtask_id,
        parameters={"language": "zh-CN", "detail_level": "standard"},
        force_regenerate=True,
        model_provider=provider,
        max_tokens=10_000,
    )

    assert len(provider.prompts) == 1
    assert "chunk_id=chunk_api_content;" in provider.prompts[0]
    assert "chunk_id=chunk_api_content_second;" in provider.prompts[0]


def test_generate_handout_stored_citation_scope_without_matching_chunks_saves_failed_record(api: ApiHarness) -> None:
    user_id, _ = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")
    _add_related_material_with_chunk(api.db, user_id=user_id, subtask_id=subtask_id)
    _set_plan_subtask_citation_scope(api.db, citation_chunk_ids=["chunk_missing"])

    with pytest.raises(CourseNexusError) as exc_info:
        generate_handout_for_subtask(
            api.db,
            user_id=user_id,
            subtask_id=subtask_id,
            parameters={"language": "zh-CN", "detail_level": "standard"},
            force_regenerate=True,
            model_provider=BrokenModelProvider(),
            max_tokens=10_000,
        )

    assert exc_info.value.code == "NO_PARSED_MATERIAL"
    content = api.db.execute(select(AIGeneratedContent)).scalar_one()
    assert content.content_type == "handout"
    assert content.study_subtask_id == subtask_id
    assert content.generation_status == "failed"
    assert content.error_code == "NO_PARSED_MATERIAL"


def test_generate_handout_is_idempotent_for_existing_success(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")

    first_response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/handouts",
        headers=headers,
        json={"parameters": {"language": "zh-CN", "detail_level": "standard"}},
    )
    assert first_response.status_code == 200
    first = first_response.json()["data"]

    app.dependency_overrides[learning_router.get_handout_model_provider] = lambda: BrokenModelProvider()
    second_response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/handouts",
        headers=headers,
        json={"parameters": {"language": "zh-CN", "detail_level": "standard"}},
    )

    assert second_response.status_code == 200
    second = second_response.json()["data"]
    assert second["id"] == first["id"]
    assert [content.id for content in _successful_contents(api.db, subtask_id=subtask_id, content_type="handout")] == [first["id"]]


def test_generate_task_test_is_idempotent_for_existing_success(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")

    first_response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/task-tests",
        headers=headers,
        json={"parameters": {"question_count": 1, "question_types": ["single_choice"], "difficulty": "medium"}},
    )
    assert first_response.status_code == 200
    first = first_response.json()["data"]

    app.dependency_overrides[learning_router.get_task_test_model_provider] = lambda: BrokenModelProvider()
    second_response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/task-tests",
        headers=headers,
        json={"parameters": {"question_count": 1, "question_types": ["single_choice"], "difficulty": "medium"}},
    )

    assert second_response.status_code == 200
    second = second_response.json()["data"]
    assert second["id"] == first["id"]
    assert [content.id for content in _successful_contents(api.db, subtask_id=subtask_id, content_type="task_test")] == [first["id"]]


def test_force_regenerate_handout_creates_new_success(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")

    first_response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/handouts",
        headers=headers,
        json={"parameters": {"language": "zh-CN", "detail_level": "standard"}},
    )
    second_response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/handouts",
        headers=headers,
        json={"force_regenerate": True, "parameters": {"language": "zh-CN", "detail_level": "standard"}},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first = first_response.json()["data"]
    second = second_response.json()["data"]
    assert second["id"] != first["id"]
    assert len(_successful_contents(api.db, subtask_id=subtask_id, content_type="handout")) == 2


def test_failed_task_test_record_does_not_block_retry(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")
    app.dependency_overrides[learning_router.get_task_test_model_provider] = lambda: BrokenModelProvider()

    failed_response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/task-tests", headers=headers, json={"parameters": {}})
    assert failed_response.status_code == 502
    failed = api.db.execute(select(AIGeneratedContent)).scalar_one()
    assert failed.generation_status == "failed"

    app.dependency_overrides[learning_router.get_task_test_model_provider] = lambda: MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [
                    {
                        "id": "q_1",
                        "question_type": "single_choice",
                        "question_text": "主键的作用是什么？",
                        "options": [{"id": "A", "text": "唯一标识一行"}, {"id": "B", "text": "存储图片"}, {"id": "C", "text": "表达外键"}, {"id": "D", "text": "删除数据"}],
                        "correct_answer": "A",
                        "explanation": "主键用于唯一标识表中的一行。",
                        "source_citation_ids": ["chunk_api_content"],
                        "sort_order": 1,
                    }
                ],
            }
        }
    )
    retry_response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/task-tests",
        headers=headers,
        json={"parameters": {"question_count": 1, "question_types": ["single_choice"], "difficulty": "medium"}},
    )

    assert retry_response.status_code == 200
    retry = retry_response.json()["data"]
    assert retry["id"] != failed.id
    assert retry["generation_status"] == "success"
    assert len(_successful_contents(api.db, subtask_id=subtask_id, content_type="task_test")) == 1


@pytest.mark.parametrize("subtask_type", ["quiz", "test"])
def test_generate_handout_rejects_quiz_and_test_subtasks(api: ApiHarness, subtask_type: str) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type=subtask_type)

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/handouts", headers=headers, json={"parameters": {}})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STATE_CONFLICT"
    assert api.db.execute(select(AIGeneratedContent)).scalars().all() == []


@pytest.mark.parametrize("subtask_type", ["learn", "review"])
def test_generate_task_test_rejects_learn_and_review_subtasks(api: ApiHarness, subtask_type: str) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type=subtask_type)

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/task-tests", headers=headers, json={"parameters": {}})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "STATE_CONFLICT"
    assert api.db.execute(select(AIGeneratedContent)).scalars().all() == []


def test_generate_task_test_rejects_empty_material_scope_and_saves_failed_record(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz", material_ids=[])

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/task-tests", headers=headers, json={"parameters": {}})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "NO_PARSED_MATERIAL"
    content = api.db.execute(select(AIGeneratedContent)).scalar_one()
    assert content.content_type == "task_test"
    assert content.study_subtask_id == subtask_id
    assert content.generation_status == "failed"
    assert content.error_code == "NO_PARSED_MATERIAL"


def test_generate_task_content_requires_auth(api: ApiHarness) -> None:
    user_id, _ = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/handouts", json={"parameters": {}})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_generate_task_content_returns_not_found_for_missing_subtask(api: ApiHarness) -> None:
    _, headers = _register_and_headers(api)

    response = api.client.post("/api/v1/study-subtasks/sub_missing/handouts", headers=headers, json={"parameters": {}})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert api.db.execute(select(AIGeneratedContent)).scalars().all() == []


def test_generate_task_content_rejects_cross_user_subtask_without_failed_record(api: ApiHarness) -> None:
    alice_id, _ = _register_user_and_headers(api, username="alice")
    _, bob_headers = _register_user_and_headers(api, username="bob")
    subtask_id = _seed_task_content_plan(api.db, user_id=alice_id, subtask_type="learn")

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/handouts", headers=bob_headers, json={"parameters": {}})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert api.db.execute(select(AIGeneratedContent)).scalars().all() == []


def test_generate_task_content_rejects_invalid_request_parameters(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")

    response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/task-tests",
        headers=headers,
        json={"parameters": {"question_count": 0}},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert api.db.execute(select(AIGeneratedContent)).scalars().all() == []




def test_generate_task_test_with_stale_invalid_saved_parameters_saves_failed_record(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")
    plan = api.db.get(StudyPlan, "sp_api_content")
    assert plan is not None
    plan.parsed_config_json = {
        "task_snapshot": [
            {
                "sort_order": 1,
                "subtasks": [
                    {
                        "sort_order": 1,
                        "generation_parameters": {"task_test": {"question_count": 0}},
                    }
                ],
            }
        ]
    }
    api.db.add(plan)
    api.db.commit()

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/task-tests", headers=headers, json={"parameters": {}})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "GENERATION_SCHEMA_INVALID"
    content = api.db.execute(select(AIGeneratedContent)).scalar_one()
    assert content.content_type == "task_test"
    assert content.study_subtask_id == subtask_id
    assert content.generation_status == "failed"
    assert content.error_code == "GENERATION_SCHEMA_INVALID"
def test_generate_handout_empty_markdown_saves_failed_record(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")
    app.dependency_overrides[learning_router.get_handout_model_provider] = lambda: MockModelProvider(text_outputs=["   "])

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/handouts", headers=headers, json={"parameters": {}})

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "GENERATION_SCHEMA_INVALID"
    content = api.db.execute(select(AIGeneratedContent)).scalar_one()
    assert content.content_type == "handout"
    assert content.study_subtask_id == subtask_id
    assert content.generation_status == "failed"
    assert content.error_code == "GENERATION_SCHEMA_INVALID"


def test_generate_task_test_model_failure_saves_failed_record(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")
    app.dependency_overrides[learning_router.get_task_test_model_provider] = lambda: BrokenModelProvider()

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/task-tests", headers=headers, json={"parameters": {}})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "GENERATION_FAILED"
    content = api.db.execute(select(AIGeneratedContent)).scalar_one()
    assert content.content_type == "task_test"
    assert content.study_subtask_id == subtask_id
    assert content.generation_status == "failed"
    assert content.error_code == "GENERATION_FAILED"


def test_generate_handout_material_coverage_incomplete_saves_failed_record(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")
    _add_related_material_without_chunks(api.db, user_id=user_id, subtask_id=subtask_id)

    response = api.client.post(f"/api/v1/study-subtasks/{subtask_id}/handouts", headers=headers, json={"parameters": {}})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "MATERIAL_COVERAGE_INCOMPLETE"
    content = api.db.execute(select(AIGeneratedContent)).scalar_one()
    assert content.content_type == "handout"
    assert content.study_subtask_id == subtask_id
    assert content.generation_status == "failed"
    assert content.error_code == "MATERIAL_COVERAGE_INCOMPLETE"


def test_generate_task_test_types_alias_keeps_stored_question_count(api: ApiHarness) -> None:
    user_id, _ = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")
    _set_stored_task_test_generation_parameters(
        api.db,
        parameters={
            "question_count": 3,
            "question_types": ["single_choice"],
            "question_type_counts": [{"question_type": "single_choice", "question_count": 3}],
            "difficulty": "medium",
        },
    )
    provider = FlexibleTaskTestModelProvider()

    result = generate_task_test_for_subtask(
        api.db,
        user_id=user_id,
        subtask_id=subtask_id,
        parameters={"types": ["short_answer"]},
        force_regenerate=True,
        model_provider=provider,
        max_tokens=10_000,
    )

    assert "题数：3；题型：short_answer" in provider.prompts[0]
    assert "每种题型数量：" not in provider.prompts[0]
    assert len(result.content_json["questions"]) == 3
    assert {question["question_type"] for question in result.content_json["questions"]} == {"short_answer"}


def test_generate_task_test_types_alias_keeps_stored_question_count_via_api(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")
    _set_stored_task_test_generation_parameters(
        api.db,
        parameters={
            "question_count": 3,
            "question_types": ["single_choice"],
            "question_type_counts": [{"question_type": "single_choice", "question_count": 3}],
            "difficulty": "medium",
        },
    )
    provider = FlexibleTaskTestModelProvider()
    app.dependency_overrides[learning_router.get_task_test_model_provider] = lambda: provider

    response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/task-tests",
        headers=headers,
        json={"force_regenerate": True, "parameters": {"types": ["short_answer"]}},
    )

    assert response.status_code == 200
    assert "题数：3；题型：short_answer" in provider.prompts[0]
    assert "每种题型数量：" not in provider.prompts[0]
    questions = response.json()["data"]["content_json"]["questions"]
    assert len(questions) == 3
    assert {question["question_type"] for question in questions} == {"short_answer"}


def test_generate_task_test_questions_alias_overrides_stored_distribution(api: ApiHarness) -> None:
    user_id, _ = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")
    _set_stored_task_test_generation_parameters(
        api.db,
        parameters={
            "question_count": 3,
            "question_types": ["single_choice"],
            "question_type_counts": [{"question_type": "single_choice", "question_count": 3}],
            "difficulty": "medium",
        },
    )
    provider = FlexibleTaskTestModelProvider()

    result = generate_task_test_for_subtask(
        api.db,
        user_id=user_id,
        subtask_id=subtask_id,
        parameters={"questions": [{"type": "short_answer", "count": 2}]},
        force_regenerate=True,
        model_provider=provider,
        max_tokens=10_000,
    )

    assert "题数：2；题型：short_answer" in provider.prompts[0]
    assert "每种题型数量：short_answer 2 道" in provider.prompts[0]
    assert len(result.content_json["questions"]) == 2
    assert {question["question_type"] for question in result.content_json["questions"]} == {"short_answer"}


def test_generate_task_test_difficulty_override_keeps_stored_distribution(api: ApiHarness) -> None:
    user_id, _ = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")
    _set_stored_task_test_generation_parameters(
        api.db,
        parameters={
            "question_count": 3,
            "question_types": ["single_choice"],
            "question_type_counts": [{"question_type": "single_choice", "question_count": 3}],
            "difficulty": "medium",
        },
    )
    provider = FlexibleTaskTestModelProvider()

    result = generate_task_test_for_subtask(
        api.db,
        user_id=user_id,
        subtask_id=subtask_id,
        parameters={"difficulty": "hard"},
        force_regenerate=True,
        model_provider=provider,
        max_tokens=10_000,
    )

    assert "题数：3；题型：single_choice" in provider.prompts[0]
    assert "每种题型数量：single_choice 3 道" in provider.prompts[0]
    assert "难度：hard" in provider.prompts[0]
    assert len(result.content_json["questions"]) == 3
    assert {question["question_type"] for question in result.content_json["questions"]} == {"single_choice"}


def test_generate_task_test_conflicting_alias_parameters_return_validation_error(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="quiz")

    response = api.client.post(
        f"/api/v1/study-subtasks/{subtask_id}/task-tests",
        headers=headers,
        json={"parameters": {"types": ["short_answer"], "question_types": ["single_choice"]}},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert api.db.execute(select(AIGeneratedContent)).scalars().all() == []

def _stored_task_test_parameters_with_counts() -> dict[str, object]:
    return {
        "question_count": 13,
        "question_types": ["single_choice", "short_answer"],
        "question_type_counts": [
            {"question_type": "single_choice", "question_count": 10},
            {"question_type": "short_answer", "question_count": 3},
        ],
        "difficulty": "medium",
    }


def test_merge_task_test_parameters_keeps_stored_question_type_counts_for_difficulty_override() -> None:
    merged = _merge_task_test_parameters(
        stored_parameters=_stored_task_test_parameters_with_counts(),
        request_parameters={"difficulty": "hard"},
    )

    assert merged["question_type_counts"] == [
        {"question_type": "single_choice", "question_count": 10},
        {"question_type": "short_answer", "question_count": 3},
    ]
    assert merged["question_count"] == 13
    assert merged["difficulty"] == "hard"


def test_merge_task_test_parameters_clears_stored_question_type_counts_for_legacy_override() -> None:
    merged = _merge_task_test_parameters(
        stored_parameters=_stored_task_test_parameters_with_counts(),
        request_parameters={"question_count": 1, "question_types": ["single_choice"]},
    )

    assert "question_type_counts" not in merged
    assert merged["question_count"] == 1
    assert merged["question_types"] == ["single_choice"]


def test_merge_task_test_parameters_types_alias_keeps_stored_question_count() -> None:
    merged = _merge_task_test_parameters(
        stored_parameters=_stored_task_test_parameters_with_counts(),
        request_parameters={"types": ["short_answer"]},
    )

    assert merged == {
        "question_count": 13,
        "types": ["short_answer"],
        "difficulty": "medium",
    }


def test_merge_task_test_parameters_replaces_stored_question_type_counts_for_per_type_override() -> None:
    merged = _merge_task_test_parameters(
        stored_parameters=_stored_task_test_parameters_with_counts(),
        request_parameters={
            "question_type_counts": [{"question_type": "short_answer", "question_count": 1}],
        },
    )

    assert merged == {
        "question_type_counts": [{"question_type": "short_answer", "question_count": 1}],
        "difficulty": "medium",
    }
