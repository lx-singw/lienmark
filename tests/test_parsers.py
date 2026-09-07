"""
test_parsers.py

Comprehensive test suite for multi-format screenplay and timeline parsers.
Validates PdfScreenplayParser, FdxScreenplayParser, FountainScreenplayParser,
EdlTimelineParser, and ParserFactory under Google AntiGravity architectural rules.
"""

from __future__ import annotations

import zlib
import pytest

from backend.parsers.base import BaseScreenplayParser
from backend.parsers.edl_parser import EdlTimelineParser
from backend.parsers.factory import ParserFactory
from backend.parsers.fdx_parser import FdxScreenplayParser
from backend.parsers.fountain_parser import FountainScreenplayParser
from backend.parsers.parser_types import (
    DocumentFormat,
    ElementType,
    ParsedDocument,
    ParserCorruptFileError,
    ParserUnsupportedFormatError,
)
from backend.parsers.pdf_parser import PdfScreenplayParser


def _build_minimal_pdf_bytes(text_content: str) -> bytes:
    """Builds a valid minimal PDF stream containing text streams compressed with zlib."""
    stream_data = f"BT\n({text_content}) Tj\nET\n".encode("latin-1")
    compressed_stream = zlib.compress(stream_data)
    stream_length = len(compressed_stream)
    return (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length " + str(stream_length).encode("latin-1") + b" /Filter /FlateDecode >>\n"
        b"stream\n" + compressed_stream + b"\nendstream\nendobj\n"
        b"trailer << /Root 1 0 R >>\n%%EOF"
    )


def test_pdf_screenplay_parser_extraction_and_scenes() -> None:
    """Verifies PdfScreenplayParser text extraction, scene classification, and page counts."""
    script_text = (
        "INT. DETECTIVE OFFICE - NIGHT\n"
        "Detective Vance checks the locked filing cabinet.\n"
        "EXT. ALLEYWAY - DAWN\n"
        "Rain pools across the broken cobblestone.\n"
    )
    pdf_bytes = _build_minimal_pdf_bytes(script_text)
    parser = PdfScreenplayParser()
    doc = parser.parse(pdf_bytes, filename="vance_investigation.pdf")

    assert doc.format == DocumentFormat.PDF
    assert doc.title == "Vance Investigation"
    assert doc.page_count >= 1
    assert doc.scene_count == 2
    assert len(doc.scenes) == 2
    assert "INT. DETECTIVE OFFICE - NIGHT" in doc.scenes[0].heading
    assert "EXT. ALLEYWAY - DAWN" in doc.scenes[1].heading

    heading_elements = [e for e in doc.elements if e.element_type == ElementType.SCENE_HEADING]
    assert len(heading_elements) == 2


def test_fdx_screenplay_parser_elements_and_malformed_xml() -> None:
    """Verifies FdxScreenplayParser elements and defensive malformed XML error handling."""
    valid_fdx = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Template="No" Version="1">
  <Content>
    <Paragraph Type="Scene Heading" Number="10">
      <Text>INT. COURTROOM - DAY</Text>
    </Paragraph>
    <Paragraph Type="Action">
      <Text>The jury takes their seats in silence.</Text>
    </Paragraph>
    <Paragraph Type="Character">
      <Text>PROSECUTOR</Text>
    </Paragraph>
    <Paragraph Type="Parenthetical">
      <Text>(standing)</Text>
    </Paragraph>
    <Paragraph Type="Dialogue">
      <Text>Your Honor, the title deed is authentic.</Text>
    </Paragraph>
  </Content>
</FinalDraft>
"""
    parser = FdxScreenplayParser()
    doc = parser.parse(valid_fdx, filename="courtroom_drama.fdx")

    assert doc.format == DocumentFormat.FDX
    assert doc.scene_count == 1
    assert doc.scenes[0].scene_number == 10

    types = [e.element_type for e in doc.elements]
    assert ElementType.SCENE_HEADING in types
    assert ElementType.ACTION in types
    assert ElementType.CHARACTER in types
    assert ElementType.PARENTHETICAL in types
    assert ElementType.DIALOGUE in types

    malformed_xml = "<FinalDraft><Content><Paragraph Type='Scene Heading'><unclosed>"
    with pytest.raises(ParserCorruptFileError):
        parser.parse(malformed_xml)


def test_fountain_screenplay_parser_syntax_and_transitions() -> None:
    """Verifies Fountain 1.1 syntax parsing of scene headings, characters, and transitions."""
    fountain_script = """Title: Neon Syndicate
