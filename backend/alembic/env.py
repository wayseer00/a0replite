from logging.config import fileConfig
import os

from sqlalchemy import create_engine, pool, text
from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _get_sync_url() -> str:
    """Return a psycopg2-compatible sync URL for Alembic migrations."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL not set — cannot run migrations")
    for prefix in ("postgres://", "postgresql://", "postgresql+asyncpg://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg2://" + url.split("://", 1)[1]
            break
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_get_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_get_sync_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
