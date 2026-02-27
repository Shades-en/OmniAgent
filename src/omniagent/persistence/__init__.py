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
from omniagent.persistence.repositories import (
    SharedMessageRepository,
    SharedSessionRepository,
    SharedSummaryRepository,
    SharedUserRepository,
)
from omniagent.persistence.serializers import (
    message_to_record,
    session_to_record,
    summary_to_record,
    user_to_record,
)
from omniagent.persistence.types import (
    MongoPersistenceConfig,
    PersistenceBackend,
    PostgresPersistenceConfig,
    RepositoryOverrides,
)

__all__ = [
    "PersistenceBackend",
    "MongoPersistenceConfig",
    "PostgresPersistenceConfig",
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
    "SharedUserRepository",
    "SharedSessionRepository",
    "SharedMessageRepository",
    "SharedSummaryRepository",
    "user_to_record",
    "session_to_record",
    "message_to_record",
    "summary_to_record",
    "initialize_persistence",
    "shutdown_persistence",
    "get_context",
]
