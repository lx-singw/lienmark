import hashlib
import json
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Use(StrictModel):
    stable_lineage_key: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=500)
    asset_type: str = Field(min_length=1, max_length=80)
    scene_or_timecode: str = Field(min_length=1, max_length=160)
    duration_or_prominence: str = Field(min_length=1, max_length=300)
    context: str = Field(default="", max_length=1500)
    intended_territory: list[str] = Field(default_factory=list, max_length=30)
    intended_media: list[str] = Field(default_factory=list, max_length=20)
    dependency_keys: list[str] = Field(default_factory=list, max_length=20)


class Change(StrictModel):
    stable_lineage_key: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    duration_or_prominence: str | None = Field(default=None, min_length=1, max_length=300)
    context: str | None = Field(default=None, max_length=1500)
    intended_territory: list[str] | None = Field(default=None, max_length=30)
    intended_media: list[str] | None = Field(default=None, max_length=20)
    dependency_keys: list[str] | None = Field(default=None, max_length=20)


class RevisionInput(StrictModel):
    production_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    parent_revision_id: str | None = None
    expected_parent_snapshot_id: str | None = None
    source_text: str | None = Field(default=None, min_length=20, max_length=24000)
    initial_uses: list[Use] = Field(default_factory=list, max_length=20)
    revised_uses: list[Change] = Field(default_factory=list, max_length=20)
    added_uses: list[Use] = Field(default_factory=list, max_length=20)
    removed_use_keys: list[str] = Field(default_factory=list, max_length=20)
    revalidate_keys: list[str] = Field(default_factory=list, max_length=20)
    max_spend_usd: float = Field(default=1, gt=0, le=5)
    agentic: bool = True

    @model_validator(mode="after")
    def validate_intake(self):
        if self.parent_revision_id:
            if not self.expected_parent_snapshot_id or self.initial_uses:
                raise ValueError("Revisions require the current snapshot ID.")
            if self.source_text and (self.revised_uses or self.added_uses or self.removed_use_keys):
                raise ValueError("Supply a complete document or structured changes, not both.")
        elif not (bool(self.source_text) ^ bool(self.initial_uses)):
            raise ValueError("Initial intake requires either source text or structured uses.")
        elif self.revised_uses or self.added_uses or self.removed_use_keys or self.revalidate_keys:
            raise ValueError("Changes require an existing revision.")
        return self


class DecisionInput(StrictModel):
    action: Literal["sign_off", "reject"]
    revision_id: str
    expected_snapshot_id: str
    rationale: str = Field(min_length=3, max_length=4000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=30)


class Assessment(StrictModel):
    summary: str = Field(max_length=3000)
    cited_ids: list[str] = Field(max_length=20)
    missing_facts: list[str] = Field(max_length=10)
    next_query: str | None = Field(default=None, max_length=300)


class ExtractedUses(StrictModel):
    uses: list[Use] = Field(min_length=1, max_length=20)


class ResearchPlan(StrictModel):
    objective: str = Field(max_length=1000)
    public_query: str = Field(min_length=3, max_length=300)
    private_facts_needed: list[str] = Field(max_length=10)
    stop_condition: str = Field(max_length=500)
    strategy: Literal["public_research", "review_documents", "request_information"] = "public_research"


class EvidenceReview(StrictModel):
    verdict: Literal["supported", "research", "needs_information"]
    explanation: str = Field(max_length=2000)
    cited_ids: list[str] = Field(max_length=20)
    missing_facts: list[str] = Field(max_length=10)
    next_query: str | None = Field(default=None, max_length=300)


class EvidenceChange(StrictModel):
    material: bool
    explanation: str = Field(max_length=2000)
    cited_ids: list[str] = Field(max_length=20)


class AgreementMatch(StrictModel):
    clarification_id: str | None = None
    explanation: str = Field(max_length=1500)
    supports_match: bool


class AutomationPolicy(StrictModel):
    enabled: bool = False
    per_run_usd: float = Field(default=1, gt=0, le=5)
    total_allowance_usd: float = Field(default=5, gt=0, le=100)
    evidence_interval_hours: int = Field(default=24, ge=1, le=168)
    watch_evidence: bool = False
    production_name: str = Field(default="Production workspace", min_length=1, max_length=120)


class SourceInput(StrictModel):
    kind: Literal["revision", "agreement", "evidence", "directive"]
    name: str = Field(min_length=1, max_length=200)
    text: str = Field(default="", max_length=24000)
    clarification_id: str | None = Field(default=None, pattern=r"^clarification_[a-f0-9]{24}$")
    claim_keys: list[str] = Field(default_factory=list, max_length=20)
    source_uri: str = Field(default="", max_length=1500)
