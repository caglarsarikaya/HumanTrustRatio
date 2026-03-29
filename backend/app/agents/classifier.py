from __future__ import annotations

import logging

from app.agents.base_agent import BaseAgent
from app.core.models.ai_config import AIServiceConfig, ModelTier
from app.core.models.resume import PersonProfile
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert resume analyst. Given a resume in plain text, "
    "extract the person's structured information. Be precise and only "
    "include information that is explicitly stated in the resume."
)

_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "full_name": {"type": "string"},
        "title": {"type": "string"},
        "email": {"type": "string"},
        "phone": {"type": "string"},
        "location": {"type": "string"},
        "summary": {"type": "string"},
        "skills": {"type": "array", "items": {"type": "string"}},
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "title": {"type": "string"},
                    "duration": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "institution": {"type": "string"},
                    "degree": {"type": "string"},
                    "field": {"type": "string"},
                    "year": {"type": "string"},
                },
            },
        },
        "links": {"type": "array", "items": {"type": "string"}},
        "certifications": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["full_name"],
}


class ClassifierAgent(BaseAgent):
    """Agent 2 -- send resume text to the AI and get a structured profile."""

    def __init__(self, ai_service: AIService) -> None:
        self._ai = ai_service

    @property
    def name(self) -> str:
        return "Classifier"

    async def execute(self, resume_text: str) -> PersonProfile:
        logger.info("Classifying resume text (%d chars)", len(resume_text))
        config = AIServiceConfig.from_tier(
            ModelTier.MEDIUM,
            system_prompt=_SYSTEM_PROMPT,
            response_format="json",
        )
        logger.debug("Using model: %s (tier=MEDIUM)", config.model)

        prompt = (
            "Extract the structured profile from the following resume.\n\n"
            f"--- RESUME START ---\n{resume_text}\n--- RESUME END ---"
        )

        logger.info("Sending prompt to AI for classification...")
        data = await self._ai.complete_structured(prompt, config, _SCHEMA)
        name = data.get("full_name", "unknown")
        skills_count = len(data.get("skills", []))
        exp_count = len(data.get("experience", []))
        logger.info(
            "Classified: name=%s, skills=%d, experience=%d, links=%d",
            name, skills_count, exp_count, len(data.get("links", [])),
        )
        return PersonProfile.model_validate(data)
