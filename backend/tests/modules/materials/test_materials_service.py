from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
from pathlib import Path
import zipfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import CourseNexusError
from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.rag.base import RagChunk
from app.integrations.rag.fake import FakeRagIndex
import app.modules.materials.service as materials_service
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.materials.schemas import MaterialFolderCreate, MaterialLinkCreate, MaterialUpdate
from app.modules.materials.models import CourseMaterial, MaterialChunk, MaterialFolder
from app.modules.materials.service import (
    create_material_folder,
    create_link_material,
    delete_material_folder,
    delete_material,
    get_material_folder,
    get_material_detail,
    list_course_materials,
    move_material_to_folder,
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


def test_create_link_material_creates_url_material(db: Session) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))

    material = create_link_material(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=MaterialLinkCreate(name="Course Site", source_url="https://example.com/course"),
    )

    assert material.material_type == "link"
    assert material.source_type == "url"
    assert material.source_url == "https://example.com/course"
    assert material.parse_status == "uploaded"


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
    db.commit()
    folder = create_material_folder(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=MaterialFolderCreate(name="Week 1"),
    )
    link_material = create_link_material(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=MaterialLinkCreate(
            name="reference",
            source_url="https://example.com/reference",
            folder_id=folder.id,
        ),
    )
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
    assert db.get(CourseMaterial, link_material.id) is None
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
    chunk = MaterialChunk(
        id="chunk-1",
        material_id=material.id,
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
    assert get_material_detail(db, user.id, material.id).parse_status == "parsed"
    assert get_material_folder(db, user.id, folder.id).deleted_at is None
    assert set(rag_index.records) == {chunk.id}
    assert (tmp_path / material.file_url).exists()


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
    chunk = MaterialChunk(
        id="chunk-1",
        material_id=material.id,
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
