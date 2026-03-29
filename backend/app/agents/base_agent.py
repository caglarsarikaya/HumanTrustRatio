from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Common contract for every agent in the pipeline."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable agent name for logging / UI."""
        ...

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Run this agent's task and return its output."""
        ...
