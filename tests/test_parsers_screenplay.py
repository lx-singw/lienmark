"""Tests for screenplay parsers (Fountain, FDX, and Base parser)."""

import pytest

from backend.parsers.base import BaseScreenplayParser
from backend.parsers.fdx_parser import FdxScreenplayParser
from backend.parsers.fountain_parser import FountainScreenplayParser
from backend.parsers.fountain_syntax import FountainSyntax
from backend.parsers.parser_types import (
    DocumentFormat,
    ElementType,
    ParserCorruptFileError,
)

SAMPLE_FOUNTAIN = """Title: Neon Noir
Author: Alex Vance

INT. DETECTIVE OFFICE - NIGHT #1#

The rain hammers against the window pane. A neon sign buzzes.

MARCUS
(lighting a cigarette)
Did you find the ledger?

ELENA
It was gone before I arrived.

> CUT TO:

EXT. ALLEYWAY - NIGHT #2#

A lone figure sprints into the shadows.
"""

SAMPLE_FDX = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Template="No" Version="1">
  <Content>
    <Paragraph Type="Scene Heading" Number="1">
      <Text>INT. SAFE HOUSE - DAY</Text>
    </Paragraph>
    <Paragraph Type="Action">
      <Text>Sunlight cuts across the dusty concrete floor.</Text>
    </Paragraph>
    <Paragraph Type="Character">
      <Text>KATE</Text>
    </Paragraph>
    <Paragraph Type="Parenthetical">
      <Text>(whispering)</Text>
    </Paragraph>
    <Paragraph Type="Dialogue">
      <Text>We have company outside.</Text>
    </Paragraph>
    <Paragraph Type="Transition">
      <Text>FADE OUT.</Text>
    </Paragraph>
  </Content>
</FinalDraft>
"""


def test_base_parser_helpers():
    """Verify base parser utility methods for decoding and token calculation."""
    assert BaseScreenplayParser._ensure_text(b"hello world") == "hello world"
    assert BaseScreenplayParser._ensure_bytes("hello world") == b"hello world"
    assert BaseScreenplayParser._count_tokens("Three words here") == 3
    assert BaseScreenplayParser._extract_title_from_filename("my_script_v2.fountain") == "My Script V2"
    assert BaseScreenplayParser._extract_title_from_filename(None) == "Untitled"


def test_base_parser_type_safety():
    """Verify type checking in base parser helper methods."""
    with pytest.raises(TypeError):
        BaseScreenplayParser._ensure_text(12345)  # type: ignore
    with pytest.raises(TypeError):
        BaseScreenplayParser._ensure_bytes(12345)  # type: ignore


def test_fountain_parser_success():
    """Verify successful parsing of a Fountain script into elements and scenes."""
    parser = FountainScreenplayParser()
    doc = parser.parse(SAMPLE_FOUNTAIN, filename="neon_noir.fountain")

    assert doc.format == DocumentFormat.FOUNTAIN
    assert doc.title == "Neon Noir"
    assert len(doc.scenes) == 2
    assert doc.scenes[0].scene_number == 1
    assert "INT. DETECTIVE OFFICE - NIGHT" in doc.scenes[0].heading
    assert doc.scenes[1].scene_number == 2

    # Check element classification
    elem_types = [e.element_type for e in doc.elements]
    assert ElementType.SCENE_HEADING in elem_types
    assert ElementType.CHARACTER in elem_types
    assert ElementType.PARENTHETICAL in elem_types
    assert ElementType.DIALOGUE in elem_types
    assert ElementType.TRANSITION in elem_types


def test_fountain_syntax_utilities():
    """Verify Fountain boneyard removal and forced syntax handling."""
    raw = "Top text /* secret comment */ and [[note]] bottom text."
    cleaned = FountainSyntax.strip_boneyard_and_notes(raw)
    assert "secret comment" not in cleaned
    assert "note" not in cleaned
    assert FountainSyntax.is_scene_heading(".FORCED SCENE")
    assert FountainSyntax.is_character_cue("@FORCED_CHAR")
    assert FountainSyntax.is_transition("> SMASH CUT TO:")


def test_fountain_empty_fails():
    """Verify empty Fountain content triggers ParserCorruptFileError."""
    parser = FountainScreenplayParser()
    with pytest.raises(ParserCorruptFileError):
        parser.parse("   \n\t  ")


def test_fdx_parser_success():
    """Verify parsing Final Draft XML scripts into scenes and elements."""
    parser = FdxScreenplayParser()
    doc = parser.parse(SAMPLE_FDX, filename="safe_house.fdx")

    assert doc.format == DocumentFormat.FDX
    assert len(doc.scenes) == 1
    scene = doc.scenes[0]
    assert scene.scene_number == 1
    assert scene.heading == "INT. SAFE HOUSE - DAY"

    elem_types = [e.element_type for e in doc.elements]
    assert elem_types == [
        ElementType.SCENE_HEADING,
        ElementType.ACTION,
        ElementType.CHARACTER,
        ElementType.PARENTHETICAL,
        ElementType.DIALOGUE,
        ElementType.TRANSITION,
    ]


def test_fdx_malformed_xml():
    """Verify malformed XML triggers ParserCorruptFileError."""
    parser = FdxScreenplayParser()
    with pytest.raises(ParserCorruptFileError):
        parser.parse("<FinalDraft><UnclosedTag>")
    with pytest.raises(ParserCorruptFileError):
        parser.parse("")
