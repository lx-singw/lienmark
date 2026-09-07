"""Fountain 1.1 screenplay parser supporting title pages, forced cues, and scenes."""

import re
from typing import List, Optional, Union

from backend.parsers.base import BaseScreenplayParser
from backend.parsers.fountain_syntax import FountainSyntax
from backend.parsers.parser_types import (
    DocumentFormat,
    ElementType,
    ParsedDocument,
    ParsedElement,
    ParsedScene,
    ParserCorruptFileError,
)


class FountainScreenplayParser(BaseScreenplayParser):
    """Parses Fountain 1.1 formatted plaintext screenplays."""

    def parse(
        self,
        content: Union[str, bytes],
        filename: Optional[str] = None,
    ) -> ParsedDocument:
        """Parse Fountain script text into a structured ParsedDocument."""
        raw_text = self._ensure_text(content)
        if not raw_text.strip():
            raise ParserCorruptFileError("Fountain content is empty")

        meta, body = FountainSyntax.extract_metadata_and_body(raw_text)
        cleaned_body = FountainSyntax.strip_boneyard_and_notes(body)

        title = meta.get("title") or self._extract_title_from_filename(filename)
        elements = self._parse_elements(cleaned_body)
        scenes = self._assemble_scenes(elements)
        page_count = max(1, len(cleaned_body.splitlines()) // 54 + 1)

        return ParsedDocument(
            format=DocumentFormat.FOUNTAIN,
            title=title,
            scenes=scenes,
            elements=elements,
            page_count=page_count,
            scene_count=len(scenes),
            raw_text=raw_text,
            metadata={
                "fountain_meta": meta,
                "source_filename": filename or "",
                "engine": "fountain_parser",
            },
        )

    def _parse_elements(self, body: str) -> List[ParsedElement]:
        """Parse screenplay body lines into structured elements."""
        elements: List[ParsedElement] = []
        paragraphs = re.split(r"\n\s*\n", body.strip())
        scene_counter = 0

        for para in paragraphs:
            lines = [l.strip() for l in para.splitlines() if l.strip()]
            if not lines:
                continue
            scene_counter = self._parse_paragraph(lines, scene_counter, elements)

        return elements

    def _parse_paragraph(
        self,
        lines: List[str],
        scene_counter: int,
        elements: List[ParsedElement],
    ) -> int:
        """Classify and parse an individual paragraph block."""
        first = lines[0]
        if FountainSyntax.is_scene_heading(first):
            return self._append_heading_block(lines, scene_counter + 1, elements)

        if FountainSyntax.is_transition(first):
            clean_trans = first.lstrip(">").strip()
            elements.append(
                ParsedElement(
                    element_type=ElementType.TRANSITION,
                    text=clean_trans,
                    scene_number=scene_counter or None,
                )
            )
            return scene_counter

        if FountainSyntax.is_character_cue(first):
            self._parse_dialogue_block(lines, scene_counter, elements)
            return scene_counter

        elements.append(
            ParsedElement(
                element_type=ElementType.ACTION,
                text="\n".join(lines),
                scene_number=scene_counter or None,
            )
        )
        return scene_counter

    def _append_heading_block(
        self,
        lines: List[str],
        next_scene_num: int,
        elements: List[ParsedElement],
    ) -> int:
        """Parse scene heading and optional following action lines."""
        clean_heading, custom_num = FountainSyntax.extract_scene_heading(lines[0])
        scene_num = custom_num or next_scene_num
        elements.append(
            ParsedElement(
                element_type=ElementType.SCENE_HEADING,
                text=clean_heading,
                scene_number=scene_num,
            )
        )
        for line in lines[1:]:
            elements.append(
                ParsedElement(
                    element_type=ElementType.ACTION,
                    text=line,
                    scene_number=scene_num,
                )
            )
        return scene_num

    def _parse_dialogue_block(
        self,
        lines: List[str],
        scene_counter: int,
        elements: List[ParsedElement],
    ) -> None:
        """Parse character cue followed by parentheticals and dialogue lines."""
        char_name = lines[0].lstrip("@").rstrip("^").strip()
        scene_num = scene_counter or None
        elements.append(
            ParsedElement(
                element_type=ElementType.CHARACTER,
                text=char_name,
                scene_number=scene_num,
            )
        )

        for line in lines[1:]:
            elem_type = ElementType.PARENTHETICAL if (line.startswith("(") and line.endswith(")")) else ElementType.DIALOGUE
            elements.append(
                ParsedElement(
                    element_type=elem_type,
                    text=line,
                    scene_number=scene_num,
                )
            )

    def _assemble_scenes(self, elements: List[ParsedElement]) -> List[ParsedScene]:
        """Aggregate elements into scenes delimited by scene headings."""
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
                scene_num = elem.scene_number or (scene_num + 1)
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
