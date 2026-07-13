from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.commands.seed_generated_content_demo import seed_demo_generated_content
from app.db.base import Base
import app.db.models  # noqa: F401
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.models import Course
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.materials.models import CourseMaterial, MaterialChunk
from app.modules.users.models import User


def _db() -> Generator[Session, None, None]:
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


def test_seed_demo_generated_content_creates_loginable_demo_graph() -> None:
    db = next(_db())

    result = seed_demo_generated_content(db=db)

    user = db.get(User, result.user_id)
    course = db.get(Course, result.course_id)
    material = db.get(CourseMaterial, result.material_id)
    chunk = db.get(MaterialChunk, result.chunk_id)
    content = db.get(AIGeneratedContent, result.generated_content_id)

    assert user is not None
    assert user.username == "demo@example.com"
    assert user.password_hash != "password123"
    assert course is not None
    assert course.user_id == user.id
    assert material is not None
    assert material.parse_status == "parsed"
    assert chunk is not None
    assert chunk.material_id == material.id
    assert content is not None
    assert content.user_id == user.id
    assert content.course_id == course.id
    assert content.content_type == "outline"
    assert content.generation_status == "success"
    assert content.content_json["sections"][0]["title"] == "1. Functions and Limits"
    assert db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == content.id)).scalars().all() == []


def test_seed_demo_generated_content_is_idempotent() -> None:
    db = next(_db())

    first = seed_demo_generated_content(db=db)
    second = seed_demo_generated_content(db=db)

    assert second == first
    assert len(db.execute(select(User)).scalars().all()) == 1
    assert len(db.execute(select(Course)).scalars().all()) == 1
    assert len(db.execute(select(AIGeneratedContent)).scalars().all()) == 1
    assert len(db.execute(select(SourceCitation)).scalars().all()) == 0
