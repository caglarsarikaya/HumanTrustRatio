from __future__ import annotations

import logging

from app.agents.base_agent import BaseAgent
from app.core.interfaces.resume_parser import ResumeParser

logger = logging.getLogger(__name__)


class ResumeResolverAgent(BaseAgent):
    """Agent 1 -- convert an uploaded file into plain text.

    Pure extraction, no AI involved.  Delegates to whichever
    ``ResumeParser`` implementation matches the file's MIME type.
    """

    def __init__(self, parsers: list[ResumeParser]) -> None:
        self._parsers = parsers

    @property
    def name(self) -> str:
        return "Resume Resolver"

    async def execute(self, file_bytes: bytes, mime_type: str) -> str:
        logger.info("Received file: %d bytes, type=%s", len(file_bytes), mime_type)
        for parser in self._parsers:
            if parser.supports(mime_type):
                logger.info("Using parser: %s", type(parser).__name__)
                text = await parser.parse(file_bytes)
                if not text.strip():
                    raise ValueError("Parser returned empty text from the document.")
                logger.info("Extracted %d characters of text", len(text))
                logger.debug("First 200 chars: %s", text[:200].replace("\n", " "))
                return text

        supported = ", ".join(
            type(p).__name__ for p in self._parsers
        )
        raise ValueError(
            f"Unsupported file type: {mime_type}. "
            f"Available parsers: {supported}"
        )
