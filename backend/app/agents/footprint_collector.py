from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field

from app.agents.base_agent import BaseAgent
from app.core.interfaces.search_engine import SearchEngine
from app.core.interfaces.web_scraper import WebScraper
from app.core.models.ai_config import AIServiceConfig, ModelTier
from app.core.models.footprint import DigitalFootprint, ScrapedPage, SearchResult
from app.core.models.resume import PersonProfile
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

_MAX_PAGES_TO_SCRAPE = 15


@dataclass
class CollectorResult:
    """Everything the footprint collector gathered."""
    queries: list[str] = field(default_factory=list)
    search_results: list[SearchResult] = field(default_factory=list)
    footprints: list[DigitalFootprint] = field(default_factory=list)

_QUERY_GEN_SYSTEM = (
    "You are an OSINT query-generation assistant for resume verification. "
    "Given a person's resume profile, generate 2-4 high-precision web search queries"
    "to find evidence of that person's online footprint.\n\n"
    "Objective:\n"
    "- Maximize the chance that each query returns results about this exact person.\n"
    "- Prefer identity-confirming sources such as LinkedIn, GitHub, employer pages, "
    "university pages, personal websites, conference bios, and publication profiles.\n\n"
    "Rules:\n"
    "- Most queries must include the person's full name in quotes.\n"
    "- Use one strong disambiguating attribute per query when available: employer, "
    "university, location, title/specialty, GitHub username, company domain, or email.\n"
    "- Queries must be short, realistic search-engine queries.\n"
    "- Queries should be diverse; do not output near-duplicates.\n"
    "- If email is available, include at most one email-based query if it is likely to be useful.\n"
    "- Prefer site-restricted queries when helpful, such as site:linkedin.com/in, site:github.com, "
    "site:company.com, or a university domain.\n"
    "- Avoid generic or low-signal queries.\n"
    "- Do not stuff many attributes into one query.\n"
    "- If the profile is sparse, use fewer queries and rely on the strongest available anchors.\n"
    "- If the name is common, prioritize stronger disambiguators like employer, university, or location."
)

_QUERY_GEN_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "queries": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 6,
        },
    },
    "required": ["queries"],
}

_SUMMARISE_SYSTEM = (
    "You are verifying a person's online presence. Given a web page's text "
    "and the person's profile, extract any information that confirms or "
    "contradicts the person's resume claims. Be concise."
)

_SUMMARISE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "platform": {"type": "string"},
        "summary": {"type": "string"},
        "matched_claims": {"type": "array", "items": {"type": "string"}},
        "relevance_score": {"type": "number", "minimum": 0, "maximum": 1},
    },
}

_URL_RE = re.compile(r"https?://[^\s,\"'<>]+|(?:[\w-]+\.)+(?:com|org|net|io|dev|me|co)[/\w.-]*")


