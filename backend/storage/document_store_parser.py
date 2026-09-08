"""
backend/storage/document_store_parser.py

Multi-format screenplay parser integration and financial calculation utilities
for the document store and deduplication engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Tuple

from backend.storage.document_store_types import VALID_DOCUMENT_FORMATS

logger = logging.getLogger("lienmark.storage.document_store.parser")


def calculate_api_spend_saved(page_count: int, claims_count: int) -> float:
    """
    Computes financial USD savings from avoided re-parsing and re-extraction.
    
    Formula: (page_count * 0.015) + (claims_count * 0.04)
    """
    pages = max(0, page_count)
    claims = max(0, claims_count)
    return round((pages * 0.015) + (claims * 0.04), 4)


def parse_document_with_factory(
    file_path_or_name: str, content_bytes: bytes
) -> Tuple[str, int, int, Dict[str, Any]]:
    """Invokes ParserFactory to detect screenplay/timeline format and extract metrics."""
    try:
        from backend.parsers.factory import ParserFactory

        parser = ParserFactory.get_parser_for_file(
            file_path_or_name, header_bytes=content_bytes[:2048]
        )
        parsed = parser.parse(content_bytes, filename=file_path_or_name)
        fmt_val = (
            parsed.format.value
            if hasattr(parsed.format, "value")
            else str(parsed.format).lower()
        )
        if fmt_val not in VALID_DOCUMENT_FORMATS:
            fmt_val = "plaintext"

        meta = dict(parsed.metadata) if parsed.metadata else {}
        if getattr(parsed, "raw_text", None):
            meta["raw_text"] = parsed.raw_text

        return (
            fmt_val,
            max(1, parsed.page_count),
            max(0, parsed.scene_count),
            meta,
        )
    except Exception as exc:
        logger.warning(
            "ParserFactory extraction failed for '%s': %s. Falling back to format detection.",
            file_path_or_name,
            exc,
        )
        ext = os.path.splitext(file_path_or_name)[1].lower().lstrip(".")
        fmt_val = ext if ext in VALID_DOCUMENT_FORMATS else "plaintext"
        return fmt_val, 1, 0, {"fallback_parser": True, "error": str(exc)}
