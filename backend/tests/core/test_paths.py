from pathlib import Path

from app.core.paths import resolve_database_url, resolve_project_path


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
