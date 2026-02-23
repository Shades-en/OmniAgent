"""OpenAI-specific LLM constants."""

# OpenAI LLM API types
LLM_API_TYPE_RESPONSES = "responses"
LLM_API_TYPE_CHAT_COMPLETION = "chat_completion"

OPENAI_RESPONSES_ALLOWED_REQUEST_KWARGS: set[str] = {
    "max_output_tokens",
    "metadata",
    "parallel_tool_calls",
    "reasoning",
    "response_format",
    "service_tier",
    "store",
    "top_p",
    "truncation",
    "user",
}

OPENAI_CHAT_COMPLETIONS_ALLOWED_REQUEST_KWARGS: set[str] = {
    "frequency_penalty",
    "logit_bias",
    "logprobs",
    "max_completion_tokens",
    "n",
    "parallel_tool_calls",
    "presence_penalty",
    "response_format",
    "seed",
    "stop",
    "top_logprobs",
    "top_p",
    "user",
}
