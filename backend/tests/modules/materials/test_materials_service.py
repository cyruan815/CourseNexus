from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
from pathlib import Path
import zipfile

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import CourseNexusError
from app.db.base import Base
from app.db.session import create_database_engine
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.base import RagChunk
from app.integrations.rag.fake import FakeRagIndex
import app.modules.materials.service as materials_service
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.materials.schemas import MaterialFolderCreate, MaterialUpdate
from app.modules.materials.models import CourseMaterial, MaterialChunk, MaterialFolder, MaterialParseVersion
from app.modules.materials.service import (
    create_material_folder,
    delete_material_folder,
    delete_material,
    get_material_folder,
    get_material_detail,
    list_course_materials,
    move_material_to_folder,
    parse_material,
    rename_material,
    upload_file_material,
)
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user


def test_materials_service_depends_on_file_storage_protocol_not_local_adapter() -> None:
    source = Path(materials_service.__file__).read_text(encoding="utf-8")

    assert "app.integrations.file_storage.local" not in source


def office_stream(member_name: str) -> BytesIO:
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(member_name, "<xml />")
    stream.seek(0)
    return stream


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


def _activate_material_version(db: Session, material: CourseMaterial) -> MaterialParseVersion:
    version = MaterialParseVersion(
        id=f"mpv_{material.id}",
        material_id=material.id,
        course_id=material.course_id,
        user_id=material.user_id,
        status="active",
        parse_quality="complete",
    )
    material.active_parse_version_id = version.id
    db.add_all([material, version])
    return version


def test_upload_file_material_creates_uploaded_material(db: Session, tmp_path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)

    material = upload_file_material(
        db,
        user_id=user.id,
        course_id=course.id,
        filename="notes.md",
        stream=BytesIO(b"# Intro"),
        content_type="application/octet-stream",
        storage=storage,
    )

    assert material.course_id == course.id
    assert material.user_id == user.id
    assert material.name == "notes.md"
    assert material.material_type == "markdown"
    assert material.source_type == "file"
    assert material.file_size == 7
    assert material.mime_type == "text/markdown"
    assert material.parse_status == "uploaded"
    assert material.file_url == f"{user.id}/{course.id}/{material.id}/source.md"
    assert (tmp_path / material.file_url).read_text(encoding="utf-8") == "# Intro"


