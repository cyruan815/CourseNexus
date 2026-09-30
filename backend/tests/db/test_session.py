from pathlib import Path

from sqlalchemy import text

from app.db.session import SQLITE_BUSY_TIMEOUT_MS, create_database_engine


def test_file_sqlite_engine_enables_runtime_pragmas(tmp_path: Path) -> None:
    database_path = tmp_path / "runtime.db"
    engine = create_database_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        with engine.connect() as connection:
            foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
            journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()
            busy_timeout = connection.execute(text("PRAGMA busy_timeout")).scalar_one()
    finally:
        engine.dispose()

    assert foreign_keys == 1
    assert str(journal_mode).lower() == "wal"
    assert busy_timeout == SQLITE_BUSY_TIMEOUT_MS


def test_memory_sqlite_engine_does_not_force_file_wal() -> None:
    engine = create_database_engine("sqlite:///:memory:")
    try:
        with engine.connect() as connection:
            journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()
            foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
            busy_timeout = connection.execute(text("PRAGMA busy_timeout")).scalar_one()
    finally:
        engine.dispose()

    assert str(journal_mode).lower() == "memory"
    assert foreign_keys == 1
    assert busy_timeout == SQLITE_BUSY_TIMEOUT_MS
