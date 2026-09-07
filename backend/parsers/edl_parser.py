"""CMX 3600 Edit Decision List (EDL) timeline parser."""

import re
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.parsers.base import BaseScreenplayParser
from backend.parsers.parser_types import (
    DocumentFormat,
    ElementType,
    ParsedDocument,
    ParsedElement,
    ParsedScene,
    ParserCorruptFileError,
)

EDL_EVENT_REGEX = re.compile(
    r"^(\d+)\s+(\S+)\s+(\S+)\s+([A-Z])(?:\s+(\d+))?\s+"
    r"(\d{2}:\d{2}:\d{2}[:;]\d{2})\s+(\d{2}:\d{2}:\d{2}[:;]\d{2})\s+"
    r"(\d{2}:\d{2}:\d{2}[:;]\d{2})\s+(\d{2}:\d{2}:\d{2}[:;]\d{2})"
)
CLIP_NAME_REGEX = re.compile(r"^\*\s*(?:FROM CLIP NAME|CLIP NAME|SOURCE FILE):\s*(.+)$", re.IGNORECASE)
TITLE_REGEX = re.compile(r"^TITLE:\s*(.+)$", re.IGNORECASE)
FCM_REGEX = re.compile(r"^FCM:\s*(.+)$", re.IGNORECASE)


class EdlTimelineParser(BaseScreenplayParser):
    """Parses standard CMX 3600 Edit Decision List files."""

    def parse(
        self,
        content: Union[str, bytes],
        filename: Optional[str] = None,
    ) -> ParsedDocument:
        """Parse EDL timeline content into a structured ParsedDocument."""
        raw_text = self._ensure_text(content)
        if not raw_text.strip():
            raise ParserCorruptFileError("EDL content is empty")

        title, frame_rate, lines = self._extract_header_info(raw_text, filename)
        elements = self._parse_edl_events(lines)
        if not elements:
            raise ParserCorruptFileError("No valid CMX 3600 events found in EDL file")

        scenes = self._assemble_scenes(elements)

        return ParsedDocument(
            format=DocumentFormat.EDL,
            title=title,
            scenes=scenes,
            elements=elements,
            page_count=max(1, len(scenes) // 20 + 1),
            scene_count=len(scenes),
            frame_rate=frame_rate,
            raw_text=raw_text,
            metadata={"source_filename": filename or "", "engine": "edl_parser"},
        )

    def _extract_header_info(
        self,
        raw_text: str,
        filename: Optional[str],
    ) -> Tuple[str, float, List[str]]:
        """Extract title, frame rate, and filter remaining event lines."""
        title = self._extract_title_from_filename(filename)
        frame_rate = 24.0
        remaining_lines: List[str] = []

        for line in raw_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            title_match = TITLE_REGEX.match(stripped)
            if title_match:
                title = title_match.group(1).strip()
                continue
            fcm_match = FCM_REGEX.match(stripped)
            if fcm_match:
                fcm_val = fcm_match.group(1).strip().upper()
                if "DROP" in fcm_val and "NON" not in fcm_val:
                    frame_rate = 29.97
                elif "25" in fcm_val:
                    frame_rate = 25.0
                continue
            remaining_lines.append(stripped)

        return title, frame_rate, remaining_lines

    def _parse_edl_events(self, lines: List[str]) -> List[ParsedElement]:
        """Parse sequential CMX 3600 event records and associated clip comments."""
        elements: List[ParsedElement] = []
        current_event: Optional[Dict[str, Any]] = None

        for line in lines:
            event_match = EDL_EVENT_REGEX.match(line)
            if event_match:
                if current_event:
                    elements.append(self._build_element(current_event))
                current_event = self._build_event_dict(event_match)
            elif current_event and line.startswith("*"):
                self._enrich_event_with_comment(current_event, line)

        if current_event:
            elements.append(self._build_element(current_event))

        return elements

    def _build_event_dict(self, match: re.Match) -> Dict[str, Any]:
        """Convert regex match groups into an event dictionary."""
        return {
            "event_number": int(match.group(1)),
            "reel": match.group(2),
            "track": match.group(3),
            "transition": match.group(4),
            "trans_duration": match.group(5),
            "source_in": match.group(6),
            "source_out": match.group(7),
            "record_in": match.group(8),
            "record_out": match.group(9),
            "clip_name": "",
            "comments": [],
        }

    def _enrich_event_with_comment(self, event: Dict[str, Any], line: str) -> None:
        """Parse clip name or append comments to active event."""
        clip_match = CLIP_NAME_REGEX.match(line)
        if clip_match:
            event["clip_name"] = clip_match.group(1).strip()
        else:
            clean_comment = re.sub(r"^\*\s*(?:COMMENT:)?\s*", "", line, flags=re.IGNORECASE).strip()
            if clean_comment:
                event["comments"].append(clean_comment)

    def _build_element(self, event: Dict[str, Any]) -> ParsedElement:
        """Construct a ParsedElement from accumulated event data."""
        clip = event.get("clip_name") or f"REEL_{event['reel']}"
        desc = f"EVENT {event['event_number']:03d}: {clip} [{event['track']} {event['transition']}]"
        return ParsedElement(
            element_type=ElementType.TIMECODE_EVENT,
            text=desc,
            scene_number=event["event_number"],
            page_or_timecode=event["record_in"],
            metadata=event,
        )

    def _assemble_scenes(self, elements: List[ParsedElement]) -> List[ParsedScene]:
        """Represent EDL cutlist events as chronological scene records."""
        scenes: List[ParsedScene] = []
        for elem in elements:
            meta = elem.metadata
            heading = f"EVENT {meta.get('event_number', 0):03d} - {meta.get('clip_name') or meta.get('reel')}"
            scenes.append(
                ParsedScene(
                    scene_number=elem.scene_number or len(scenes) + 1,
                    heading=heading,
                    elements=[elem],
                    token_count=self._count_tokens(elem.text),
                )
            )
        return scenes
