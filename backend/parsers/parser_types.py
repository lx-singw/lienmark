"""Data structures, enums, and exceptions for the multi-format parser subsystem."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentFormat(str, Enum):
    """Supported document and timeline formats."""

    PDF = "pdf"
    FDX = "fdx"
    FOUNTAIN = "fountain"
    EDL = "edl"
    PLAINTEXT = "plaintext"
    UNKNOWN = "unknown"


class ElementType(str, Enum):
    """Syntactic element classifications within screenplays and cutlists."""

    SCENE_HEADING = "scene_heading"
    ACTION = "action"
    CHARACTER = "character"
    DIALOGUE = "dialogue"
    PARENTHETICAL = "parenthetical"
    TRANSITION = "transition"
    TIMECODE_EVENT = "timecode_event"


class ParsedElement(BaseModel):
    """An individual structural element parsed from a script or edit timeline."""

    element_type: ElementType
    text: str
    scene_number: Optional[int] = None
    page_or_timecode: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ParsedScene(BaseModel):
    """A logical scene unit comprising a heading and sequential elements."""

    scene_number: int
    heading: str
    elements: List[ParsedElement] = Field(default_factory=list)
    token_count: int = 0


class ParsedDocument(BaseModel):
    """Normalized document representation produced across all parser engines."""

    format: DocumentFormat
    title: str = ""
    scenes: List[ParsedScene] = Field(default_factory=list)
    elements: List[ParsedElement] = Field(default_factory=list)
    page_count: int = 0
    scene_count: int = 0
    frame_rate: Optional[float] = None
    raw_text: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ParserError(Exception):
    """Base exception for parsing operations."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ParserUnsupportedFormatError(ParserError):
    """Raised when encountering an unrecognized or unsupported document format."""

    pass


class ParserCorruptFileError(ParserError):
    """Raised when file contents are corrupted, truncated, or unparseable."""

    pass
