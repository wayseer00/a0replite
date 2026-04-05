from logging.config import fileConfig
import os

from sqlalchemy import create_engine, pool, text
from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def get_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL not set — cannot run migrations")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def get_url_asyncpg() -> str:
    """Return a sync-compatible URL using asyncpg DBAPI via psycopg2-free path."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL not set — cannot run migrations")
    for prefix in ("postgres://", "postgresql://", "postgresql+asyncpg://"):
        if url.startswith(prefix):
            url = url.replace(prefix, "postgresql+psycopg2://", 1)
            break
    return url


def _try_drivers(url_base: str) -> "sqlalchemy.engine.Engine":
    """Try psycopg2, then pg8000 as fallback sync drivers."""
    drivers = ["psycopg2", "pg8000"]
    last_err = None
    for drv in drivers:
        try:
            url = url_base.replace("postgresql://", f"postgresql+{drv}://", 1)
            if "+" not in url.split("://")[0]:
                url = f"postgresql+{drv}://" + url.split("://", 1)[1]
            engine = create_engine(url, poolclass=pool.NullPool)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"No working sync DB driver found. Last error: {last_err}")


def _make_engine():
    """Try psycopg2 first, then pg8000."""
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url:
        raise RuntimeError("DATABASE_URL not set")
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)

    base = raw_url.split("://", 1)[1]

    for drv in ["psycopg2", "pg8000"]:
        url = f"postgresql+{drv}://{base}"
        try:
            engine = create_engine(url, poolclass=pool.NullPool)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except Exception:
            continue

    raise RuntimeError("No working sync DB driver available (tried psycopg2, pg8000)")


def run_migrations_offline() -> None:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = _make_engine()
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
