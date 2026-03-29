from __future__ import annotations

import json
import logging
from typing import Any

import google.generativeai as genai

from app.core.interfaces.ai_provider import AIProvider
from app.core.models.ai_config import AIServiceConfig

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    """Concrete ``AIProvider`` backed by the Google Gemini API."""

    def __init__(self, api_key: str) -> None:
        genai.configure(api_key=api_key)
        self._api_key = api_key

    def _build_model(self, config: AIServiceConfig) -> genai.GenerativeModel:
        system_parts: list[str] = []
        if config.system_prompt:
            system_parts.append(config.system_prompt)
        if config.instructions:
            system_parts.append(config.instructions)

        return genai.GenerativeModel(
            model_name=config.model,
            system_instruction="\n\n".join(system_parts) if system_parts else None,
            generation_config=genai.GenerationConfig(
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
            ),
        )

    async def generate(self, prompt: str, config: AIServiceConfig) -> str:
        logger.debug("Gemini generate() model=%s temp=%.1f max_tokens=%d", config.model, config.temperature, config.max_tokens)
        model = self._build_model(config)
        response = await model.generate_content_async(prompt)
        logger.debug("Gemini response received (%d chars)", len(response.text))
        return response.text

    async def generate_structured(
        self,
        prompt: str,
        config: AIServiceConfig,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        logger.debug("Gemini generate_structured() model=%s", config.model)
        json_config = config.model_copy(
            update={
                "instructions": (
                    f"{config.instructions}\n\n"
                    "You MUST respond with valid JSON only, no markdown fences.\n"
                    f"Expected schema: {json.dumps(schema)}"
                ),
            },
        )
        model = self._build_model(json_config)
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        logger.debug("Gemini structured response (%d chars)", len(text))

        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error("Gemini returned non-JSON: %s", text[:200])
            raise
