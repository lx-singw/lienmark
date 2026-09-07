"""Edge case and boundary tests for the multi-format screenplay parsers."""

import pytest

from backend.parsers.edl_parser import EdlTimelineParser
from backend.parsers.factory import ParserFactory
from backend.parsers.fdx_parser import FdxScreenplayParser
from backend.parsers.fountain_parser import FountainScreenplayParser
from backend.parsers.parser_types import DocumentFormat, ElementType
from backend.parsers.pdf_stream_reader import PdfStreamReader

EDL_DROP_FRAME_SAMPLE = """TITLE: Live_Broadcast
FCM: DROP FRAME

001  REEL_1   A     C        00:00:00;00 00:00:10;00 01:00:00;00 01:00:10;00
* FROM CLIP NAME: AUDIO_TRACK_1.WAV
* COMMENT: Mic check
* COMMENT: Take 3
"""

FDX_NAMESPACED_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft xmlns="http://www.finaldraft.com/xml" DocumentType="Script">
  <Content>
    <Paragraph Type="Scene Heading">
      <Text>EXT. ROOFTOP - DUSK</Text>
    </Paragraph>
    <Paragraph Type="General">
      <Text>Wind howls across the gravel.</Text>
    </Paragraph>
    <Paragraph Type="Character">
      <Text>SARAH (V.O.)</Text>
    </Paragraph>
    <Paragraph Type="Dialogue">
      <Text>We have to move now.</Text>
    </Paragraph>
  </Content>
</FinalDraft>
"""

FOUNTAIN_EDGE_SAMPLE = """Title: Edge Stories

.ABANDONED MINE - CONTINUOUS

Dust settles.

@CYBORG_99
(rebooting)
Systems operational.

> FADE TO BLACK <
"""


def test_edl_drop_frame_and_comments():
    """Verify drop frame rate detection (29.97) and multiple comment parsing."""
    parser = EdlTimelineParser()
    doc = parser.parse(EDL_DROP_FRAME_SAMPLE, filename="broadcast.edl")

    assert doc.frame_rate == 29.97
    assert len(doc.elements) == 1
    event = doc.elements[0]
    assert event.metadata["track"] == "A"
    assert len(event.metadata["comments"]) == 2
    assert "Mic check" in event.metadata["comments"]


def test_fdx_namespaced_and_auto_scene_numbers():
    """Verify XML with xmlns default namespaces and auto-incrementing scene numbers."""
    parser = FdxScreenplayParser()
    doc = parser.parse(FDX_NAMESPACED_SAMPLE, filename="namespaced.fdx")

    assert doc.format == DocumentFormat.FDX
    assert len(doc.scenes) == 1
    scene = doc.scenes[0]
    assert scene.scene_number == 1
    assert scene.heading == "EXT. ROOFTOP - DUSK"
    assert any(e.element_type == ElementType.CHARACTER and "SARAH" in e.text for e in doc.elements)


def test_fountain_forced_cues_and_actions():
    """Verify forced scene headings (leading dot) and forced character cues (@)."""
    parser = FountainScreenplayParser()
    doc = parser.parse(FOUNTAIN_EDGE_SAMPLE, filename="edge.fountain")

    assert doc.format == DocumentFormat.FOUNTAIN
    assert len(doc.scenes) == 1
    assert doc.scenes[0].heading == "ABANDONED MINE - CONTINUOUS"

    char_elem = next(e for e in doc.elements if e.element_type == ElementType.CHARACTER)
    assert char_elem.text == "CYBORG_99"


def test_pdf_stream_reader_unescaping():
    """Verify PdfStreamReader unescapes octal sequences and special characters."""
    reader = PdfStreamReader(b"%PDF-1.4\n1 0 obj << /Type /Page >> endobj\n%%EOF")
    unescaped = reader._unescape_pdf_string(r"Hello\nWorld\(test\)\101")
    assert "Hello\nWorld(test)A" == unescaped


def test_factory_sniff_plaintext_formats():
    """Verify ParserFactory detects Fountain vs EDL inside plaintext content."""
    fountain_txt = "INT. LIVING ROOM - DAY\nJohn enters."
    p1 = ParserFactory.get_parser_for_file("script.txt", header_bytes=fountain_txt.encode("utf-8"))
    assert isinstance(p1, FountainScreenplayParser)

    edl_txt = "001  AX  V  C  01:00:00:00 01:00:05:00 01:00:00:00 01:00:05:00"
    p2 = ParserFactory.get_parser_for_file("cutlist.txt", header_bytes=edl_txt.encode("utf-8"))
    assert isinstance(p2, EdlTimelineParser)
