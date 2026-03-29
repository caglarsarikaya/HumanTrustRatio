from __future__ import annotations

import logging

import httpx
from bs4 import BeautifulSoup

from app.core.interfaces.web_scraper import WebScraper
from app.core.models.footprint import ScrapedPage

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0
_MAX_CONTENT_LENGTH = 500_000


class BS4Scraper(WebScraper):
    """Scrape web pages with httpx + BeautifulSoup."""

    async def scrape(self, url: str) -> ScrapedPage:
        logger.debug("Scraping: %s", url)
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=_TIMEOUT,
                headers={"User-Agent": "ProofOfHumanityBot/1.0"},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()

            html = resp.text[:_MAX_CONTENT_LENGTH]
            soup = BeautifulSoup(html, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            text = soup.get_text(separator="\n", strip=True)

            logger.debug("Scraped %s: title=%r text_len=%d", url, title[:60], len(text))
            return ScrapedPage(url=url, title=title, text=text)

        except Exception as exc:
            logger.warning("Failed to scrape %s: %s", url, exc)
            return ScrapedPage(url=url, success=False, error=str(exc))
