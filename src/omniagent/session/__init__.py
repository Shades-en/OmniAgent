"""
Session management for OmniAgent.

This module provides the base SessionManager class and database-specific implementations.
"""

from omniagent.session.base import SessionManager
from omniagent.session.chat_name import generate_chat_name
from omniagent.session.mongo import MongoSessionManager

__all__ = [
    "generate_chat_name",
    "SessionManager",
    "MongoSessionManager",
]
