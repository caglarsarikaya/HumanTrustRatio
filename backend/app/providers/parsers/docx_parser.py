from __future__ import annotations

import io
import logging

import docx

from app.core.interfaces.resume_parser import ResumeParser

logger = logging.getLogger(__name__)

_SUPPORTED_MIMES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class DocxParser(ResumeParser):
    """Extract text from DOCX files using python-docx."""

    async def parse(self, file_bytes: bytes) -> str:
        logger.debug("Opening DOCX (%d bytes)", len(file_bytes))
        document = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        total = sum(len(p) for p in paragraphs)
        logger.info("DOCX parsed: %d paragraphs, %d total chars", len(paragraphs), total)
        return "\n\n".join(paragraphs)

    def supports(self, mime_type: str) -> bool:
        return mime_type in _SUPPORTED_MIMES
