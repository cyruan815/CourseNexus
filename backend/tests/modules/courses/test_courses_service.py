from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import CourseNexusError
from app.db.base import Base
import app.db.models  # noqa: F401
from app.modules.courses.schemas import CourseCreate, CourseUpdate
from app.modules.courses.service import (
    assert_course_owner,
    create_course,
    delete_course,
    get_course_detail,
    list_courses,
    update_course,
)
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user


@pytest.fixture()
def db() -> Session:
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


def test_create_and_list_courses_are_scoped_to_user(db: Session) -> None:
    alice = register_user(db, UserCreate(username="alice", password="password123"))
    bob = register_user(db, UserCreate(username="bob", password="password123"))

    alice_course = create_course(db, alice.id, CourseCreate(name="Linear Algebra", teacher="Prof. A"))
    create_course(db, bob.id, CourseCreate(name="Databases", teacher="Prof. B"))

    courses = list_courses(db, alice.id)

    assert [course.id for course in courses] == [alice_course.id]
    assert courses[0].user_id == alice.id


def test_assert_course_owner_rejects_other_user_course(db: Session) -> None:
    alice = register_user(db, UserCreate(username="alice", password="password123"))
    bob = register_user(db, UserCreate(username="bob", password="password123"))
    bob_course = create_course(db, bob.id, CourseCreate(name="Databases"))

    with pytest.raises(CourseNexusError) as exc_info:
        assert_course_owner(db, alice.id, bob_course.id)

    assert exc_info.value.code == "NOT_FOUND"


def test_update_course_changes_owned_course_only(db: Session) -> None:
    alice = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, alice.id, CourseCreate(name="Old Name"))

    updated = update_course(
        db,
        alice.id,
        course.id,
        CourseUpdate(name="New Name", description="Updated"),
    )

    assert updated.name == "New Name"
    assert updated.description == "Updated"


def test_delete_course_soft_deletes_and_hides_from_list(db: Session) -> None:
    alice = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, alice.id, CourseCreate(name="Linear Algebra"))

    deleted_course = delete_course(db, alice.id, course.id)

    assert deleted_course.status == "deleted"
    assert isinstance(deleted_course.deleted_at, datetime)
    assert list_courses(db, alice.id) == []

    with pytest.raises(CourseNexusError):
        get_course_detail(db, alice.id, course.id)
