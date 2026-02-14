## Configuration file for OmniAgent

from omniagent.constants import GPT_4_1_MINI, TEXT_EMBEDDING_3_SMALL, OPENAI
from omniagent.utils.general import _env_flag

import os

# LLM Providers
LLM_PROVIDER = os.getenv("LLM_PROVIDER", OPENAI)
MOCK_AI_RESPONSE = _env_flag("MOCK_AI_RESPONSE", False)
MOCK_AI_CHAT_NAME = _env_flag("MOCK_AI_CHAT_NAME", False)
MOCK_AI_SUMMARY = _env_flag("MOCK_AI_SUMMARY", False)

# Model Configuration
BASE_MODEL = os.getenv("BASE_MODEL", GPT_4_1_MINI)
BASE_EMBEDDING_MODEL = os.getenv("BASE_EMBEDDING_MODEL", TEXT_EMBEDDING_3_SMALL)

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
