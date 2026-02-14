"""
Utility modules for OmniAgent.

This package provides common utilities for:
- General helpers (ID generation, environment variables, token counting)
- Logging with colored output and OpenTelemetry integration
- Singleton pattern implementations
- Task registry for managing async tasks
- Distributed tracing with OpenTelemetry
"""

from omniagent.utils.general import (
    generate_id,
    get_env_int,
    _env_flag,
    get_token_count,
    safe_get_arg,
    generate_order,
)

from omniagent.utils.logger import (
    OTelColorFormatter,
    setup_logging,
)

from omniagent.utils.singleton import (
    SingletonMeta,
    SingletonABCMeta,
)

from omniagent.utils.task_registry import (
    register_task,
    cancel_task,
    unregister_task,
)

from omniagent.utils.tracing import (
    trace_context,
    set_trace_context,
    get_trace_context,
    clear_trace_context,
    trace_method,
    trace_operation,
    add_graph_attributes,
    pop_graph_node,
    track_state_change,
    CustomSpanKinds,
)

__all__ = [
    # General utilities
    "generate_id",
    "get_env_int",
    "_env_flag",
    "get_token_count",
    "safe_get_arg",
    "generate_order",
    # Logging
    "OTelColorFormatter",
    "setup_logging",
    # Singleton patterns
    "SingletonMeta",
    "SingletonABCMeta",
    # Task registry
    "register_task",
    "cancel_task",
    "unregister_task",
    # Tracing - Context management
    "trace_context",
    "set_trace_context",
    "get_trace_context",
    "clear_trace_context",
    # Tracing - Decorators
    "trace_method",
    "trace_operation",
    # Tracing - Graph visualization
    "add_graph_attributes",
    "pop_graph_node",
    # Tracing - State tracking
    "track_state_change",
    # Tracing - Span kinds
    "CustomSpanKinds",
]
