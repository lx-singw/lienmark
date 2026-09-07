"""Factory for resolving and instantiating appropriate screenplay and timeline parsers."""

import os
import re
from typing import Optional

from backend.parsers.base import BaseScreenplayParser
from backend.parsers.edl_parser import EdlTimelineParser
from backend.parsers.fdx_parser import FdxScreenplayParser
from backend.parsers.fountain_parser import FountainScreenplayParser
from backend.parsers.parser_types import DocumentFormat, ParserUnsupportedFormatError
from backend.parsers.pdf_parser import PdfScreenplayParser

EXTENSION_MAP = {
    ".pdf": DocumentFormat.PDF,
    ".fdx": DocumentFormat.FDX,
    ".fountain": DocumentFormat.FOUNTAIN,
    ".spmd": DocumentFormat.FOUNTAIN,
    ".edl": DocumentFormat.EDL,
}


class ParserFactory:
    """Factory resolving appropriate BaseScreenplayParser by extension or magic bytes."""

    @classmethod
    def get_parser_for_file(
        cls,
        filename_or_path: str,
        header_bytes: Optional[bytes] = None,
    ) -> BaseScreenplayParser:
        """Resolve and instantiate the proper parser for a given file or header."""
        doc_format = cls.detect_format(filename_or_path, header_bytes)
        return cls._create_parser(doc_format)

    @classmethod
    def detect_format(
        cls,
        filename_or_path: str,
        header_bytes: Optional[bytes] = None,
    ) -> DocumentFormat:
        """Detect document format from header magic bytes, physical file inspection, or extension."""
        header = header_bytes or cls._read_file_header(filename_or_path)

        if header:
            sniffed = cls._sniff_magic_bytes(header)
            if sniffed and sniffed != DocumentFormat.UNKNOWN:
                return sniffed

        _, ext = os.path.splitext(filename_or_path.lower())
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]

        if ext == ".txt" and header:
            # Check if plaintext is actually Fountain or EDL
            text_preview = header.decode("latin-1", errors="replace")
            if re.search(r"\b(?:INT|EXT|INT/EXT|EXT/INT|I/E)[\.\s]", text_preview, re.IGNORECASE):
                return DocumentFormat.FOUNTAIN
            if re.search(r"^\d{3,}\s+\S+\s+\S+", text_preview, re.MULTILINE):
                return DocumentFormat.EDL

        raise ParserUnsupportedFormatError(
            f"Unable to determine parser format for '{filename_or_path}'",
            details={"filename": filename_or_path, "header_snippet": (header[:32] if header else b"")},
        )

    @staticmethod
    def _read_file_header(filepath: str, length: int = 2048) -> Optional[bytes]:
        """Safely read header bytes from local file if it exists."""
        if os.path.isfile(filepath):
            try:
                with open(filepath, "rb") as f:
                    return f.read(length)
            except OSError:
                return None
        return None

    @classmethod
    def _sniff_magic_bytes(cls, header: bytes) -> Optional[DocumentFormat]:
        """Inspect initial byte stream for signature tokens and magic numbers."""
        if b"%PDF-" in header[:1024]:
            return DocumentFormat.PDF
        if b"<FinalDraft" in header or (b"<?xml" in header and b"FinalDraft" in header):
            return DocumentFormat.FDX
        if b"TITLE:" in header and (b"FCM:" in header or re.search(rb"\d{2}:\d{2}:\d{2}", header)):
            return DocumentFormat.EDL
        return None

    @classmethod
    def _create_parser(cls, doc_format: DocumentFormat) -> BaseScreenplayParser:
        """Instantiate parser instance corresponding to DocumentFormat."""
        if doc_format == DocumentFormat.PDF:
            return PdfScreenplayParser()
        if doc_format == DocumentFormat.FDX:
            return FdxScreenplayParser()
        if doc_format == DocumentFormat.FOUNTAIN:
            return FountainScreenplayParser()
        if doc_format == DocumentFormat.EDL:
            return EdlTimelineParser()
        raise ParserUnsupportedFormatError(f"No parser implementation available for format: {doc_format}")
