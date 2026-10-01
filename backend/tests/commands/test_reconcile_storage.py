from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.commands.reconcile_storage as reconcile_command
from app.commands.reconcile_storage import (
    _assert_configured_database_exists,
    reconcile_storage,
    render_human_report,
    report_exit_code,
)
from app.core.errors import CourseNexusError
from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.rag.base import RagIndexRecord
from app.modules.courses.models import Course
from app.modules.materials.models import CourseMaterial, MaterialChunk, MaterialParseVersion
from app.modules.users.models import User


@pytest.fixture()
def engine():
    value = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(value)
    try:
        yield value
    finally:
        value.dispose()


@pytest.fixture()
def db(engine) -> Session:
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    try:
        yield session
    finally:
        session.close()


def _seed_active_material(db: Session, storage_root: Path) -> RagIndexRecord:
    db.add(User(id="usr_1", username="alice", password_hash="hash", status="active"))
    db.add(Course(id="crs_1", user_id="usr_1", name="课程", status="active"))
    db.add(
        CourseMaterial(
            id="mat_1",
            user_id="usr_1",
            course_id="crs_1",
            name="notes.txt",
            material_type="text",
            source_type="file",
            file_url="usr_1/crs_1/mat_1/source.txt",
            parse_status="parsed",
            active_parse_version_id="mpv_active",
        )
    )
    db.add(
        MaterialParseVersion(
            id="mpv_active",
            material_id="mat_1",
            user_id="usr_1",
            course_id="crs_1",
            status="active",
            parse_quality="complete",
        )
    )
    db.add(
        MaterialChunk(
            id="chk_active",
            material_id="mat_1",
            parse_version_id="mpv_active",
            course_id="crs_1",
            chunk_index=0,
            content_text="private material content",
        )
    )
    db.commit()
    source_path = storage_root / "usr_1" / "crs_1" / "mat_1" / "source.txt"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("private file content", encoding="utf-8")
    return RagIndexRecord(
        chunk_id="chk_active",
        user_id="usr_1",
        course_id="crs_1",
        material_id="mat_1",
        parse_version_id="mpv_active",
    )


def _database_counts(db: Session) -> tuple[int, int, int]:
    return (
        int(db.scalar(select(func.count()).select_from(CourseMaterial)) or 0),
        int(db.scalar(select(func.count()).select_from(MaterialParseVersion)) or 0),
        int(db.scalar(select(func.count()).select_from(MaterialChunk)) or 0),
    )


def test_reconciliation_reports_clean_data_without_mutation(db: Session, tmp_path: Path) -> None:
    record = _seed_active_material(db, tmp_path)
    source_path = tmp_path / "usr_1" / "crs_1" / "mat_1" / "source.txt"
    before_counts = _database_counts(db)
    before_content = source_path.read_text(encoding="utf-8")

    report = reconcile_storage(db=db, storage_root=tmp_path, rag_records=[record])

    assert report.status == "clean"
    assert report.issue_count == 0
    assert report.inconsistency_count == 0
    assert report_exit_code(report) == 0
    assert _database_counts(db) == before_counts
    assert source_path.read_text(encoding="utf-8") == before_content


def test_reconciliation_detects_missing_file_and_orphan_directory(db: Session, tmp_path: Path) -> None:
    record = _seed_active_material(db, tmp_path)
    (tmp_path / "usr_1" / "crs_1" / "mat_1" / "source.txt").unlink()
    orphan = tmp_path / "usr_1" / "crs_1" / "mat_orphan"
    orphan.mkdir(parents=True)
    (orphan / "source.txt").write_text("orphan", encoding="utf-8")

    report = reconcile_storage(db=db, storage_root=tmp_path, rag_records=[record])

    assert {issue.code for issue in report.issues} == {
        "MATERIAL_FILE_MISSING",
        "ORPHAN_MATERIAL_DIRECTORY",
    }
    assert report.status == "inconsistent"
    assert report_exit_code(report) == 1


def test_reconciliation_detects_vector_set_orphan_and_metadata_mismatch(
    db: Session,
    tmp_path: Path,
) -> None:
    _seed_active_material(db, tmp_path)
    records = [
        RagIndexRecord(
            chunk_id="chk_active",
            user_id="usr_1",
            course_id="crs_1",
            material_id="mat_wrong",
            parse_version_id="mpv_active",
        ),
        RagIndexRecord(
            chunk_id="chk_orphan",
            user_id="usr_1",
            course_id="crs_1",
            material_id="mat_1",
            parse_version_id="mpv_active",
        ),
        RagIndexRecord(
            chunk_id="chk_invalid",
            user_id=None,
            course_id="crs_1",
            material_id=None,
            parse_version_id=None,
        ),
    ]

    report = reconcile_storage(db=db, storage_root=tmp_path, rag_records=records)

    codes = {issue.code for issue in report.issues}
    assert "ACTIVE_VECTOR_SET_MISMATCH" in codes
    assert "ORPHAN_VECTOR" in codes
    assert "VECTOR_METADATA_INVALID" in codes
    assert "VECTOR_METADATA_MISMATCH" in codes
    assert "private material content" not in json.dumps(report.to_dict(), ensure_ascii=False)
    assert "private file content" not in render_human_report(report)


