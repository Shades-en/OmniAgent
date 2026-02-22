"""Request-scoped tracing context helpers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any

# Global context variable for tracing context (isolated per async request)
_trace_context: ContextVar[dict[str, Any]] = ContextVar("trace_context", default={})


def set_trace_context(
    query: str | None = None,
    session_id: str | None = None,
    user_client_id: str | None = None,
) -> None:
    """
    Set tracing context for the current async execution context.

    This should be called once at the entry point of a request (e.g., ChatService.chat).
    The context will automatically propagate through all async calls within the same request.
    """
    _trace_context.set(
        {
            "query": query,
            "session_id": session_id,
            "user_client_id": user_client_id,
        }
    )


def get_trace_context() -> dict[str, Any]:
    """Get the current tracing context for this async execution."""
    return _trace_context.get()


def clear_trace_context() -> None:
    """Clear tracing context for the current async execution."""
    _trace_context.set({})


@asynccontextmanager
async def trace_context(
    query: str | None = None,
    session_id: str | None = None,
    user_client_id: str | None = None,
):
    """Context manager for tracing context lifecycle."""
    set_trace_context(
        query=query,
        session_id=session_id,
        user_client_id=user_client_id,
    )
    try:
        yield
    finally:
        clear_trace_context()

