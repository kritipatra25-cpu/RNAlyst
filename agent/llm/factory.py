"""
Factory for resolving configured LLM Providers (Gemini, Groq, Mock, Unavailable) in RNAlyst.
"""

import os
import logging
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from agent.llm.client import BaseLLMProvider
from agent.llm.providers import GeminiLLMProvider, GroqLLMProvider, UnavailableLLMProvider, ConfigurationError

logger = logging.getLogger(__name__)


def get_llm_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None
) -> BaseLLMProvider:
    """
    Resolve and return configured LLM Provider instance.

    Checks provider_name parameter, or falls back to LLM_PROVIDER env variable ('gemini' or 'groq').
    Default is 'gemini'.

    Returns:
        BaseLLMProvider (GeminiLLMProvider, GroqLLMProvider, or UnavailableLLMProvider on config failure).
    """
    env_provider = os.getenv("LLM_PROVIDER")
    if provider_name:
        selected_provider = provider_name.strip().lower()
    elif env_provider:
        selected_provider = env_provider.strip().lower()
    elif os.getenv("GROQ_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        selected_provider = "groq"
    else:
        selected_provider = "gemini"

    if selected_provider == "groq":
        try:
            # If model_name is unspecified or a Gemini model identifier, resolve to configured Groq model
            groq_model = model_name
            if not groq_model or groq_model.lower().startswith("gemini"):
                groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
            logger.info("Initializing GroqLLMProvider with model '%s'...", groq_model)
            return GroqLLMProvider(api_key=api_key, model_name=groq_model)
        except ConfigurationError as config_err:
            logger.warning("GroqLLMProvider configuration failure: %s", config_err)
            return UnavailableLLMProvider(str(config_err))
        except Exception as err:
            logger.error("Failed to instantiate GroqLLMProvider: %s", err)
            return UnavailableLLMProvider(f"Groq provider initialization error: {str(err)}")

    # Default: GeminiLLMProvider
    try:
        gemini_model = model_name
        if not gemini_model or any(gemini_model.lower().startswith(p) for p in ["llama", "mixtral", "gemma"]):
            gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        logger.info("Initializing GeminiLLMProvider with model '%s'...", gemini_model)
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        if gemini_model:
            kwargs["model_name"] = gemini_model
        return GeminiLLMProvider(**kwargs)
    except ConfigurationError as config_err:
        logger.warning("GeminiLLMProvider configuration failure: %s", config_err)
        return UnavailableLLMProvider(str(config_err))
    except Exception as err:
        logger.error("Failed to instantiate GeminiLLMProvider: %s", err)
        return UnavailableLLMProvider(f"Gemini provider initialization error: {str(err)}")

