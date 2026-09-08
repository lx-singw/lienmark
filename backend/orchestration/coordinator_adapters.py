"""
backend/orchestration/coordinator_adapters.py

Typed adapters integrating agent modules into EvidenceDrivenCoordinator.
Establishes a unified, configurable evaluation contract to resolve threshold conflicts.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.agents.research.query_builder import StructuredQueryBuilder, InverseDomainSteeringEngine
from backend.agents.research.query_types import SearchQueryRequest, EvidenceEvaluation
from backend.agents.research.entity_extractor import EntityExtractor
from backend.agents.research.subgoal_decomposer import SubgoalDecomposer
from backend.core.conflict_arbiter import ConflictArbiter

class EvaluationContract(BaseModel):
    """
    Unified configurable evaluation contract covering critical thresholds.
    Resolves threshold conflicts (e.g. 0.5 vs 0.6 vs 0.7) across the platform.
    """
    identity_match_threshold: float = Field(default=0.7)
    relevance_threshold: float = Field(default=0.7)
    authority_threshold: float = Field(default=0.7)
    missing_rights_flags: List[str] = Field(default_factory=lambda: ["unregistered", "unknown", "missing"])
    contradictory_evidence_flags: List[str] = Field(default_factory=lambda: ["dispute", "infringement", "lawsuit"])

class CoordinatorAdapters:
    """Typed adapters connecting interfaces to EvidenceDrivenCoordinator."""
    
    def __init__(self, contract: Optional[EvaluationContract] = None):
        self.contract = contract or EvaluationContract()
        self.query_builder = StructuredQueryBuilder()
        self.steering_engine = InverseDomainSteeringEngine(self.query_builder)
        self.entity_extractor = EntityExtractor()
        self.subgoal_decomposer = SubgoalDecomposer()
        self.conflict_arbiter = ConflictArbiter()
        
    def build_search_query(self, request: SearchQueryRequest) -> Any:
        return self.query_builder.build_query(request)
        
    def steer_next_query(self, request: SearchQueryRequest, evaluation: EvidenceEvaluation) -> Any:
        return self.steering_engine.next_query(request, evaluation)
        
    def extract_leads(self, findings: List[Any]) -> Any:
        # Apply contract before extraction if possible, or adapt results
        return self.entity_extractor.extract_leads_from_findings(findings)
        
    def decompose_subgoals(self, context: Any) -> Any:
        return self.subgoal_decomposer.decompose(context)
        
    def arbitrate_conflicts(self, claim_id: str, findings: List[Any], asset_type: str) -> Any:
        filtered_findings = self._filter_findings_by_contract(findings)
        return self.conflict_arbiter.arbitrate(claim_id, filtered_findings, asset_type=asset_type)
        
    def _filter_findings_by_contract(self, findings: List[Any]) -> List[Any]:
        """Applies the unified EvaluationContract thresholds to findings."""
        valid = []
        for finding in findings:
            if isinstance(finding, dict):
                id_score = finding.get('identity_match_score', 1.0)
                rel_score = finding.get('relevance_score', 1.0)
                auth_score = finding.get('authority_score', 1.0)
            else:
                id_score = getattr(finding, 'identity_match_score', 1.0)
                rel_score = getattr(finding, 'relevance_score', 1.0)
                auth_score = getattr(finding, 'authority_score', 1.0)
                
            if (id_score >= self.contract.identity_match_threshold and 
                rel_score >= self.contract.relevance_threshold and 
                auth_score >= self.contract.authority_threshold):
                valid.append(finding)
        return valid
