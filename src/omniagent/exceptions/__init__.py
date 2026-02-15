"""
OmniAgent exceptions module.

All exceptions are exported from this module for convenient imports:
    from omniagent.exceptions import UserNotFoundError, SessionCreationError
"""

from omniagent.exceptions.base import OmniAgentError

from omniagent.exceptions.database import (
    DatabaseError,
    NotFoundError,
    UserNotFoundError,
    SessionNotFoundError,
    RetrievalError,
    UserRetrievalError,
    SessionRetrievalError,
    MessageRetrievalError,
    SummaryRetrievalError,
    CreationError,
    SessionCreationError,
    MessageCreationError,
    SummaryCreationError,
    UpdateError,
    SessionUpdateError,
    MessageUpdateError,
    DeletionError,
    UserDeletionError,
    SessionDeletionError,
    MessageDeletionError,
)

from omniagent.exceptions.agent import (
    AgentError,
    MaxStepsReachedError,
)

from omniagent.exceptions.provider import (
    ProviderError,
    UnrecognizedMessageTypeError,
    MessageParseError,
)

__all__ = [
    # Base
    "OmniAgentError",
    # Database - Base
    "DatabaseError",
    # Database - Not Found
    "NotFoundError",
    "UserNotFoundError",
    "SessionNotFoundError",
    # Database - Retrieval
    "RetrievalError",
    "UserRetrievalError",
    "SessionRetrievalError",
    "MessageRetrievalError",
    "SummaryRetrievalError",
    # Database - Creation
    "CreationError",
    "SessionCreationError",
    "MessageCreationError",
    "SummaryCreationError",
    # Database - Update
    "UpdateError",
    "SessionUpdateError",
    "MessageUpdateError",
    # Database - Deletion
    "DeletionError",
    "UserDeletionError",
    "SessionDeletionError",
    "MessageDeletionError",
    # Agent
    "AgentError",
    "MaxStepsReachedError",
    # Provider
    "ProviderError",
    "UnrecognizedMessageTypeError",
    "MessageParseError",
]
