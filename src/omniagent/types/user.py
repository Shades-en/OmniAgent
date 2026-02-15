"""
User-related types for OmniAgent.
"""

from enum import Enum


class UserType(Enum):
    """Type of user - guest or logged in."""
    GUEST = "guest"
    USER = "logged_in"
