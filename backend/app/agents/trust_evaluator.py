from __future__ import annotations

import logging
from datetime import date

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
    "2. Use each footprint's identity_match_score (0 to 10) to judge whether the page is about "
    "the same person.\n"
    "3. Use each footprint's strong_evidence_score (0 to 10) to judge how strongly the page "
    "supports or contradicts resume claims.\n"
    "4. For each category (identity, employment, skills, education, "
    "online_presence), assign a score from 0 to 100.\n"
    "3. Flag ONLY when you find concrete evidence that CONTRADICTS a resume claim.\n"
    "4. Compute an overall trust score (weighted average).\n"
    "5. Provide clear reasoning for each score.\n\n"
    "CRITICAL RULES:\n"
    "- Absence of evidence is NOT a red flag. If you cannot find information "
    "about a claim, that is NEUTRAL — do NOT lower the score or flag it. "
    "Most people and companies do not publish everything online.\n"
    "- Only flag something if you find DIRECT CONTRADICTING evidence "
    "(e.g. a source says they worked at Company X from 2018-2020, but the "
    "resume says 2016-2021).\n"
    "- 'Unverified' is NOT the same as 'contradicted'. Never flag a claim "
    "simply because you could not find online confirmation.\n"
    "- When you find a profile with the same name but different career details, "
    "consider that it may be a DIFFERENT PERSON with the same name. Only flag "
    "it as conflicting if there is strong evidence it is the SAME person "
    "(e.g. same photo, same email, same location, overlapping employment).\n"
    "- For employment dates, use today's date to determine if a date is in "
    "the past or future. Today's date will be provided in the prompt.\n"
    "- A score of 50 means no evidence either way (neutral). Scores below 50 "
    "require actual contradicting evidence. Scores above 50 mean supporting "
    "evidence was found."
    "Do not rely on pages with weak identity_match_score "
    "as strong evidence for trust."
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
            f"Strong evidence: {fp.strong_evidence_score:.1f}/10\n"
            f"Identity match: {fp.identity_match_score:.1f}/10\n"
            "Use this page only to the extent the identity match is credible."
            for fp in footprints
        )

        if not footprint_summaries:
            footprint_summaries = "(No digital footprints were found.)"

        today = date.today().strftime("%B %d, %Y")

        prompt = (
            f"## Today's Date\n{today}\n\n"
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
            "Now produce the trust index. Remember: only flag claims where "
            "you see CONTRADICTING evidence. If no evidence was found for a "
            "claim, that is neutral — do NOT flag it."
            "Treat identity_match_score as a gate on how much a page should influence trust. "
            "Treat strong_evidence_score as the strength of support or contradiction once identity is credible.\n\n"
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
