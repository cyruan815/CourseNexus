from __future__ import annotations

from collections.abc import Generator
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.material_context.schemas import MaterialScope
from app.modules.materials.service import parse_material, upload_file_material
from app.modules.study_plans.models import StudyPlan
from app.modules.study_plans.schemas import (
    StudyPlanBuildRequest,
    StudyPlanConfigParseRequest,
    StudyPlanParsedConfig,
    StudyPlanReplaceRequest,
    StudyPlanSaveRequest,
    StudySubTaskPreview,
)
from app.modules.study_plans.service import parse_study_plan_config, preview_study_plan
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user


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


class ConfigParseProvider:
    def __init__(self, output: StudyPlanParsedConfig) -> None:
        self.output = output
        self.prompts: list[str] = []

    def generate_structured(self, *, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        self.prompts.append(prompt)
        return output_schema.model_validate(self.output.model_dump(mode="json"))


class RecordingPlanProvider:
    def __init__(self, material_ids: list[str]) -> None:
        self.material_ids = material_ids
        self.batch_prompts: list[str] = []
        self.reduce_prompts: list[str] = []

    def generate_structured(self, *, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        if output_schema.__name__ == "PlanBatchExtraction":
            self.batch_prompts.append(prompt)
            material_id = self.material_ids[min(len(self.batch_prompts) - 1, len(self.material_ids) - 1)]
            return output_schema.model_validate(
                {
                    "units": [
                        {
                            "topic": f"topic-{len(self.batch_prompts)}",
                            "summary": "batch summary",
                            "difficulty": "medium",
                            "estimated_minutes": 30,
                            "related_material_ids": [material_id],
                            "citation_chunk_ids": [f"chk-{len(self.batch_prompts)}"],
                        }
                    ],
                    "citation_chunk_ids": [f"chk-{len(self.batch_prompts)}"],
                }
            )
        if output_schema.__name__ == "StudyPlanReduction":
            self.reduce_prompts.append(prompt)
            return output_schema.model_validate(
                {
                    "title": "Computer Networks 学习计划",
                    "tasks": [
                        {
                            "title": "传输层集中学习",
                            "task_date": "2026-07-11",
                            "sort_order": 1,
                            "subtasks": [
                                {
                                    "title": "理解可靠传输",
                                    "subtask_type": "learn",
                                    "description": "学习滑动窗口和确认机制",
                                    "related_material_ids": self.material_ids,
                                    "estimated_minutes": 45,
                                    "citation_chunk_ids": ["chk-reduce"],
                                    "sort_order": 1,
                                },
                                {
                                    "title": "传输层自测",
                                    "subtask_type": "test",
                                    "description": "检查核心概念掌握情况",
                                    "related_material_ids": self.material_ids,
                                    "estimated_minutes": 15,
                                    "citation_chunk_ids": ["chk-reduce"],
                                    "sort_order": 2,
                                },
                            ],
                        }
                    ],
                    "citation_chunk_ids": ["chk-reduce"],
                }
            )
        raise AssertionError(output_schema)


def create_parsed_material(db: Session, tmp_path: Path, user_id: str, course_id: str, filename: str, content: bytes) -> str:
    material = upload_file_material(
        db,
        user_id=user_id,
        course_id=course_id,
        filename=filename,
        stream=BytesIO(content),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=4096),
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


def _subtask(**overrides: object) -> StudySubTaskPreview:
    data = {
        "title": "理解滑动窗口",
        "subtask_type": "learn",
        "description": "学习窗口推进、确认与重传关系",
        "related_material_ids": ["mat_1"],
        "estimated_minutes": 30,
        "citation_chunk_ids": ["chk_1"],
        "sort_order": 1,
    }
    data.update(overrides)
    return StudySubTaskPreview.model_validate(data)


def test_config_parse_schema_returns_unresolved_fields() -> None:
    request = StudyPlanConfigParseRequest.model_validate(
        {
            "goal_text": "从 2026-07-11 到 2026-07-24，每天 60 分钟精通传输层",
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        }
    )
    parsed = StudyPlanParsedConfig.model_validate(
        {
            "goal_text": "精通传输层",
            "start_date": None,
            "end_date": None,
            "daily_available_minutes": 60,
            "preference": "mastery",
            "material_scope": request.material_scope.model_dump(mode="json"),
            "unresolved_fields": ["start_date", "end_date"],
        }
    )

    assert parsed.unresolved_fields == ["start_date", "end_date"]
    assert parsed.material_scope.include_all_parsed_materials is True


def test_subtask_preview_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        _subtask(subtask_type="watch")


def test_subtask_preview_requires_positive_minutes() -> None:
    with pytest.raises(ValidationError):
        _subtask(estimated_minutes=0)


def test_save_request_accepts_old_body_without_tasks() -> None:
    request = StudyPlanSaveRequest.model_validate(
        {
            "goal_text": "两周掌握传输层",
            "start_date": "2026-07-11",
            "end_date": "2026-07-24",
            "daily_available_minutes": 60,
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
        }
    )

    assert request.tasks is None
    assert request.preference == "balanced"


def test_replace_request_requires_tasks() -> None:
    with pytest.raises(ValidationError):
        StudyPlanReplaceRequest.model_validate(
            {
                "expected_updated_at": datetime.now(timezone.utc).isoformat(),
                "title": "传输层冲刺计划",
                "goal_text": "掌握传输层",
                "start_date": "2026-07-11",
                "end_date": "2026-07-20",
                "daily_available_minutes": 60,
                "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
                "tasks": [],
            }
        )


def test_parse_config_returns_model_fields_without_writing_db(db: Session) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    provider = ConfigParseProvider(
        StudyPlanParsedConfig(
            goal_text="精通传输层",
            start_date=None,
            end_date=None,
            daily_available_minutes=60,
            preference="mastery",
            unresolved_fields=["start_date", "end_date"],
        )
    )
    before_count = db.scalar(select(func.count()).select_from(StudyPlan))

    parsed = parse_study_plan_config(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=StudyPlanConfigParseRequest(
            goal_text="从 2026-07-11 到 2026-07-24，每天 60 分钟精通传输层",
            material_scope={"include_all_parsed_materials": True, "material_ids": []},
        ),
        model_provider=provider,
    )

    assert parsed.goal_text == "精通传输层"
    assert parsed.daily_available_minutes == 60
    assert parsed.preference == "mastery"
    assert parsed.unresolved_fields == ["start_date", "end_date"]
    assert parsed.material_scope.include_all_parsed_materials is True
    assert db.scalar(select(func.count()).select_from(StudyPlan)) == before_count
    assert provider.prompts


def test_preview_study_plan_processes_all_material_batches_without_writing_db(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_ids = [
        create_parsed_material(db, tmp_path, user.id, course.id, "transport-a.txt", b"Alpha reliable transport"),
        create_parsed_material(db, tmp_path, user.id, course.id, "transport-b.txt", b"Beta congestion control"),
    ]
    provider = RecordingPlanProvider(material_ids)
    before_count = db.scalar(select(func.count()).select_from(StudyPlan))

    preview = preview_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=StudyPlanBuildRequest(
            goal_text="掌握传输层",
            start_date=date(2026, 7, 11),
            end_date=date(2026, 7, 11),
            daily_available_minutes=60,
            material_scope=MaterialScope(include_all_parsed_materials=True, material_ids=[]),
        ),
        model_provider=provider,
        max_tokens=1,
    )

    assert preview.coverage.expected_material_ids == sorted(material_ids)
    assert preview.coverage.processed_material_ids == sorted(material_ids)
    assert preview.coverage.batch_count == len(provider.batch_prompts)
    assert len(provider.batch_prompts) >= 2
    assert len(provider.reduce_prompts) == 1
    assert preview.tasks[0].subtasks[-1].subtask_type == "test"
    assert sum(subtask.estimated_minutes for subtask in preview.tasks[0].subtasks) == 60
    assert set(preview.tasks[0].subtasks[0].related_material_ids) == set(material_ids)
    assert db.scalar(select(func.count()).select_from(StudyPlan)) == before_count