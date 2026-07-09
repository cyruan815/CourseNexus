from __future__ import annotations

from collections.abc import Generator
from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
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

    preview = preview_study_plan(db, user_id=user.id, course_id=course.id, payload=build_request())

    assert preview.course_id == course.id
    assert preview.title == "Linear Algebra 学习计划"
    assert [task.task_date for task in preview.tasks] == [date(2026, 7, 10), date(2026, 7, 11), date(2026, 7, 12)]
    assert preview.tasks[0].subtasks[0].related_material_ids == [material_id]
    assert 1 <= len(preview.tasks[0].subtasks) <= 3


def test_preview_study_plan_requires_parsed_material(db: Session) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))

    with pytest.raises(CourseNexusError) as exc_info:
        preview_study_plan(db, user_id=user.id, course_id=course.id, payload=build_request())

    assert exc_info.value.code == "NO_PARSED_MATERIAL"


def test_save_study_plan_writes_plan_tasks_and_subtasks(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material_id = create_parsed_material(db, tmp_path, user.id, course.id, b"Alpha\n\nBeta")

    saved = save_study_plan(db, user_id=user.id, course_id=course.id, payload=build_request())

    assert saved.plan.course_id == course.id
    assert len(saved.tasks) == 3
    assert saved.tasks[0].course_id == course.id
    assert saved.subtasks[0].course_id == course.id
    assert saved.subtasks[0].related_material_ids_json == [material_id]
    assert list_study_plans(db, user_id=user.id, course_id=course.id)[0].id == saved.plan.id
    assert get_study_plan_detail(db, user_id=user.id, plan_id=saved.plan.id).plan.id == saved.plan.id


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
        )

    assert exc_info.value.code == "NOT_FOUND"
