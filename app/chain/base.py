"""Base chain abstraction for composing agents / steps."""
from abc import ABC, abstractmethod
from typing import Any


class BaseChain(ABC):
    """A chain orchestrates a sequence of steps or agents."""

    @abstractmethod
    async def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Run the chain end-to-end and return its outputs."""
        raise NotImplementedError
