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
from app.modules.materials.models import MaterialChunk, MaterialParseVersion
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


def parse_versions(db: Session, material_id: str) -> list[MaterialParseVersion]:
    return list(
        db.execute(
            select(MaterialParseVersion)
            .where(MaterialParseVersion.material_id == material_id)
            .order_by(MaterialParseVersion.created_at, MaterialParseVersion.id)
        ).scalars()
    )


def active_material_chunks(db: Session, material) -> list[MaterialChunk]:
    return [
        chunk
        for chunk in material_chunks(db, material.id)
        if chunk.parse_version_id == material.active_parse_version_id
    ]


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
    assert parsed.active_parse_version_id is not None
    assert chunks[0].parse_version_id == parsed.active_parse_version_id
    assert chunks[0].id == f"chk_{parsed.active_parse_version_id.removeprefix('mpv_')}_000000"
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


def test_reparse_failure_keeps_previous_active_diagnostics(db: Session, tmp_path: Path) -> None:
    class FailingParser:
        def parse(self, file_path: Path) -> ParsedDocument:
            raise CourseNexusError(code="PARSE_FAILED", message="解析失败")

    user, _, material = create_uploaded_material(db, tmp_path)
    rag_index = FakeRagIndex()
    first = parse_material(
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

    assert failed.parse_status == "parsed"
    assert failed.parse_error == "PARSE_FAILED"
    assert failed.active_parse_version_id == first.active_parse_version_id
    assert failed.parse_quality == "partial"
    assert failed.page_count == 59
    assert failed.parse_diagnostics_json["failed_pages"] == [17]
    assert [version.status for version in parse_versions(db, material.id)] == ["active", "failed"]


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


def test_parse_material_rejects_empty_candidate(db: Session, tmp_path: Path) -> None:
    class EmptyParser:
        def parse(self, file_path: Path) -> ParsedDocument:
            return ParsedDocument(
                chunks=[],
                diagnostics=ParseDiagnostics(parser="test", conversion_status="success"),
            )

    user, _, material = create_uploaded_material(db, tmp_path)

    parsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=EmptyParser(),
        rag_index=FakeRagIndex(),
        storage_root=tmp_path,
    )

    assert parsed.parse_status == "parse_failed"
    assert parsed.parse_error == "PARSE_FAILED"
    assert parsed.active_parse_version_id is None
    assert [version.status for version in parse_versions(db, material.id)] == ["failed"]


def test_parse_material_rejects_concurrent_building_version(db: Session, tmp_path: Path) -> None:
    user, _, material = create_uploaded_material(db, tmp_path)
    db.add(
        MaterialParseVersion(
            id="mpv_existing_build",
            material_id=material.id,
            course_id=material.course_id,
            user_id=material.user_id,
            status="building",
        )
    )
    db.commit()

    with pytest.raises(CourseNexusError) as exc_info:
        parse_material(
            db,
            user_id=user.id,
            material_id=material.id,
            parser=PlainTextParser(),
            rag_index=FakeRagIndex(),
            storage_root=tmp_path,
        )

    assert exc_info.value.code == "PARSE_ALREADY_IN_PROGRESS"
    assert exc_info.value.status_code == 409
    assert [(version.id, version.status) for version in parse_versions(db, material.id)] == [
        ("mpv_existing_build", "building")
    ]


def test_reparse_material_activates_new_chunks_and_retires_old_version(db: Session, tmp_path: Path) -> None:
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

    chunks = active_material_chunks(db, reparsed)
    assert reparsed.parse_status == "parsed"
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert [chunk.content_text for chunk in chunks] == ["First", "Second"]
    versions = parse_versions(db, material.id)
    assert [version.status for version in versions] == ["retired", "active"]
    assert len(material_chunks(db, material.id)) == 3
    assert set(rag_index.records) == {chunk.id for chunk in material_chunks(db, material.id)}


def test_reparse_material_keeps_retired_vectors_for_version_history(db: Session, tmp_path: Path) -> None:
    class RecordingRagIndex(FakeRagIndex):
        def __init__(self) -> None:
            super().__init__()
            self.operations: list[tuple[str, str]] = []

        def index_chunks(self, chunks):
            indexed_chunks = list(chunks)
            self.operations.extend(("index", chunk.parse_version_id or "") for chunk in indexed_chunks)
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

    versions = parse_versions(db, material.id)
    assert len(rag_index.operations) == 2
    assert rag_index.operations == [("index", versions[0].id), ("index", versions[1].id)]
    assert set(rag_index.records) == {chunk.id for chunk in material_chunks(db, material.id)}


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


def test_reparse_index_failure_keeps_previous_active_version(db: Session, tmp_path: Path) -> None:
    class ToggleFailingRagIndex(FakeRagIndex):
        fail_indexing = False

        def index_chunks(self, chunks):
            indexed_chunks = list(chunks)
            super().index_chunks(indexed_chunks)
            if self.fail_indexing:
                raise CourseNexusError(code="INDEXING_FAILED", message="索引失败", status_code=502)

    rag_index = ToggleFailingRagIndex()
    user, _, material = create_uploaded_material(db, tmp_path)
    first = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )
    first_version_id = first.active_parse_version_id
    first_chunk_ids = set(rag_index.records)
    (tmp_path / material.file_url).write_text("replacement", encoding="utf-8")
    rag_index.fail_indexing = True

    failed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    assert failed.parse_status == "parsed"
    assert failed.parse_error == "INDEXING_FAILED"
    assert failed.active_parse_version_id == first_version_id
    assert {version.status for version in parse_versions(db, material.id)} == {"active", "failed"}
    assert {chunk.id for chunk in material_chunks(db, material.id)} == first_chunk_ids
    assert set(rag_index.records) == first_chunk_ids


def test_parse_material_rejects_incomplete_candidate_vectors(db: Session, tmp_path: Path) -> None:
    class IncompleteRagIndex(FakeRagIndex):
        def list_parse_version_chunk_ids(self, parse_version_id: str) -> set[str]:
            return set()

    rag_index = IncompleteRagIndex()
    user, _, material = create_uploaded_material(db, tmp_path)

    failed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    assert failed.parse_status == "parse_failed"
    assert failed.parse_error == "INDEXING_FAILED"
    assert failed.active_parse_version_id is None
    assert [version.status for version in parse_versions(db, material.id)] == ["failed"]
    assert material_chunks(db, material.id) == []
    assert rag_index.records == {}


def test_reparse_switch_failure_keeps_previous_active_version(
    db: Session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    rag_index = FakeRagIndex()
    user, _, material = create_uploaded_material(db, tmp_path)
    first = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )
    first_version_id = first.active_parse_version_id
    first_chunk_ids = set(rag_index.records)
    (tmp_path / material.file_url).write_text("replacement", encoding="utf-8")

    original_commit = db.commit
    commit_count = 0

    def fail_switch_commit() -> None:
        nonlocal commit_count
        commit_count += 1
        if commit_count == 3:
            raise RuntimeError("switch failed")
        original_commit()

    monkeypatch.setattr(db, "commit", fail_switch_commit)

    failed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    assert failed.parse_status == "parsed"
    assert failed.parse_error == "PARSE_VERSION_SWITCH_FAILED"
    assert failed.active_parse_version_id == first_version_id
    assert {version.status for version in parse_versions(db, material.id)} == {"active", "failed"}
    assert {chunk.id for chunk in material_chunks(db, material.id)} == first_chunk_ids
    assert set(rag_index.records) == first_chunk_ids


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

        def delete_parse_version(self, parse_version_id: str) -> None:
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
