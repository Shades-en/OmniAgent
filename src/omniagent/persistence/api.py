"""Public persistence API with explicit backend selection."""

from __future__ import annotations

from dataclasses import replace

from omniagent.persistence.backends.mongo import MongoBackendAdapter
from omniagent.persistence.context import PersistenceContext, RepositoryBundle
from omniagent.persistence.contracts import (
    MessageRepository,
    SessionRepository,
    SummaryRepository,
    UserRepository,
)
from omniagent.persistence.runtime import (
    clear_active_context,
    get_active_backend,
    get_active_context,
    set_active_context,
)
from omniagent.persistence.types import (
    MongoPersistenceConfig,
    PersistenceBackend,
    PostgresPersistenceConfig,
    RepositoryOverrides,
)


def _resolve_backend(backend: PersistenceBackend | str) -> PersistenceBackend:
    if isinstance(backend, PersistenceBackend):
        return backend
    try:
        return PersistenceBackend(backend)
    except ValueError as exc:
        raise ValueError(f"Unsupported persistence backend: {backend}") from exc


def _validate_repository_bundle(repositories: RepositoryBundle) -> None:
    contract_checks: tuple[tuple[object, type[object], str], ...] = (
        (repositories.users, UserRepository, "users"),
        (repositories.sessions, SessionRepository, "sessions"),
        (repositories.messages, MessageRepository, "messages"),
        (repositories.summaries, SummaryRepository, "summaries"),
    )
    for repository, protocol, name in contract_checks:
        if not isinstance(repository, protocol):
            raise TypeError(
                f"Repository override for '{name}' must implement {protocol.__name__}."
            )


def _apply_repository_overrides(
    repositories: RepositoryBundle,
    repository_overrides: RepositoryOverrides | None,
) -> RepositoryBundle:
    if repository_overrides is None:
        return repositories

    resolved_bundle = RepositoryBundle(
        users=repository_overrides.users if repository_overrides.users is not None else repositories.users,
        sessions=repository_overrides.sessions if repository_overrides.sessions is not None else repositories.sessions,
        messages=repository_overrides.messages if repository_overrides.messages is not None else repositories.messages,
        summaries=repository_overrides.summaries if repository_overrides.summaries is not None else repositories.summaries,
    )
    _validate_repository_bundle(resolved_bundle)
    return resolved_bundle


async def initialize_persistence(
    *,
    backend: PersistenceBackend | str,
    backend_config: MongoPersistenceConfig | PostgresPersistenceConfig,
    repository_overrides: RepositoryOverrides | None = None,
) -> PersistenceContext:
    """Initialize persistence for the selected backend exactly once."""
    resolved_backend = _resolve_backend(backend)
    active_backend = get_active_backend()
    if active_backend is not None:
        if active_backend != resolved_backend:
            raise RuntimeError(
                "Persistence is already initialized with backend "
                f"'{active_backend.value}', cannot switch to '{resolved_backend.value}'."
            )
        return get_active_context()

    if resolved_backend is PersistenceBackend.MONGO:
        if not isinstance(backend_config, MongoPersistenceConfig):
            raise TypeError("Mongo backend requires MongoPersistenceConfig.")
        context = await MongoBackendAdapter.initialize(config=backend_config)
    elif resolved_backend is PersistenceBackend.POSTGRES:
        if not isinstance(backend_config, PostgresPersistenceConfig):
            raise TypeError("Postgres backend requires PostgresPersistenceConfig.")
        from omniagent.persistence.backends.postgres import PostgresBackendAdapter

        context = await PostgresBackendAdapter.initialize(config=backend_config)
    else:
        raise ValueError(f"Unsupported persistence backend: {resolved_backend.value}")

    repositories = _apply_repository_overrides(
        repositories=context.repositories,
        repository_overrides=repository_overrides,
    )
    context = replace(context, repositories=repositories)
    set_active_context(context)
    return context


def get_context() -> PersistenceContext:
    """Get active persistence context."""
    return get_active_context()


async def shutdown_persistence() -> None:
    """Shutdown active persistence backend and clear runtime state."""
    active_backend = get_active_backend()
    if active_backend is None:
        return

    if active_backend is PersistenceBackend.MONGO:
        await MongoBackendAdapter.shutdown()
    elif active_backend is PersistenceBackend.POSTGRES:
        from omniagent.persistence.backends.postgres import PostgresBackendAdapter

        await PostgresBackendAdapter.shutdown()
    else:
        raise ValueError(f"Unsupported persistence backend: {active_backend.value}")

    clear_active_context()
