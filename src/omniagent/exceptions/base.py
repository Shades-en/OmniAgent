"""
Base exception classes for OmniAgent.
"""


class OmniAgentError(Exception):
    """Base exception for all OmniAgent errors.
    
    All custom exceptions in the omniagent package should inherit from this class.
    This allows consumers to catch all omniagent-related errors with a single except clause.
    
    Attributes:
        message: Human-readable error description
        details: Additional context about the error (optional)
    """
    
    def __init__(self, message: str, *, details: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"
