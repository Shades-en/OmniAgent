"""Postgres schema bootstrap helpers."""

from __future__ import annotations

from sqlalchemy import MetaData

from omniagent.db.postgres.engine import PostgresDB
from omniagent.db.postgres.model_registry import PostgresModels


def _get_models_metadata(models: PostgresModels) -> MetaData:
    metadata = models.user.metadata
    if (
        models.session.metadata is not metadata
        or models.summary.metadata is not metadata
        or models.message.metadata is not metadata
    ):
        raise RuntimeError(
            "Postgres model bundle is invalid: all models must share the same SQLAlchemy metadata."
        )
    return metadata


async def bootstrap_postgres_schema(
    *,
    models: PostgresModels,
    reset_schema: bool,
) -> None:
    """Create (and optionally recreate) schema for configured Postgres models."""

    engine = PostgresDB.get_engine()
    metadata = _get_models_metadata(models=models)
    async with engine.begin() as connection:
        if reset_schema:
            await connection.run_sync(metadata.drop_all)
        await connection.run_sync(metadata.create_all)
