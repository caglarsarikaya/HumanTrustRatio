from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.models.footprint import SearchResult


class SearchEngine(ABC):
    """Abstract base for web search providers (DuckDuckGo, Google, etc.)."""

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Run a web search and return a list of results."""
        ...
