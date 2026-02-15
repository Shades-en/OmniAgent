"""
LLM Provider-related exceptions for OmniAgent.
"""

from omniagent.exceptions.base import OmniAgentError


class ProviderError(OmniAgentError):
    """Base exception for all LLM provider-related errors."""
    pass


class UnrecognizedMessageTypeError(ProviderError):
    """Raised when an unrecognized message type is received from an LLM provider."""
    pass


class MessageParseError(ProviderError):
    """Raised when parsing of LLM response fails."""
    pass
