from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
import app.db.models  # noqa: F401
from app.modules.checkins.models import CheckinRecord
from app.modules.courses.models import Course
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.study_plans.models import StudyPlan, StudySubTask, StudyTask
from app.modules.users.models import User


EXPECTED_CORE_TABLES = {
    "users",
    "courses",
    "material_folders",
    "course_materials",
    "material_chunks",
    "conversations",
    "messages",
    "source_citations",
    "ai_generated_contents",
    "study_plans",
    "study_tasks",
    "study_subtasks",
    "checkin_records",
}

FORBIDDEN_STUDY_MODE_TABLES = {
    "todos",
    "calendar_events",
    "handouts",
    "task_tests",
    "export_records",
}

EXPECTED_COLUMNS = {
    "users": {
        "id",
        "username",
        "password_hash",
        "nickname",
        "avatar_url",
        "status",
        "created_at",
        "updated_at",
        "deleted_at",
    },
    "courses": {
        "id",
        "user_id",
        "name",
        "description",
        "teacher",
        "term",
        "status",
        "created_at",
        "updated_at",
        "deleted_at",
    },
    "material_folders": {
        "id",
        "user_id",
        "course_id",
        "name",
        "sort_order",
        "created_at",
        "updated_at",
        "deleted_at",
    },
    "course_materials": {
        "id",
        "course_id",
        "user_id",
        "folder_id",
        "name",
        "material_type",
        "source_type",
        "file_url",
        "source_url",
        "file_size",
        "mime_type",
        "parse_status",
        "parse_error",
        "page_count",
        "created_at",
        "updated_at",
        "deleted_at",
    },
    "material_chunks": {
        "id",
        "material_id",
        "course_id",
        "chunk_index",
        "page",
        "page_index",
        "heading",
        "content_text",
        "embedding_id",
        "created_at",
    },
    "conversations": {
        "id",
        "user_id",
        "course_id",
        "title",
        "source_page",
        "status",
        "created_at",
        "updated_at",
        "deleted_at",
    },
    "messages": {
        "id",
        "conversation_id",
        "course_id",
        "role",
        "content",
        "answer_type",
        "generation_status",
        "error_code",
        "material_scope_json",
        "created_at",
    },
    "source_citations": {
        "id",
        "message_id",
        "generated_content_id",
        "material_id",
        "chunk_id",
        "material_name",
        "page",
        "page_index",
        "hit_text",
        "sort_order",
        "created_at",
    },
    "ai_generated_contents": {
        "id",
        "user_id",
        "course_id",
        "study_subtask_id",
        "source_message_id",
        "content_type",
        "title",
        "content",
        "content_json",
        "generation_status",
        "material_scope_json",
        "error_code",
        "created_at",
        "updated_at",
        "deleted_at",
    },
    "study_plans": {
        "id",
        "user_id",
        "course_id",
        "title",
        "goal_text",
        "parsed_config_json",
        "start_date",
        "end_date",
        "daily_available_minutes",
        "status",
        "created_at",
        "updated_at",
        "deleted_at",
    },
    "study_tasks": {
        "id",
        "plan_id",
        "course_id",
        "title",
        "task_date",
        "start_time",
        "end_time",
        "status",
        "sort_order",
        "created_at",
        "updated_at",
    },
    "study_subtasks": {
        "id",
        "task_id",
        "plan_id",
        "course_id",
        "title",
        "subtask_type",
        "description",
        "related_material_ids_json",
        "status",
        "completed_at",
        "sort_order",
        "created_at",
        "updated_at",
    },
    "checkin_records": {
        "id",
        "user_id",
        "checkin_date",
        "total_subtask_count",
        "completed_subtask_count",
        "completion_ratio",
        "color_level",
        "created_at",
        "updated_at",
    },
}


@pytest.fixture()
def engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def _column_names(engine, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table_name)}


def _constraint_names(engine, table_name: str) -> set[str]:
    inspector = inspect(engine)
    names = {constraint["name"] for constraint in inspector.get_check_constraints(table_name)}
    names.update(constraint["name"] for constraint in inspector.get_unique_constraints(table_name))
    return names


