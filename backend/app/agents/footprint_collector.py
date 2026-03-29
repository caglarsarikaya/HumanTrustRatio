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
    "You are a resume analyst. Given a person's resume profile, generate TARGETED "
    "search queries to find evidence of that person's online footprint.\n\n"
    "RULES:\n"
    "- Every query MUST include the person's full name in quotes.\n"
    "- Each query should also include at least one specific identifier: "
    "a company name, university name, city, email, or a URL from their resume.\n"
    "- Do NOT generate broad queries with just a name and generic terms.\n"
    "- Prefer narrow queries that will only match the specific person.\n\n"
    "Good queries:\n"
    '- \'"John Smith" "Acme Corp"\'\n'
    '- \'"John Smith" "MIT" Boston\'\n'
    '- \'"john.smith@email.com"\'\n'
    '- \'site:github.com "johnsmith"\'\n\n'
    "Bad queries (too broad, will match wrong people):\n"
    '- \'"John Smith" software engineer\'\n'
    '- \'"John Smith" developer portfolio\'\n'
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
    "contradicts the person's resume claims. Be concise.\n\n"
    "IDENTITY MATCHING RULES (critical):\n"
    "- You will receive the person's full profile: name, email, location, "
    "all companies, education, and skills.\n"
    "- If the page mentions someone with the same name but DIFFERENT companies, "
    "DIFFERENT job titles, DIFFERENT education, or DIFFERENT industry, this is "
    "a DIFFERENT PERSON. Set relevance_score to 0.\n"
    "- Only consider a page relevant (relevance_score > 0) if at least ONE "
    "identifying detail matches beyond just the name — e.g. same company, "
    "same university, same email, same city, same GitHub username.\n"
    "- A common name can belong to many people. Name match alone is NOT enough."
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

        snippet_map: dict[str, SearchResult] = {}
        for sr in collector_result.search_results:
            if sr.url not in snippet_map:
                snippet_map[sr.url] = sr

        unique_urls = list(dict.fromkeys(all_urls))[:_MAX_PAGES_TO_SCRAPE]
        logger.info("Scraping %d unique pages (from %d total URLs)", len(unique_urls), len(all_urls))

        pages = await asyncio.gather(
            *(self._scraper.scrape(url) for url in unique_urls),
            return_exceptions=True,
        )

        success_count = 0
        fail_count = 0
        snippet_fallback_count = 0
        for i, page in enumerate(pages):
            url = unique_urls[i]
            scraped_ok = (
                isinstance(page, ScrapedPage)
                and page.success
                and len(page.text.strip()) > 20
            )

            if scraped_ok:
                success_count += 1
                logger.info("Analysing page: %s (%d chars)", page.url, len(page.text))
                fp = await self._analyse_page(page, profile)
            elif url in snippet_map:
                sr = snippet_map[url]
                if sr.snippet.strip():
                    snippet_fallback_count += 1
                    fallback_text = f"Title: {sr.title}\nSnippet: {sr.snippet}"
                    logger.info(
                        "Scrape failed for %s — using search snippet as fallback (%d chars)",
                        url, len(fallback_text),
                    )
                    fallback_page = ScrapedPage(
                        url=url, title=sr.title, text=fallback_text,
                    )
                    fp = await self._analyse_page(fallback_page, profile)
                else:
                    fail_count += 1
                    continue
            else:
                fail_count += 1
                continue

            if fp and fp.relevance_score > 0.1:
                logger.info("  -> Footprint found (relevance=%.0f%%)", fp.relevance_score * 100)
                collector_result.footprints.append(fp)
            elif fp:
                logger.info("  -> Skipped low-relevance footprint (%.0f%%) — likely different person", fp.relevance_score * 100)
            else:
                logger.info("  -> No relevant footprint")

        logger.info(
            "Footprint collection done: %d scraped, %d snippet-fallbacks, %d failed, %d footprints found",
            success_count, snippet_fallback_count, fail_count, len(collector_result.footprints),
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
        experience_lines = "\n".join(
            f"  - {e.title} at {e.company} ({e.duration})"
            for e in profile.experience
        )
        education_lines = "\n".join(
            f"  - {ed.degree} in {ed.field} from {ed.institution} ({ed.year})"
            for ed in profile.education
        )
        companies = [e.company for e in profile.experience if e.company]
        prompt = (
            f"## Person's Resume Profile\n"
            f"Name: {profile.full_name}\n"
            f"Email: {profile.email}\n"
            f"Title: {profile.title}\n"
            f"Location: {profile.location}\n"
            f"Companies worked at: {', '.join(companies)}\n"
            f"Experience:\n{experience_lines}\n"
            f"Education:\n{education_lines}\n"
            f"Skills: {', '.join(profile.skills[:10])}\n"
            f"Links: {', '.join(profile.links)}\n\n"
            f"## Web Page to Analyse\n"
            f"URL: {page.url}\n"
            f"Title: {page.title}\n"
            f"Content:\n{truncated_text}"
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

        for exp in profile.experience:
            if exp.company:
                queries.append(f'"{name}" "{exp.company}"')

        for edu in profile.education:
            if edu.institution:
                queries.append(f'"{name}" "{edu.institution}"')
            if edu.institution and profile.location:
                queries.append(f'"{name}" "{edu.institution}" {profile.location}')

        queries.append(f'"{name}" LinkedIn OR GitHub OR portfolio')

        return queries

