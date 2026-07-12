from __future__ import annotations

import hashlib
import json
from collections.abc import Generator
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import CourseNexusError
from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.modules.checkins.models import CheckinRecord
from app.modules.generated_content.models import AIGeneratedContent
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.material_context.schemas import MaterialScope
from app.modules.materials.service import parse_material, upload_file_material
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask
from app.modules.study_plans.schemas import (
    StudyPlanBuildRequest,
    StudyPlanConfigParseRequest,
    StudyPlanParsedConfig,
    StudyPlanRegenerationPreviewRequest,
    StudyPlanReplaceRequest,
    StudyPlanSaveRequest,
    StudySubTaskPreview,
)
from app.modules.study_plans.service import delete_study_plan, get_study_plan_detail, list_study_plans, parse_study_plan_config, preview_study_plan, preview_study_plan_regeneration, replace_study_plan, save_study_plan
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
    assert parsed.daily_minutes_source == "user_text"
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

def _save_request(material_ids: list[str]) -> StudyPlanSaveRequest:
    return StudyPlanSaveRequest.model_validate(
        {
            "title": "传输层冲刺计划",
            "goal_text": "掌握传输层",
            "start_date": "2026-07-11",
            "end_date": "2026-07-11",
            "daily_available_minutes": 60,
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
            "preference": "fast_track",
            "tasks": [
                {
                    "title": "用户调整后的任务",
                    "task_date": "2026-07-11",
                    "sort_order": 1,
                    "subtasks": [
                        {
                            "title": "用户调整后的学习项",
                            "subtask_type": "learn",
                            "description": "按用户确认内容保存",
                            "related_material_ids": material_ids,
                            "estimated_minutes": 60,
                            "citation_chunk_ids": ["chk_save"],
                            "sort_order": 1,
                        }
                    ],
                }
            ],
        }
    )




def _study_plan_counts(db: Session) -> dict[str, int]:
    return {
        "plans": int(db.scalar(select(func.count()).select_from(StudyPlan)) or 0),
        "tasks": int(db.scalar(select(func.count()).select_from(StudyTask)) or 0),
        "subtasks": int(db.scalar(select(func.count()).select_from(StudySubTask)) or 0),
        "checkins": int(db.scalar(select(func.count()).select_from(CheckinRecord)) or 0),
    }


def _assert_no_plan_write_side_effects(db: Session) -> None:
    assert _study_plan_counts(db) == {"plans": 0, "tasks": 0, "subtasks": 0, "checkins": 0}


def _request_data(material_ids: list[str]) -> dict[str, object]:
    return _save_request(material_ids).model_dump(mode="json")


def _save_request_from_data(data: dict[str, object]) -> StudyPlanSaveRequest:
    return StudyPlanSaveRequest.model_validate(data)


def _replace_request_from_data(saved_updated_at: datetime, data: dict[str, object]) -> StudyPlanReplaceRequest:
    return StudyPlanReplaceRequest.model_validate(
        data
        | {
            "expected_updated_at": saved_updated_at.isoformat(),
            "title": "替换后的传输层计划",
        }
    )


def _material_violation_case(
    db: Session,
    tmp_path: Path,
    *,
    user_id: str,
    course_id: str,
    valid_material_id: str,
    case_name: str,
) -> tuple[str, dict[str, object]]:
    if case_name == "missing":
        return "mat_missing", {"include_all_parsed_materials": True, "material_ids": []}
    if case_name == "cross_user":
        other_user = register_user(db, UserCreate(username="material-other-user", password="password123"))
        other_course = create_course(db, other_user.id, CourseCreate(name="Other User Course"))
        material_id = create_parsed_material(db, tmp_path, other_user.id, other_course.id, "other-user.txt", b"Other user material")
        return material_id, {"include_all_parsed_materials": True, "material_ids": []}
    if case_name == "cross_course":
        other_course = create_course(db, user_id, CourseCreate(name="Other Course"))
        material_id = create_parsed_material(db, tmp_path, user_id, other_course.id, "other-course.txt", b"Other course material")
        return material_id, {"include_all_parsed_materials": True, "material_ids": []}
    if case_name == "outside_scope":
        outside_material_id = create_parsed_material(db, tmp_path, user_id, course_id, "outside-scope.txt", b"Outside scope material")
        return outside_material_id, {"include_all_parsed_materials": False, "material_ids": [valid_material_id]}
    raise AssertionError(case_name)


