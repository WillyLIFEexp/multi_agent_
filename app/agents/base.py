"""Base agent abstraction."""
from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Common interface for all agents."""

    name: str = "base"

    def __init__(self, model: str | None = None) -> None:
        self.model = model

    @abstractmethod
    async def run(self, prompt: str, **kwargs: Any) -> str:
        """Execute the agent against a prompt and return its response."""
        raise NotImplementedError
