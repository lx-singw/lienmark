"""Tests for PDF parser, EDL parser, ParserFactory, and parser data models."""

import zlib
import pytest

from backend.parsers.edl_parser import EdlTimelineParser
from backend.parsers.factory import ParserFactory
from backend.parsers.fdx_parser import FdxScreenplayParser
from backend.parsers.fountain_parser import FountainScreenplayParser
from backend.parsers.parser_types import (
    DocumentFormat,
    ElementType,
    ParsedDocument,
    ParsedElement,
    ParsedScene,
    ParserCorruptFileError,
    ParserError,
    ParserUnsupportedFormatError,
)
from backend.parsers.pdf_parser import PdfScreenplayParser
from backend.parsers.pdf_stream_reader import PdfStreamReader

SAMPLE_EDL = """TITLE: Cyberpunk_Edit
FCM: NON-DROP FRAME

001  REEL_A   V     C        01:00:00:00 01:00:05:00 01:00:00:00 01:00:05:00
* FROM CLIP NAME: INT_LAB_01.MOV
* COMMENT: Master shot

002  REEL_B   V     D    024 02:00:10:00 02:00:14:00 01:00:05:00 01:00:09:00
* FROM CLIP NAME: INT_LAB_CLOSEUP.MOV
"""


def create_synthetic_pdf(text_content: str) -> bytes:
    """Build a minimal valid PDF binary with a zlib-compressed content stream."""
    stream_body = f"BT\n({text_content}) Tj\nET\n".encode("latin-1")
    compressed = zlib.compress(stream_body)
    length = len(compressed)
    return (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length " + str(length).encode("latin-1") + b" /Filter /FlateDecode >>\n"
        b"stream\n" + compressed + b"\nendstream\nendobj\n"
        b"trailer << /Root 1 0 R >>\n%%EOF"
    )


def test_parser_types_and_exceptions():
    """Verify data model instantiations and exception hierarchies."""
    elem = ParsedElement(element_type=ElementType.SCENE_HEADING, text="INT. TEST - DAY", scene_number=1)
    scene = ParsedScene(scene_number=1, heading="INT. TEST - DAY", elements=[elem], token_count=4)
    doc = ParsedDocument(
        format=DocumentFormat.PLAINTEXT,
        title="Test Doc",
        scenes=[scene],
        elements=[elem],
        page_count=1,
        scene_count=1,
        raw_text="INT. TEST - DAY",
    )
    assert doc.scenes[0].scene_number == 1
    assert issubclass(ParserCorruptFileError, ParserError)
    assert issubclass(ParserUnsupportedFormatError, ParserError)


def test_pdf_stream_reader_decompression():
    """Verify PdfStreamReader extracts text streams and counts pages."""
    pdf_bytes = create_synthetic_pdf("INT. ROOFTOP - NIGHT")
    reader = PdfStreamReader(pdf_bytes)
    assert reader.count_pages() >= 1
    extracted = reader.extract_text_streams()
    assert "INT. ROOFTOP - NIGHT" in extracted


def test_pdf_stream_reader_corrupt():
    """Verify PdfStreamReader rejects corrupt or headerless data."""
    with pytest.raises(ParserCorruptFileError):
        PdfStreamReader(b"not a real pdf binary stream")


def test_pdf_screenplay_parser_pipeline():
    """Verify full PdfScreenplayParser extracts elements and scenes."""
    pdf_bytes = create_synthetic_pdf("INT. WAREHOUSE - DAY\nJack inspects the crate.")
    parser = PdfScreenplayParser()
    doc = parser.parse(pdf_bytes, filename="warehouse.pdf")

    assert doc.format == DocumentFormat.PDF
    assert doc.title == "Warehouse"
    assert len(doc.elements) >= 1
    assert any(e.element_type == ElementType.SCENE_HEADING for e in doc.elements)


def test_edl_parser_success():
    """Verify parsing CMX 3600 EDL records into timecode events and scenes."""
    parser = EdlTimelineParser()
    doc = parser.parse(SAMPLE_EDL, filename="edit_timeline.edl")

    assert doc.format == DocumentFormat.EDL
    assert doc.title == "Cyberpunk_Edit"
    assert doc.frame_rate == 24.0
    assert len(doc.elements) == 2
    assert len(doc.scenes) == 2

    e1 = doc.elements[0]
    assert e1.element_type == ElementType.TIMECODE_EVENT
    assert e1.metadata["clip_name"] == "INT_LAB_01.MOV"
    assert e1.metadata["reel"] == "REEL_A"
    assert e1.metadata["transition"] == "C"

    e2 = doc.elements[1]
    assert e2.metadata["transition"] == "D"
    assert e2.metadata["clip_name"] == "INT_LAB_CLOSEUP.MOV"


def test_edl_parser_corrupt():
    """Verify empty or non-CMX EDL throws ParserCorruptFileError."""
    parser = EdlTimelineParser()
    with pytest.raises(ParserCorruptFileError):
        parser.parse("")
    with pytest.raises(ParserCorruptFileError):
        parser.parse("Just random text without CMX 3600 timecodes")


def test_parser_factory_resolution():
    """Verify ParserFactory correctly resolves parsers by extension and magic bytes."""
    p_pdf = ParserFactory.get_parser_for_file("script.pdf")
    assert isinstance(p_pdf, PdfScreenplayParser)

    p_fdx = ParserFactory.get_parser_for_file("script.fdx")
    assert isinstance(p_fdx, FdxScreenplayParser)

    p_fountain = ParserFactory.get_parser_for_file("script.fountain")
    assert isinstance(p_fountain, FountainScreenplayParser)

    p_edl = ParserFactory.get_parser_for_file("timeline.edl")
    assert isinstance(p_edl, EdlTimelineParser)

    # By magic bytes
    p_sniffed_pdf = ParserFactory.get_parser_for_file("unknown", header_bytes=b"%PDF-1.4\nsome data")
    assert isinstance(p_sniffed_pdf, PdfScreenplayParser)

    with pytest.raises(ParserUnsupportedFormatError):
        ParserFactory.get_parser_for_file("unsupported.xyz")
