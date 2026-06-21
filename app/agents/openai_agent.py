"""A concrete single-shot chat agent, backed by any configured LLM provider."""
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.base import BaseAgent
from app.core.settings.config import get_settings
from app.utility.llm import get_llm


class OpenAIAgent(BaseAgent):
    """Single-shot chat agent. Provider chosen via the LLM factory."""

    name = "chat"

    def __init__(
        self,
        model: str | None = None,
        system_prompt: str = "You are a helpful assistant.",
        provider: str | None = None,
    ) -> None:
        settings = get_settings()
        super().__init__(model=model or settings.default_model)
        self.system_prompt = system_prompt
        self._llm = get_llm(provider=provider, model=model)

    async def run(self, prompt: str, **kwargs: Any) -> str:
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt),
        ]
        response = await self._llm.ainvoke(messages, **kwargs)
        return response.content
