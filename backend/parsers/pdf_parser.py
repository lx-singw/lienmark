"""PDF screenplay parser supporting native zlib decompression and optional pypdf."""

import io
import re
from typing import List, Optional, Tuple, Union

from backend.parsers.base import BaseScreenplayParser
from backend.parsers.parser_types import (
    DocumentFormat,
    ElementType,
    ParsedDocument,
    ParsedElement,
    ParsedScene,
    ParserCorruptFileError,
)
from backend.parsers.pdf_stream_reader import PdfStreamReader

HEADING_REGEX = re.compile(
    r"^(?:\d+\s+)?(?:INT|EXT|INT/EXT|EXT/INT|I/E)(?:[\.\s]).*",
    re.IGNORECASE,
)
TRANSITION_REGEX = re.compile(
    r"^(?:CUT TO:|FADE OUT\.|FADE IN:|DISSOLVE TO:|SMASH CUT:|MATCH CUT:|BACK TO:).*$|.*TO:$",
    re.IGNORECASE,
)


class PdfScreenplayParser(BaseScreenplayParser):
    """Parses PDF screenplays into structured scene elements."""

    def parse(
        self,
        content: Union[str, bytes],
        filename: Optional[str] = None,
    ) -> ParsedDocument:
        """Parse PDF document content into a structured ParsedDocument."""
        raw_bytes = self._ensure_bytes(content)
        title = self._extract_title_from_filename(filename)

        raw_text, page_count = self._extract_text_and_pages(raw_bytes)
        elements = self._parse_elements(raw_text)
        scenes = self._assemble_scenes(elements)

        return ParsedDocument(
            format=DocumentFormat.PDF,
            title=title,
            scenes=scenes,
            elements=elements,
            page_count=page_count,
            scene_count=len(scenes),
            raw_text=raw_text,
            metadata={"source_filename": filename or "", "engine": "pdf_parser"},
        )

    def _extract_text_and_pages(self, raw_bytes: bytes) -> Tuple[str, int]:
        """Extract text content and page count, using pypdf if available or native reader."""
        try:
            import pypdf  # type: ignore

            stream = io.BytesIO(raw_bytes)
            reader = pypdf.PdfReader(stream)
            page_texts = [p.extract_text() or "" for p in reader.pages]
            full_text = "\n\n".join(page_texts)
            return full_text, len(reader.pages)
        except (ImportError, Exception):
            pass

        # Fallback to native zlib-based stream reader
        reader_native = PdfStreamReader(raw_bytes)
        text = reader_native.extract_text_streams()
        page_count = reader_native.count_pages()
        return text, page_count

    def _parse_elements(self, raw_text: str) -> List[ParsedElement]:
        """Parse raw text lines into typed screenplay elements."""
        elements: List[ParsedElement] = []
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        current_scene_num = 0

        for line in lines:
            elem_type = self._classify_line(line, elements[-1] if elements else None)
            if elem_type == ElementType.SCENE_HEADING:
                current_scene_num += 1

            elements.append(
                ParsedElement(
                    element_type=elem_type,
                    text=line,
                    scene_number=current_scene_num if current_scene_num > 0 else None,
                    metadata={"char_length": len(line)},
                )
            )

        return elements

    def _classify_line(self, line: str, prev: Optional[ParsedElement]) -> ElementType:
        """Classify a line into its semantic screenplay element type."""
        if self._is_scene_heading(line):
            return ElementType.SCENE_HEADING
        if self._is_transition(line):
            return ElementType.TRANSITION
        if line.startswith("(") and line.endswith(")"):
            return ElementType.PARENTHETICAL
        if self._is_character_cue(line):
            return ElementType.CHARACTER
        if prev and prev.element_type in (ElementType.CHARACTER, ElementType.PARENTHETICAL):
            return ElementType.DIALOGUE
        return ElementType.ACTION

    def _is_scene_heading(self, line: str) -> bool:
        """Check if line matches scene heading conventions."""
        return bool(HEADING_REGEX.match(line.strip()))

    def _is_transition(self, line: str) -> bool:
        """Check if line matches transition cues."""
        stripped = line.strip().upper()
        return bool(TRANSITION_REGEX.match(stripped))

    def _is_character_cue(self, line: str) -> bool:
        """Detect character cues formatted in uppercase."""
        stripped = line.strip()
        if len(stripped) > 40 or len(stripped) < 2:
            return False
        # Strip common extensions like (V.O.) or (O.S.)
        cleaned = re.sub(r"\s*\(.*?\)\s*", "", stripped)
        if not cleaned:
            return False
        return cleaned.isupper() and bool(re.match(r"^[A-Z0-9\s\.\-']+$", cleaned))

    def _assemble_scenes(self, elements: List[ParsedElement]) -> List[ParsedScene]:
        """Aggregate sequential elements into scenes delimited by scene headings."""
        scenes: List[ParsedScene] = []
        current_elements: List[ParsedElement] = []
        current_heading = "PROLOGUE"
        scene_num = 0

        for elem in elements:
            if elem.element_type == ElementType.SCENE_HEADING:
                if current_elements or scene_num > 0:
                    text_blob = " ".join(e.text for e in current_elements)
                    scenes.append(
                        ParsedScene(
                            scene_number=scene_num,
                            heading=current_heading,
                            elements=current_elements,
                            token_count=self._count_tokens(text_blob),
                        )
                    )
                scene_num += 1
                current_heading = elem.text
                current_elements = [elem]
            else:
                current_elements.append(elem)

        if current_elements:
            text_blob = " ".join(e.text for e in current_elements)
            scenes.append(
                ParsedScene(
                    scene_number=scene_num or 1,
                    heading=current_heading,
                    elements=current_elements,
                    token_count=self._count_tokens(text_blob),
                )
            )

        return scenes
