"""LLM configuration types for provider/model routing."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from omniagent.constants import LLM_API_TYPE_RESPONSES, LLM_TOOL_CHOICE_AUTO


APIType = Literal["responses", "chat_completion"]


class SummaryLLMOverrides(BaseModel):
    """Optional overrides applied only to summary generation."""

    model_config = ConfigDict(extra="forbid")

    model: str | None = None
    temperature: float | None = None
    request_kwargs: dict[str, Any] = Field(default_factory=dict)


class LLMModelConfig(BaseModel):
    """Normalized runtime LLM configuration."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    api_type: APIType = LLM_API_TYPE_RESPONSES
    model: str
    temperature: float | None = None
    tool_choice: str = LLM_TOOL_CHOICE_AUTO
    request_kwargs: dict[str, Any] = Field(default_factory=dict)
    summary: SummaryLLMOverrides | None = None

    def effective_summary_config(self) -> "LLMModelConfig":
        """Build the effective config for summary generation."""
        if self.summary is None:
            return self

        summary_request_kwargs = dict(self.request_kwargs)
        summary_request_kwargs.update(self.summary.request_kwargs)

        return self.model_copy(
            update={
                "model": self.summary.model or self.model,
                "temperature": (
                    self.summary.temperature
                    if self.summary.temperature is not None
                    else self.temperature
                ),
                "request_kwargs": summary_request_kwargs,
                "summary": None,
            }
        )
