"""
backend/orchestration/studio_policy_engine.py

Lienmark Studio Policy Engine module.
Sprint 5.1 - Studio Policy Inheritance & Statutory Clearance Invariants.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from backend.core.policy_engine import (
    StudioPolicyEngine,
    get_policy_engine,
)
from backend.core.policy_types import (
    LicensingScope,
    PolicyActionRequirement,
    PolicyEvaluationResult,
    PolicyViolation,
    ProductionPolicyOverride,
    RuleEvaluationItem,
    RuleEvaluationStatus,
    StudioPolicyConfig,
    StudioProfileType,
    TerritoryScope,
)

__all__ = [
    "StudioPolicyEngine",
    "get_policy_engine",
    "StudioPolicyConfig",
    "ProductionPolicyOverride",
    "PolicyEvaluationResult",
    "PolicyViolation",
    "StudioProfileType",
    "LicensingScope",
    "TerritoryScope",
    "RuleEvaluationStatus",
    "PolicyActionRequirement",
    "RuleEvaluationItem",
]

