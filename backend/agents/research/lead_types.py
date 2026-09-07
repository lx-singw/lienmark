"""
backend/agents/research/lead_types.py

Canonical Pydantic v2 schemas and taxonomy for lead and entity extraction.
Sprint 3.2: Snippet Entity & Lead Extractor Specialist.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class LeadEntityType(str, Enum):
    """Classified legal entity categories for IP rights and clearance leads."""
    PUBLISHER = "publisher"
    LABEL = "label"
    ESTATE = "estate"
    CORPORATE_PARENT = "corporate_parent"
    ASSIGNEE = "assignee"
    TRUST_FOUNDATION = "trust_foundation"


class LeadRelationshipType(str, Enum):
    """Actionable legal relationship signal types connecting assets to entities."""
    ADMINISTERED_BY = "administered_by"
    PUBLISHED_BY = "published_by"
    CATALOG_OWNED_BY = "catalog_owned_by"
    COURTESY_OF = "master_recording_courtesy_of"
    LICENSED_TO = "under_exclusive_license_to"
    SUBSIDIARY_OF = "subsidiary_of"
    ESTATE_ADMINISTERED = "estate_administered"
    TRADEMARK_ASSIGNED = "trademark_assigned"


class EntityExtractionError(Exception):
    """Base domain exception for entity extraction failures."""
    pass


class ExtractedLead(BaseModel):
    """Actionable legal entity lead extracted from Parallel Search snippets."""
    model_config = ConfigDict(frozen=True)

    lead_id: str = Field(..., description="Deterministic unique identifier for lead.")
    parent_finding_id: str = Field(..., description="ID or URL hash of originating finding.")
    entity_name: str = Field(..., min_length=1, description="Normalized entity name.")
    entity_type: LeadEntityType = Field(..., description="Classified entity type.")
    relationship_type: LeadRelationshipType = Field(..., description="Detected relationship signal.")
    confidence_score: float = Field(default=0.75, ge=0.0, le=1.0, description="Extraction confidence.")
    source_sentence: str = Field(..., description="Exact attributable sentence containing signal.")
    proposed_query_extension: str = Field(..., description="Actionable follow-up query extension.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic telemetry.")
