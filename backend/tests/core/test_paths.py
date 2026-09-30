from pathlib import Path

import pytest

from app.core.paths import (
    assert_no_legacy_data_conflicts,
    find_legacy_data_conflicts,
    resolve_database_url,
    resolve_project_path,
)


def test_relative_project_path_resolves_from_config_root(tmp_path: Path) -> None:
    assert resolve_project_path("./data/chroma", project_root=tmp_path) == (
        tmp_path / "data" / "chroma"
    ).resolve()


def test_absolute_project_path_is_preserved(tmp_path: Path) -> None:
    absolute = (tmp_path / "outside" / "uploads").resolve()

    assert resolve_project_path(absolute, project_root=tmp_path / "other") == absolute


def test_relative_sqlite_url_resolves_from_config_root(tmp_path: Path) -> None:
    resolved = resolve_database_url(
        "sqlite:///./course_nexus.db",
        project_root=tmp_path,
    )

    assert resolved == f"sqlite:///{(tmp_path / 'course_nexus.db').as_posix()}"


def test_sqlite_memory_url_is_preserved(tmp_path: Path) -> None:
    assert (
        resolve_database_url("sqlite:///:memory:", project_root=tmp_path)
        == "sqlite:///:memory:"
    )


def test_non_sqlite_url_is_preserved(tmp_path: Path) -> None:
    url = "postgresql://user:password@example.test/course_nexus"

    assert resolve_database_url(url, project_root=tmp_path) == url


def test_legacy_data_is_reported_when_canonical_location_is_empty(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    launch_directory = project_root / "backend"
    launch_directory.mkdir(parents=True)
    (launch_directory / "course_nexus.db").write_bytes(b"legacy")
    legacy_upload = launch_directory / "uploads" / "mat_1"
    legacy_upload.mkdir(parents=True)
    (legacy_upload / "notes.txt").write_text("notes", encoding="utf-8")

    conflicts = find_legacy_data_conflicts(
        database_url=f"sqlite:///{(project_root / 'course_nexus.db').as_posix()}",
        file_storage_path=project_root / "uploads",
        chroma_persist_path=project_root / "data" / "chroma",
        launch_directory=launch_directory,
        project_root=project_root,
    )

    assert [conflict.kind for conflict in conflicts] == ["sqlite", "uploads"]


def test_existing_canonical_data_prevents_false_legacy_conflict(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    launch_directory = project_root / "backend"
    launch_directory.mkdir(parents=True)
    (launch_directory / "course_nexus.db").write_bytes(b"legacy")
    project_root.mkdir(exist_ok=True)
    (project_root / "course_nexus.db").write_bytes(b"canonical")

    conflicts = find_legacy_data_conflicts(
        database_url=f"sqlite:///{(project_root / 'course_nexus.db').as_posix()}",
        file_storage_path=project_root / "uploads",
        chroma_persist_path=project_root / "data" / "chroma",
        launch_directory=launch_directory,
        project_root=project_root,
    )

    assert conflicts == []


def test_legacy_conflict_guard_includes_migration_locations(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    launch_directory = project_root / "backend"
    legacy_chroma = launch_directory / "data" / "chroma"
    legacy_chroma.mkdir(parents=True)
    (legacy_chroma / "chroma.sqlite3").write_bytes(b"legacy")

    with pytest.raises(RuntimeError, match="拒绝启动") as exc_info:
        assert_no_legacy_data_conflicts(
            database_url=f"sqlite:///{(project_root / 'course_nexus.db').as_posix()}",
            file_storage_path=project_root / "uploads",
            chroma_persist_path=project_root / "data" / "chroma",
            launch_directory=launch_directory,
            project_root=project_root,
        )

    assert str(legacy_chroma.resolve()) in str(exc_info.value)
    assert str((project_root / "data" / "chroma").resolve()) in str(
        exc_info.value
    )
