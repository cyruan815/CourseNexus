from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import CourseNexusError
from app.db.base import Base
import app.db.models  # noqa: F401
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generated_content.repository import save_generated_content
from app.modules.generated_content.service import get_generated_content_detail, list_generated_contents
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


def create_content(db: Session, user_id: str, course_id: str, content_id: str) -> AIGeneratedContent:
    return save_generated_content(
        db,
        AIGeneratedContent(
            id=content_id,
            user_id=user_id,
            course_id=course_id,
            content_type="outline",
            title="Outline",
            content="Alpha",
            content_json={"items": ["Alpha"]},
            generation_status="success",
        ),
    )


def test_list_and_detail_generated_contents_are_scoped_to_user(db: Session) -> None:
    alice = register_user(db, UserCreate(username="alice", password="password123"))
    bob = register_user(db, UserCreate(username="bob", password="password123"))
    alice_course = create_course(db, alice.id, CourseCreate(name="Linear Algebra"))
    bob_course = create_course(db, bob.id, CourseCreate(name="Databases"))
    alice_content = create_content(db, alice.id, alice_course.id, "gen_alice")
    bob_content = create_content(db, bob.id, bob_course.id, "gen_bob")

    assert [content.id for content in list_generated_contents(db, user_id=alice.id, course_id=alice_course.id)] == [
        alice_content.id
    ]
    assert get_generated_content_detail(db, user_id=alice.id, generated_content_id=alice_content.id).id == alice_content.id

    with pytest.raises(CourseNexusError) as exc_info:
        get_generated_content_detail(db, user_id=alice.id, generated_content_id=bob_content.id)

    assert exc_info.value.code == "NOT_FOUND"
