"""Persistence runtime context models."""

from __future__ import annotations

from dataclasses import dataclass

from omniagent.persistence.contracts import (
    MessageRepository,
    SessionRepository,
    SummaryRepository,
    UserRepository,
)
from omniagent.persistence.types import PersistenceBackend
from omniagent.session.base import SessionManager


@dataclass(slots=True, frozen=True)
class RepositoryBundle:
    users: UserRepository
    sessions: SessionRepository
    messages: MessageRepository
    summaries: SummaryRepository


@dataclass(slots=True)
class PersistenceContext:
    backend: PersistenceBackend
    repositories: RepositoryBundle
    session_manager_cls: type[SessionManager]
