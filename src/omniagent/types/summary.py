"""Summary value objects."""

from dataclasses import dataclass


@dataclass(slots=True)
class GeneratedSummary:
    """Backend-agnostic summary produced by providers."""

    content: str
    start_turn_number: int
    end_turn_number: int
    token_count: int


__all__ = ["GeneratedSummary"]
