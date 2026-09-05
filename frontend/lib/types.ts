/**
 * Lienmark Canonical Domain Models & Types
 * Mirroring backend/domain/models.py and Agentic Cinema clearance workflows.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript definitions.
 */

// ============================================================================
// Enums and Discriminators
// ============================================================================

export const ChangeKind = {
  ADDED: 'added',
  MATERIALLY_MODIFIED: 'materially_modified',
  REMOVED: 'removed',
  UNCHANGED: 'unchanged',
  UNCERTAIN: 'uncertain',
} as const;

export type ChangeKind = (typeof ChangeKind)[keyof typeof ChangeKind];

export const DecisionState = {
  CARRIED_FORWARD: 'carried_forward',
  STALE: 'stale',
  RE_ATTESTED: 're_attested',
  EXCEPTION: 'exception',
} as const;

export type DecisionState = (typeof DecisionState)[keyof typeof DecisionState];

export const DecisionStatus = {
  APPROVED: 'approved',
  APPROVED_WITH_CONDITION: 'approved_with_condition',
  REJECTED: 'rejected',
  NEEDS_REVIEW: 'needs_review',
} as const;

export type DecisionStatus = (typeof DecisionStatus)[keyof typeof DecisionStatus];

export const EvidenceStance = {
  SUPPORTING: 'supporting',
  INFORMATIONAL: 'informational',
  CONTRADICTORY: 'contradictory',
  INSUFFICIENT: 'insufficient',
} as const;

export type EvidenceStance = (typeof EvidenceStance)[keyof typeof EvidenceStance];

// ============================================================================
// Core Domain Entities
// ============================================================================

/**
 * ProductionVersion represents an immutable script revision or cut snapshot.
 */
export interface ProductionVersion {
  version_id: string;
  project_id: string;
  label: string;
  created_at: string;
  content_hash: string;
  parent_version_id: string | null;
  source_type: string;
}

/**
 * CreativeUse captures a single rights-bearing asset instance within a production version.
 */
export interface CreativeUse {
  use_id: string;
  version_id: string;
  scene_or_timecode: string;
  asset_type: string;
  description: string;
  duration_or_prominence: string;
  context: string;
  stable_lineage_key: string;
  source_span?: string | null;
  context_hash: string;
}

/**
 * CreativeDelta captures the detected differential between creative uses across versions.
 */
export interface CreativeDelta {
  delta_id: string;
  before_use_id: string | null;
  after_use_id: string | null;
  stable_lineage_key: string;
  change_kind: ChangeKind;
  materiality: 'none' | 'low' | 'high' | string;
  match_confidence: number;
  changed_fields: string[];
  reason_codes: string[];
}

/**
 * PublicEvidenceSnapshot records external search/registry corroboration (e.g., from Parallel Search API).
 */
export interface PublicEvidenceSnapshot {
  snapshot_id: string;
  use_id: string;
  stable_lineage_key: string;
  query: string;
  retrieved_at: string;
  provider: string;
  source_url: string;
  source_title: string;
  excerpt: string;
  publisher?: string | null;
  stance: EvidenceStance;
  cached_or_live: 'cached' | 'live' | string;
  provider_call_id?: string | null;
  retrieval_latency_ms?: number | null;
}

/**
 * CounselDecision represents human clearance counsel attestation and legal determinations.
 */
export interface CounselDecision {
  decision_id: string;
  use_id: string;
  stable_lineage_key: string;
  applicable_version_id: string;
  status: DecisionStatus;
  rationale: string;
  reviewer_display_name: string;
  reviewed_at: string;
  supersedes_decision_id?: string | null;
  dependency_ids: string[];
  system_recommendation?: string | null;
  human_confirmed: boolean;
}

/**
 * DecisionValidity captures the deterministic evaluation of a prior counsel decision
 * against subsequent version deltas and external evidence.
 */
export interface DecisionValidity {
  decision_id: string;
  evaluated_for_version_id: string;
  stable_lineage_key: string;
  state: DecisionState;
  reason_code: string;
  changed_dependency_ids: string[];
  revalidation_action: 'carry' | 'revalidate' | 'close' | 'manual' | string;
  evidence_snapshot?: PublicEvidenceSnapshot | null;
  creative_delta?: CreativeDelta | null;
}

