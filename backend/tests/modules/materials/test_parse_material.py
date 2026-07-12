from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
import logging
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import CourseNexusError
from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.parsers.base import ParseDiagnostics, ParseWarning, ParsedChunk, ParsedDocument
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.materials.models import MaterialChunk
from app.modules.materials.service import delete_material, parse_material, upload_file_material
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user


class DiagnosticParser:
    def __init__(self, *, partial: bool) -> None:
        warning = ParseWarning(code="OCR_MEMORY_ERROR", message="OCR 内存分配失败", page_no=17)
        self.document = ParsedDocument(
            chunks=[ParsedChunk(chunk_index=0, content_text="Kept", page="16", page_index=15)],
            diagnostics=ParseDiagnostics(
                parser="docling",
                profile="pdf_text_first",
                conversion_status="partial_success" if partial else "success",
                page_count=59,
                processed_pages=tuple(range(1, 60)),
                pages_with_content=(16,),
                pages_with_chunks=(16,),
                failed_pages=(17,) if partial else (),
                warnings=(warning,) if partial else (),
            ),
        )

    def parse(self, file_path: Path) -> ParsedDocument:
        return self.document


def capture_course_logs(caplog) -> logging.Logger:
    logger = logging.getLogger("course_nexus")
    logger.addHandler(caplog.handler)
    logger.setLevel(logging.INFO)
    return logger


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


def create_uploaded_material(db: Session, tmp_path: Path, filename: str = "notes.md"):
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material = upload_file_material(
        db,
        user_id=user.id,
        course_id=course.id,
        filename=filename,
        stream=BytesIO(b"# Intro\nAlpha\n"),
        content_type="text/markdown",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )
    return user, course, material


def material_chunks(db: Session, material_id: str) -> list[MaterialChunk]:
    return list(
        db.execute(
            select(MaterialChunk)
            .where(MaterialChunk.material_id == material_id)
            .order_by(MaterialChunk.chunk_index)
        ).scalars()
    )


def test_parse_material_writes_chunks_and_marks_parsed(db: Session, tmp_path: Path, caplog) -> None:
    logger = capture_course_logs(caplog)
    user, course, material = create_uploaded_material(db, tmp_path)
    rag_index = FakeRagIndex()

    try:
        parsed = parse_material(
            db,
            user_id=user.id,
            material_id=material.id,
            parser=PlainTextParser(),
            rag_index=rag_index,
            storage_root=tmp_path,
        )
    finally:
        logger.removeHandler(caplog.handler)

    chunks = material_chunks(db, material.id)
    assert parsed.parse_status == "parsed"
    assert parsed.parse_error is None
    assert len(chunks) == 1
    assert chunks[0].course_id == course.id
    assert chunks[0].chunk_index == 0
    assert chunks[0].heading == "Intro"
    assert chunks[0].content_text == "Alpha"
    assert chunks[0].id == f"chk_{material.id.removeprefix('mat_')}_000000"
    assert chunks[0].embedding_id == chunks[0].id
    assert {record.material_id for record in rag_index.records.values()} == {material.id}
    assert {record.course_id for record in rag_index.records.values()} == {course.id}
    assert {record.user_id for record in rag_index.records.values()} == {user.id}
    record = next(record for record in caplog.records if record.name.endswith("materials.parse"))
    assert "解析成功" in record.getMessage()
    assert f"material={material.id}" in record.getMessage()
    assert "chunks=1" in record.getMessage()
    assert "cost_ms=" in record.getMessage()


def test_parse_material_persists_complete_diagnostics(db: Session, tmp_path: Path) -> None:
    user, _, material = create_uploaded_material(db, tmp_path)

    parsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=DiagnosticParser(partial=False),
        rag_index=FakeRagIndex(),
        storage_root=tmp_path,
    )

    assert parsed.parse_status == "parsed"
    assert parsed.parse_quality == "complete"
    assert parsed.page_count == 59
    assert parsed.parse_diagnostics_json["conversion_status"] == "success"
    assert parsed.parse_diagnostics_json["failed_pages"] == []
    assert parsed.parse_diagnostics_json["warnings"] == []


