from __future__ import annotations

from collections.abc import Generator
from datetime import date

import pytest
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.db.models  # noqa: F401
from app.modules.checkins.models import CheckinRecord
from app.modules.courses.models import Course
from app.modules.materials.models import CourseMaterial, MaterialChunk
from app.modules.study_plans.models import StudyTask
from app.modules.study_plans.schemas import StudyPlanReplaceRequest, StudyPlanSaveRequest
from app.modules.study_plans.service import delete_study_plan, replace_study_plan, save_study_plan
from app.modules.users.models import User
from tests.fixtures.study_mode_samples import compliant_daily_task, study_subtask


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


class DummyProvider:
    def generate_structured(self, *, prompt: str, output_schema: type[BaseModel]) -> BaseModel:
        raise AssertionError("explicit task payload should not call model provider")


def _seed_owner_course(db: Session) -> tuple[User, Course]:
    user = User(id="usr_lifecycle", username="lifecycle", password_hash="hash", status="active")
    course = Course(id="crs_lifecycle", user_id=user.id, name="数据库", status="active")
    material = CourseMaterial(
        id="mat_seed",
        user_id=user.id,
        course_id=course.id,
        name="seed.txt",
        material_type="text",
        source_type="file",
        file_url="memory://seed.txt",
        file_size=16,
        mime_type="text/plain",
        parse_status="parsed",
    )
    chunk = MaterialChunk(
        id="chk_mat_seed_000001",
        material_id=material.id,
        course_id=course.id,
        chunk_index=1,
        heading="Seed",
        content_text="Seed material",
    )
    db.add_all([user, course, material, chunk])
    db.commit()
    return user, course


def _payload(*, title: str = "数据库计划", day: date = date(2026, 7, 11), second_day: date | None = None) -> StudyPlanSaveRequest:
    tasks: list[dict[str, object]] = [
        # 保存契约要求每天恰好一个测试任务并排在最后（见 tests/fixtures/study_mode_samples.py）。
        compliant_daily_task(
            title=f"{day.isoformat()} 学习任务",
            task_date=day.isoformat(),
            sort_order=1,
            plan_material_ids=["mat_seed"],
            study_subtasks=[
                study_subtask(
                    title="阅读数据库设计",
                    subtask_type="learn",
                    material_ids=["mat_seed"],
                    description="学习数据库设计步骤",
                    sort_order=1,
                ),
                study_subtask(
                    title="复盘数据库设计",
                    subtask_type="review",
                    material_ids=["mat_seed"],
                    description="整理设计流程",
                    sort_order=2,
                ),
            ],
        )
    ]
    if second_day is not None:
        tasks.append(
            {
                "title": f"{second_day.isoformat()} 学习任务",
                "task_date": second_day.isoformat(),
                "sort_order": 2,
                "subtasks": [
                    {
                        "title": "练习 E-R 图",
                        "subtask_type": "test",
                        "description": "完成 E-R 图练习",
                        "related_material_ids": ["mat_seed"],
                        "estimated_minutes": 60,
                        "citation_chunk_ids": [],
                        "sort_order": 1,
                    }
                ],
            }
        )
    return StudyPlanSaveRequest.model_validate(
        {
            "title": title,
            "goal_text": "两周掌握数据库设计",
            "start_date": min(task["task_date"] for task in tasks),
            "end_date": max(task["task_date"] for task in tasks),
            "daily_available_minutes": 60,
            "material_scope": {"include_all_parsed_materials": True, "material_ids": []},
            "preference": "balanced",
            "tasks": tasks,
        }
    )


def _replace_payload(saved_updated_at, *, day: date, second_day: date | None = None) -> StudyPlanReplaceRequest:
    base = _payload(title="替换后的数据库计划", day=day, second_day=second_day).model_dump(mode="json")
    base["expected_updated_at"] = saved_updated_at.isoformat()
    return StudyPlanReplaceRequest.model_validate(base)


def _records(db: Session, user_id: str) -> dict[date, CheckinRecord]:
    rows = db.execute(select(CheckinRecord).where(CheckinRecord.user_id == user_id)).scalars().all()
    return {row.checkin_date: row for row in rows}


def _task_dates(db: Session, plan_id: str) -> set[date]:
    return set(db.execute(select(StudyTask.task_date).where(StudyTask.plan_id == plan_id)).scalars())


def test_save_study_plan_recalculates_new_task_dates(db: Session) -> None:
    user, course = _seed_owner_course(db)

    bundle = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_payload(day=date(2026, 7, 11), second_day=date(2026, 7, 12)),
        model_provider=DummyProvider(),
        max_tokens=4000,
    )

    dates = {task.task_date for task in bundle.tasks}
    records = _records(db, user.id)
    assert set(records) == dates
    assert records[date(2026, 7, 11)].total_subtask_count == 3
    assert records[date(2026, 7, 12)].total_subtask_count == 1
    assert all(record.completed_subtask_count == 0 for record in records.values())


def test_replace_study_plan_recalculates_old_and_new_dates(db: Session) -> None:
    user, course = _seed_owner_course(db)
    saved = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_payload(day=date(2026, 7, 11)),
        model_provider=DummyProvider(),
        max_tokens=4000,
    )
    old_dates = _task_dates(db, saved.plan.id)

    replace_study_plan(
        db,
        user_id=user.id,
        plan_id=saved.plan.id,
        payload=_replace_payload(saved.plan.updated_at, day=date(2026, 7, 12), second_day=date(2026, 7, 13)),
    )

    records = _records(db, user.id)
    assert set(records) == old_dates | {date(2026, 7, 12), date(2026, 7, 13)}
    assert records[date(2026, 7, 11)].total_subtask_count == 0
    assert records[date(2026, 7, 12)].total_subtask_count == 3
    assert records[date(2026, 7, 13)].total_subtask_count == 1


def test_delete_study_plan_recalculates_plan_dates_to_zero_when_no_other_tasks(db: Session) -> None:
    user, course = _seed_owner_course(db)
    saved = save_study_plan(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=_payload(day=date(2026, 7, 11), second_day=date(2026, 7, 12)),
        model_provider=DummyProvider(),
        max_tokens=4000,
    )
    dates = _task_dates(db, saved.plan.id)

    delete_study_plan(db, user_id=user.id, plan_id=saved.plan.id)

    records = _records(db, user.id)
    assert set(records) == dates
    assert all(record.total_subtask_count == 0 for record in records.values())