def test_save_study_plan_rejects_confirmed_task_outside_date_range_without_side_effects(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="save-date-range", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "transport-date.txt", b"Reliable transport")
    data = _request_data([material_id])
    data["tasks"][0]["task_date"] = "2026-07-12"

    with pytest.raises(CourseNexusError) as exc_info:
        save_study_plan(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=_save_request_from_data(data),
            model_provider=RecordingPlanProvider([material_id]),
            max_tokens=12_000,
        )

    assert exc_info.value.code == "VALIDATION_ERROR"
    _assert_no_plan_write_side_effects(db)


@pytest.mark.parametrize("case_name", ["missing", "cross_user", "cross_course", "outside_scope"])
def test_save_study_plan_rejects_confirmed_task_material_violations_without_side_effects(
    db: Session,
    tmp_path: Path,
    case_name: str,
) -> None:
    user = register_user(db, UserCreate(username=f"save-material-{case_name}", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    valid_material_id = create_parsed_material(db, tmp_path, user.id, course.id, f"valid-{case_name}.txt", b"Valid material")
    invalid_material_id, material_scope = _material_violation_case(
        db,
        tmp_path,
        user_id=user.id,
        course_id=course.id,
        valid_material_id=valid_material_id,
        case_name=case_name,
    )
    data = _request_data([invalid_material_id])
    data["material_scope"] = material_scope

    with pytest.raises(CourseNexusError) as exc_info:
        save_study_plan(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=_save_request_from_data(data),
            model_provider=RecordingPlanProvider([valid_material_id]),
            max_tokens=12_000,
        )

    assert exc_info.value.code in {"VALIDATION_ERROR", "NOT_FOUND"}
    _assert_no_plan_write_side_effects(db)


def test_save_study_plan_rejects_empty_confirmed_task_tree_without_side_effects(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="save-empty-tree", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "transport-empty-tree.txt", b"Reliable transport")
    data = _request_data([material_id])
    data["tasks"] = []

    with pytest.raises(CourseNexusError) as exc_info:
        save_study_plan(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=_save_request_from_data(data),
            model_provider=RecordingPlanProvider([material_id]),
            max_tokens=12_000,
        )

    assert exc_info.value.code == "VALIDATION_ERROR"
    _assert_no_plan_write_side_effects(db)


def test_save_study_plan_rejects_task_without_subtasks_without_side_effects(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="save-empty-subtasks", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "transport-empty-subtasks.txt", b"Reliable transport")
    data = _request_data([material_id])
    data["tasks"][0]["subtasks"] = []

    with pytest.raises(CourseNexusError) as exc_info:
        save_study_plan(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=_save_request_from_data(data),
            model_provider=RecordingPlanProvider([material_id]),
            max_tokens=12_000,
        )

    assert exc_info.value.code == "VALIDATION_ERROR"
    _assert_no_plan_write_side_effects(db)


def test_replace_study_plan_rejects_confirmed_task_outside_date_range_without_side_effects(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="replace-date-range", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "replace-date.txt", b"Reliable transport")
    saved = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_save_request([material_id]),
        model_provider=RecordingPlanProvider([material_id]),
        max_tokens=12_000,
    )
    before_counts = _study_plan_counts(db)
    data = _request_data([material_id])
    data["tasks"][0]["task_date"] = "2026-07-12"

    with pytest.raises(CourseNexusError) as exc_info:
        replace_study_plan(db, user_id=user.id, plan_id=saved.plan.id, payload=_replace_request_from_data(saved.plan.updated_at, data))

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert _study_plan_counts(db) == before_counts
    assert get_study_plan_detail(db, user_id=user.id, plan_id=saved.plan.id).tasks[0].title == "用户调整后的任务"


@pytest.mark.parametrize("case_name", ["missing", "cross_user", "cross_course", "outside_scope"])
def test_replace_study_plan_rejects_confirmed_task_material_violations_without_side_effects(
    db: Session,
    tmp_path: Path,
    case_name: str,
) -> None:
    user = register_user(db, UserCreate(username=f"replace-material-{case_name}", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    valid_material_id = create_parsed_material(db, tmp_path, user.id, course.id, f"replace-valid-{case_name}.txt", b"Valid material")
    saved = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_save_request([valid_material_id]),
        model_provider=RecordingPlanProvider([valid_material_id]),
        max_tokens=12_000,
    )
    invalid_material_id, material_scope = _material_violation_case(
        db,
        tmp_path,
        user_id=user.id,
        course_id=course.id,
        valid_material_id=valid_material_id,
        case_name=case_name,
    )
    before_counts = _study_plan_counts(db)
    data = _request_data([invalid_material_id])
    data["material_scope"] = material_scope

    with pytest.raises(CourseNexusError) as exc_info:
        replace_study_plan(db, user_id=user.id, plan_id=saved.plan.id, payload=_replace_request_from_data(saved.plan.updated_at, data))

    assert exc_info.value.code in {"VALIDATION_ERROR", "NOT_FOUND"}
    assert _study_plan_counts(db) == before_counts
    assert get_study_plan_detail(db, user_id=user.id, plan_id=saved.plan.id).subtasks[0].related_material_ids_json == [valid_material_id]


def test_replace_study_plan_rejects_task_without_subtasks_without_side_effects(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="replace-empty-subtasks", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "replace-empty-subtasks.txt", b"Reliable transport")
    saved = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_save_request([material_id]),
        model_provider=RecordingPlanProvider([material_id]),
        max_tokens=12_000,
    )
    before_counts = _study_plan_counts(db)
    data = _request_data([material_id])
    data["tasks"][0]["subtasks"] = []

    with pytest.raises(CourseNexusError) as exc_info:
        replace_study_plan(db, user_id=user.id, plan_id=saved.plan.id, payload=_replace_request_from_data(saved.plan.updated_at, data))

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert _study_plan_counts(db) == before_counts
    assert get_study_plan_detail(db, user_id=user.id, plan_id=saved.plan.id).subtasks[0].title == "用户调整后的学习项"

def test_save_study_plan_uses_adjusted_task_tree_and_idempotency(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="carol", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "transport-save.txt", b"Reliable transport")
    payload = _save_request([material_id])
    provider = RecordingPlanProvider([material_id])

    first = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=payload,
        model_provider=provider,
        max_tokens=12_000,
        idempotency_key="stable-save-key",
    )
    second = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=payload,
        model_provider=provider,
        max_tokens=12_000,
        idempotency_key="stable-save-key",
    )

    assert first.plan.id == second.plan.id
    assert first.plan.title == "传输层冲刺计划"
    assert first.plan.parsed_config_json["preference"] == "fast_track"
    assert first.plan.parsed_config_json["idempotency"]["key_hash"]
    assert first.plan.idempotency_key_hash == first.plan.parsed_config_json["idempotency"]["key_hash"]
    assert first.tasks[0].title == "用户调整后的任务"
    assert first.subtasks[0].title == "用户调整后的学习项"
    assert first.subtasks[0].related_material_ids_json == [material_id]
    assert len(list_study_plans(db, user_id=user.id, course_id=course.id)) == 1
    assert provider.batch_prompts == []


