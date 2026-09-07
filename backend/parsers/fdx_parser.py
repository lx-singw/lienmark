"""Final Draft XML (FDX) screenplay parser with robust namespace handling."""

import re
from typing import List, Optional, Union
import xml.etree.ElementTree as ET

from backend.parsers.base import BaseScreenplayParser
from backend.parsers.parser_types import (
    DocumentFormat,
    ElementType,
    ParsedDocument,
    ParsedElement,
    ParsedScene,
    ParserCorruptFileError,
)

FDX_TYPE_MAP = {
    "scene heading": ElementType.SCENE_HEADING,
    "action": ElementType.ACTION,
    "character": ElementType.CHARACTER,
    "dialogue": ElementType.DIALOGUE,
    "parenthetical": ElementType.PARENTHETICAL,
    "transition": ElementType.TRANSITION,
    "shot": ElementType.ACTION,
    "general": ElementType.ACTION,
}


class FdxScreenplayParser(BaseScreenplayParser):
    """Parses Final Draft XML (.fdx) screenplay files into structured elements."""

    def parse(
        self,
        content: Union[str, bytes],
        filename: Optional[str] = None,
    ) -> ParsedDocument:
        """Parse FDX XML content into a structured ParsedDocument."""
        content_str = self._ensure_text(content)
        root = self._clean_and_parse_xml(content_str)
        title = self._extract_title(root, filename)

        elements = self._extract_elements(root)
        scenes = self._assemble_scenes(elements)
        raw_text = "\n".join(e.text for e in elements)
        page_count = max(1, len(elements) // 25 + 1)

        return ParsedDocument(
            format=DocumentFormat.FDX,
            title=title,
            scenes=scenes,
            elements=elements,
            page_count=page_count,
            scene_count=len(scenes),
            raw_text=raw_text,
            metadata={"source_filename": filename or "", "engine": "fdx_parser"},
        )

    def _clean_and_parse_xml(self, content_str: str) -> ET.Element:
        """Parse XML string defensively removing namespaces and invalid prefixes."""
        if not content_str or not content_str.strip():
            raise ParserCorruptFileError("FDX content is empty")

        # Strip default XML namespace declarations to prevent query failures
        cleaned = re.sub(r'\sxmlns(:\w+)?="[^"]*"', "", content_str, count=5)
        try:
            return ET.fromstring(cleaned)
        except ET.ParseError as exc:
            # Attempt to locate root element if wrapped in junk
            match = re.search(r"(<FinalDraft\b.*?</FinalDraft>)", cleaned, re.DOTALL)
            if match:
                try:
                    return ET.fromstring(match.group(1))
                except ET.ParseError:
                    pass
            raise ParserCorruptFileError(f"Malformed FDX XML document: {exc}") from exc

    def _extract_title(self, root: ET.Element, filename: Optional[str]) -> str:
        """Extract screenplay title from TitlePage elements or fallback to filename."""
        for elem in root.iter():
            tag = elem.tag.split("}")[-1]
            if tag.lower() == "title":
                text = "".join(elem.itertext()).strip()
                if text:
                    return text
        return self._extract_title_from_filename(filename)

    def _extract_elements(self, root: ET.Element) -> List[ParsedElement]:
        """Extract parsed screenplay elements from XML Paragraph tags."""
        elements: List[ParsedElement] = []
        scene_counter = 0

        for elem in root.iter():
            tag = elem.tag.split("}")[-1]
            if tag.lower() != "paragraph":
                continue

            ptype = elem.attrib.get("Type", "Action").strip().lower()
            elem_type = FDX_TYPE_MAP.get(ptype, ElementType.ACTION)
            text = self._extract_paragraph_text(elem)
            if not text:
                continue

            scene_num_attr = elem.attrib.get("Number")
            if elem_type == ElementType.SCENE_HEADING:
                scene_counter += 1
                scene_num = int(scene_num_attr) if scene_num_attr and scene_num_attr.isdigit() else scene_counter
            else:
                scene_num = scene_counter if scene_counter > 0 else None

            elements.append(
                ParsedElement(
                    element_type=elem_type,
                    text=text,
                    scene_number=scene_num,
                    metadata={"fdx_type": ptype},
                )
            )

        return elements

    def _extract_paragraph_text(self, paragraph_elem: ET.Element) -> str:
        """Gather all text runs inside a paragraph element."""
        text_parts: List[str] = []
        for child in paragraph_elem.iter():
            tag = child.tag.split("}")[-1]
            if tag.lower() == "text" and child.text:
                text_parts.append(child.text)
        if not text_parts and paragraph_elem.text:
            text_parts.append(paragraph_elem.text)
        return "".join(text_parts).strip()

    def _assemble_scenes(self, elements: List[ParsedElement]) -> List[ParsedScene]:
        """Group elements into sequential ParsedScene containers."""
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
