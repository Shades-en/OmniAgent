"""
Database-related exceptions for OmniAgent.
"""

from omniagent.exceptions.base import OmniAgentError


class DatabaseError(OmniAgentError):
    """Base exception for all database-related errors."""
    pass


# Not Found Errors
class NotFoundError(DatabaseError):
    """Base exception for resource not found errors."""
    pass


class UserNotFoundError(NotFoundError):
    """Raised when a user cannot be found in the database."""
    pass


class SessionNotFoundError(NotFoundError):
    """Raised when a session cannot be found in the database."""
    pass


# Retrieval Errors
class RetrievalError(DatabaseError):
    """Base exception for database retrieval failures."""
    pass


class UserRetrievalError(RetrievalError):
    """Raised when user retrieval from database fails."""
    pass


class SessionRetrievalError(RetrievalError):
    """Raised when session retrieval from database fails."""
    pass


class MessageRetrievalError(RetrievalError):
    """Raised when message retrieval from database fails."""
    pass


class SummaryRetrievalError(RetrievalError):
    """Raised when summary retrieval from database fails."""
    pass


# Creation Errors
class CreationError(DatabaseError):
    """Base exception for database creation/insertion failures."""
    pass


class SessionCreationError(CreationError):
    """Raised when session creation in database fails."""
    pass


class MessageCreationError(CreationError):
    """Raised when message creation in database fails."""
    pass


class SummaryCreationError(CreationError):
    """Raised when summary creation in database fails."""
    pass


# Update Errors
class UpdateError(DatabaseError):
    """Base exception for database update failures."""
    pass


class SessionUpdateError(UpdateError):
    """Raised when session update in database fails."""
    pass


class MessageUpdateError(UpdateError):
    """Raised when message update in database fails."""
    pass


# Deletion Errors
class DeletionError(DatabaseError):
    """Base exception for database deletion failures."""
    pass


class UserDeletionError(DeletionError):
    """Raised when user deletion from database fails."""
    pass


class SessionDeletionError(DeletionError):
    """Raised when session deletion from database fails."""
    pass


class MessageDeletionError(DeletionError):
    """Raised when message deletion from database fails."""
    pass
