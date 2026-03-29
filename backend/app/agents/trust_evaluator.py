from __future__ import annotations

import logging

from app.agents.base_agent import BaseAgent
from app.core.models.ai_config import AIServiceConfig, ModelTier
from app.core.models.footprint import DigitalFootprint
from app.core.models.resume import PersonProfile
from app.core.models.trust import TrustIndex
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a trust verification analyst. You will receive a person's "
    "resume profile and their digital footprints gathered from the web.\n\n"
    "Your job:\n"
    "1. Compare the resume claims against the online evidence.\n"
    "2. For each category (identity, employment, skills, education, "
    "online_presence), assign a score from 0 to 100.\n"
    "3. Flag any discrepancies or red flags.\n"
    "4. Compute an overall trust score (weighted average).\n"
    "5. Provide clear reasoning for each score.\n\n"
    "Be fair but thorough. Absence of evidence is not evidence of fraud, "
    "but should lower confidence."
)

_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "overall_score": {"type": "number", "minimum": 0, "maximum": 100},
        "categories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "score": {"type": "number"},
                    "evidence": {"type": "string"},
                },
            },
        },
        "flags": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["overall_score", "categories", "reasoning"],
}


class TrustEvaluatorAgent(BaseAgent):
    """Agent 4 -- compare the resume profile against digital footprints
    and produce a Trust Index."""

    def __init__(self, ai_service: AIService) -> None:
        self._ai = ai_service

    @property
    def name(self) -> str:
        return "Trust Evaluator"

    async def execute(
        self,
        profile: PersonProfile,
        footprints: list[DigitalFootprint],
    ) -> TrustIndex:
        logger.info(
            "Evaluating trust for '%s' with %d footprints",
            profile.full_name, len(footprints),
        )
        config = AIServiceConfig.from_tier(
            ModelTier.HIGH,
            system_prompt=_SYSTEM_PROMPT,
            response_format="json",
        )
        logger.debug("Using model: %s (tier=HIGH)", config.model)

        footprint_summaries = "\n\n".join(
            f"Source: {fp.source_url}\n"
            f"Platform: {fp.platform}\n"
            f"Summary: {fp.summary}\n"
            f"Matched claims: {', '.join(fp.matched_claims)}\n"
            f"Relevance: {fp.relevance_score:.1%}"
            for fp in footprints
        )

        if not footprint_summaries:
            footprint_summaries = "(No digital footprints were found.)"

        prompt = (
            "## Resume Profile\n"
            f"Name: {profile.full_name}\n"
            f"Title: {profile.title}\n"
            f"Location: {profile.location}\n"
            f"Skills: {', '.join(profile.skills)}\n"
            f"Experience:\n"
            + "\n".join(
                f"  - {e.title} at {e.company} ({e.duration})"
                for e in profile.experience
            )
            + f"\nEducation:\n"
            + "\n".join(
                f"  - {ed.degree} in {ed.field} from {ed.institution} ({ed.year})"
                for ed in profile.education
            )
            + f"\nLinks: {', '.join(profile.links)}\n\n"
            f"## Digital Footprints\n{footprint_summaries}\n\n"
            "Now produce the trust index."
        )

        logger.info("Sending prompt to AI for trust evaluation...")
        data = await self._ai.complete_structured(prompt, config, _SCHEMA)
        score = data.get("overall_score", -1)
        categories = data.get("categories", [])
        flags = data.get("flags", [])
        logger.info("Trust score for '%s': %.0f / 100", profile.full_name, score)
        for cat in categories:
            logger.info("  Category %-20s score=%.0f", cat.get("name", "?"), cat.get("score", 0))
        if flags:
            logger.warning("  Flags: %s", ", ".join(flags))
        return TrustIndex.model_validate(data)
