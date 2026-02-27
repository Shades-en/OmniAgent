"""Postgres engine/session management."""

from __future__ import annotations

from urllib.parse import quote, quote_plus

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from omniagent.persistence.types import PostgresPersistenceConfig


class PostgresDB:
    """Async SQLAlchemy engine/session lifecycle for Postgres."""

    _engine: AsyncEngine | None = None
    _sessionmaker: async_sessionmaker[AsyncSession] | None = None

    @classmethod
    def _build_dsn(cls, config: PostgresPersistenceConfig) -> str:
        if config.dsn:
            return config.dsn

        if config.password and not config.user:
            raise ValueError("Postgres split config cannot include password without user.")

        missing = [
            key
            for key, value in {
                "host": config.host,
                "dbname": config.dbname,
            }.items()
            if value in (None, "")
        ]
        if missing:
            missing_text = ", ".join(missing)
            raise ValueError(
                "Postgres DSN is not provided and split config is incomplete: "
                f"missing {missing_text}."
            )

        user = (config.user or "").strip()
        password = config.password or ""
        if user:
            auth = f"{quote_plus(user)}@"
            if password:
                auth = f"{quote_plus(user)}:{quote_plus(password)}@"
        else:
            auth = ""

        host = str(config.host)
        port = int(config.port) if config.port is not None else 5432
        dbname = quote(str(config.dbname), safe="")

        return (
            f"postgresql+asyncpg://{auth}"
            f"{host}:{port}/{dbname}"
        )

    @classmethod
    def _build_connect_args(cls, config: PostgresPersistenceConfig) -> dict[str, str]:
        sslmode = (config.sslmode or "").strip().lower()
        if not sslmode or sslmode == "disable":
            return {}
        return {"ssl": "require"}

    @classmethod
    async def init(cls, config: PostgresPersistenceConfig) -> None:
        dsn = cls._build_dsn(config)
        cls._engine = create_async_engine(
            dsn,
            echo=False,
            pool_pre_ping=True,
            future=True,
            connect_args=cls._build_connect_args(config),
        )
        cls._sessionmaker = async_sessionmaker(
            bind=cls._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        async with cls._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    @classmethod
    async def close(cls) -> None:
        if cls._engine is not None:
            await cls._engine.dispose()
        cls._engine = None
        cls._sessionmaker = None

    @classmethod
    def get_engine(cls) -> AsyncEngine:
        if cls._engine is None:
            raise RuntimeError("Postgres is not initialized. Call initialize_persistence(...) first.")
        return cls._engine

    @classmethod
    def get_sessionmaker(cls) -> async_sessionmaker[AsyncSession]:
        if cls._sessionmaker is None:
            raise RuntimeError("Postgres is not initialized. Call initialize_persistence(...) first.")
        return cls._sessionmaker


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Convenience accessor for the active async sessionmaker."""
    return PostgresDB.get_sessionmaker()
