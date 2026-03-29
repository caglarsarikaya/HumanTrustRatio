from __future__ import annotations

import io
import logging

import pdfplumber

from app.core.interfaces.resume_parser import ResumeParser

logger = logging.getLogger(__name__)

_SUPPORTED_MIMES = {
    "application/pdf",
}


class PdfParser(ResumeParser):
    """Extract text from PDF files using pdfplumber."""

    async def parse(self, file_bytes: bytes) -> str:
        logger.debug("Opening PDF (%d bytes)", len(file_bytes))
        pages: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            logger.info("PDF has %d page(s)", len(pdf.pages))
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    pages.append(text)
                    logger.debug("  Page %d: %d chars", i, len(text))
                else:
                    logger.debug("  Page %d: empty", i)
        total = sum(len(p) for p in pages)
        logger.info("PDF parsed: %d pages with text, %d total chars", len(pages), total)
        return "\n\n".join(pages)

    def supports(self, mime_type: str) -> bool:
        return mime_type in _SUPPORTED_MIMES
