from __future__ import annotations

import asyncio
import logging

from serpapi import GoogleSearch

from app.core.interfaces.search_engine import SearchEngine
from app.core.models.footprint import SearchResult

logger = logging.getLogger(__name__)


class SerpApiEngine(SearchEngine):
    """Web search via SerpAPI (Google results)."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        logger.info("SerpAPI search: %r (max=%d)", query, max_results)
        loop = asyncio.get_running_loop()
        raw = await loop.run_in_executor(None, self._sync_search, query, max_results)
        logger.info("SerpAPI returned %d results", len(raw))
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("link", ""),
                snippet=r.get("snippet", ""),
            )
            for r in raw
        ]

    def _sync_search(self, query: str, max_results: int) -> list[dict]:
        try:
            params = {
                "q": query,
                "num": max_results,
                "api_key": self._api_key,
                "engine": "google",
            }
            search = GoogleSearch(params)
            results = search.get_dict()
            return results.get("organic_results", [])[:max_results]
        except Exception:
            logger.exception("SerpAPI search failed for query: %s", query)
            return []