Author: Jane Doe

INT. APARTMENT - MORNING

Sunlight filters through dusty Venetian blinds.

DETECTIVE COLE
(wearily)
Another cold case on my desk.

> CUT TO:

EXT. ROOFTOP - NIGHT

The city lights glimmer below.
"""
    parser = FountainScreenplayParser()
    doc = parser.parse(fountain_script, filename="neon_syndicate.fountain")

    assert doc.format == DocumentFormat.FOUNTAIN
    assert doc.title == "Neon Syndicate"
    assert doc.scene_count == 2
    assert "INT. APARTMENT - MORNING" in doc.scenes[0].heading
    assert "EXT. ROOFTOP - NIGHT" in doc.scenes[1].heading

    types = [e.element_type for e in doc.elements]
    assert ElementType.SCENE_HEADING in types
    assert ElementType.ACTION in types
    assert ElementType.CHARACTER in types
    assert ElementType.PARENTHETICAL in types
    assert ElementType.DIALOGUE in types
    assert ElementType.TRANSITION in types


def test_edl_timeline_parser_events_tracks_and_timecodes() -> None:
    """Verifies CMX 3600 EDL parsing of events, reel IDs, tracks (V, A, A2), and clip names."""
    edl_content = """TITLE: PRODUCTION_REEL_MASTER
FCM: NON-DROP FRAME

001  REEL_A01  V     C        01:00:00:00 01:00:05:12 01:00:00:00 01:00:05:12
* FROM CLIP NAME: SCENE_01_HERO_TAKE1.MOV
* COMMENT: Wide master angle

002  REEL_S02  A     C        01:00:05:12 01:00:10:00 01:00:05:12 01:00:10:00
* FROM CLIP NAME: DIA_TRACK_01_LAV.WAV

003  REEL_FX3  A2    C        01:00:10:00 01:00:15:00 01:00:10:00 01:00:15:00
* FROM CLIP NAME: FOLEY_FOOTSTEPS.WAV
"""
    parser = EdlTimelineParser()
    doc = parser.parse(edl_content, filename="master_cut.edl")

    assert doc.format == DocumentFormat.EDL
    assert doc.title == "PRODUCTION_REEL_MASTER"
    assert len(doc.elements) == 3
    assert doc.scene_count == 3

    e1, e2, e3 = doc.elements
    assert e1.metadata["reel"] == "REEL_A01"
    assert e1.metadata["track"] == "V"
    assert e1.metadata["source_in"] == "01:00:00:00"
    assert e1.metadata["clip_name"] == "SCENE_01_HERO_TAKE1.MOV"

    assert e2.metadata["reel"] == "REEL_S02"
    assert e2.metadata["track"] == "A"
    assert e2.metadata["clip_name"] == "DIA_TRACK_01_LAV.WAV"

    assert e3.metadata["reel"] == "REEL_FX3"
    assert e3.metadata["track"] == "A2"
    assert e3.metadata["clip_name"] == "FOLEY_FOOTSTEPS.WAV"


def test_parser_factory_resolution_and_fallback() -> None:
    """Verifies ParserFactory resolution by extension, header magic bytes, and error fallback."""
    pdf_p = ParserFactory.get_parser_for_file("script.pdf")
    assert isinstance(pdf_p, PdfScreenplayParser)

    fdx_p = ParserFactory.get_parser_for_file("draft.fdx")
    assert isinstance(fdx_p, FdxScreenplayParser)

    fountain_p = ParserFactory.get_parser_for_file("story.fountain")
    assert isinstance(fountain_p, FountainScreenplayParser)

    edl_p = ParserFactory.get_parser_for_file("timeline.edl")
    assert isinstance(edl_p, EdlTimelineParser)

    sniffed_pdf = ParserFactory.get_parser_for_file("unnamed_stream", header_bytes=b"%PDF-1.5")
    assert isinstance(sniffed_pdf, PdfScreenplayParser)

    sniffed_fdx = ParserFactory.get_parser_for_file("unnamed_stream", header_bytes=b"<?xml <FinalDraft>")
    assert isinstance(sniffed_fdx, FdxScreenplayParser)

    with pytest.raises(ParserUnsupportedFormatError):
        ParserFactory.get_parser_for_file("unsupported.xyz", header_bytes=b"RANDOM_BYTES")
