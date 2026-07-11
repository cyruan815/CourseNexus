from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import CourseNexusError
from app.db.base import Base
import app.db.models  # noqa: F401
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
import app.modules.generated_content.repository as generated_content_repository
import app.modules.generated_content.service as generated_content_service
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


def create_content(
    db: Session,
    user_id: str,
    course_id: str,
    content_id: str,
    *,
    generation_status: str = "success",
    deleted_at: datetime | None = None,
) -> AIGeneratedContent:
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
            generation_status=generation_status,
            deleted_at=deleted_at,
        ),
    )


def create_citation(
    db: Session,
    *,
    citation_id: str,
    generated_content_id: str,
    material_id: str,
    chunk_id: str | None,
    sort_order: int | None,
) -> SourceCitation:
    citation = SourceCitation(
        id=citation_id,
        generated_content_id=generated_content_id,
        material_id=material_id,
        chunk_id=chunk_id,
        material_name=f"{material_id}.md",
        page="p-2",
        page_index=1,
        hit_text=f"hit-{citation_id}",
        sort_order=sort_order,
    )
    db.add(citation)
    db.commit()
    db.refresh(citation)
    return citation


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


def test_list_generated_contents_groups_ordered_citations_and_uses_one_bulk_query(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = register_user(db, UserCreate(username="citation-list", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    cited = create_content(db, user.id, course.id, "gen_cited")
    failed = create_content(
        db,
        user.id,
        course.id,
        "gen_failed",
        generation_status="failed",
    )
    create_citation(
        db,
        citation_id="cit_b",
        generated_content_id=cited.id,
        material_id="mat_a",
        chunk_id="chunk_b",
        sort_order=1,
    )
    create_citation(
        db,
        citation_id="cit_a",
        generated_content_id=cited.id,
        material_id="mat_a",
        chunk_id="chunk_a",
        sort_order=1,
    )
    create_citation(
        db,
        citation_id="cit_c",
        generated_content_id=cited.id,
        material_id="mat_b",
        chunk_id=None,
        sort_order=2,
    )
    create_citation(
        db,
        citation_id="cit_z",
        generated_content_id=cited.id,
        material_id="mat_b",
        chunk_id="chunk_z",
        sort_order=None,
    )
    calls: list[list[str]] = []

    def recording_bulk_query(session: Session, generated_content_ids: list[str]) -> list[SourceCitation]:
        calls.append(generated_content_ids)
        return generated_content_repository.list_generated_content_citations(session, generated_content_ids)

    monkeypatch.setattr(
        generated_content_service,
        "list_generated_content_citations",
        recording_bulk_query,
        raising=False,
    )

    contents = list_generated_contents(db, user_id=user.id, course_id=course.id)
    contents_by_id = {content.id: content for content in contents}

    assert calls == [[content.id for content in contents]]
    assert set(contents_by_id) == {cited.id, failed.id}
    assert [citation.id for citation in contents_by_id[cited.id].source_citations] == [
        "cit_a",
        "cit_b",
        "cit_c",
        "cit_z",
    ]
    assert [citation.sort_order for citation in contents_by_id[cited.id].source_citations] == [
        1,
        1,
        2,
        None,
    ]
    assert contents_by_id[cited.id].source_citations[0].model_dump() == {
        "id": "cit_a",
        "material_id": "mat_a",
        "chunk_id": "chunk_a",
        "material_name": "mat_a.md",
        "page": "p-2",
        "page_index": 1,
        "hit_text": "hit-cit_a",
        "sort_order": 1,
    }
    assert contents_by_id[failed.id].source_citations == []


def test_generated_content_detail_returns_ordered_citations(db: Session) -> None:
    user = register_user(db, UserCreate(username="citation-detail", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    content = create_content(db, user.id, course.id, "gen_detail")
    create_citation(
        db,
        citation_id="cit_2",
        generated_content_id=content.id,
        material_id="mat_detail",
        chunk_id=None,
        sort_order=2,
    )
    create_citation(
        db,
        citation_id="cit_1",
        generated_content_id=content.id,
        material_id="mat_detail",
        chunk_id="chunk_1",
        sort_order=1,
    )

    detail = get_generated_content_detail(db, user_id=user.id, generated_content_id=content.id)

    assert [citation.id for citation in detail.source_citations] == ["cit_1", "cit_2"]
    assert detail.source_citations[1].sort_order == 2
    assert detail.source_citations[1].chunk_id is None


def test_cross_user_detail_does_not_load_or_expose_citations(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alice = register_user(db, UserCreate(username="citation-owner", password="password123"))
    bob = register_user(db, UserCreate(username="citation-intruder", password="password123"))
    course = create_course(db, alice.id, CourseCreate(name="Linear Algebra"))
    content = create_content(db, alice.id, course.id, "gen_private")
    create_citation(
        db,
        citation_id="cit_private",
        generated_content_id=content.id,
        material_id="mat_private",
        chunk_id="chunk_private",
        sort_order=1,
    )

    def unexpected_citation_query(session: Session, generated_content_ids: list[str]) -> list[SourceCitation]:
        raise AssertionError("citations must not load before the ownership check")

    monkeypatch.setattr(
        generated_content_service,
        "list_generated_content_citations",
        unexpected_citation_query,
        raising=False,
    )

    with pytest.raises(CourseNexusError) as exc_info:
        get_generated_content_detail(db, user_id=bob.id, generated_content_id=content.id)

    assert exc_info.value.code == "NOT_FOUND"


def test_soft_deleted_generated_contents_remain_excluded(db: Session) -> None:
    user = register_user(db, UserCreate(username="citation-deleted", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    deleted = create_content(
        db,
        user.id,
        course.id,
        "gen_deleted",
        deleted_at=datetime.now(timezone.utc),
    )

    assert list_generated_contents(db, user_id=user.id, course_id=course.id) == []
    with pytest.raises(CourseNexusError) as exc_info:
        get_generated_content_detail(db, user_id=user.id, generated_content_id=deleted.id)
    assert exc_info.value.code == "NOT_FOUND"