def test_parse_material_keeps_chunks_and_marks_partial_diagnostics(db: Session, tmp_path: Path) -> None:
    user, _, material = create_uploaded_material(db, tmp_path)

    parsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=DiagnosticParser(partial=True),
        rag_index=FakeRagIndex(),
        storage_root=tmp_path,
    )

    assert parsed.parse_status == "parsed"
    assert parsed.parse_quality == "partial"
    assert parsed.page_count == 59
    assert [chunk.content_text for chunk in material_chunks(db, material.id)] == ["Kept"]
    assert parsed.parse_diagnostics_json["failed_pages"] == [17]
    assert parsed.parse_diagnostics_json["warnings"][0] == {
        "code": "OCR_MEMORY_ERROR",
        "message": "OCR 内存分配失败",
        "page_no": 17,
        "component": None,
        "severity": "warning",
    }


def test_reparse_replaces_previous_partial_diagnostics(db: Session, tmp_path: Path) -> None:
    user, _, material = create_uploaded_material(db, tmp_path)
    rag_index = FakeRagIndex()
    parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=DiagnosticParser(partial=True),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    reparsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=DiagnosticParser(partial=False),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    assert reparsed.parse_quality == "complete"
    assert reparsed.parse_diagnostics_json["failed_pages"] == []
    assert reparsed.parse_diagnostics_json["warnings"] == []


def test_parse_failure_clears_previous_diagnostics(db: Session, tmp_path: Path) -> None:
    class FailingParser:
        def parse(self, file_path: Path) -> ParsedDocument:
            raise CourseNexusError(code="PARSE_FAILED", message="解析失败")

    user, _, material = create_uploaded_material(db, tmp_path)
    rag_index = FakeRagIndex()
    parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=DiagnosticParser(partial=True),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    failed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=FailingParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    assert failed.parse_status == "parse_failed"
    assert failed.parse_quality == "unknown"
    assert failed.page_count is None
    assert failed.parse_diagnostics_json is None


def test_parse_material_failure_marks_parse_failed(db: Session, tmp_path: Path, caplog) -> None:
    class FailingParser:
        def parse(self, file_path: Path):
            raise ValueError("broken pdf")

    logger = capture_course_logs(caplog)
    user, _, material = create_uploaded_material(db, tmp_path)

    try:
        parsed = parse_material(
            db,
            user_id=user.id,
            material_id=material.id,
            parser=FailingParser(),
            rag_index=FakeRagIndex(),
            storage_root=tmp_path,
        )
    finally:
        logger.removeHandler(caplog.handler)

    assert parsed.parse_status == "parse_failed"
    assert parsed.parse_error == "PARSE_FAILED"
    assert material_chunks(db, material.id) == []
    record = next(record for record in caplog.records if record.name.endswith("materials.parse"))
    assert "解析失败：文件内容无法识别" in record.getMessage()
    assert "code=PARSE_FAILED" in record.getMessage()
    assert isinstance(record.exc_info[1], ValueError)


def test_reparse_material_replaces_old_chunks(db: Session, tmp_path: Path) -> None:
    user, _, material = create_uploaded_material(db, tmp_path)
    parser = PlainTextParser()
    rag_index = FakeRagIndex()
    parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=parser,
        rag_index=rag_index,
        storage_root=tmp_path,
    )
    (tmp_path / material.file_url).write_text("First\n\nSecond\n", encoding="utf-8")

    reparsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=parser,
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    chunks = material_chunks(db, material.id)
    assert reparsed.parse_status == "parsed"
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert [chunk.content_text for chunk in chunks] == ["First", "Second"]
    assert set(rag_index.records) == {
        f"chk_{material.id.removeprefix('mat_')}_000000",
        f"chk_{material.id.removeprefix('mat_')}_000001",
    }


def test_reparse_material_deletes_old_vectors_before_reindex(db: Session, tmp_path: Path) -> None:
    class RecordingRagIndex(FakeRagIndex):
        def __init__(self) -> None:
            super().__init__()
            self.deleted_material_ids: list[str] = []
            self.operations: list[tuple[str, str]] = []

        def delete_material(self, material_id: str) -> None:
            self.deleted_material_ids.append(material_id)
            self.operations.append(("delete", material_id))
            super().delete_material(material_id)

        def index_chunks(self, chunks):
            indexed_chunks = list(chunks)
            self.operations.extend(("index", chunk.material_id) for chunk in indexed_chunks)
            super().index_chunks(indexed_chunks)

    user, _, material = create_uploaded_material(db, tmp_path)
    parser = PlainTextParser()
    rag_index = RecordingRagIndex()
    parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=parser,
        rag_index=rag_index,
        storage_root=tmp_path,
    )
    (tmp_path / material.file_url).write_text("Only replacement\n", encoding="utf-8")

    parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=parser,
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    assert rag_index.deleted_material_ids == [material.id, material.id]
    assert rag_index.operations == [
        ("delete", material.id),
        ("index", material.id),
        ("delete", material.id),
        ("index", material.id),
    ]


