from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.core.models.ai_config import AIServiceConfig


class AIProvider(ABC):
    """Abstract base for all AI/LLM providers (Gemini, OpenAI, etc.)."""

    @abstractmethod
    async def generate(self, prompt: str, config: AIServiceConfig) -> str:
        """Return a plain-text completion."""
        ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        config: AIServiceConfig,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a JSON dict that conforms to *schema*."""
        ...
