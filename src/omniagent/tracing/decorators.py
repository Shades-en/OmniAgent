"""Tracing decorators and span-kind helpers."""

from __future__ import annotations

import asyncio
from enum import Enum
from functools import wraps
import json
import time
from typing import Any, Callable

from openinference.semconv.trace import SpanAttributes
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from omniagent.tracing.context import get_trace_context
from omniagent.tracing.graph import add_graph_attributes, pop_graph_node
from omniagent.tracing.helpers import _attach_output_to_span, _set_span_attributes
from omniagent.tracing.runtime import _get_tracer


def track_state_change(key: str, old_value: Any, new_value: Any) -> None:
    """Track a state change by adding attributes and an event to the current span."""
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        current_span.set_attribute(f"state.{key}.before", str(old_value))
        current_span.set_attribute(f"state.{key}.after", str(new_value))
        current_span.add_event(
            "state_updated",
            attributes={
                "key": key,
                "old_value": str(old_value),
                "new_value": str(new_value),
            },
        )


def trace_method(
    name: str | None = None,
    kind=None,
    capture_input: bool = True,
    capture_output: bool = True,
    graph_node_id: str | Callable | None = None,
):
    """Decorator for tracing async methods with automatic context and graph metadata."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            tracer = _get_tracer(__name__)
            span_name = name or f"{self.__class__.__name__}.{func.__name__}"
            ctx = get_trace_context()

            input_value = None
            if capture_input and args:
                input_value = args[0] if isinstance(args[0], str) else ctx.get("query")
            elif capture_input:
                input_value = ctx.get("query")

            metadata = {
                "class": self.__class__.__name__,
                "method": func.__name__,
            }

            if hasattr(self, "agent") and self.agent:
                metadata["agent_name"] = self.agent.__class__.__name__
                metadata["agent_description"] = self.agent.description
                metadata["tools"] = [tool.__class__.__name__ for tool in self.agent.tools]

            with tracer.start_as_current_span(span_name) as span:
                try:
                    _set_span_attributes(
                        span,
                        {
                            SpanAttributes.OPENINFERENCE_SPAN_KIND: (
                                getattr(kind, "value", kind) if kind is not None else ""
                            ),
                            SpanAttributes.INPUT_VALUE: input_value or "",
                            "session_id": ctx.get("session_id", ""),
                            "user_id": ctx.get("user_id", ""),
                            "user_client_id": ctx.get("user_client_id", ""),
                            "turn_number": ctx.get("turn_number", ""),
                            "new_chat": ctx.get("new_chat", False),
                            "new_user": ctx.get("new_user", False),
                            "created_at": time.time(),
                            "metadata": json.dumps(metadata),
                        },
                    )

                    if graph_node_id:
                        resolved_node_id = graph_node_id(self) if callable(graph_node_id) else graph_node_id
                        add_graph_attributes(span, resolved_node_id)

                    try:
                        result = await func(self, *args, **kwargs)
                        if capture_output:
                            _attach_output_to_span(span, result)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as exc:
                        error_msg = str(exc) if str(exc) else type(exc).__name__
                        span.set_status(Status(StatusCode.ERROR, str(error_msg)))
                        span.record_exception(exc)
                        raise
                finally:
                    if graph_node_id:
                        pop_graph_node()

        return wrapper

    return decorator


def trace_operation(
    kind: str | None = None,
    open_inference_kind: str | None = None,
    category: str | None = None,
    capture_input: bool = False,
    capture_output: bool = False,
):
    """Decorator for tracing CRUD operations and non-agent functions."""

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = _get_tracer(__name__)

            if args and hasattr(args[0], "__class__"):
                class_name = args[0].__class__.__name__ if not isinstance(args[0], type) else args[0].__name__
                span_name = f"{class_name}.{func.__name__}"
            else:
                span_name = func.__name__

            span_kwargs = {"name": span_name}
            if kind:
                span_kwargs["kind"] = kind

            with tracer.start_as_current_span(**span_kwargs) as span:
                try:
                    if category:
                        span.set_attribute("span.category", category)
                    if capture_input:
                        span.set_attribute("input.args", str(args))
                        span.set_attribute("input.kwargs", str(kwargs))
                    if open_inference_kind:
                        kind_value = getattr(open_inference_kind, "value", open_inference_kind)
                        span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, kind_value)

                    result = await func(*args, **kwargs)
                    if capture_output:
                        span.set_attribute("output", str(result))
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    error_msg = str(exc) if str(exc) else type(exc).__name__
                    span.set_status(Status(StatusCode.ERROR, str(error_msg)))
                    span.record_exception(exc)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = _get_tracer(__name__)

            if args and hasattr(args[0], "__class__"):
                class_name = args[0].__class__.__name__ if not isinstance(args[0], type) else args[0].__name__
                span_name = f"{class_name}.{func.__name__}"
            else:
                span_name = func.__name__

            span_kwargs = {"name": span_name}
            if kind:
                span_kwargs["kind"] = kind

            with tracer.start_as_current_span(**span_kwargs) as span:
                try:
                    if category:
                        span.set_attribute("span.category", category)
                    if capture_input:
                        span.set_attribute("input.args", str(args))
                        span.set_attribute("input.kwargs", str(kwargs))
                    if open_inference_kind:
                        kind_value = getattr(open_inference_kind, "value", open_inference_kind)
                        span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, kind_value)

                    result = func(*args, **kwargs)
                    if capture_output:
                        span.set_attribute("output", str(result))
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    error_msg = str(exc) if str(exc) else type(exc).__name__
                    span.set_status(Status(StatusCode.ERROR, error_msg))
                    span.record_exception(exc)
                    raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class CustomSpanKinds(Enum):
    INIT = "INIT"
    DATABASE = "DATABASE"
    CACHE = "CACHE"
    VECTOR_INDEX = "VECTOR_INDEX"
    SERVER = "SERVER"

