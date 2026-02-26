"""Persistence backend types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable


class PersistenceBackend(str, Enum):
    """Supported persistence backends."""

    MONGO = "mongo"


if TYPE_CHECKING:
    from omniagent.persistence.contracts import (
        MessageRepository,
        SessionRepository,
        SummaryRepository,
        UserRepository,
    )


UserRepositoryOverride = Callable[["UserRepository"], "UserRepository"]
SessionRepositoryOverride = Callable[["SessionRepository"], "SessionRepository"]
MessageRepositoryOverride = Callable[["MessageRepository"], "MessageRepository"]
SummaryRepositoryOverride = Callable[["SummaryRepository"], "SummaryRepository"]


@dataclass(slots=True)
class RepositoryOverrides:
    """Init-time repository wrappers for domain customization."""

    users: UserRepositoryOverride | None = None
    sessions: SessionRepositoryOverride | None = None
    messages: MessageRepositoryOverride | None = None
    summaries: SummaryRepositoryOverride | None = None
