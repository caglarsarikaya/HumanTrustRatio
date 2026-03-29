from __future__ import annotations

from typing import Any

from pydantic import BaseModel, model_validator

from app.core.models.resume import _strip_nones


class _SafeBase(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _drop_nones(cls, values: Any) -> Any:
        return _strip_nones(values)


class SearchResult(_SafeBase):
    """A single result from a web search."""

    title: str
    url: str
    snippet: str = ""


class ScrapedPage(_SafeBase):
    """Text content extracted from a web page."""

    url: str
    title: str = ""
    text: str = ""
    success: bool = True
    error: str = ""


class DigitalFootprint(_SafeBase):
    """A piece of online evidence about a person."""

    source_url: str
    platform: str = ""
    summary: str = ""
    matched_claims: list[str] = []
    relevance_score: float = 0.0
