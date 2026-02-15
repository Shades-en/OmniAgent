"""
Protocol classes for OmniAgent.

These protocols define the interface contracts for database models,
allowing the base SessionManager to work with any backend implementation
(MongoDB, PostgreSQL, Redis, etc.) through structural subtyping.
"""

from typing import Protocol, List, Any, runtime_checkable
from datetime import datetime


@runtime_checkable
class UserProtocol(Protocol):
    """Protocol for User objects across different DB backends."""
    id: Any
    cookie_id: str
    created_at: datetime


@runtime_checkable
class SummaryProtocol(Protocol):
    """Protocol for Summary objects."""
    end_turn_number: int


@runtime_checkable
class MessageProtocol(Protocol):
    """Protocol for Message objects."""
    turn_number: int
    token_count: int


@runtime_checkable
class SessionProtocol(Protocol):
    """Protocol for Session objects across different DB backends."""
    id: Any
    name: str
    latest_turn_number: int
    user: Any
    
    async def insert_messages(
        self, 
        messages: List[Any], 
        turn_number: int, 
        previous_summary: Any
    ) -> None:
        """Insert messages into the session."""
        ...


__all__ = [
    "UserProtocol",
    "SessionProtocol",
    "MessageProtocol",
    "SummaryProtocol",
]
