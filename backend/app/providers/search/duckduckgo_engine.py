from __future__ import annotations

import asyncio
import logging

from ddgs import DDGS

from app.core.interfaces.search_engine import SearchEngine
from app.core.models.footprint import SearchResult

logger = logging.getLogger(__name__)


class DuckDuckGoEngine(SearchEngine):
    """Free web search via DuckDuckGo (ddgs package)."""

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        logger.info("DuckDuckGo search: %r (max=%d)", query, max_results)
        loop = asyncio.get_running_loop()
        raw = await loop.run_in_executor(None, self._sync_search, query, max_results)
        logger.info("DuckDuckGo returned %d results", len(raw))
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("href", ""),
                snippet=r.get("body", ""),
            )
            for r in raw
        ]

    @staticmethod
    def _sync_search(query: str, max_results: int) -> list[dict]:
        try:
            ddgs = DDGS()
            return ddgs.text(query, max_results=max_results, backend="google")
        except Exception:
            logger.exception("DuckDuckGo search failed for query: %s", query)
            return []