def _legacy_request_hash_without_client_flow(payload: StudyPlanSaveRequest) -> str:
    data = payload.model_dump(mode="json")
    data.pop("client_flow", None)
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def test_save_study_plan_replays_legacy_idempotency_hash_without_client_flow(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="legacy-idem-hash", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "legacy-idem-hash.txt", b"Reliable transport")
    payload = _save_request([material_id])

    first = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=payload,
        model_provider=RecordingPlanProvider([material_id]),
        max_tokens=12_000,
        idempotency_key="legacy-idem-hash-key",
    )
    config = dict(first.plan.parsed_config_json)
    config["idempotency"] = dict(config["idempotency"])
    config["idempotency"]["request_hash"] = _legacy_request_hash_without_client_flow(payload)
    first.plan.parsed_config_json = config
    db.add(first.plan)
    db.commit()

    second = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=payload,
        model_provider=RecordingPlanProvider([material_id]),
        max_tokens=12_000,
        idempotency_key="legacy-idem-hash-key",
    )

    assert second.plan.id == first.plan.id

def test_save_study_plan_without_idempotency_key_keeps_existing_create_behavior(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="idem-no-key", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "idem-no-key.txt", b"Reliable transport")
    provider = RecordingPlanProvider([material_id])

    first = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_save_request([material_id]),
        model_provider=provider,
        max_tokens=12_000,
    )
    second = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_save_request([material_id]),
        model_provider=provider,
        max_tokens=12_000,
    )

    assert first.plan.id != second.plan.id
    assert first.plan.idempotency_key_hash is None
    assert second.plan.idempotency_key_hash is None
    assert len(list_study_plans(db, user_id=user.id, course_id=course.id)) == 2


