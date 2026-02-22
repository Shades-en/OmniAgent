"""Serialization and span-attribute helper functions for tracing."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
import json
import logging
from typing import Any, Mapping

from beanie import PydanticObjectId
from bson import ObjectId
from openinference.semconv.trace import SpanAttributes
from opentelemetry import trace

logger = logging.getLogger(__name__)


def _set_span_attributes(span: trace.Span, attributes: Mapping[str, Any]) -> None:
    """Set multiple attributes on a span, skipping None/empty values."""
    for key, value in attributes.items():
        if value:
            span.set_attribute(key, value)


def _serialize_for_json(obj: Any) -> Any:
    """Custom JSON serializer for enums, datetimes, ObjectIds, and model objects."""
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, (ObjectId, PydanticObjectId)):
        return str(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize_for_json(item) for item in obj]
    return obj


def _attach_output_to_span(span: trace.Span, result: Any) -> None:
    """Attach serializable output value to a span."""
    try:
        if result is None:
            return

        output_value = None
        if hasattr(result, "model_dump"):
            output_value = json.dumps(result.model_dump())
        elif isinstance(result, list) and all(hasattr(item, "model_dump") for item in result):
            output_value = json.dumps([item.model_dump() for item in result])
        elif isinstance(result, (dict, list, str, int, float, bool)):
            output_value = json.dumps(_serialize_for_json(result))

        if not output_value:
            logger.debug("Could not serialize output of type %s", type(result))
            return

        max_length = 10000
        if len(output_value) > max_length:
            output_value = output_value[:max_length] + "... [truncated]"
            logger.debug("Output truncated to %s chars for span", max_length)

        span.set_attribute(SpanAttributes.OUTPUT_VALUE, output_value)
        logger.debug("Attached output to span: %s chars", len(output_value))
    except Exception as exc:
        logger.warning("Failed to attach output to span: %s", exc)