@pytest.mark.parametrize(
    ("filename", "stream", "material_type", "mime_type"),
    [
        ("slides.pdf", BytesIO(b"%PDF-1.7\n%%EOF"), "pdf", "application/pdf"),
        (
            "notes.docx",
            office_stream("word/document.xml"),
            "word",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (
            "deck.pptx",
            office_stream("ppt/presentation.xml"),
            "ppt",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ),
        ("diagram.png", BytesIO(b"\x89PNG\r\n\x1a\nrest"), "image", "image/png"),
        ("photo.jpeg", BytesIO(b"\xff\xd8\xff\xe0rest"), "image", "image/jpeg"),
    ],
)
def test_upload_file_material_accepts_complex_formats(
    db: Session,
    tmp_path,
    filename: str,
    stream: BytesIO,
    material_type: str,
    mime_type: str,
) -> None:
    user = register_user(db, UserCreate(username=f"alice_{material_type}_{filename}", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)

    material = upload_file_material(
        db,
        user_id=user.id,
        course_id=course.id,
        filename=filename,
        stream=stream,
        content_type="application/octet-stream",
        storage=storage,
    )

    assert material.material_type == material_type
    assert material.mime_type == mime_type
    assert material.parse_status == "uploaded"


def test_parse_material_rejects_legacy_url_material_without_state_change(db: Session, tmp_path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    legacy_url = CourseMaterial(
        id="mat_legacy_url",
        course_id=course.id,
        user_id=user.id,
        name="Course Site",
        material_type="link",
        source_type="url",
        source_url="https://example.com/course",
        parse_status="uploaded",
    )
    db.add(legacy_url)
    db.commit()

    with pytest.raises(CourseNexusError) as exc_info:
        parse_material(
            db,
            user_id=user.id,
            material_id=legacy_url.id,
            parser=PlainTextParser(),
            rag_index=FakeRagIndex(),
            storage_root=tmp_path,
        )

    assert exc_info.value.code == "MATERIAL_LINK_REMOVED"
    assert exc_info.value.status_code == 409
    refreshed = db.get(CourseMaterial, legacy_url.id)
    assert refreshed.parse_status == "uploaded"
    assert refreshed.parse_error is None


def test_rename_material_only_changes_display_name(db: Session, tmp_path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material = upload_file_material(
        db,
        user_id=user.id,
        course_id=course.id,
        filename="notes.txt",
        stream=BytesIO(b"notes"),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )
    original_file_url = material.file_url

    renamed = rename_material(
        db,
        user_id=user.id,
        material_id=material.id,
        payload=MaterialUpdate(name="  Week 1 Notes  "),
    )

    assert renamed.name == "Week 1 Notes"
    assert renamed.file_url == original_file_url
    assert renamed.parse_status == "uploaded"


def test_list_and_detail_are_scoped_to_user(db: Session, tmp_path) -> None:
    alice = register_user(db, UserCreate(username="alice", password="password123"))
    bob = register_user(db, UserCreate(username="bob", password="password123"))
    alice_course = create_course(db, alice.id, CourseCreate(name="Linear Algebra"))
    bob_course = create_course(db, bob.id, CourseCreate(name="Databases"))
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)
    alice_material = upload_file_material(
        db,
        user_id=alice.id,
        course_id=alice_course.id,
        filename="alice.txt",
        stream=BytesIO(b"alice notes"),
        content_type="text/plain",
        storage=storage,
    )
    bob_material = upload_file_material(
        db,
        user_id=bob.id,
        course_id=bob_course.id,
        filename="bob.txt",
        stream=BytesIO(b"bob notes"),
        content_type="text/plain",
        storage=storage,
    )

    assert [material.id for material in list_course_materials(db, alice.id, alice_course.id)] == [alice_material.id]
    assert get_material_detail(db, alice.id, alice_material.id).id == alice_material.id

    with pytest.raises(CourseNexusError) as exc_info:
        get_material_detail(db, alice.id, bob_material.id)

    assert exc_info.value.code == "NOT_FOUND"


def test_delete_material_permanently_removes_database_row_and_file(db: Session, tmp_path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material = upload_file_material(
        db,
        user_id=user.id,
        course_id=course.id,
        filename="notes.txt",
        stream=BytesIO(b"notes"),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )

    source_path = tmp_path / material.file_url
    deleted = delete_material(
        db,
        user.id,
        material.id,
        rag_index=FakeRagIndex(),
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )

    assert deleted.parse_status == "deleted"
    assert deleted.deleted_at is not None
    assert db.get(CourseMaterial, material.id) is None
    assert not source_path.exists()
    assert list_course_materials(db, user.id, course.id) == []


def test_moving_and_deleting_folder_updates_material_and_rag_metadata(db: Session, tmp_path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material = upload_file_material(
        db,
        user_id=user.id,
        course_id=course.id,
        filename="notes.txt",
        stream=BytesIO(b"matrix notes"),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )
    material.parse_status = "parsed"
    parse_version = _activate_material_version(db, material)
    material.parse_status = "parsing"
    db.commit()
    folder = create_material_folder(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=MaterialFolderCreate(name="Week 1"),
    )
    legacy_url_material = CourseMaterial(
        id="mat_legacy_url",
        course_id=course.id,
        user_id=user.id,
        name="reference",
        material_type="link",
        source_type="url",
        source_url="https://example.com/reference",
        folder_id=folder.id,
        parse_status="uploaded",
    )
    db.add(legacy_url_material)
    db.commit()
    rag_index = FakeRagIndex.from_chunks(
        [
            RagChunk(
                chunk_id="chunk-1",
                user_id=user.id,
                course_id=course.id,
                material_id=material.id,
                folder_id=None,
                chunk_index=0,
                text="matrix notes",
                page=None,
                page_index=None,
                heading=None,
            )
        ]
    )

    moved = move_material_to_folder(
        db,
        user_id=user.id,
        material_id=material.id,
        folder_id=folder.id,
        rag_index=rag_index,
    )

    assert moved.folder_id == folder.id
    assert rag_index.records["chunk-1"].folder_id == folder.id
    chunk = MaterialChunk(
        id="chunk-1",
        material_id=material.id,
        parse_version_id=parse_version.id,
        course_id=course.id,
        chunk_index=0,
        content_text="matrix notes",
        embedding_id="chunk-1",
    )
    generated_content = AIGeneratedContent(
        id="gen-1",
        user_id=user.id,
        course_id=course.id,
        content_type="note",
        title="Matrix summary",
        generation_status="success",
    )
    citation = SourceCitation(
        id="cit-1",
        generated_content_id=generated_content.id,
        material_id=material.id,
        chunk_id=chunk.id,
        material_name=material.name,
        page="1",
        hit_text="matrix notes",
    )
    db.add_all([chunk, generated_content, citation])
    db.commit()

    source_path = tmp_path / material.file_url
    deleted_folder = delete_material_folder(
        db,
        user_id=user.id,
        folder_id=folder.id,
        rag_index=rag_index,
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )

    assert deleted_folder.deleted_at is not None
    assert db.get(MaterialFolder, folder.id) is None
    assert db.get(CourseMaterial, material.id) is None
    assert db.get(CourseMaterial, legacy_url_material.id) is None
    assert db.get(MaterialChunk, "chunk-1") is None
    preserved_citation = db.get(SourceCitation, citation.id)
    assert db.get(AIGeneratedContent, generated_content.id) is not None
    assert preserved_citation is not None
    assert preserved_citation.material_id is None
    assert preserved_citation.chunk_id is None
    assert preserved_citation.material_name == "notes.txt"
    assert preserved_citation.hit_text == "matrix notes"
    assert not source_path.exists()
    assert list_course_materials(db, user.id, course.id) == []
    assert rag_index.records == {}


def test_delete_folder_rag_failure_rolls_back_database_and_restores_vectors(db: Session, tmp_path) -> None:
    class FailingDeleteRagIndex(FakeRagIndex):
        def delete_materials(self, material_ids):
            super().delete_materials(material_ids)
            raise CourseNexusError(code="INDEXING_FAILED", message="删除失败", status_code=502)

    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    folder = create_material_folder(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=MaterialFolderCreate(name="Week 1"),
    )
    material = upload_file_material(
        db,
        user_id=user.id,
        course_id=course.id,
        folder_id=folder.id,
        filename="notes.txt",
        stream=BytesIO(b"matrix notes"),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )
    material.parse_status = "parsed"
    parse_version = _activate_material_version(db, material)
    material.parse_status = "parsing"
    chunk = MaterialChunk(
        id="chunk-1",
        material_id=material.id,
        parse_version_id=parse_version.id,
        course_id=course.id,
        chunk_index=0,
        content_text="matrix notes",
        embedding_id="chunk-1",
    )
    db.add_all([material, chunk])
    db.commit()
    rag_index = FailingDeleteRagIndex.from_chunks(
        [
            RagChunk(
                chunk_id=chunk.id,
                user_id=user.id,
                course_id=course.id,
                material_id=material.id,
                folder_id=folder.id,
                chunk_index=0,
                text=chunk.content_text,
                page=None,
                page_index=None,
                heading=None,
            )
        ]
    )

    with pytest.raises(CourseNexusError) as exc_info:
        delete_material_folder(
            db,
            user_id=user.id,
            folder_id=folder.id,
            rag_index=rag_index,
            storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
        )

    assert exc_info.value.code == "INDEXING_FAILED"
    assert get_material_detail(db, user.id, material.id).parse_status == "parsing"
    assert get_material_folder(db, user.id, folder.id).deleted_at is None
    assert set(rag_index.records) == {chunk.id}
    assert (tmp_path / material.file_url).exists()


def test_delete_material_cascades_parse_versions_with_foreign_keys(tmp_path) -> None:
    database_path = tmp_path / "foreign-keys.db"
    engine = create_database_engine(f"sqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    storage_root = tmp_path / "uploads"
    storage = LocalFileStorage(root_path=storage_root, max_file_size_bytes=1024)
    rag_index = FakeRagIndex()

    with testing_session() as db:
        user = register_user(db, UserCreate(username="fk-delete", password="password123"))
        course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
        material = upload_file_material(
            db,
            user_id=user.id,
            course_id=course.id,
            filename="notes.txt",
            stream=BytesIO(b"matrix notes"),
            content_type="text/plain",
            storage=storage,
        )
        parsed = parse_material(
            db,
            user_id=user.id,
            material_id=material.id,
            parser=PlainTextParser(),
            rag_index=rag_index,
            storage_root=storage_root,
        )
        version_id = parsed.active_parse_version_id
        assert version_id is not None

        delete_material(
            db,
            user_id=user.id,
            material_id=material.id,
            rag_index=rag_index,
            storage=storage,
        )

        assert db.get(CourseMaterial, material.id) is None
        assert db.get(MaterialParseVersion, version_id) is None
        assert db.execute(
            select(MaterialChunk).where(MaterialChunk.material_id == material.id)
        ).scalars().all() == []
        assert rag_index.records == {}

    engine.dispose()


def test_delete_folder_commit_failure_rolls_back_database_and_restores_vectors(
    db: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    folder = create_material_folder(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=MaterialFolderCreate(name="Week 1"),
    )
    material = upload_file_material(
        db,
        user_id=user.id,
        course_id=course.id,
        folder_id=folder.id,
        filename="notes.txt",
        stream=BytesIO(b"matrix notes"),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )
    material.parse_status = "parsed"
    parse_version = _activate_material_version(db, material)
    chunk = MaterialChunk(
        id="chunk-1",
        material_id=material.id,
        parse_version_id=parse_version.id,
        course_id=course.id,
        chunk_index=0,
        content_text="matrix notes",
        embedding_id="chunk-1",
    )
    db.add_all([material, chunk])
    db.commit()
    rag_index = FakeRagIndex.from_chunks(
        [
            RagChunk(
                chunk_id=chunk.id,
                user_id=user.id,
                course_id=course.id,
                material_id=material.id,
                folder_id=folder.id,
                chunk_index=0,
                text=chunk.content_text,
                page=None,
                page_index=None,
                heading=None,
            )
        ]
    )

    monkeypatch.setattr(db, "commit", lambda: (_ for _ in ()).throw(RuntimeError("commit failed")))

    with pytest.raises(RuntimeError, match="commit failed"):
        delete_material_folder(
            db,
            user_id=user.id,
            folder_id=folder.id,
            rag_index=rag_index,
            storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
        )

    assert get_material_detail(db, user.id, material.id).parse_status == "parsed"
    assert get_material_folder(db, user.id, folder.id).deleted_at is None
    assert set(rag_index.records) == {chunk.id}
    assert (tmp_path / material.file_url).exists()