def test_reconciliation_reports_retained_and_stale_parse_versions(
    db: Session,
    tmp_path: Path,
) -> None:
    record = _seed_active_material(db, tmp_path)
    old_time = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)
    db.add_all(
        [
            MaterialParseVersion(
                id="mpv_retired",
                material_id="mat_1",
                user_id="usr_1",
                course_id="crs_1",
                status="retired",
                parse_quality="complete",
            ),
            MaterialParseVersion(
                id="mpv_failed",
                material_id="mat_1",
                user_id="usr_1",
                course_id="crs_1",
                status="failed",
            ),
            MaterialParseVersion(
                id="mpv_building",
                material_id="mat_1",
                user_id="usr_1",
                course_id="crs_1",
                status="building",
                created_at=old_time,
            ),
            MaterialParseVersion(
                id="mpv_second_active",
                material_id="mat_1",
                user_id="usr_1",
                course_id="crs_1",
                status="active",
            ),
        ]
    )
    db.commit()

    report = reconcile_storage(
        db=db,
        storage_root=tmp_path,
        rag_records=[record],
        now=old_time + timedelta(hours=2),
        building_stale_after=timedelta(hours=1),
    )

    codes = [issue.code for issue in report.issues]
    assert codes.count("PARSE_VERSION_RETAINED") == 2
    assert "PARSE_VERSION_BUILDING_STALE" in codes
    assert "MULTIPLE_ACTIVE_PARSE_VERSIONS" in codes
    assert report.inconsistency_count == 2


def test_notices_do_not_make_command_exit_nonzero(db: Session, tmp_path: Path) -> None:
    record = _seed_active_material(db, tmp_path)
    db.add(
        MaterialParseVersion(
            id="mpv_retired",
            material_id="mat_1",
            user_id="usr_1",
            course_id="crs_1",
            status="retired",
        )
    )
    db.commit()

    report = reconcile_storage(db=db, storage_root=tmp_path, rag_records=[record])

    assert report.status == "notices"
    assert report.issue_count == 1
    assert report.inconsistency_count == 0
    assert report_exit_code(report) == 0


def test_missing_sqlite_database_is_rejected_without_creating_file(tmp_path: Path) -> None:
    database_path = tmp_path / "missing.db"

    with pytest.raises(CourseNexusError) as exc_info:
        _assert_configured_database_exists(f"sqlite:///{database_path.as_posix()}")

    assert exc_info.value.code == "DATABASE_NOT_FOUND"
    assert not database_path.exists()


def test_main_emits_json_and_uses_distinct_exit_codes(
    engine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with testing_session() as seed_db:
        _seed_active_material(seed_db, tmp_path)
    settings = SimpleNamespace(
        database_url="sqlite:///:memory:",
        file_storage_path=str(tmp_path),
        chroma_persist_path=str(tmp_path / "chroma"),
        chroma_collection="test",
    )
    monkeypatch.setattr(reconcile_command, "get_settings", lambda: settings)
    monkeypatch.setattr(reconcile_command, "assert_no_legacy_data_conflicts", lambda **_kwargs: None)
    monkeypatch.setattr(reconcile_command, "configure_logging", lambda _settings: None)
    monkeypatch.setattr(reconcile_command, "SessionLocal", testing_session)
    monkeypatch.setattr(reconcile_command, "open_existing_chroma_rag_index", lambda **_kwargs: None)

    inconsistent_exit = reconcile_command.main(["--json"])
    inconsistent_output = json.loads(capsys.readouterr().out)

    assert inconsistent_exit == 1
    assert inconsistent_output["status"] == "inconsistent"
    assert inconsistent_output["inconsistency_count"] >= 1

    monkeypatch.setattr(reconcile_command, "get_settings", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    error_exit = reconcile_command.main(["--json"])
    error_output = json.loads(capsys.readouterr().err.splitlines()[0])

    assert error_exit == 2
    assert error_output == {
        "error_code": "STORAGE_RECONCILIATION_FAILED",
        "schema_version": 1,
        "status": "error",
    }
