from omniagent.ai.providers.llm_provider import LLMProvider
from omniagent.ai.providers.openai import OpenAIChatCompletionAPI, OpenAIResponsesAPI
from omniagent.constants import (
    LLM_API_TYPE_CHAT_COMPLETION,
    LLM_API_TYPE_RESPONSES,
    OPENAI,
)
from omniagent.types.llm import APIType


def get_llm_provider(
    provider_name: str,
    api_type: APIType = LLM_API_TYPE_RESPONSES,
) -> type[LLMProvider]:
    if provider_name == OPENAI:
        if api_type == LLM_API_TYPE_CHAT_COMPLETION:
            return OpenAIChatCompletionAPI
        return OpenAIResponsesAPI
    raise ValueError(f"Unknown provider: {provider_name}")
