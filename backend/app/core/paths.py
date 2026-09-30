from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class LegacyPathConflict:
    kind: str
    legacy_path: Path
    canonical_path: Path


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


def find_legacy_data_conflicts(
    *,
    database_url: str,
    file_storage_path: str | Path,
    chroma_persist_path: str | Path,
    launch_directory: Path | None = None,
    project_root: Path = PROJECT_ROOT,
) -> list[LegacyPathConflict]:
    launch_root = (launch_directory or Path.cwd()).resolve(strict=False)
    canonical_root = project_root.resolve(strict=False)
    if launch_root == canonical_root:
        return []

    candidates: list[tuple[str, Path]] = []
    database_path = _sqlite_database_path(database_url)
    if database_path is not None:
        candidates.append(("sqlite", database_path))
    candidates.extend(
        [
            ("uploads", Path(file_storage_path)),
            ("chroma", Path(chroma_persist_path)),
        ]
    )

    conflicts: list[LegacyPathConflict] = []
    for kind, configured_path in candidates:
        canonical_path = configured_path.resolve(strict=False)
        try:
            relative_path = canonical_path.relative_to(canonical_root)
        except ValueError:
            continue
        legacy_path = (launch_root / relative_path).resolve(strict=False)
        if (
            legacy_path != canonical_path
            and _path_has_data(legacy_path)
            and not _path_has_data(canonical_path)
        ):
            conflicts.append(
                LegacyPathConflict(
                    kind=kind,
                    legacy_path=legacy_path,
                    canonical_path=canonical_path,
                )
            )
    return conflicts


def assert_no_legacy_data_conflicts(
    *,
    database_url: str,
    file_storage_path: str | Path,
    chroma_persist_path: str | Path,
    launch_directory: Path | None = None,
    project_root: Path = PROJECT_ROOT,
) -> None:
    conflicts = find_legacy_data_conflicts(
        database_url=database_url,
        file_storage_path=file_storage_path,
        chroma_persist_path=chroma_persist_path,
        launch_directory=launch_directory,
        project_root=project_root,
    )
    if not conflicts:
        return
    locations = "; ".join(
        f"{conflict.kind}: {conflict.legacy_path} -> {conflict.canonical_path}"
        for conflict in conflicts
    )
    raise RuntimeError(
        "检测到旧启动目录中的本地数据，已拒绝启动以避免创建第二套数据。"
        f"请先按迁移文档备份并迁移：{locations}"
    )


def _sqlite_database_path(database_url: str) -> Path | None:
    url = make_url(database_url)
    if (
        url.get_backend_name() != "sqlite"
        or not url.database
        or url.database == ":memory:"
        or url.database.startswith("file:")
    ):
        return None
    return Path(url.database)


def _path_has_data(path: Path) -> bool:
    if path.is_file():
        return path.stat().st_size > 0
    if path.is_dir():
        return any(item.is_file() for item in path.rglob("*"))
    return False
