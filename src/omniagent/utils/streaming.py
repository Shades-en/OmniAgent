"""Streaming utilities for OmniAgent.

Provides helper functions for SSE (Server-Sent Events) streaming
compatible with AI SDK data stream protocol.
"""

import json
from typing import Dict, Any

from omniagent.constants import (
    STREAM_HEADER_NAME,
    STREAM_HEADER_VERSION,
    STREAM_DONE_SENTINEL,
)


def get_streaming_headers() -> Dict[str, str]:
    """
    Get the required HTTP headers for SSE streaming responses.
    
    Returns headers compatible with Vercel AI SDK and standard SSE.
    
    Returns:
        Dict of header name to value
    """
    return {
        STREAM_HEADER_NAME: STREAM_HEADER_VERSION,
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "x-vercel-ai-protocol": "data",
    }


def format_sse_event(event: Dict[str, Any]) -> str:
    """
    Format an event dictionary as an SSE data line.
    
    Args:
        event: Event dictionary to format
        
    Returns:
        Formatted SSE string: "data: {json}\n\n"
    """
    return f"data: {json.dumps(event)}\n\n"


def format_sse_done() -> str:
    """
    Get the SSE done sentinel string.
    
    Returns:
        Formatted SSE done string: "data: [DONE]\n\n"
    """
    return f"data: {STREAM_DONE_SENTINEL}\n\n"
