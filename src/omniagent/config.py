## Configuration file for OmniAgent

import os

from omniagent.constants import (
    GPT_4_1_MINI,
    LLM_API_TYPE_CHAT_COMPLETION,
    LLM_API_TYPE_RESPONSES,
    LLM_MODEL_PROVIDER_INFERENCE_MAP_DEFAULT,
    LLM_PROVIDER_DEFAULT_API_TYPE_MAP_DEFAULT,
    OPENAI,
    TEXT_EMBEDDING_3_SMALL,
)
from omniagent.utils.general import _env_flag, _load_json_dict, _load_json_string_map

# LLM Providers
LLM_PROVIDER = os.getenv("LLM_PROVIDER", OPENAI)
LLM_API_TYPE = os.getenv("LLM_API_TYPE", LLM_API_TYPE_RESPONSES)
LLM_MODEL_PROVIDER_INFERENCE_MAP = _load_json_string_map(
    "LLM_MODEL_PROVIDER_INFERENCE_MAP",
    LLM_MODEL_PROVIDER_INFERENCE_MAP_DEFAULT,
)
LLM_PROVIDER_DEFAULT_API_TYPE_MAP = _load_json_string_map(
    "LLM_PROVIDER_DEFAULT_API_TYPE_MAP",
    LLM_PROVIDER_DEFAULT_API_TYPE_MAP_DEFAULT,
)
_VALID_LLM_API_TYPES = {LLM_API_TYPE_RESPONSES, LLM_API_TYPE_CHAT_COMPLETION}
for provider_name, provider_api_type in LLM_PROVIDER_DEFAULT_API_TYPE_MAP.items():
    if provider_api_type not in _VALID_LLM_API_TYPES:
        raise ValueError(
            "LLM_PROVIDER_DEFAULT_API_TYPE_MAP contains invalid api_type "
            f"'{provider_api_type}' for provider '{provider_name}'. "
            f"Valid values are: {sorted(_VALID_LLM_API_TYPES)}"
        )
MOCK_AI_RESPONSE = _env_flag("MOCK_AI_RESPONSE", False)
MOCK_AI_CHAT_NAME = _env_flag("MOCK_AI_CHAT_NAME", False)
MOCK_AI_SUMMARY = _env_flag("MOCK_AI_SUMMARY", False)

# Model Configuration
BASE_MODEL = os.getenv("BASE_MODEL", GPT_4_1_MINI)
BASE_EMBEDDING_MODEL = os.getenv("BASE_EMBEDDING_MODEL", TEXT_EMBEDDING_3_SMALL)
CHAT_NAME_LLM_PROVIDER = os.getenv("CHAT_NAME_LLM_PROVIDER", LLM_PROVIDER)
CHAT_NAME_LLM_API_TYPE = os.getenv("CHAT_NAME_LLM_API_TYPE", LLM_API_TYPE)
CHAT_NAME_MODEL = os.getenv("CHAT_NAME_MODEL", BASE_MODEL)
CHAT_NAME_TEMPERATURE = float(os.getenv("CHAT_NAME_TEMPERATURE", "0.7"))
CHAT_NAME_REQUEST_KWARGS = _load_json_dict("CHAT_NAME_REQUEST_KWARGS")

# Context Configuration - For Summary
MAX_TOKEN_THRESHOLD = int(os.getenv("MAX_TOKEN_THRESHOLD", 50000))
MAX_TURNS_TO_FETCH = int(os.getenv("MAX_TURNS_TO_FETCH", 100))

# Tracing config
ENABLE_TRACING = _env_flag("ENABLE_TRACING", True)
ENABLE_INPUT_GUARDRAIL = _env_flag("ENABLE_INPUT_GUARDRAIL", True)
ENABLE_OUTPUT_GUARDRAIL = _env_flag("ENABLE_OUTPUT_GUARDRAIL", True)

# AGENT
MAX_STEPS = 10

# AI SDK Configuration
AISDK_ID_LENGTH = 16

# Session Configuration
DEFAULT_SESSION_NAME = os.getenv("DEFAULT_SESSION_NAME", "New Chat")
CHAT_NAME_CONTEXT_MAX_MESSAGES = 40

# Pagination Configuration
DEFAULT_MESSAGE_PAGE_SIZE = int(os.getenv("DEFAULT_MESSAGE_PAGE_SIZE", 50))
MAX_MESSAGE_PAGE_SIZE = int(os.getenv("MAX_MESSAGE_PAGE_SIZE", 100))
DEFAULT_SESSION_PAGE_SIZE = int(os.getenv("DEFAULT_SESSION_PAGE_SIZE", 20))
MAX_SESSION_PAGE_SIZE = int(os.getenv("MAX_SESSION_PAGE_SIZE", 50))
