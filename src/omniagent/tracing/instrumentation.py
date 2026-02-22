"""OpenTelemetry instrumentor for OmniAgent runtime spans."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from opentelemetry import trace
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor

from omniagent.tracing import runtime as tracing_runtime


class OmniAgentInstrumentor(BaseInstrumentor):  # type: ignore[misc]
    """Instrument OmniAgent tracing decorators with a tracer provider."""

    def instrumentation_dependencies(self) -> Collection[str]:
        return []

    def _instrument(self, **kwargs: Any) -> None:
        tracer_provider = kwargs.get("tracer_provider") or trace.get_tracer_provider()
        tracing_runtime._set_tracer_provider(tracer_provider)
        tracing_runtime._set_instrumented(True)

    def _uninstrument(self, **kwargs: Any) -> None:
        tracing_runtime._clear_tracer_provider()
        tracing_runtime._set_instrumented(False)


__all__ = ["OmniAgentInstrumentor"]
