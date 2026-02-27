"""Persistence backend types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING


class PersistenceBackend(str, Enum):
    """Supported persistence backends."""

    MONGO = "mongo"
    POSTGRES = "postgres"


if TYPE_CHECKING:
    from beanie import Document

    from omniagent.db.mongo import DocumentModels
    from omniagent.db.postgres import PostgresModels
    from omniagent.persistence.contracts import (
        MessageRepository,
        SessionRepository,
        SummaryRepository,
        UserRepository,
    )


@dataclass(slots=True)
class RepositoryOverrides:
    """Init-time repository replacements for domain customization."""

    users: "UserRepository | None" = None
    sessions: "SessionRepository | None" = None
    messages: "MessageRepository | None" = None
    summaries: "SummaryRepository | None" = None


@dataclass(slots=True)
class MongoPersistenceConfig:
    """Mongo backend initialization config."""

    db_name: str | None = None
    srv_uri: str | None = None
    allow_index_dropping: bool = False
    models: "DocumentModels | None" = None
    extra_document_models: list[type["Document"]] | None = None


@dataclass(slots=True)
class PostgresPersistenceConfig:
    """Postgres backend initialization config."""

    dsn: str | None = None
    user: str | None = None
    password: str | None = None
    host: str | None = None
    port: int | None = None
    dbname: str | None = None
    sslmode: str = "require"
    reset_schema: bool = False
    models: "PostgresModels | None" = None
