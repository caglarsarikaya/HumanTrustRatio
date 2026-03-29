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
from app.providers.search.duckduckgo_engine import DuckDuckGoEngine
from app.services.ai_service import AIService
from app.services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_ai_service() -> AIService:
    logger.info("Creating AIService with GeminiProvider")
    provider = GeminiProvider(api_key=settings.gemini_api_key)
    return AIService(provider)


def get_pipeline() -> PipelineService:
    logger.info("Assembling pipeline...")
    ai = get_ai_service()
    search = DuckDuckGoEngine()
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
