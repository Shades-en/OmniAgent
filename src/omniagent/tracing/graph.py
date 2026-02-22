"""Graph node helpers for tracing visualization."""

from __future__ import annotations

from contextvars import ContextVar

from opentelemetry import trace

# Stack to track graph node hierarchy for automatic parent detection
_graph_node_stack: ContextVar[list[str]] = ContextVar("graph_node_stack", default=[])


def add_graph_attributes(
    span: trace.Span,
    node_id: str,
    parent_id: str | None = None,
    display_name: str | None = None,
) -> None:
    """Add graph visualization attributes to a span for agent path rendering."""
    span.set_attribute("graph.node.id", node_id)

    if parent_id is None:
        try:
            stack = _graph_node_stack.get()
            if stack:
                parent_id = stack[-1]
        except LookupError:
            pass

    if parent_id:
        span.set_attribute("graph.node.parent_id", parent_id)

    if display_name:
        span.set_attribute("graph.node.display_name", display_name)
    else:
        span.set_attribute("graph.node.display_name", node_id.replace("_", " ").title())

    try:
        stack = _graph_node_stack.get().copy()
    except LookupError:
        stack = []
    stack.append(node_id)
    _graph_node_stack.set(stack)


def pop_graph_node() -> None:
    """Pop the current node from the graph node stack."""
    try:
        stack = _graph_node_stack.get().copy()
        if stack:
            stack.pop()
            _graph_node_stack.set(stack)
    except (LookupError, IndexError):
        pass