def test_save_study_plan_allows_different_idempotency_keys(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="idem-different-key", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "idem-different-key.txt", b"Reliable transport")
    provider = RecordingPlanProvider([material_id])

    first = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_save_request([material_id]),
        model_provider=provider,
        max_tokens=12_000,
        idempotency_key="idem-key-one",
    )
    second = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_save_request([material_id]),
        model_provider=provider,
        max_tokens=12_000,
        idempotency_key="idem-key-two",
    )

    assert first.plan.id != second.plan.id
    assert first.plan.idempotency_key_hash != second.plan.idempotency_key_hash
    assert len(list_study_plans(db, user_id=user.id, course_id=course.id)) == 2


def test_save_study_plan_recovers_existing_plan_when_idempotent_insert_races(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    setup_db = testing_session()
    try:
        user = register_user(setup_db, UserCreate(username="idem-race-same", password="password123"))
        course = create_course(setup_db, user.id, CourseCreate(name="Computer Networks"))
        material_id = create_parsed_material(setup_db, tmp_path, user.id, course.id, "idem-race-same.txt", b"Reliable transport")
        user_id = user.id
        course_id = course.id
    finally:
        setup_db.close()

    from app.modules.study_plans import repository as study_plan_repository

    original_lookup = study_plan_repository.get_active_study_plan_for_idempotency_key
    calls = {"count": 0}

    def miss_initial_race_reads(*args: object, **kwargs: object) -> StudyPlan | None:
        calls["count"] += 1
        if calls["count"] <= 2:
            return None
        return original_lookup(*args, **kwargs)

    monkeypatch.setattr(study_plan_repository, "get_active_study_plan_for_idempotency_key", miss_initial_race_reads)

    first_db = testing_session()
    second_db = testing_session()
    verify_db = testing_session()
    try:
        first = save_study_plan(
            first_db,
            user_id=user_id,
            course_id=course_id,
            payload=_save_request([material_id]),
            model_provider=RecordingPlanProvider([material_id]),
            max_tokens=12_000,
            idempotency_key="idem-race-key",
        )
        second = save_study_plan(
            second_db,
            user_id=user_id,
            course_id=course_id,
            payload=_save_request([material_id]),
            model_provider=RecordingPlanProvider([material_id]),
            max_tokens=12_000,
            idempotency_key="idem-race-key",
        )

        assert second.plan.id == first.plan.id
        assert _study_plan_counts(verify_db) == {"plans": 1, "tasks": 1, "subtasks": 1, "checkins": 1}
    finally:
        first_db.close()
        second_db.close()
        verify_db.close()


def test_save_study_plan_returns_conflict_when_raced_idempotency_body_differs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    setup_db = testing_session()
    try:
        user = register_user(setup_db, UserCreate(username="idem-race-conflict", password="password123"))
        course = create_course(setup_db, user.id, CourseCreate(name="Computer Networks"))
        material_id = create_parsed_material(setup_db, tmp_path, user.id, course.id, "idem-race-conflict.txt", b"Reliable transport")
        user_id = user.id
        course_id = course.id
    finally:
        setup_db.close()

    from app.modules.study_plans import repository as study_plan_repository

    original_lookup = study_plan_repository.get_active_study_plan_for_idempotency_key
    calls = {"count": 0}

    def miss_initial_race_reads(*args: object, **kwargs: object) -> StudyPlan | None:
        calls["count"] += 1
        if calls["count"] <= 2:
            return None
        return original_lookup(*args, **kwargs)

    monkeypatch.setattr(study_plan_repository, "get_active_study_plan_for_idempotency_key", miss_initial_race_reads)

    first_db = testing_session()
    second_db = testing_session()
    verify_db = testing_session()
    try:
        save_study_plan(
            first_db,
            user_id=user_id,
            course_id=course_id,
            payload=_save_request([material_id]),
            model_provider=RecordingPlanProvider([material_id]),
            max_tokens=12_000,
            idempotency_key="idem-race-conflict-key",
        )

        changed_payload = _save_request([material_id]).model_copy(update={"title": "changed race title"})
        with pytest.raises(CourseNexusError) as exc_info:
            save_study_plan(
                second_db,
                user_id=user_id,
                course_id=course_id,
                payload=changed_payload,
                model_provider=RecordingPlanProvider([material_id]),
                max_tokens=12_000,
                idempotency_key="idem-race-conflict-key",
            )

        assert exc_info.value.code == "IDEMPOTENCY_CONFLICT"
        assert _study_plan_counts(verify_db) == {"plans": 1, "tasks": 1, "subtasks": 1, "checkins": 1}
    finally:
        first_db.close()
        second_db.close()
        verify_db.close()


def test_save_study_plan_rejects_reusing_idempotency_key_after_soft_delete(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="idem-deleted", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "idem-deleted.txt", b"Reliable transport")
    provider = RecordingPlanProvider([material_id])
    saved = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_save_request([material_id]),
        model_provider=provider,
        max_tokens=12_000,
        idempotency_key="deleted-key",
    )

    delete_study_plan(db, user_id=user.id, plan_id=saved.plan.id)

    with pytest.raises(CourseNexusError) as exc_info:
        save_study_plan(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=_save_request([material_id]),
            model_provider=provider,
            max_tokens=12_000,
            idempotency_key="deleted-key",
        )

    assert exc_info.value.code == "IDEMPOTENCY_CONFLICT"