/**
 * ReattestationRequest models clearance counsel re-affirmation or exception designation.
 */
export interface ReattestationRequest {
  decision_id: string;
  stable_lineage_key: string;
  version_id: string;
  new_status: DecisionStatus;
  counsel_rationale: string;
  reviewer_name: string;
}

/**
 * Citations supporting an item on the underwriter exceptions schedule.
 */
export interface EvidenceCitation {
  source_title: string;
  source_url: string;
  excerpt: string;
  provider: string;
  [key: string]: string;
}

/**
 * Individual line item on the underwriter Exceptions Schedule.
 */
export interface ExceptionsScheduleItem {
  stable_lineage_key: string;
  asset_type: string;
  description: string;
  scene_or_timecode: string;
  v7_decision_status: string;
  v8_evaluation_state: DecisionState | string;
  invalidation_reason?: string | null;
  counsel_action: string;
  evidence_citations: EvidenceCitation[];
}

/**
 * Version-bound Form E&O Exceptions Schedule generated for underwriter review.
 */
export interface ExceptionsSchedule {
  schedule_id: string;
  project_id: string;
  project_name: string;
  target_version_id: string;
  base_version_id: string;
  generated_at: string;
  policy_version: string;
  total_claims: number;
  carried_forward_count: number;
  reopened_count: number;
  re_attested_count: number;
  unresolved_exception_count: number;
  items: ExceptionsScheduleItem[];
}

// ============================================================================
// Workflow, Drift Evaluation & Telemetry Types
// ============================================================================

export interface ClaimEvidence {
  provider: string;
  source_title: string;
  source_url: string;
  excerpt: string;
  stance: EvidenceStance;
  latency_ms: number | null;
  call_id: string | null;
}

export interface EvaluatedClaim {
  stable_lineage_key: string;
  asset_type: string;
  description: string;
  scene: string;
  prominence: string;
  state: DecisionState;
  reason_code: string;
  revalidation_action: string;
  evidence: ClaimEvidence | null;
}

export interface ClearanceBriefing {
  claim_id: string;
  asset_name: string;
  counsel_summary: string;
  parallel_evidence_stance: string;
  suggested_counsel_action: string;
  confidence: number;
}

export interface WorkflowStepTrace {
  step_name: string;
  component: string;
  status: string;
  duration_ms: number;
  details: Record<string, unknown>;
}

/**
 * DriftEvaluationResult represents the comprehensive output of the clearance drift comparison workflow.
 * Conforms to WorkflowRunResult in backend/orchestration/workflow.py.
 */
export interface DriftEvaluationResult {
  run_id: string;
  base_version: string;
  target_version: string;
  total_claims: number;
  carried_forward_count: number;
  reopened_count: number;
  claims: EvaluatedClaim[];
  counsel_briefings: Record<string, ClearanceBriefing>;
  execution_traces: WorkflowStepTrace[];
  total_duration_ms: number;
}

export type WorkflowRunResult = DriftEvaluationResult;

// ============================================================================
// API Response & Fixture Contracts
// ============================================================================

export interface V7ClaimFixture {
  use_id: string;
  key: string;
  scene: string;
  asset_type: string;
  description: string;
  prominence: string;
  status: string;
}

export interface FixturesResponse {
  v7_version: ProductionVersion;
  v8_version: ProductionVersion;
  v7_claims: V7ClaimFixture[];
  v7_uses?: CreativeUse[];
  v8_uses?: CreativeUse[];
  v7_decisions?: CounselDecision[];
  v8_evidence?: Record<string, PublicEvidenceSnapshot>;
}

export interface ReattestationResponse {
  status: string;
  stable_lineage_key: string;
  new_status: string;
  rationale: string;
}

export interface HealthCheckResponse {
  status: string;
  service: string;
  provenance: string;
  track: string;
  integrations: {
    gemini: string;
    parallel_search: string;
    agent_platform: string;
  };
  policy_version: string;
}

export type HealthResponse = HealthCheckResponse;
