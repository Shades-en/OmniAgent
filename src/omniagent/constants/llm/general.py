"""General LLM constants shared across providers."""

from omniagent.constants.llm.openai import LLM_API_TYPE_RESPONSES

# Providers
OPENAI = "openai"

# LLM config defaults
LLM_TOOL_CHOICE_AUTO = "auto"
LLM_MODEL_PROVIDER_INFERENCE_MAP_DEFAULT: dict[str, str] = {
    "gpt-": OPENAI,
    "o1": OPENAI,
    "o3": OPENAI,
}
LLM_PROVIDER_DEFAULT_API_TYPE_MAP_DEFAULT: dict[str, str] = {
    OPENAI: LLM_API_TYPE_RESPONSES,
}