def test_save_study_plan_rejects_same_idempotency_key_with_different_body(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="dave", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "transport-conflict.txt", b"Reliable transport")
    provider = RecordingPlanProvider([material_id])

    save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_save_request([material_id]),
        model_provider=provider,
        max_tokens=12_000,
        idempotency_key="conflict-key",
    )

    changed_payload = _save_request([material_id]).model_copy(update={"title": "另一个计划标题"})
    with pytest.raises(CourseNexusError) as exc_info:
        save_study_plan(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=changed_payload,
            model_provider=provider,
            max_tokens=12_000,
            idempotency_key="conflict-key",
        )

    assert exc_info.value.code == "IDEMPOTENCY_CONFLICT"


def test_save_study_plan_rolls_back_when_subtask_flush_fails(db: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    user = register_user(db, UserCreate(username="erin", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "transport-rollback.txt", b"Reliable transport")
    payload = _save_request([material_id])

    from app.modules.study_plans import repository as study_plan_repository

    def fail_after_add(*args: object, **kwargs: object) -> object:
        db.add(kwargs["plan"])
        db.add_all(kwargs["tasks"])
        db.add_all(kwargs["subtasks"])
        db.flush()
        raise RuntimeError("forced flush failure")

    monkeypatch.setattr(study_plan_repository, "add_study_plan_bundle", fail_after_add)

    with pytest.raises(RuntimeError):
        save_study_plan(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=payload,
            model_provider=RecordingPlanProvider([material_id]),
            max_tokens=12_000,
            idempotency_key="rollback-key",
        )

    assert db.scalar(select(func.count()).select_from(StudyPlan)) == 0

def test_regeneration_preview_does_not_write_db(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="frank", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "transport-regen.txt", b"Reliable transport")
    provider = RecordingPlanProvider([material_id])
    saved = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_save_request([material_id]),
        model_provider=provider,
        max_tokens=12_000,
        idempotency_key="regen-save-key",
    )
    before_count = db.scalar(select(func.count()).select_from(StudyPlan))

    preview = preview_study_plan_regeneration(
        db,
        user_id=user.id,
        plan_id=saved.plan.id,
        payload=StudyPlanRegenerationPreviewRequest(goal_text="重新掌握传输层"),
        model_provider=RecordingPlanProvider([material_id]),
        max_tokens=12_000,
    )

    assert preview.goal_text == "重新掌握传输层"
    assert db.scalar(select(func.count()).select_from(StudyPlan)) == before_count


def test_replace_study_plan_replaces_task_tree_atomically(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="gina", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "transport-replace.txt", b"Reliable transport")
    saved = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_save_request([material_id]),
        model_provider=RecordingPlanProvider([material_id]),
        max_tokens=12_000,
        idempotency_key="replace-save-key",
    )
    replace_payload = StudyPlanReplaceRequest.model_validate(
        _save_request([material_id]).model_dump(mode="json")
        | {
            "expected_updated_at": saved.plan.updated_at.isoformat(),
            "title": "替换后的传输层计划",
            "tasks": [
                {
                    "title": "替换后的任务",
                    "task_date": "2026-07-11",
                    "sort_order": 1,
                    "subtasks": [
                        {
                            "title": "替换后的测试",
                            "subtask_type": "test",
                            "description": "确认掌握情况",
                            "related_material_ids": [material_id],
                            "estimated_minutes": 60,
                            "citation_chunk_ids": ["chk_replace"],
                            "sort_order": 1,
                        }
                    ],
                }
            ],
        }
    )

    replaced = replace_study_plan(db, user_id=user.id, plan_id=saved.plan.id, payload=replace_payload)

    assert replaced.plan.title == "替换后的传输层计划"
    assert [task.title for task in replaced.tasks] == ["替换后的任务"]
    assert [subtask.title for subtask in replaced.subtasks] == ["替换后的测试"]



