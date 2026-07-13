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
from app.main import app
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.models import Course
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generation.generators.handout.schemas import HandoutContent
from app.modules.generation.generators.task_test.schemas import TaskTestContent
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.learning_execution import router as learning_router
from app.modules.learning_execution.service import (
    _reduce_task_content_outputs,
    generate_handout_for_subtask,
    generate_task_test_for_subtask,
)
from app.modules.materials.models import CourseMaterial, MaterialChunk
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
        structured_outputs={
            HandoutContent: {
                "overview": "学习关系模型。",
                "learning_objectives": ["解释主键和关系"],
                "sections": [
                    {
                        "id": "sec_1",
                        "title": "主键",
                        "body": "主键用于唯一标识表中的一行。",
                        "key_points": ["唯一标识"],
                        "source_citation_ids": ["chunk_api_content"],
                        "sort_order": 1,
                    }
                ],
                "summary": "完成主键概念学习。",
            }
        }
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
        )
    )
    db.add(
        MaterialChunk(
            id="chunk_api_content",
            material_id="mat_api_content",
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
        )
    )
    db.add(
        MaterialChunk(
            id="chunk_api_content_second",
            material_id="mat_api_content_second",
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


class CountingHandoutModelProvider:
    def __init__(self, *, citation_chunk_id: str = "chunk_api_content") -> None:
        self.prompts: list[str] = []
        self.citation_chunk_id = citation_chunk_id

    def answer_question(self, *, question, context_chunks):  # pragma: no cover - unused in S06 tests
        raise AssertionError("answer_question should not be called")

    def generate_structured(self, *, prompt, output_schema):
        self.prompts.append(prompt)
        assert output_schema is HandoutContent
        return HandoutContent.model_validate(
            {
                "overview": "学习任务范围内的知识点。",
                "learning_objectives": ["解释当前任务知识点"],
                "sections": [
                    {
                        "id": "sec_1",
                        "title": "任务知识点",
                        "body": "根据任务范围生成讲义。",
                        "key_points": ["只使用任务范围内的引用"],
                        "source_citation_ids": [self.citation_chunk_id],
                        "sort_order": 1,
                    }
                ],
                "summary": "完成任务范围学习。",
            }
        )


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


def _handout_output(
    *,
    overview: str,
    summary: str,
    sections: list[dict[str, object]],
    item_citation_chunk_ids: dict[str, list[str]],
) -> GeneratorOutput:
    return GeneratorOutput(
        title="今日讲义",
        content_json={
            "overview": overview,
            "learning_objectives": ["解释主键和外键"],
            "sections": sections,
            "summary": summary,
        },
        item_citation_chunk_ids=item_citation_chunk_ids,
    )


def test_reduce_handout_outputs_preserves_section_citation_bindings_after_reindex() -> None:
    first_output = _handout_output(
        overview="学习数据库约束。",
        summary="完成主键和外键学习。",
        sections=[
            {
                "id": "sec_primary_key",
                "title": "主键",
                "body": "主键用于唯一标识表中的一行。",
                "key_points": ["唯一标识"],
                "source_citation_ids": ["chunk_primary"],
                "sort_order": 1,
            },
            {
                "id": "sec_foreign_key",
                "title": "外键",
                "body": "外键用于表达两个表之间的关系。",
                "key_points": ["表间关系"],
                "source_citation_ids": ["chunk_foreign"],
                "sort_order": 2,
            },
        ],
        item_citation_chunk_ids={
            "sec_primary_key": ["chunk_primary"],
            "sec_foreign_key": ["chunk_foreign"],
        },
    )
    second_output = _handout_output(
        overview="学习索引。",
        summary="完成索引学习。",
        sections=[
            {
                "id": "sec_index",
                "title": "索引",
                "body": "索引用于提高查询效率。",
                "key_points": ["提高查询效率"],
                "source_citation_ids": ["chunk_index", "chunk_index"],
                "sort_order": 1,
            }
        ],
        item_citation_chunk_ids={},
    )

    reduced = _reduce_task_content_outputs(content_type="handout", outputs=[first_output, second_output])

    assert [section["id"] for section in reduced.content_json["sections"]] == ["sec_1", "sec_2", "sec_3"]
    assert reduced.item_citation_chunk_ids == {
        "sec_1": ["chunk_primary"],
        "sec_2": ["chunk_foreign"],
        "sec_3": ["chunk_index"],
    }


def _v2_handout_output(*, section_id: str, section_title: str, chunk_id: str, latex: str) -> GeneratorOutput:
    return GeneratorOutput(
        title="结构化讲义",
        content_json={
            "schema_version": 2,
            "title": "结构化讲义",
            "overview": "围绕信道容量建立公式和直觉。",
            "difficulty": "medium",
            "estimated_minutes": 40,
            "learning_objectives": ["区分 Nyquist 和 Shannon 公式"],
            "prerequisites": [],
            "sections": [
                {
                    "id": section_id,
                    "title": section_title,
                    "lead": "先说结论。",
                    "source_citation_ids": [chunk_id],
                    "blocks": [
                        {
                            "type": "formula",
                            "title": "Shannon 公式",
                            "latex": latex,
                            "purpose": "计算理论最大数据率。",
                            "variables": [{"symbol": "C", "meaning": "最大数据率", "unit": "bps"}],
                            "conditions": ["有噪声信道"],
                            "limitations": ["理论上限"],
                            "source_citation_ids": [chunk_id],
                        }
                    ],
                    "key_points": ["按条件选公式。"],
                    "sort_order": 1,
                }
            ],
            "knowledge_map": None,
            "formula_cards": [],
            "exam_focus": [],
            "self_check": [],
            "summary": "按条件选公式。",
        },
        item_citation_chunk_ids={section_id: [chunk_id]},
    )


def test_reduce_handout_outputs_preserves_v2_blocks_and_schema() -> None:
    reduced = _reduce_task_content_outputs(
        content_type="handout",
        outputs=[
            _v2_handout_output(section_id="sec_a", section_title="Shannon", chunk_id="chunk_primary", latex="C = W"),
            _v2_handout_output(section_id="sec_b", section_title="Nyquist", chunk_id="chunk_secondary", latex="C = 2B"),
        ],
    )

    assert reduced.content_json["schema_version"] == 2
    assert [section["id"] for section in reduced.content_json["sections"]] == ["sec_1", "sec_2"]
    assert reduced.content_json["sections"][0]["blocks"][0]["type"] == "formula"
    assert reduced.item_citation_chunk_ids == {"sec_1": ["chunk_primary"], "sec_2": ["chunk_secondary"]}


def test_generate_handout_binds_v2_section_and_block_citations(api: ApiHarness) -> None:
    class StructuredHandoutModelProvider:
        def answer_question(self, *, question, context_chunks):  # pragma: no cover - unused in S06 tests
            raise AssertionError("answer_question should not be called")

        def generate_structured(self, *, prompt, output_schema):
            assert output_schema is HandoutContent
            return HandoutContent.model_validate(
                {
                    "schema_version": 2,
                    "title": "结构化讲义",
                    "overview": "围绕信道容量建立公式和直觉。",
                    "difficulty": "medium",
                    "estimated_minutes": 40,
                    "learning_objectives": ["区分 Nyquist 和 Shannon 公式"],
                    "prerequisites": [],
                    "sections": [
                        {
                            "id": "sec_1",
                            "title": "Shannon 公式",
                            "lead": "先说结论。",
                            "source_citation_ids": ["chunk_api_content"],
                            "blocks": [
                                {
                                    "type": "formula",
                                    "title": "Shannon 公式",
                                    "latex": "C = W \\\\log_2(1 + S/N)",
                                    "purpose": "计算理论最大数据率。",
                                    "variables": [{"symbol": "C", "meaning": "最大数据率", "unit": "bps"}],
                                    "conditions": ["有噪声信道"],
                                    "limitations": ["理论上限"],
                                    "source_citation_ids": ["chunk_api_content_second"],
                                }
                            ],
                            "key_points": ["按条件选公式。"],
                            "sort_order": 1,
                        }
                    ],
                    "knowledge_map": None,
                    "formula_cards": [],
                    "exam_focus": [],
                    "self_check": [],
                    "summary": "按条件选公式。",
                }
            )

    user_id, _ = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")
    _add_related_material_with_chunk(api.db, user_id=user_id, subtask_id=subtask_id)

    result = generate_handout_for_subtask(
        api.db,
        user_id=user_id,
        subtask_id=subtask_id,
        parameters={"language": "zh-CN"},
        force_regenerate=True,
        model_provider=StructuredHandoutModelProvider(),
        max_tokens=10_000,
    )

    section = result.content_json["sections"][0]
    block = section["blocks"][0]
    assert len(section["source_citation_ids"]) == 1
    assert len(block["source_citation_ids"]) == 1
    assert section["source_citation_ids"] != block["source_citation_ids"]
    assert all(citation_id.startswith("cit_") for citation_id in section["source_citation_ids"])
    assert all(citation_id.startswith("cit_") for citation_id in block["source_citation_ids"])
    assert "chunk_api_content" not in str(result.content_json)
    assert "chunk_api_content_second" not in str(result.content_json)
    citations = api.db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == result.id)).scalars().all()
    assert {citation.chunk_id for citation in citations} == {"chunk_api_content", "chunk_api_content_second"}


