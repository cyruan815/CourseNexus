from __future__ import annotations

from collections.abc import Generator
from datetime import date
from io import BytesIO
import logging
from pathlib import Path

import pytest
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import CourseNexusError
from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.material_context.schemas import MaterialScope
from app.modules.materials.models import CourseMaterial
from app.modules.materials.service import parse_material, upload_file_material
from app.modules.study_plans.schemas import StudyPlanBuildRequest
from app.modules.study_plans.service import (
    get_study_plan_detail,
    list_study_plans,
    preview_study_plan,
    save_study_plan,
)
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user


def capture_course_logs(caplog) -> logging.Logger:
    logger = logging.getLogger("course_nexus")
    logger.addHandler(caplog.handler)
    logger.setLevel(logging.INFO)
    return logger


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


class FoundationPlanProvider:
    def __init__(self, material_id: str) -> None:
        self.material_id = material_id

    def generate_structured(self, *, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        if output_schema.__name__ == "PlanBatchExtraction":
            return output_schema.model_validate(
                {
                    "units": [
                        {
                            "topic": "linear algebra topic",
                            "summary": "summary",
                            "difficulty": "medium",
                            "estimated_minutes": 30,
                            "related_material_ids": [self.material_id],
                            "citation_chunk_ids": ["chk_foundation"],
                        }
                    ],
                    "citation_chunk_ids": ["chk_foundation"],
                }
            )
        if output_schema.__name__ == "StudyPlanReduction":
            return output_schema.model_validate(
                {
                    "title": "Linear Algebra 学习计划",
                    "tasks": [
                        {
                            "title": f"第 {index + 1} 天学习任务",
                            "task_date": task_date,
                            "sort_order": index + 1,
                            "subtasks": [
                                {
                                    "title": "学习: Intro",
                                    "subtask_type": "learn",
                                    "description": "Alpha",
                                    "related_material_ids": [self.material_id],
                                    "estimated_minutes": 45,
                                    "citation_chunk_ids": ["chk_foundation"],
                                    "sort_order": 1,
                                },
                                {
                                    "title": "foundation day test",
                                    "subtask_type": "test",
                                    "description": "cover scheduled learning",
                                    "related_material_ids": [self.material_id],
                                    "estimated_minutes": 15,
                                    "citation_chunk_ids": ["chk_foundation"],
                                    "sort_order": 2,
                                }
                            ],
                        }
                        for index, task_date in enumerate(["2026-07-10", "2026-07-11", "2026-07-12"])
                    ],
                    "citation_chunk_ids": ["chk_foundation"],
                }
            )
        raise AssertionError(output_schema)




class QuantityRetryPlanProvider:
    def __init__(self, material_id: str) -> None:
        self.material_id = material_id
        self.map_prompts: list[str] = []
        self.reduce_prompts: list[str] = []

    def generate_structured(self, *, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        if output_schema.__name__ == "PlanBatchExtraction":
            self.map_prompts.append(prompt)
            return output_schema.model_validate(
                {
                    "units": [
                        {
                            "topic": "physical layer formula",
                            "summary": "summary",
                            "difficulty": "medium",
                            "estimated_minutes": 30,
                            "related_material_ids": [self.material_id],
                            "citation_chunk_ids": ["chk_foundation"],
                        }
                    ],
                    "citation_chunk_ids": ["chk_foundation"],
                }
            )
        if output_schema.__name__ == "StudyPlanReduction":
            self.reduce_prompts.append(prompt)
            learn_description = "学习公式并完成 10 道选择题" if len(self.reduce_prompts) == 1 else "学习公式含义"
            quiz_description = "完成当天自测" if len(self.reduce_prompts) == 1 else "完成 10 道选择题"
            return output_schema.model_validate(
                {
                    "title": "Linear Algebra 学习计划",
                    "tasks": [
                        {
                            "title": "第 1 天学习任务",
                            "task_date": "2026-07-10",
                            "sort_order": 1,
                            "subtasks": [
                                {
                                    "title": "学习公式",
                                    "subtask_type": "learn",
                                    "description": learn_description,
                                    "related_material_ids": [self.material_id],
                                    "estimated_minutes": 45,
                                    "citation_chunk_ids": ["chk_foundation"],
                                    "sort_order": 1,
                                },
                                {
                                    "title": "当天测试",
                                    "subtask_type": "test",
                                    "description": quiz_description,
                                    "related_material_ids": [self.material_id],
                                    "estimated_minutes": 15,
                                    "citation_chunk_ids": ["chk_foundation"],
                                    "sort_order": 2,
                                },
                            ],
                        }
                    ],
                    "citation_chunk_ids": ["chk_foundation"],
                }
            )
        raise AssertionError(output_schema)
def create_parsed_material(db: Session, tmp_path: Path, user_id: str, course_id: str, content: bytes = b"Alpha") -> str:
    material = upload_file_material(
        db,
        user_id=user_id,
        course_id=course_id,
        filename="notes.txt",
        stream=BytesIO(content),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )
    parse_material(
        db,
        user_id=user_id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=FakeRagIndex(),
        storage_root=tmp_path,
    )
    return material.id


def build_request(material_scope: MaterialScope | None = None) -> StudyPlanBuildRequest:
    return StudyPlanBuildRequest(
        goal_text="期末复习",
        start_date=date(2026, 7, 10),
        end_date=date(2026, 7, 12),
        daily_available_minutes=60,
        material_scope=material_scope or MaterialScope(),
    )


def test_preview_study_plan_uses_resolved_context(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, b"Alpha\n\nBeta")

    preview = preview_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=build_request(),
        model_provider=FoundationPlanProvider(material_id),
        max_tokens=12_000,
    )

    assert preview.course_id == course.id
    assert preview.title == "Linear Algebra 学习计划"
    assert [task.task_date for task in preview.tasks] == [date(2026, 7, 10), date(2026, 7, 11), date(2026, 7, 12)]
    assert preview.tasks[0].subtasks[0].related_material_ids == [material_id]
    assert preview.coverage.expected_material_ids == [material_id]




def test_preview_study_plan_retries_when_learn_task_contains_question_quantity(
    db: Session,
    tmp_path: Path,
) -> None:
    user = register_user(db, UserCreate(username="retry-user", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, b"Alpha\n\nBeta")
    provider = QuantityRetryPlanProvider(material_id)

    preview = preview_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=build_request(),
        model_provider=provider,
        max_tokens=12_000,
    )

    assert len(provider.map_prompts) == 1
    assert len(provider.reduce_prompts) == 2
    assert "学习或复习任务不能包含测试题量要求" in provider.reduce_prompts[1]
    assert preview.tasks[0].subtasks[0].description == "学习公式含义"
    assert preview.tasks[0].subtasks[1].description == "完成 10 道选择题"

def test_preview_study_plan_requires_parsed_material(db: Session) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))

    with pytest.raises(CourseNexusError) as exc_info:
        preview_study_plan(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=build_request(),
            model_provider=FoundationPlanProvider("mat_missing"),
            max_tokens=12_000,
        )

    assert exc_info.value.code == "NO_PARSED_MATERIAL"