def test_replace_study_plan_rejects_stale_expected_updated_at_from_concurrent_session(tmp_path: Path) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    setup_db = testing_session()
    try:
        user = register_user(setup_db, UserCreate(username="replace-race", password="password123"))
        course = create_course(setup_db, user.id, CourseCreate(name="Computer Networks"))
        material_id = create_parsed_material(setup_db, tmp_path, user.id, course.id, "replace-race.txt", b"Reliable transport")
        saved = save_study_plan(
            setup_db,
            user_id=user.id,
            course_id=course.id,
            payload=_save_request([material_id]),
            model_provider=RecordingPlanProvider([material_id]),
            max_tokens=12_000,
        )
        user_id = user.id
        plan_id = saved.plan.id
        expected_updated_at = saved.plan.updated_at
    finally:
        setup_db.close()

    first_db = testing_session()
    second_db = testing_session()
    verify_db = testing_session()
    try:
        stale_bundle = get_study_plan_detail(second_db, user_id=user_id, plan_id=plan_id)
        assert stale_bundle.plan.updated_at == expected_updated_at

        first_data = _request_data([material_id])
        first_data["tasks"][0]["title"] = "第一轮替换任务"
        second_data = _request_data([material_id])
        second_data["tasks"][0]["title"] = "第二轮替换任务"

        replace_study_plan(
            first_db,
            user_id=user_id,
            plan_id=plan_id,
            payload=_replace_request_from_data(expected_updated_at, first_data),
        )

        with pytest.raises(CourseNexusError) as exc_info:
            replace_study_plan(
                second_db,
                user_id=user_id,
                plan_id=plan_id,
                payload=_replace_request_from_data(expected_updated_at, second_data),
            )

        assert exc_info.value.code == "STATE_CONFLICT"
        current = get_study_plan_detail(verify_db, user_id=user_id, plan_id=plan_id)
        assert [task.title for task in current.tasks] == ["第一轮替换任务"]
        assert [subtask.title for subtask in current.subtasks] == ["用户调整后的学习项"]
    finally:
        first_db.close()
        second_db.close()
        verify_db.close()

