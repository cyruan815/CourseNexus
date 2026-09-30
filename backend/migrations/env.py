from logging.config import fileConfig

from alembic import context

from app.core.config import get_settings
from app.core.paths import assert_no_legacy_data_conflicts
from app.db.base import Base
from app.db.session import create_database_engine
import app.db.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    settings = get_settings()
    assert_no_legacy_data_conflicts(
        database_url=settings.database_url,
        file_storage_path=settings.file_storage_path,
        chroma_persist_path=settings.chroma_persist_path,
    )
    return settings.database_url or config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_database_engine(get_url())
    try:
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
