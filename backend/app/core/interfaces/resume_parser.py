from abc import ABC, abstractmethod


class ResumeParser(ABC):
    """Abstract base for document-to-text parsers (PDF, DOCX, etc.)."""

    @abstractmethod
    async def parse(self, file_bytes: bytes) -> str:
        """Extract plain text from a document's raw bytes."""
        ...

    @abstractmethod
    def supports(self, mime_type: str) -> bool:
        """Return True if this parser can handle the given MIME type."""
        ...
