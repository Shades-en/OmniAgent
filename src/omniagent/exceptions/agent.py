"""
Agent-related exceptions for OmniAgent.
"""

from omniagent.exceptions.base import OmniAgentError


class AgentError(OmniAgentError):
    """Base exception for all agent-related errors."""
    pass


class MaxStepsReachedError(AgentError):
    """Raised when the agent exceeds the maximum number of steps allowed in a single turn.
    
    Attributes:
        current_step: The step number when the limit was reached
        max_steps: The maximum allowed steps
    """
    
    def __init__(
        self,
        message: str = "Maximum number of steps reached",
        *,
        details: str | None = None,
        current_step: int | None = None,
        max_steps: int | None = None,
    ):
        # Build details with step information
        detail_parts = []
        if details:
            detail_parts.append(details)
        if current_step is not None:
            detail_parts.append(f"Current step: {current_step}")
        if max_steps is not None:
            detail_parts.append(f"Max steps: {max_steps}")
        
        full_details = ". ".join(detail_parts) if detail_parts else None
        
        super().__init__(message, details=full_details)
        self.current_step = current_step
        self.max_steps = max_steps
