from __future__ import annotations

import logging
import time
from typing import Any

from app.core.interfaces.ai_provider import AIProvider
from app.core.models.ai_config import AIServiceConfig

logger = logging.getLogger(__name__)


class AIService:
    """Thin, provider-agnostic wrapper around any ``AIProvider``.

    Instantiate with whichever provider you want, then call
    ``complete`` / ``complete_structured`` with an ``AIServiceConfig``.
    """

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider
        logger.info("AIService initialised with provider: %s", type(provider).__name__)

    async def complete(self, prompt: str, config: AIServiceConfig) -> str:
        logger.debug("complete() model=%s prompt_len=%d", config.model, len(prompt))
        t0 = time.perf_counter()
        result = await self._provider.generate(prompt, config)
        elapsed = time.perf_counter() - t0
        logger.info("complete() finished in %.2fs (response_len=%d)", elapsed, len(result))
        return result

    async def complete_structured(
        self,
        prompt: str,
        config: AIServiceConfig,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        logger.debug("complete_structured() model=%s prompt_len=%d", config.model, len(prompt))
        t0 = time.perf_counter()
        result = await self._provider.generate_structured(prompt, config, schema)
        elapsed = time.perf_counter() - t0
        logger.info("complete_structured() finished in %.2fs (keys=%s)", elapsed, list(result.keys()))
        return result
