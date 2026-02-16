"""Feedback types for messages."""

from enum import Enum


class Feedback(Enum):
    """Feedback enum for message feedback."""
    LIKE = "liked"
    DISLIKE = "disliked"
