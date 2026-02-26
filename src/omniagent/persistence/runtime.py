"""Runtime state for persistence context."""

from __future__ import annotations

from omniagent.persistence.context import PersistenceContext
from omniagent.persistence.types import PersistenceBackend


_ACTIVE_BACKEND: PersistenceBackend | None = None
_ACTIVE_CONTEXT: PersistenceContext | None = None


def set_active_context(context: PersistenceContext) -> None:
    """Set active backend context exactly once per process lifecycle."""
    global _ACTIVE_BACKEND, _ACTIVE_CONTEXT
    if _ACTIVE_CONTEXT is not None:
        if _ACTIVE_BACKEND != context.backend:
            raise RuntimeError(
                "Persistence is already initialized with a different backend "
                f"('{_ACTIVE_BACKEND.value}' != '{context.backend.value}')."
            )
        return
    _ACTIVE_BACKEND = context.backend
    _ACTIVE_CONTEXT = context


def get_active_context() -> PersistenceContext:
    """Get the active persistence context."""
    if _ACTIVE_CONTEXT is None:
        raise RuntimeError(
            "Persistence context is not initialized. "
            "Call initialize_persistence(...) during application startup."
        )
    return _ACTIVE_CONTEXT


def get_active_backend() -> PersistenceBackend | None:
    return _ACTIVE_BACKEND


def clear_active_context() -> None:
    """Reset active context/backend runtime state."""
    global _ACTIVE_BACKEND, _ACTIVE_CONTEXT
    _ACTIVE_BACKEND = None
    _ACTIVE_CONTEXT = None

