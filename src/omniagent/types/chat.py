"""Chat-related types for the OmniAgent runtime."""

from pydantic import BaseModel, Field
from typing import Literal, Dict, Any
from dataclasses import dataclass

from omniagent.utils.general import generate_id
from omniagent.config import AISDK_ID_LENGTH

# Type alias for LLM API type selection
APIType = Literal["responses", "chat_completion"]


class MessageQuery(BaseModel):
    """
    Represents a user query message to be processed by the agent.
    
    Attributes:
        query: The text content of the user's query
        id: Optional frontend-generated message ID (e.g., from AI SDK)
    """
    query: str = Field(..., description="The query to be sent to the agent")
    id: str | None = Field(
        default_factory=lambda: generate_id(AISDK_ID_LENGTH, "nanoid"),
        description="The frontend-generated id of the message (e.g., from AI SDK)"
    )


@dataclass
class RunnerOptions:
    """
    Configuration options for the Runner.
    
    Attributes:
        provider_options: Provider-specific options (e.g., {'api_type': 'chat_completion'} for OpenAI)
        stream: Whether to enable streaming responses (default: True)
    """
    provider_options: Dict[str, Any] | None = None
    stream: bool = True