def test_save_study_plan_writes_plan_tasks_and_subtasks(db: Session, tmp_path: Path, caplog) -> None:
    logger = capture_course_logs(caplog)
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, b"Alpha\n\nBeta")

    try:
        saved = save_study_plan(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=build_request(),
            model_provider=FoundationPlanProvider(material_id),
            max_tokens=12_000,
        )
    finally:
        logger.removeHandler(caplog.handler)

    assert saved.plan.course_id == course.id
    assert len(saved.tasks) == 3
    assert saved.tasks[0].course_id == course.id
    assert saved.subtasks[0].course_id == course.id
    assert saved.subtasks[0].related_material_ids_json == [material_id]
    assert saved.plan.parsed_config_json["coverage"]["expected_material_ids"] == [material_id]
    assert list_study_plans(db, user_id=user.id, course_id=course.id)[0].id == saved.plan.id
    assert get_study_plan_detail(db, user_id=user.id, plan_id=saved.plan.id).plan.id == saved.plan.id
    record = next(
        record
        for record in caplog.records
        if record.name.endswith("study_plan.build") and "计划保存成功" in record.getMessage()
    )
    assert "tasks=3" in record.getMessage()
    assert f"plan={saved.plan.id}" in record.getMessage()
    assert build_request().goal_text not in record.getMessage()


def test_study_plan_scope_rejects_cross_user_material_id(db: Session, tmp_path: Path) -> None:
    alice = register_user(db, UserCreate(username="alice", password="password123"))
    bob = register_user(db, UserCreate(username="bob", password="password123"))
    alice_course = create_course(db, alice.id, CourseCreate(name="Linear Algebra"))
    bob_course = create_course(db, bob.id, CourseCreate(name="Databases"))
    bob_material_id = create_parsed_material(db, tmp_path, bob.id, bob_course.id, b"Bob")

    with pytest.raises(CourseNexusError) as exc_info:
        preview_study_plan(
            db,
            user_id=alice.id,
            course_id=alice_course.id,
            payload=build_request(MaterialScope(include_all_parsed_materials=False, material_ids=[bob_material_id])),
            model_provider=FoundationPlanProvider(bob_material_id),
            max_tokens=12_000,
        )

    assert exc_info.value.code == "NOT_FOUND"


def test_preview_study_plan_exposes_material_quality_warnings_in_generation_metadata(
    db: Session,
    tmp_path: Path,
) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, b"Alpha\n\nBeta")
    material = db.get(CourseMaterial, material_id)
    assert material is not None
    material.parse_quality = "partial"
    material.page_count = 4
    material.parse_diagnostics_json = {
        "parser": "docling",
        "profile": "pdf_text_first",
        "conversion_status": "partial_success",
        "page_count": 4,
        "processed_pages": [1, 2, 4],
        "pages_with_content": [1, 2, 4],
        "pages_with_chunks": [1, 2],
        "failed_pages": [3],
        "warnings": [
            {
                "code": "OCR_MEMORY_ERROR",
                "message": "OCR memory limit hit",
                "page_no": 3,
                "component": "ocr",
                "severity": "warning",
            }
        ],
    }
    db.add(material)
    db.commit()

    preview = preview_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=build_request(),
        model_provider=FoundationPlanProvider(material_id),
        max_tokens=12_000,
    )

    material_quality = preview.generation_metadata["material_quality"]
    warning_codes = [warning["code"] for warning in material_quality["warnings"]]
    assert warning_codes == ["MATERIAL_PARSE_PARTIAL", "MATERIAL_PARSE_DIAGNOSTIC_WARNING"]
    assert material_quality["warnings"][0]["material_id"] == material_id
    assert material_quality["warnings"][0]["parse_quality"] == "partial"
    assert material_quality["warnings"][1]["details"]["diagnostic_code"] == "OCR_MEMORY_ERROR"
    assert preview.capacity["warnings"] == []
