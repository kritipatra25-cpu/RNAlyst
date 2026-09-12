"""
LLM Provider Factory.
Provides a configurable mechanism for instantiating LLM providers based on environment settings.
"""
import os
import logging
from typing import Optional
from pipeline.llm_provider import BaseLLMProvider, MockLLMProvider, OpenAILLMProvider, GeminiLLMProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """
    Factory for instantiating LLM providers.
    Controlled by environment variable `LLM_PROVIDER_TYPE` or explicit parameter.
    Defaults to 'none' (disabled / deterministic fallback).
    """

    @staticmethod
    def get_provider(provider_type: Optional[str] = None, **kwargs) -> Optional[BaseLLMProvider]:
        ptype = provider_type or os.environ.get("LLM_PROVIDER_TYPE", "none")
        ptype = str(ptype).strip().lower()

        if ptype in ["none", "disabled", "false", "off", ""]:
            logger.info("LLMProviderFactory: Provider disabled ('%s'). Using deterministic fallback.", ptype)
            return None
        elif ptype == "mock":
            logger.info("LLMProviderFactory: Using MockLLMProvider.")
            return MockLLMProvider(**kwargs)
        elif ptype == "openai":
            logger.info("LLMProviderFactory: Instantiating OpenAILLMProvider.")
            return OpenAILLMProvider(**kwargs)
        elif ptype == "gemini":
            logger.info("LLMProviderFactory: Instantiating GeminiLLMProvider.")
            return GeminiLLMProvider(**kwargs)
        else:
            logger.warning("LLMProviderFactory: Unknown provider type '%s'. Falling back to 'none'.", ptype)
            return None
