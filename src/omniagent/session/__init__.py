"""
Session management for OmniAgent.

This module provides the base SessionManager class and database-specific implementations.
"""

from omniagent.session.base import SessionManager
from omniagent.session.mongo import MongoSessionManager
from omniagent.session.postgres import PostgresSessionManager


__all__ = [
    "SessionManager",
    "MongoSessionManager",
    "PostgresSessionManager",
]
