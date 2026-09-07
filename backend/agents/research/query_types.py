"""
backend/agents/research/query_types.py

Canonical Pydantic v2 schemas and taxonomy for clearance search query formulation.
Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
Authored strictly under Google AntiGravity architectural guidelines.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class AssetClass(str, Enum):
    """Five core intellectual property asset classes for clearance research."""
    MUSIC = "music"
    BRAND = "brand"
    FOOTAGE = "footage"
    ARTWORK = "artwork"
    LIKENESS = "likeness"

    @classmethod
    def from_claim_category(cls, category: Union[str, Any]) -> "AssetClass":
        """Maps an intake claim category string or enum to an AssetClass."""
        val = str(category.value if hasattr(category, "value") else category).lower().strip()
        mapping = {
            "music": cls.MUSIC,
            "brand": cls.BRAND,
            "footage": cls.FOOTAGE,
            "artwork": cls.ARTWORK,
            "real_person": cls.LIKENESS,
            "historical_figure": cls.LIKENESS,
            "likeness": cls.LIKENESS,
        }
        if val not in mapping:
            raise InvalidAssetClassError(f"Unsupported claim category for query building: '{category}'")
        return mapping[val]


class SteeringState(str, Enum):
    """Lifecycle state machine for registry fallback and inverse domain steering."""
    STRICT_REGISTRY = "strict_registry"
    INVERSE_STEERING = "inverse_steering"
    ADVERSARIAL_PROBE = "adversarial_probe"
    DEEP_TASK = "deep_task"
    EXHAUSTED = "exhausted"


class QueryBuilderError(Exception):
    """Base domain exception for query builder operations."""
    pass


class EntityDisambiguationError(QueryBuilderError):
    """Raised when query parameters fail entity disambiguation invariants."""
    pass


class InvalidAssetClassError(QueryBuilderError):
    """Raised when an unknown or invalid asset class is requested."""
    pass


class InvalidSteeringTransitionError(QueryBuilderError):
    """Raised when an illegal fallback state machine transition is attempted."""
    pass


class SearchQueryRequest(BaseModel):
    """Structured request specification for query formulation."""
    model_config = ConfigDict(frozen=True)

    asset_id: str = Field(..., description="Unique asset identifier.")
    asset_class: AssetClass = Field(..., description="Target intellectual property asset class.")
    title: str = Field(..., min_length=1, description="Title, mark, or subject name.")
    creator_or_owner: Optional[str] = Field(default=None, description="Artist, author, applicant, or owner.")
    year: Optional[int] = Field(default=None, description="Creation, release, or registration year.")
    catalog_or_reg_no: Optional[str] = Field(default=None, description="Catalog, registration, or serial ID.")
    stable_lineage_key: Optional[str] = Field(default=None, description="Lineage key for cache isolation.")
    current_state: SteeringState = Field(default=SteeringState.STRICT_REGISTRY, description="Current fallback state.")
    retry_count: int = Field(default=0, ge=0, description="Number of fallback retries executed.")
    context_notes: Optional[str] = Field(default=None, description="Additional context or cues.")


class GeneratedQuery(BaseModel):
    """Synthesized search query ready for execution by Parallel Search API."""
    model_config = ConfigDict(frozen=True)

    query_string: str = Field(..., description="Final formulated search query string.")
    state: SteeringState = Field(..., description="Fallback steering state associated with this query.")
    asset_class: AssetClass = Field(..., description="Target asset class.")
    disambiguation_key: str = Field(..., description="Unique deterministic entity isolation key.")
    registry_domains: List[str] = Field(default_factory=list, description="Registry site: constraints applied.")
    negative_operators: List[str] = Field(default_factory=list, description="Negative exclusion operators applied.")
    ownership_keywords: List[str] = Field(default_factory=list, description="Targeted ownership terms appended.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic telemetry.")


class EvidenceEvaluation(BaseModel):
    """Summary of search execution results used to evaluate fallback transitions."""
    model_config = ConfigDict(frozen=True)

    result_count: int = Field(default=0, ge=0, description="Total search results returned.")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Highest evidence confidence.")
    stance: Optional[str] = Field(default=None, description="Reconciled evidence stance if known.")
    error_status: Optional[int] = Field(default=None, description="HTTP status code if request failed.")
