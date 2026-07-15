from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
import logging

import pytest
from pydantic import ValidationError
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
from app.modules.generated_content.schemas import FlashcardCardsUpdate
from app.modules.generated_content.service import (
    delete_generated_content,
    get_generated_content_detail,
    list_generated_contents,
    rename_generated_content,
    update_flashcard_cards,
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


def create_content(
    db: Session,
    user_id: str,
    course_id: str,
    content_id: str,
    *,
    content_type: str = "outline",
    generation_status: str = "success",
    deleted_at: datetime | None = None,
    study_subtask_id: str | None = None,
) -> AIGeneratedContent:
    return save_generated_content(
        db,
        AIGeneratedContent(
            id=content_id,
            user_id=user_id,
            course_id=course_id,
            study_subtask_id=study_subtask_id,
            content_type=content_type,
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
    cited = create_content(db, user.id, course.id, "gen_cited", content_type="handout")
    failed = create_content(
        db,
        user.id,
        course.id,
        "gen_failed",
        content_type="handout",
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
    content = create_content(db, user.id, course.id, "gen_detail", content_type="handout")
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


def test_poc_generation_types_ignore_legacy_citation_rows(db: Session) -> None:
    user = register_user(db, UserCreate(username="poc-no-citations", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    content = create_content(db, user.id, course.id, "gen_poc", content_type="mindmap")
    create_citation(
        db,
        citation_id="cit_legacy",
        generated_content_id=content.id,
        material_id="mat_legacy",
        chunk_id="chunk_legacy",
        sort_order=1,
    )

    detail = get_generated_content_detail(db, user_id=user.id, generated_content_id=content.id)

    assert detail.source_citations == []


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


def test_list_generated_contents_excludes_study_plan_handouts_only(db: Session) -> None:
    user = register_user(db, UserCreate(username="course-history", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Computer Networks"))
    outline = create_content(db, user.id, course.id, "gen_outline")
    legacy_handout = create_content(
        db,
        user.id,
        course.id,
        "gen_course_handout",
        content_type="handout",
    )
    study_handout = create_content(
        db,
        user.id,
        course.id,
        "gen_study_handout",
        content_type="handout",
        study_subtask_id="sub_learn",
    )
    task_test = create_content(
        db,
        user.id,
        course.id,
        "gen_task_test",
        content_type="task_test",
        study_subtask_id="sub_quiz",
    )

    listed_ids = {
        content.id for content in list_generated_contents(db, user_id=user.id, course_id=course.id)
    }

    assert listed_ids == {outline.id, legacy_handout.id, task_test.id}
    assert get_generated_content_detail(
        db,
        user_id=user.id,
        generated_content_id=study_handout.id,
    ).id == study_handout.id


def test_rename_generated_content_changes_only_normalized_title(db: Session) -> None:
    user = register_user(db, UserCreate(username="content-renamer", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    content = create_content(db, user.id, course.id, "gen_rename", content_type="handout")
    create_citation(
        db,
        citation_id="cit_rename",
        generated_content_id=content.id,
        material_id="mat_rename",
        chunk_id="chunk_rename",
        sort_order=1,
    )
    original_json = content.content_json
    original_status = content.generation_status
    original_updated_at = content.updated_at

    renamed = rename_generated_content(
        db,
        user_id=user.id,
        generated_content_id=content.id,
        title="  期末重点讲义  ",
    )

    assert renamed.title == "期末重点讲义"
    assert renamed.content_json == original_json
    assert renamed.generation_status == original_status
    assert renamed.updated_at > original_updated_at
    assert [citation.id for citation in renamed.source_citations] == ["cit_rename"]


def test_delete_generated_content_permanently_removes_content_and_citations(db: Session) -> None:
    user = register_user(db, UserCreate(username="content-deleter", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    content = create_content(db, user.id, course.id, "gen_delete", content_type="handout")
    citation = create_citation(
        db,
        citation_id="cit_delete",
        generated_content_id=content.id,
        material_id="mat_delete",
        chunk_id="chunk_delete",
        sort_order=1,
    )

    deleted = delete_generated_content(db, user_id=user.id, generated_content_id=content.id)

    assert deleted.deleted_at is not None
    assert deleted.id == content.id
    assert [item.id for item in deleted.source_citations] == [citation.id]
    assert db.get(AIGeneratedContent, content.id) is None
    assert db.get(SourceCitation, citation.id) is None
    assert list_generated_contents(db, user_id=user.id, course_id=course.id) == []
    with pytest.raises(CourseNexusError) as exc_info:
        get_generated_content_detail(db, user_id=user.id, generated_content_id=content.id)
    assert exc_info.value.code == "NOT_FOUND"


def test_generated_content_mutations_hide_cross_user_records(db: Session) -> None:
    owner = register_user(db, UserCreate(username="content-owner", password="password123"))
    other = register_user(db, UserCreate(username="content-other", password="password123"))
    course = create_course(db, owner.id, CourseCreate(name="Networks"))
    content = create_content(db, owner.id, course.id, "gen_private_mutation")

    with pytest.raises(CourseNexusError) as rename_exc:
        rename_generated_content(
            db,
            user_id=other.id,
            generated_content_id=content.id,
            title="不可修改",
        )
    assert rename_exc.value.code == "NOT_FOUND"

    with pytest.raises(CourseNexusError) as delete_exc:
        delete_generated_content(db, user_id=other.id, generated_content_id=content.id)
    assert delete_exc.value.code == "NOT_FOUND"
    assert get_generated_content_detail(db, user_id=owner.id, generated_content_id=content.id).id == content.id


def test_flashcard_cards_update_rejects_duplicate_fronts_and_oversized_decks() -> None:
    card = {"front": "Question", "back": "Answer", "tags": [], "explanation": None}

    with pytest.raises(ValidationError):
        FlashcardCardsUpdate(cards=[card, {**card, "front": "  question  "}])
    with pytest.raises(ValidationError):
        FlashcardCardsUpdate(cards=[{**card, "front": f"Question {index}"} for index in range(101)])


def test_update_flashcard_cards_persists_normalized_deck_for_owner(
    db: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user = register_user(db, UserCreate(username="flashcard-editor", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Networks"))
    content = create_content(db, user.id, course.id, "gen_flashcards", content_type="flashcard")

    original_updated_at = content.updated_at
    with caplog.at_level(logging.INFO, logger="course_nexus.generated_content.flashcards"):
        result = update_flashcard_cards(
            db,
            user_id=user.id,
            generated_content_id=content.id,
            cards=[
                {"front": " Question one ", "back": " Answer one ", "tags": [], "explanation": None},
                {"front": "Question two", "back": "Answer two", "tags": ["TCP"], "explanation": "Detail"},
            ],
        )

    assert result.content_json == {"cards": [
        {"front": "Question one", "back": "Answer one", "tags": [], "explanation": None, "id": "card_001", "mastery_status": "unknown", "sort_order": 1},
        {"front": "Question two", "back": "Answer two", "tags": ["TCP"], "explanation": "Detail", "id": "card_002", "mastery_status": "unknown", "sort_order": 2},
    ]}
    assert result.updated_at > original_updated_at
    assert "Flashcard deck updated" in caplog.text
    assert f"content={content.id}" in caplog.text
    assert "before=0 after=2" in caplog.text


def test_update_flashcard_cards_rejects_wrong_owner_and_non_flashcard(db: Session) -> None:
    owner = register_user(db, UserCreate(username="flashcard-owner", password="password123"))
    other = register_user(db, UserCreate(username="flashcard-other", password="password123"))
    course = create_course(db, owner.id, CourseCreate(name="Networks"))
    flashcards = create_content(db, owner.id, course.id, "gen_private_flashcards", content_type="flashcard")
    outline = create_content(db, owner.id, course.id, "gen_outline_edit", content_type="outline")
    cards = [{"front": "Q", "back": "A", "tags": [], "explanation": None}]

    with pytest.raises(CourseNexusError) as owner_exc:
        update_flashcard_cards(db, user_id=other.id, generated_content_id=flashcards.id, cards=cards)
    assert owner_exc.value.code == "NOT_FOUND"
    with pytest.raises(CourseNexusError) as type_exc:
        update_flashcard_cards(db, user_id=owner.id, generated_content_id=outline.id, cards=cards)
    assert type_exc.value.code == "INVALID_GENERATED_CONTENT_TYPE"
