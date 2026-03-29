"""Composition root -- the only file that knows about concrete classes.

Swap any provider here (e.g. GeminiProvider -> OpenAIProvider) without
touching the rest of the codebase.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.agents.classifier import ClassifierAgent
from app.agents.footprint_collector import FootprintCollectorAgent
from app.agents.resume_resolver import ResumeResolverAgent
from app.agents.trust_evaluator import TrustEvaluatorAgent
from app.config import settings
from app.providers.ai.gemini_provider import GeminiProvider
from app.providers.parsers.docx_parser import DocxParser
from app.providers.parsers.pdf_parser import PdfParser
from app.providers.scraper.bs4_scraper import BS4Scraper
from app.core.interfaces.search_engine import SearchEngine
from app.providers.search.duckduckgo_engine import DuckDuckGoEngine
from app.providers.search.serpapi_engine import SerpApiEngine
from app.services.ai_service import AIService
from app.services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_ai_service() -> AIService:
    logger.info("Creating AIService with GeminiProvider")
    provider = GeminiProvider(api_key=settings.gemini_api_key)
    return AIService(provider)


def _build_search_engine() -> SearchEngine:
    engine_name = settings.search_engine.lower()
    if engine_name == "serpapi":
        if not settings.serpapi_api_key:
            raise ValueError("SERPAPI_API_KEY is required when search_engine=serpapi")
        logger.info("Using SerpAPI search engine")
        return SerpApiEngine(api_key=settings.serpapi_api_key)
    logger.info("Using DuckDuckGo search engine")
    return DuckDuckGoEngine()


def get_pipeline() -> PipelineService:
    logger.info("Assembling pipeline...")
    ai = get_ai_service()
    search = _build_search_engine()
    scraper = BS4Scraper()

    resolver = ResumeResolverAgent(parsers=[PdfParser(), DocxParser()])
    classifier = ClassifierAgent(ai_service=ai)
    collector = FootprintCollectorAgent(
        ai_service=ai,
        search_engine=search,
        web_scraper=scraper,
    )
    evaluator = TrustEvaluatorAgent(ai_service=ai)

    logger.info(
        "Pipeline ready: %s -> %s -> %s -> %s",
        resolver.name, classifier.name, collector.name, evaluator.name,
    )
    return PipelineService(
        resolver=resolver,
        classifier=classifier,
        collector=collector,
        evaluator=evaluator,
    )