def test_generate_handout_for_learn_subtask_saves_content_and_citations(api: ApiHarness) -> None:
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
    assert data["content_json"]["overview"] == "学习关系模型。"
    content = api.db.get(AIGeneratedContent, data["id"])
    assert content is not None
    assert content.study_subtask_id == subtask_id
    citations = api.db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == data["id"])).scalars().all()
    assert [citation.chunk_id for citation in citations] == ["chunk_api_content"]


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
    assert data["content_json"]["questions"][0]["question_type"] == "single_choice"


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
    assert [citation.chunk_id for citation in citations] == ["chunk_api_content"]


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
def test_generate_handout_schema_invalid_saves_failed_record(api: ApiHarness) -> None:
    user_id, headers = _register_and_headers(api)
    subtask_id = _seed_task_content_plan(api.db, user_id=user_id, subtask_type="learn")
    app.dependency_overrides[learning_router.get_handout_model_provider] = lambda: MockModelProvider(
        structured_outputs={
            HandoutContent: {
                "overview": "学习关系模型。",
                "learning_objectives": ["解释主键"],
                "sections": [
                    {
                        "id": "sec_1",
                        "title": "主键",
                        "body": "主键用于唯一标识表中的一行。",
                        "key_points": ["唯一标识"],
                        "source_citation_ids": ["chunk_not_in_context"],
                        "sort_order": 1,
                    }
                ],
                "summary": "完成主键概念学习。",
            }
        }
    )

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
