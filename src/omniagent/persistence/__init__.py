"""Persistence package."""

from omniagent.persistence.api import (
    get_context,
    initialize_persistence,
    shutdown_persistence,
)
from omniagent.persistence.context import PersistenceContext, RepositoryBundle
from omniagent.persistence.contracts import (
    MessageRecord,
    MessageRepository,
    Page,
    SessionRecord,
    SessionRepository,
    SummaryRecord,
    SummaryRepository,
    UserRecord,
    UserRepository,
)
from omniagent.persistence.types import PersistenceBackend, RepositoryOverrides

__all__ = [
    "PersistenceBackend",
    "RepositoryOverrides",
    "PersistenceContext",
    "RepositoryBundle",
    "Page",
    "UserRecord",
    "SessionRecord",
    "MessageRecord",
    "SummaryRecord",
    "UserRepository",
    "SessionRepository",
    "MessageRepository",
    "SummaryRepository",
    "initialize_persistence",
    "shutdown_persistence",
    "get_context",
]
