"""Postgres persistence backend adapter lifecycle."""

from __future__ import annotations

from omniagent.db.postgres import (
    DEFAULT_MODELS,
    PostgresDB,
    bootstrap_postgres_schema,
    set_postgres_models,
)
from omniagent.persistence.backends.base import BackendAdapterBase
from omniagent.persistence.backends.postgres.model_contracts import (
    validate_document_models,
    validate_repository_models,
)
from omniagent.persistence.context import PersistenceContext, RepositoryBundle
from omniagent.persistence.repositories import (
    SharedMessageRepository,
    SharedSessionRepository,
    SharedSummaryRepository,
    SharedUserRepository,
)
from omniagent.persistence.types import PersistenceBackend, PostgresPersistenceConfig
from omniagent.session.postgres import PostgresSessionManager


class PostgresBackendAdapter(BackendAdapterBase):
    """Lifecycle adapter for Postgres persistence initialization and shutdown."""

    @classmethod
    async def initialize(
        cls,
        config: PostgresPersistenceConfig,
    ) -> PersistenceContext:
        if not isinstance(config, PostgresPersistenceConfig):
            raise TypeError("Postgres backend requires PostgresPersistenceConfig.")

        resolved_models = config.models or DEFAULT_MODELS
        validate_document_models(resolved_models)
        validate_repository_models(resolved_models)

        set_postgres_models(resolved_models)
        await PostgresDB.init(config=config)
        await bootstrap_postgres_schema(
            models=resolved_models,
            reset_schema=config.reset_schema,
        )

        repositories = RepositoryBundle(
            users=SharedUserRepository(user_model=resolved_models.user),
            sessions=SharedSessionRepository(session_model=resolved_models.session),
            messages=SharedMessageRepository(message_model=resolved_models.message),
            summaries=SharedSummaryRepository(summary_model=resolved_models.summary),
        )

        return PersistenceContext(
            backend=PersistenceBackend.POSTGRES,
            repositories=repositories,
            session_manager_cls=PostgresSessionManager,
        )

    @classmethod
    async def shutdown(cls) -> None:
        await PostgresDB.close()
