from __future__ import annotations

from collections.abc import Generator
from datetime import date

from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.db.models  # noqa: F401
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.materials.models import CourseMaterial, MaterialChunk, MaterialParseVersion
from app.modules.study_plans.schemas import StudyPlanSaveRequest
from app.modules.study_plans.service import get_study_plan_detail, save_study_plan
from app.modules.todos_calendar.service import get_course_day_todos, get_global_day_todos, get_global_month_calendar
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user
from tests.fixtures.study_mode_samples import compliant_daily_task, study_subtask


class UnusedProvider:
    def generate_structured(self, *, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        raise AssertionError("S03 integration should read saved adjusted tasks and not generate preview")


import pytest


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


def test_saved_plan_appears_in_today_calendar_and_plan_detail(db: Session) -> None:
    user = register_user(db, UserCreate(username="s03alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    db.add_all(
        [
            CourseMaterial(
                id="mat_s03",
                user_id=user.id,
                course_id=course.id,
                name="s03.txt",
                material_type="text",
                source_type="file",
                file_url="memory://s03.txt",
                file_size=12,
                mime_type="text/plain",
                parse_status="parsed",
                active_parse_version_id="mpv_mat_s03",
            ),
            MaterialParseVersion(
                id="mpv_mat_s03",
                material_id="mat_s03",
                course_id=course.id,
                user_id=user.id,
                status="active",
                parse_quality="complete",
            ),
            MaterialChunk(
                id="chk_mat_s03_000001",
                material_id="mat_s03",
                parse_version_id="mpv_mat_s03",
                course_id=course.id,
                chunk_index=1,
                heading="S03",
                content_text="S03 material",
            ),
        ]
    )
    db.commit()
    payload = StudyPlanSaveRequest.model_validate(
        {
            "title": "期末复习计划",
            "goal_text": "复习传输层",
            "start_date": "2026-07-11",
            "end_date": "2026-07-12",
            "daily_available_minutes": 60,
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
            "tasks": [
                # 保存契约要求每天恰好一个测试任务并排在最后（见 tests/fixtures/study_mode_samples.py）。
                compliant_daily_task(
                    title="可靠传输",
                    task_date="2026-07-11",
                    sort_order=1,
                    plan_material_ids=["mat_s03"],
                    study_subtasks=[
                        study_subtask(
                            title="学习滑动窗口",
                            subtask_type="learn",
                            material_ids=["mat_s03"],
                            description="学习窗口推进",
                        )
                    ],
                ),
                compliant_daily_task(
                    title="拥塞控制",
                    task_date="2026-07-12",
                    sort_order=2,
                    plan_material_ids=["mat_s03"],
                    study_subtasks=[
                        study_subtask(
                            title="复习拥塞窗口",
                            subtask_type="review",
                            material_ids=["mat_s03"],
                            description="复习拥塞控制",
                        )
                    ],
                ),
            ],
        }
    )
    saved = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=payload,
        model_provider=UnusedProvider(),
        max_tokens=12_000,
        idempotency_key="s03-integration",
    )

    today = get_global_day_todos(db, user_id=user.id, target_date=date(2026, 7, 11))
    course_day = get_course_day_todos(db, user_id=user.id, course_id=course.id, target_date=date(2026, 7, 11))
    month = get_global_month_calendar(db, user_id=user.id, month="2026-07")
    detail = get_study_plan_detail(db, user_id=user.id, plan_id=saved.plan.id)

    assert today.courses[0].tasks[0].title == "可靠传输"
    assert course_day.tasks[0].subtasks[0].title == "学习滑动窗口"
    assert month.days[0].task_summaries[0].plan_id == saved.plan.id
    assert detail.plan.start_date == date(2026, 7, 11)
