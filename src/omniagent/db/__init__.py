"""
Database module for OmniAgent.

Re-exports database implementations for convenience.
"""

from omniagent.db.mongo import MongoDB

__all__ = [
    "MongoDB",
]
