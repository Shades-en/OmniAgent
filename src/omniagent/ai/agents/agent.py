from __future__ import annotations

from typing import Callable, cast

from omniagent import config
from omniagent.ai.providers import get_llm_provider
from omniagent.ai.tools.tools import Tool
from omniagent.types.llm import APIType, LLMModelConfig
from omniagent.types.state import State


class Agent:
    def __init__(
        self,
        name: str,
        description: str,
        instructions: str,
        model: LLMModelConfig | str | None = None,
        tools: list[Tool] | None = None,
        current_state: State | None = None,
        before_model_callback: Callable | None = None,
        after_model_callback: Callable | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.instructions = instructions
        self.model = self._normalize_model_config(model)
        self.llm_provider = get_llm_provider(
            provider_name=self.model.provider,
            api_type=self.model.api_type,
        )
        self.tools = tools or []
        self.current_state = current_state
        self.before_model_callback = before_model_callback
        self.after_model_callback = after_model_callback

    @staticmethod
    def _lookup_model_mapping(
        model_name: str,
        mapping: dict[str, str],
    ) -> str | None:
        matched_value: str | None = None
        matched_pattern_length = -1

        for pattern, value in mapping.items():
            prefix = pattern[:-1] if pattern.endswith("*") else pattern
            if not prefix:
                continue
            if model_name == prefix or model_name.startswith(prefix):
                prefix_length = len(prefix)
                if prefix_length > matched_pattern_length:
                    matched_pattern_length = prefix_length
                    matched_value = value

        return matched_value

    @classmethod
    def _infer_provider_and_api_type(cls, model_name: str) -> tuple[str, APIType]:
        provider = cls._lookup_model_mapping(
            model_name=model_name,
            mapping=config.LLM_MODEL_PROVIDER_INFERENCE_MAP,
        )
        if provider is None:
            raise ValueError(
                f"Unrecognized model '{model_name}'. Add inference mappings in "
                "LLM_MODEL_PROVIDER_INFERENCE_MAP, or pass an explicit LLMModelConfig."
            )

        api_type = config.LLM_PROVIDER_DEFAULT_API_TYPE_MAP.get(provider)
        if api_type is None:
            raise ValueError(
                f"No default API type configured for provider '{provider}'. "
                "Update LLM_PROVIDER_DEFAULT_API_TYPE_MAP or pass an explicit "
                "LLMModelConfig."
            )
        return provider, cast(APIType, api_type)

    @classmethod
    def _normalize_model_config(cls, model: LLMModelConfig | str | None) -> LLMModelConfig:
        if model is None:
            return LLMModelConfig(
                provider=config.LLM_PROVIDER,
                api_type=config.LLM_API_TYPE,
                model=config.BASE_MODEL,
            )

        if isinstance(model, LLMModelConfig):
            return model

        if isinstance(model, str):
            provider, api_type = cls._infer_provider_and_api_type(model_name=model)
            return LLMModelConfig(
                provider=provider,
                api_type=api_type,
                model=model,
            )
        
        raise TypeError(
            "Agent.model must be None, a model string, or an LLMModelConfig."
        )
