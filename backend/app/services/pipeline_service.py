from __future__ import annotations

import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from app.agents.classifier import ClassifierAgent
from app.agents.footprint_collector import FootprintCollectorAgent
from app.agents.resume_resolver import ResumeResolverAgent
from app.agents.trust_evaluator import TrustEvaluatorAgent
from app.core.models.footprint import DigitalFootprint, SearchResult
from app.core.models.resume import PersonProfile
from app.core.models.trust import TrustIndex

logger = logging.getLogger(__name__)

ProgressCallback = Callable[
    [int, int, str, str], Coroutine[Any, Any, None]
]

PIPELINE_STEPS = [
    "Parsing resume",
    "Classifying profile",
    "Searching the web",
    "Evaluating trust index",
]


@dataclass
class PipelineResult:
    """Full result bundle returned after the pipeline completes."""

    resume_text: str = ""
    profile: PersonProfile | None = None
    search_queries: list[str] = field(default_factory=list)
    search_results: list[SearchResult] = field(default_factory=list)
    footprints: list[DigitalFootprint] = field(default_factory=list)
    trust_index: TrustIndex | None = None


class PipelineService:
    """Orchestrates the four-agent chain from upload to Trust Index."""

    def __init__(
        self,
        resolver: ResumeResolverAgent,
        classifier: ClassifierAgent,
        collector: FootprintCollectorAgent,
        evaluator: TrustEvaluatorAgent,
    ) -> None:
        self._resolver = resolver
        self._classifier = classifier
        self._collector = collector
        self._evaluator = evaluator

    async def run(
        self,
        file_bytes: bytes,
        mime_type: str,
        on_progress: ProgressCallback | None = None,
    ) -> PipelineResult:
        result = PipelineResult()
        total = len(PIPELINE_STEPS)
        pipeline_start = time.perf_counter()

        async def _emit(step: int, status: str) -> None:
            if on_progress:
                await on_progress(step, total, PIPELINE_STEPS[step - 1], status)

        logger.info("=" * 60)
        logger.info("PIPELINE START  (%d steps)", total)
        logger.info("=" * 60)

        # Step 1
        await _emit(1, "running")
        logger.info("[Step 1/%d] %s ...", total, PIPELINE_STEPS[0])
        t0 = time.perf_counter()
        result.resume_text = await self._resolver.execute(file_bytes, mime_type)
        logger.info("[Step 1/%d] %s DONE (%.2fs)", total, PIPELINE_STEPS[0], time.perf_counter() - t0)
        await _emit(1, "done")

        # Step 2
        await _emit(2, "running")
        logger.info("[Step 2/%d] %s ...", total, PIPELINE_STEPS[1])
        t0 = time.perf_counter()
        result.profile = await self._classifier.execute(result.resume_text)
        logger.info("[Step 2/%d] %s DONE (%.2fs)", total, PIPELINE_STEPS[1], time.perf_counter() - t0)
        await _emit(2, "done")

        # Step 3
        await _emit(3, "running")
        logger.info("[Step 3/%d] %s ...", total, PIPELINE_STEPS[2])
        t0 = time.perf_counter()
        collector_out = await self._collector.execute(result.profile)
        result.search_queries = collector_out.queries
        result.search_results = collector_out.search_results
        result.footprints = collector_out.footprints
        logger.info("[Step 3/%d] %s DONE (%.2fs)", total, PIPELINE_STEPS[2], time.perf_counter() - t0)
        await _emit(3, "done")

        # Step 4
        await _emit(4, "running")
        logger.info("[Step 4/%d] %s ...", total, PIPELINE_STEPS[3])
        t0 = time.perf_counter()
        result.trust_index = await self._evaluator.execute(
            result.profile, result.footprints
        )
        logger.info("[Step 4/%d] %s DONE (%.2fs)", total, PIPELINE_STEPS[3], time.perf_counter() - t0)
        await _emit(4, "done")

        total_elapsed = time.perf_counter() - pipeline_start
        logger.info("=" * 60)
        logger.info(
            "PIPELINE COMPLETE  trust_score=%.0f  total_time=%.2fs",
            result.trust_index.overall_score, total_elapsed,
        )
        logger.info("=" * 60)
        return result