class FootprintCollectorAgent(BaseAgent):
    """Agent 3 -- search the web and scrape pages for digital footprints."""

    def __init__(
        self,
        ai_service: AIService,
        search_engine: SearchEngine,
        web_scraper: WebScraper,
    ) -> None:
        self._ai = ai_service
        self._search = search_engine
        self._scraper = web_scraper

    @property
    def name(self) -> str:
        return "Footprint Collector"

    async def execute(self, profile: PersonProfile) -> CollectorResult:
        collector_result = CollectorResult()

        direct_urls = self._extract_direct_urls(profile)
        if direct_urls:
            logger.info("Found %d direct URLs in resume: %s", len(direct_urls), direct_urls)

        queries = await self._generate_queries(profile)
        collector_result.queries = queries
        logger.info("AI generated %d search queries for '%s'", len(queries), profile.full_name)
        for i, q in enumerate(queries, 1):
            logger.info("  Query %d: %s", i, q)

        all_urls: list[str] = list(direct_urls)
        for q in queries:
            logger.info("Searching: %s", q)
            results = await self._search.search(q, max_results=5)
            logger.info("  -> %d results found", len(results))
            for r in results:
                logger.debug("  -> %s", r.url)
            collector_result.search_results.extend(results)
            all_urls.extend(r.url for r in results)

        unique_urls = list(dict.fromkeys(all_urls))[:_MAX_PAGES_TO_SCRAPE]
        logger.info("Scraping %d unique pages (from %d total URLs)", len(unique_urls), len(all_urls))

        pages = await asyncio.gather(
            *(self._scraper.scrape(url) for url in unique_urls),
            return_exceptions=True,
        )

        success_count = 0
        fail_count = 0
        for page in pages:
            if isinstance(page, Exception):
                fail_count += 1
                continue
            if not isinstance(page, ScrapedPage) or not page.success:
                fail_count += 1
                continue
            success_count += 1
            logger.info("Analysing page: %s (%d chars)", page.url, len(page.text))
            fp = await self._analyse_page(page, profile)
            if fp:
                logger.info("  -> Footprint found (relevance=%.0f%%)", fp.relevance_score * 100)
                collector_result.footprints.append(fp)
            else:
                logger.info("  -> No relevant footprint")

        logger.info(
            "Footprint collection done: %d scraped, %d failed, %d footprints found",
            success_count, fail_count, len(collector_result.footprints),
        )
        return collector_result

    async def _generate_queries(self, profile: PersonProfile) -> list[str]:
        """Use AI (low tier) to produce smart, diverse search queries."""
        config = AIServiceConfig.from_tier(
            ModelTier.LOW,
            system_prompt=_QUERY_GEN_SYSTEM,
            response_format="json",
        )

        profile_dump = profile.model_dump(exclude_none=True, exclude_defaults=True)
        prompt = (
            "Generate search queries to find this person's digital footprint.\n"
            "Here is the full structured resume profile as JSON:\n\n"
            f"```json\n{json.dumps(profile_dump, indent=2)}\n```\n"
        )

        logger.info("Asking AI to generate search queries...")
        try:
            data = await self._ai.complete_structured(prompt, config, _QUERY_GEN_SCHEMA)
            queries = data.get("queries", [])
            if queries:
                return queries
        except Exception:
            logger.exception("AI query generation failed, falling back to basic queries")

        return self._fallback_queries(profile)

    @staticmethod
    def _extract_direct_urls(profile: PersonProfile) -> list[str]:
        """Pull URLs directly mentioned in the resume."""
        urls: list[str] = []

        for link in profile.links:
            cleaned = link.strip().rstrip("/")
            if not cleaned.startswith("http"):
                cleaned = "https://" + cleaned
            urls.append(cleaned)

        return urls

    async def _analyse_page(
        self, page: ScrapedPage, profile: PersonProfile
    ) -> DigitalFootprint | None:
        truncated_text = page.text[:3000]
        if not truncated_text.strip():
            return None

        config = AIServiceConfig.from_tier(
            ModelTier.MEDIUM,
            system_prompt=_SUMMARISE_SYSTEM,
            response_format="json",
        )
        prompt = (
            f"Person: {profile.full_name}, Title: {profile.title}\n"
            f"Skills: {', '.join(profile.skills[:10])}\n\n"
            f"Web page URL: {page.url}\n"
            f"Web page title: {page.title}\n"
            f"Web page content:\n{truncated_text}"
        )

        try:
            data = await self._ai.complete_structured(prompt, config, _SUMMARISE_SCHEMA)
            return DigitalFootprint(source_url=page.url, **data)
        except Exception:
            logger.exception("Failed to analyse page %s", page.url)
            return None
    @staticmethod
    def _fallback_queries(profile: PersonProfile) -> list[str]:
        """Basic hardcoded queries used when AI generation fails."""
        name = profile.full_name
        queries = [f'"{name}"']

        if profile.title:
            queries.append(f'"{name}" {profile.title}')

        if profile.email:
            queries.append(f'"{profile.email}"')

        if profile.experience:
            latest = profile.experience[0]
            if latest.company:
                queries.append(f'"{name}" {latest.company}')

        if profile.education:
            latest_edu = profile.education[0]
            if latest_edu.institution:
                queries.append(f'"{name}" {latest_edu.institution}')

        queries.append(f'"{name}" LinkedIn OR GitHub OR portfolio')

        return queries

