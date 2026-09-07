"""
Lienmark Targeted Clarification Subsystem.
Exports clarification generator engine, canonical Pydantic v2 schemas, and taxonomy.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

from backend.agents.clarification.clarification_types import (
    ClarificationError,
    ClarificationGenerationError,
    ClarificationInput,
    ClarificationOutput,
    ClarificationUrgency,
    ClarificationValidationError,
    DocumentTypeRequirement,
    ProductionRole,
    TargetedClarification,
)
from backend.agents.clarification.generator import ClarificationGenerator
from backend.agents.clarification.heuristics import generate_rule_based_clarification

__all__ = [
    "ClarificationError",
    "ClarificationGenerationError",
    "ClarificationInput",
    "ClarificationOutput",
    "ClarificationUrgency",
    "ClarificationValidationError",
    "DocumentTypeRequirement",
    "ProductionRole",
    "TargetedClarification",
    "ClarificationGenerator",
    "generate_rule_based_clarification",
]
