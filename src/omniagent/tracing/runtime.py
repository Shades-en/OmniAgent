"""Runtime state and tracer provider wiring for OmniAgent tracing."""

from __future__ import annotations

from typing import Any

from opentelemetry import trace

_is_instrumented = False
_tracer_provider: Any | None = None


def _set_tracer_provider(tracer_provider: Any | None) -> None:
    """Set a tracer provider override used by OmniAgent spans."""
    global _tracer_provider
    _tracer_provider = tracer_provider


def _clear_tracer_provider() -> None:
    """Clear any tracer provider override used by OmniAgent spans."""
    global _tracer_provider
    _tracer_provider = None


def _set_instrumented(flag: bool) -> None:
    """Set instrumentation status for OmniAgent tracing."""
    global _is_instrumented
    _is_instrumented = flag


def _get_tracer(module_name: str):
    """Get a tracer, honoring the OmniAgent-specific tracer provider override."""
    if _tracer_provider is not None:
        return trace.get_tracer(module_name, tracer_provider=_tracer_provider)
    return trace.get_tracer(module_name)
