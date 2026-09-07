"""Base abstract class and common utilities for multi-format screenplay parsers."""

from abc import ABC, abstractmethod
import os
import re
from typing import Optional, Union

from backend.parsers.parser_types import ParsedDocument


class BaseScreenplayParser(ABC):
    """Abstract base class for all screenplay and cutlist parsers."""

    @abstractmethod
    def parse(
        self,
        content: Union[str, bytes],
        filename: Optional[str] = None,
    ) -> ParsedDocument:
        """Parse screenplay content into a structured ParsedDocument.

        Args:
            content: Raw text string or raw bytes of the file.
            filename: Optional original filename to assist format detection or title inference.

        Returns:
            ParsedDocument containing scenes, elements, and metadata.
        """
        raise NotImplementedError

    @staticmethod
    def _ensure_text(content: Union[str, bytes], encoding: str = "utf-8") -> str:
        """Decode bytes to str if needed using defensive fallbacks."""
        if isinstance(content, str):
            return content
        if isinstance(content, (bytes, bytearray)):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                # Fallback to latin-1 to avoid losing bytes
                return content.decode("latin-1", errors="replace")
        raise TypeError(f"Expected str or bytes, got {type(content).__name__}")

    @staticmethod
    def _ensure_bytes(content: Union[str, bytes], encoding: str = "utf-8") -> bytes:
        """Encode str to bytes if needed."""
        if isinstance(content, (bytes, bytearray)):
            return bytes(content)
        if isinstance(content, str):
            return content.encode(encoding, errors="replace")
        raise TypeError(f"Expected str or bytes, got {type(content).__name__}")

    @staticmethod
    def _count_tokens(text: str) -> int:
        """Estimate token count for a block of text using whitespace split."""
        if not text or not text.strip():
            return 0
        return len(re.findall(r"\b\w+\b", text))

    @staticmethod
    def _extract_title_from_filename(filename: Optional[str]) -> str:
        """Derive a clean human-readable title from the given filename."""
        if not filename:
            return "Untitled"
        base = os.path.splitext(os.path.basename(filename))[0]
        cleaned = re.sub(r"[_\-]+", " ", base).strip()
        return cleaned.title() if cleaned else "Untitled"