def _insert_minimal_task_tree(session: Session, suffix: str = "1") -> None:
    user = User(
        id=f"usr_{suffix}",
        username=f"esther_{suffix}",
        password_hash="hash",
        status="active",
    )
    course = Course(
        id=f"crs_{suffix}",
        user_id=user.id,
        name="Computer Networks",
        status="active",
    )
    plan = StudyPlan(
        id=f"sp_{suffix}",
        user_id=user.id,
        course_id=course.id,
        title="Transport Layer Plan",
        goal_text="Master transport layer",
        start_date=date(2026, 7, 10),
        end_date=date(2026, 7, 12),
        daily_available_minutes=60,
        status="active",
    )
    task = StudyTask(
        id=f"tsk_{suffix}",
        plan_id=plan.id,
        course_id=course.id,
        title="Reliable Transport",
        task_date=date(2026, 7, 10),
        status="not_started",
        sort_order=1,
    )
    subtask = StudySubTask(
        id=f"sub_{suffix}",
        task_id=task.id,
        plan_id=plan.id,
        course_id=course.id,
        title="Read lecture notes",
        subtask_type="learn",
        status="not_started",
        sort_order=1,
        related_material_ids_json=[],
    )
    session.add_all([user, course, plan, task, subtask])
    session.flush()


def test_baseline_has_exact_thirteen_core_tables(engine) -> None:
    assert set(inspect(engine).get_table_names()) == EXPECTED_CORE_TABLES


def test_study_mode_reuses_existing_columns(engine) -> None:
    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        assert expected_columns <= _column_names(engine, table_name)


def test_checkin_user_date_is_unique(engine) -> None:
    assert "uq_checkin_records_user_date" in _constraint_names(engine, "checkin_records")

    with Session(engine) as session:
        session.add(User(id="usr_1", username="esther", password_hash="hash", status="active"))
        session.flush()
        session.add_all(
            [
                CheckinRecord(
                    id="chk_1",
                    user_id="usr_1",
                    checkin_date=date(2026, 7, 10),
                    total_subtask_count=1,
                    completed_subtask_count=1,
                    completion_ratio=Decimal("1.0000"),
                    color_level=5,
                ),
                CheckinRecord(
                    id="chk_2",
                    user_id="usr_1",
                    checkin_date=date(2026, 7, 10),
                    total_subtask_count=1,
                    completed_subtask_count=0,
                    completion_ratio=Decimal("0.0000"),
                    color_level=1,
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_generated_content_supports_task_bound_types(engine) -> None:
    assert "ck_ai_generated_contents_ai_generated_content_type" in _constraint_names(
        engine,
        "ai_generated_contents",
    )

    with Session(engine) as session:
        _insert_minimal_task_tree(session)
        session.add_all(
            [
                AIGeneratedContent(
                    id="gen_handout",
                    user_id="usr_1",
                    course_id="crs_1",
                    study_subtask_id="sub_1",
                    content_type="handout",
                    title="Daily handout",
                    generation_status="success",
                    content_json={"overview": "handout"},
                ),
                AIGeneratedContent(
                    id="gen_task_test",
                    user_id="usr_1",
                    course_id="crs_1",
                    study_subtask_id="sub_1",
                    content_type="task_test",
                    title="Task test",
                    generation_status="success",
                    content_json={"questions": []},
                ),
            ]
        )
        session.commit()

    with Session(engine) as session:
        _insert_minimal_task_tree(session, "2")
        session.add(
            AIGeneratedContent(
                id="gen_invalid",
                user_id="usr_2",
                course_id="crs_2",
                study_subtask_id="sub_2",
                content_type="worksheet",
                title="Invalid content",
                generation_status="success",
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_no_todo_calendar_export_business_tables(engine) -> None:
    table_names = set(inspect(engine).get_table_names())
    assert table_names.isdisjoint(FORBIDDEN_STUDY_MODE_TABLES)


@pytest.mark.parametrize(
    ("model_factory", "constraint_name"),
    [
        (
            lambda: StudyPlan(
                id="sp_bad",
                user_id="usr_1",
                course_id="crs_1",
                title="bad",
                goal_text="bad",
                start_date=date(2026, 7, 10),
                end_date=date(2026, 7, 12),
                daily_available_minutes=60,
                status="paused",
            ),
            "ck_study_plans_study_plan_status",
        ),
        (
            lambda: StudyTask(
                id="tsk_bad",
                plan_id="sp_1",
                course_id="crs_1",
                title="bad",
                task_date=date(2026, 7, 10),
                status="paused",
                sort_order=1,
            ),
            "ck_study_tasks_study_task_status",
        ),
        (
            lambda: StudySubTask(
                id="sub_bad",
                task_id="tsk_1",
                plan_id="sp_1",
                course_id="crs_1",
                title="bad",
                subtask_type="watch",
                status="not_started",
                sort_order=1,
            ),
            "ck_study_subtasks_study_subtask_type",
        ),
    ],
)
def test_plan_and_task_enum_constraints(engine, model_factory, constraint_name: str) -> None:
    assert constraint_name in _constraint_names(engine, model_factory().__tablename__)

    with Session(engine) as session:
        _insert_minimal_task_tree(session)
        session.add(model_factory())

        with pytest.raises(IntegrityError):
            session.commit()