def test_deleted_material_cannot_be_parsed(db: Session, tmp_path: Path) -> None:
    user, _, material = create_uploaded_material(db, tmp_path)
    delete_material(
        db,
        user.id,
        material.id,
        rag_index=FakeRagIndex(),
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )

    with pytest.raises(CourseNexusError) as exc_info:
        parse_material(
            db,
            user_id=user.id,
            material_id=material.id,
            parser=PlainTextParser(),
            rag_index=FakeRagIndex(),
            storage_root=tmp_path,
        )

    assert exc_info.value.code == "NOT_FOUND"


def test_parse_indexes_every_saved_chunk(db: Session, tmp_path: Path) -> None:
    rag_index = FakeRagIndex()
    user, course, material = create_uploaded_material(db, tmp_path)

    parsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    assert parsed.parse_status == "parsed"
    assert {record.material_id for record in rag_index.records.values()} == {material.id}
    assert {record.course_id for record in rag_index.records.values()} == {course.id}


def test_parse_material_index_failure_marks_failed_and_clears_chunks(db: Session, tmp_path: Path) -> None:
    class FailingRagIndex(FakeRagIndex):
        def index_chunks(self, chunks):
            super().index_chunks(chunks)
            raise CourseNexusError(code="INDEXING_FAILED", message="索引失败", status_code=502)

    rag_index = FailingRagIndex()
    user, _, material = create_uploaded_material(db, tmp_path)

    parsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    assert parsed.parse_status == "parse_failed"
    assert parsed.parse_error == "INDEXING_FAILED"
    assert material_chunks(db, material.id) == []
    assert rag_index.records == {}


def test_parse_material_normalizes_index_errors_to_indexing_failed(db: Session, tmp_path: Path, caplog) -> None:
    class UnexpectedRagIndex(FakeRagIndex):
        def index_chunks(self, chunks):
            raise ValueError("broken vector store")

    logger = capture_course_logs(caplog)
    user, _, material = create_uploaded_material(db, tmp_path)

    try:
        parsed = parse_material(
            db,
            user_id=user.id,
            material_id=material.id,
            parser=PlainTextParser(),
            rag_index=UnexpectedRagIndex(),
            storage_root=tmp_path,
        )
    finally:
        logger.removeHandler(caplog.handler)

    assert parsed.parse_status == "parse_failed"
    assert parsed.parse_error == "INDEXING_FAILED"
    record = next(record for record in caplog.records if record.name.endswith("rag.index"))
    assert "索引失败" in record.getMessage()
    assert "code=INDEXING_FAILED" in record.getMessage()
    assert isinstance(record.exc_info[1], ValueError)


def test_parse_material_index_failure_still_marks_failed_when_cleanup_raises(db: Session, tmp_path: Path) -> None:
    class FailingCleanupRagIndex(FakeRagIndex):
        def index_chunks(self, chunks):
            super().index_chunks(chunks)
            raise CourseNexusError(code="INDEXING_FAILED", message="索引失败", status_code=502)

        def delete_material(self, material_id: str) -> None:
            raise CourseNexusError(code="INDEXING_FAILED", message="删除失败", status_code=502)

    user, _, material = create_uploaded_material(db, tmp_path)

    parsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=FailingCleanupRagIndex(),
        storage_root=tmp_path,
    )

    assert parsed.parse_status == "parse_failed"
    assert parsed.parse_error == "INDEXING_FAILED"
    assert material_chunks(db, material.id) == []


def test_delete_material_removes_vectors(db: Session, tmp_path: Path) -> None:
    rag_index = FakeRagIndex()
    user, _, material = create_uploaded_material(db, tmp_path)
    parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    deleted = delete_material(
        db,
        user.id,
        material.id,
        rag_index=rag_index,
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )

    assert deleted.parse_status == "deleted"
    assert rag_index.records == {}


def test_delete_material_requires_rag_index(db: Session, tmp_path: Path) -> None:
    user, _, material = create_uploaded_material(db, tmp_path)

    with pytest.raises(TypeError):
        delete_material(db, user.id, material.id)
