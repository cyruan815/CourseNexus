from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.commands.rebuild_rag_index as rebuild_command
from app.core.config import Settings
from app.core.errors import CourseNexusError
from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.rag.base import RagChunk
from app.integrations.rag.fake import FakeRagIndex
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.materials.models import CourseMaterial, MaterialChunk
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user
from app.commands.rebuild_rag_index import RebuildRagIndexResult, rebuild_all, rebuild_material


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


def test_rebuild_all_indexes_only_parsed_materials(db: Session) -> None:
    user_id, course_id = _create_owner(db)
    first = _material(db, user_id=user_id, course_id=course_id, material_id="mat_first", parse_status="parsed")
    second = _material(db, user_id=user_id, course_id=course_id, material_id="mat_second", parse_status="parsed")
    uploaded = _material(db, user_id=user_id, course_id=course_id, material_id="mat_uploaded", parse_status="uploaded")
    deleted = _material(db, user_id=user_id, course_id=course_id, material_id="mat_deleted", parse_status="deleted")
    deleted.deleted_at = deleted.created_at
    chunks = [
        _chunk(db, first, chunk_id="chk_first_0", text="matrix"),
        _chunk(db, second, chunk_id="chk_second_0", text="history"),
        _chunk(db, uploaded, chunk_id="chk_uploaded_0", text="uploaded"),
        _chunk(db, deleted, chunk_id="chk_deleted_0", text="deleted"),
    ]
    db.commit()
    rag_index = FakeRagIndex.from_chunks([_rag_chunk("stale", user_id=user_id, course_id=course_id)])

    result = rebuild_all(db=db, rag_index=rag_index)

    assert result.material_count == 2
    assert result.chunk_count == 2
    assert set(rag_index.records) == {chunks[0].id, chunks[1].id}


def test_rebuild_material_replaces_single_material_vectors(db: Session) -> None:
    user_id, course_id = _create_owner(db)
    material = _material(db, user_id=user_id, course_id=course_id, material_id="mat_target", parse_status="parsed")
    other = _material(db, user_id=user_id, course_id=course_id, material_id="mat_other", parse_status="parsed")
    current = _chunk(db, material, chunk_id="chk_target_current", text="updated matrix")
    _chunk(db, other, chunk_id="chk_other", text="other")
    db.commit()
    rag_index = FakeRagIndex.from_chunks(
        [
            _rag_chunk("chk_target_old", user_id=user_id, course_id=course_id, material_id=material.id),
            _rag_chunk("chk_other", user_id=user_id, course_id=course_id, material_id=other.id),
        ]
    )

    result = rebuild_material(db=db, rag_index=rag_index, material_id=material.id)

    assert result.material_count == 1
    assert result.chunk_count == 1
    assert set(rag_index.records) == {"chk_other", current.id}
    assert rag_index.records[current.id].text == "updated matrix"


def test_rebuild_material_missing_or_deleted_material_raises_not_found(db: Session) -> None:
    user_id, course_id = _create_owner(db)
    deleted = _material(db, user_id=user_id, course_id=course_id, material_id="mat_deleted", parse_status="deleted")
    deleted.deleted_at = deleted.created_at
    db.commit()

    for material_id in ["mat_missing", deleted.id]:
        with pytest.raises(CourseNexusError) as exc_info:
            rebuild_material(db=db, rag_index=FakeRagIndex(), material_id=material_id)

        assert exc_info.value.code == "NOT_FOUND"


def test_rebuild_material_skips_unparsed_material_and_deletes_stale_vectors(db: Session) -> None:
    user_id, course_id = _create_owner(db)
    material = _material(db, user_id=user_id, course_id=course_id, material_id="mat_uploaded", parse_status="uploaded")
    db.commit()
    rag_index = FakeRagIndex.from_chunks(
        [_rag_chunk("chk_uploaded_stale", user_id=user_id, course_id=course_id, material_id=material.id)]
    )

    result = rebuild_material(db=db, rag_index=rag_index, material_id=material.id)

    assert result.material_count == 0
    assert result.chunk_count == 0
    assert rag_index.records == {}


def test_rebuild_command_passes_embedding_endpoint_to_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeSessionLocal:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_create_openai_chroma_rag_index(
        *,
        persist_path: str,
        collection_name: str,
        api_key: str,
        embedding_model: str,
        api_base_url: str | None,
    ):
        captured.update(
            persist_path=persist_path,
            collection_name=collection_name,
            api_key=api_key,
            embedding_model=embedding_model,
            api_base_url=api_base_url,
        )
        return FakeRagIndex()

    monkeypatch.setattr(
        rebuild_command,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            embedding_api_key="embedding-key",
            embedding_model="text-embedding-3-large",
            embedding_base_url="https://embedding.example/v1",
        ),
    )
    monkeypatch.setattr(rebuild_command, "create_openai_chroma_rag_index", fake_create_openai_chroma_rag_index)
    monkeypatch.setattr(rebuild_command, "SessionLocal", lambda: FakeSessionLocal())
    monkeypatch.setattr(
        rebuild_command,
        "rebuild_all",
        lambda *, db, rag_index: RebuildRagIndexResult(material_count=0, chunk_count=0),
    )

    exit_code = rebuild_command.main(["--all"])

    assert exit_code == 0
    assert captured == {
        "persist_path": "./data/chroma",
        "collection_name": "course_nexus_material_chunks",
        "api_key": "embedding-key",
        "embedding_model": "text-embedding-3-large",
        "api_base_url": "https://embedding.example/v1",
    }


def _create_owner(db: Session) -> tuple[str, str]:
    user = register_user(db, UserCreate(username=f"user_{id(db)}", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    return user.id, course.id


def _material(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_id: str,
    parse_status: str,
) -> CourseMaterial:
    material = CourseMaterial(
        id=material_id,
        user_id=user_id,
        course_id=course_id,
        name=f"{material_id}.txt",
        material_type="text",
        source_type="file",
        file_url=f"{material_id}.txt",
        parse_status=parse_status,
    )
    db.add(material)
    db.flush()
    return material


def _chunk(db: Session, material: CourseMaterial, *, chunk_id: str, text: str) -> MaterialChunk:
    chunk = MaterialChunk(
        id=chunk_id,
        material_id=material.id,
        course_id=material.course_id,
        chunk_index=0,
        page=None,
        page_index=None,
        heading=None,
        content_text=text,
        embedding_id=chunk_id,
    )
    db.add(chunk)
    return chunk


def _rag_chunk(
    chunk_id: str,
    *,
    user_id: str,
    course_id: str,
    material_id: str = "mat_stale",
) -> RagChunk:
    return RagChunk(
        chunk_id=chunk_id,
        user_id=user_id,
        course_id=course_id,
        material_id=material_id,
        folder_id=None,
        chunk_index=0,
        text="stale",
        page=None,
        page_index=None,
        heading=None,
    )