def test_replace_study_plan_rejects_progress_and_generated_content(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="hank", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "transport-state.txt", b"Reliable transport")
    saved = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_save_request([material_id]),
        model_provider=RecordingPlanProvider([material_id]),
        max_tokens=12_000,
        idempotency_key="state-save-key",
    )
    saved.subtasks[0].status = "completed"
    db.add(saved.subtasks[0])
    db.commit()
    replace_payload = StudyPlanReplaceRequest.model_validate(
        _save_request([material_id]).model_dump(mode="json") | {"expected_updated_at": saved.plan.updated_at.isoformat(), "title": "冲突计划"}
    )

    with pytest.raises(CourseNexusError) as progress_exc:
        replace_study_plan(db, user_id=user.id, plan_id=saved.plan.id, payload=replace_payload)

    assert progress_exc.value.code == "STATE_CONFLICT"


def test_delete_study_plan_soft_deletes_and_hides_plan(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="ivy", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "transport-delete.txt", b"Reliable transport")
    saved = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_save_request([material_id]),
        model_provider=RecordingPlanProvider([material_id]),
        max_tokens=12_000,
        idempotency_key="delete-save-key",
    )

    deleted = delete_study_plan(db, user_id=user.id, plan_id=saved.plan.id)

    assert deleted.status == "deleted"
    assert deleted.deleted_at is not None
    assert list_study_plans(db, user_id=user.id, course_id=course.id) == []
    with pytest.raises(CourseNexusError) as exc_info:
        get_study_plan_detail(db, user_id=user.id, plan_id=saved.plan.id)
    assert exc_info.value.code == "NOT_FOUND"


def test_replace_study_plan_rejects_bound_generated_content(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="jane", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, "transport-bound.txt", b"Reliable transport")
    saved = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_save_request([material_id]),
        model_provider=RecordingPlanProvider([material_id]),
        max_tokens=12_000,
        idempotency_key="bound-save-key",
    )
    db.add(
        AIGeneratedContent(
            id="gen_bound_handout",
            user_id=user.id,
            course_id=course.id,
            study_subtask_id=saved.subtasks[0].id,
            content_type="handout",
            title="讲义",
            content="content",
            generation_status="success",
        )
    )
    db.commit()
    replace_payload = StudyPlanReplaceRequest.model_validate(
        _save_request([material_id]).model_dump(mode="json") | {"expected_updated_at": saved.plan.updated_at.isoformat(), "title": "绑定冲突计划"}
    )

    with pytest.raises(CourseNexusError) as exc_info:
        replace_study_plan(db, user_id=user.id, plan_id=saved.plan.id, payload=replace_payload)

    assert exc_info.value.code == "STATE_CONFLICT"
