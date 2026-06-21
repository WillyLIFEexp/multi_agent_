"""LLM provider factory.

Lets the caller choose which backend to use for a chat model:

- ``openai`` : OpenAI API
- ``azure``  : Azure OpenAI API
- ``ollama`` : Local Ollama server

All three return a LangChain ``BaseChatModel`` so the rest of the app
(agents, chains, tools) is provider-agnostic.
"""
from enum import Enum

from langchain_core.language_models import BaseChatModel

from app.core.settings.config import get_settings


class LLMProvider(str, Enum):
    """Supported LLM backends."""

    OPENAI = "openai"
    AZURE = "azure"
    OLLAMA = "ollama"


def get_llm(
    provider: str | LLMProvider | None = None,
    model: str | None = None,
    temperature: float | None = None,
    **kwargs,
) -> BaseChatModel:
    """Return a chat model for the chosen provider.

    Args:
        provider: ``openai``, ``azure`` or ``ollama``. Falls back to
            ``settings.llm_provider`` when not given.
        model: Model / deployment name. Falls back to a provider default.
        temperature: Sampling temperature. Falls back to ``settings.temperature``.
        **kwargs: Extra keyword args forwarded to the underlying chat model.

    Raises:
        ValueError: if the provider is unknown or required config is missing.
    """
    settings = get_settings()
    provider = LLMProvider((provider or settings.llm_provider).lower())
    temperature = settings.temperature if temperature is None else temperature

    if provider is LLMProvider.OPENAI:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model or settings.default_model,
            temperature=temperature,
            api_key=settings.openai_api_key,
            **kwargs,
        )

    if provider is LLMProvider.AZURE:
        from langchain_openai import AzureChatOpenAI

        if not settings.azure_openai_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is required for the azure provider")
        return AzureChatOpenAI(
            azure_deployment=model or settings.azure_openai_deployment,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            temperature=temperature,
            **kwargs,
        )

    if provider is LLMProvider.OLLAMA:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model or settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
            **kwargs,
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")
