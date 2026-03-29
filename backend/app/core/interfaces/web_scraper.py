from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.models.footprint import ScrapedPage


class WebScraper(ABC):
    """Abstract base for web page scrapers (BS4, Playwright, etc.)."""

    @abstractmethod
    async def scrape(self, url: str) -> ScrapedPage:
        """Fetch a URL and return its extracted text content."""
        ...
