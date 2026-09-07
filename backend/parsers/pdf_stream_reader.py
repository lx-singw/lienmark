"""Native PDF binary stream reader and content stream text extractor using zlib."""

import re
from typing import List, Tuple
import zlib

from backend.parsers.parser_types import ParserCorruptFileError


class PdfStreamReader:
    """Extracts raw text and page counts from PDF binaries without external dependencies."""

    def __init__(self, raw_bytes: bytes) -> None:
        self.raw_bytes = raw_bytes
        self._validate_pdf_header()

    def _validate_pdf_header(self) -> None:
        """Ensure the input data contains a valid PDF header magic byte signature."""
        if not self.raw_bytes or len(self.raw_bytes) < 8:
            raise ParserCorruptFileError("PDF file is empty or truncated")
        if b"%PDF-" not in self.raw_bytes[:1024]:
            raise ParserCorruptFileError("Missing valid %PDF- magic header signature")

    def count_pages(self) -> int:
        """Estimate the number of pages by scanning for Page object dictionaries."""
        page_matches = re.findall(rb"/Type\s*/Page\b", self.raw_bytes)
        count = len(page_matches)
        # Avoid counting /Pages catalog as a page
        pages_catalog = len(re.findall(rb"/Type\s*/Pages\b", self.raw_bytes))
        estimated = count - pages_catalog
        return max(1, estimated if estimated > 0 else count or 1)

    def extract_text_streams(self) -> str:
        """Decompress and decode all text streams in the PDF file."""
        stream_pattern = re.compile(rb"stream[\r\n]+(.*?)[\r\n]+endstream", re.DOTALL)
        extracted_chunks: List[str] = []

        for match in stream_pattern.finditer(self.raw_bytes):
            stream_data = match.group(1)
            decompressed = self._try_decompress(stream_data)
            if decompressed:
                text_chunk = self._extract_operators_text(decompressed)
                if text_chunk.strip():
                    extracted_chunks.append(text_chunk)

        if not extracted_chunks:
            # Fallback: scan for any readable ASCII strings in binary
            ascii_chunk = self._extract_printable_ascii(self.raw_bytes)
            if ascii_chunk.strip():
                extracted_chunks.append(ascii_chunk)

        return "\n\n".join(extracted_chunks)

    def _try_decompress(self, stream_data: bytes) -> bytes:
        """Attempt zlib decompression with various window buffer configurations."""
        # Try standard zlib
        try:
            return zlib.decompress(stream_data)
        except Exception:
            pass

        # Try raw deflate (wbits = -15)
        try:
            return zlib.decompress(stream_data, -15)
        except Exception:
            pass

        # Try gzip header (wbits = 31)
        try:
            return zlib.decompress(stream_data, 31)
        except Exception:
            pass

        return stream_data

    def _extract_operators_text(self, stream_bytes: bytes) -> str:
        """Extract text from PDF text operators (Tj, TJ, ', \") in a content stream."""
        # Decode stream bytes defensively
        content = stream_bytes.decode("latin-1", errors="replace")
        lines: List[str] = []

        # Find TJ array blocks: [(str) 20 (str)] TJ
        tj_array_pattern = re.compile(r"\[(.*?)\]\s*TJ", re.DOTALL)
        for match in tj_array_pattern.finditer(content):
            inner = match.group(1)
            pieces = re.findall(r"\((.*?)(?<!\\)\)", inner)
            decoded = "".join(self._unescape_pdf_string(p) for p in pieces)
            if decoded.strip():
                lines.append(decoded.strip())

        # Find individual Tj blocks: (str) Tj
        tj_single_pattern = re.compile(r"\((.*?)(?<!\\)\)\s*(?:Tj|'|\")", re.DOTALL)
        for match in tj_single_pattern.finditer(content):
            decoded = self._unescape_pdf_string(match.group(1))
            if decoded.strip():
                lines.append(decoded.strip())

        return "\n".join(lines)

    def _unescape_pdf_string(self, s: str) -> str:
        """Unescape standard PDF string escape sequences."""
        s = s.replace(r"\(", "(").replace(r"\)", ")")
        s = s.replace(r"\n", "\n").replace(r"\r", "\r").replace(r"\t", "\t")
        s = s.replace(r"\\", "\\")
        # Octal escapes \ddd
        s = re.sub(
            r"\\([0-7]{1,3})",
            lambda m: chr(int(m.group(1), 8)),
            s,
        )
        return s

    def _extract_printable_ascii(self, data: bytes) -> str:
        """Fallback scanner for legible strings in non-standard PDF formats."""
        strings = re.findall(rb"[\x20-\x7E]{4,}", data)
        valid_lines = [
            s.decode("latin-1")
            for s in strings
            if not s.startswith(b"/") and not s.startswith(b"end")
        ]
        return "\n".join(valid_lines)
