from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def resolve_project_path(
    value: str | Path,
    *,
    project_root: Path = PROJECT_ROOT,
) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve(strict=False)


def resolve_database_url(
    database_url: str,
    *,
    project_root: Path = PROJECT_ROOT,
) -> str:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        return database_url
    if url.database == ":memory:" or url.database.startswith("file:"):
        return database_url

    database_path = resolve_project_path(url.database, project_root=project_root)
    return url.set(database=database_path.as_posix()).render_as_string(
        hide_password=False
    )
