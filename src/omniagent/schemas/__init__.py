"""
Schema module for OmniAgent.

Re-exports MongoDB schemas for backward compatibility.
"""

from omniagent.schemas.mongo import User, UserType, Session, Summary, Message, Feedback

__all__ = [
    "User",
    "UserType",
    "Session",
    "Summary",
    "Message",
    "Feedback",
]
