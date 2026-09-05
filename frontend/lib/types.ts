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
  REMOVED: 'removed',
  NEW: 'new',
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
  payload_hash?: string | null;
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
 * ContractAgreement models legal clearance contracts, option purchase agreements, or licenses.
 */
export interface ContractAgreement {
  agreement_id: string;
  stable_lineage_key: string;
  licensor: string;
  licensee: string;
  scope: string;
  term: string;
  agreement_hash: string;
  is_active: boolean;
  metadata?: Record<string, unknown>;
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
  explanation?: string | null;
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
 * Statutory carrier header for Form E&O-2026.
 */
export interface CarrierHeader {
  carrier_name: string;
  policy_number: string;
  broker_name: string;
  warranty_clause: string;
  underwriter_status: string;
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
  policy_number?: string;
  carrier_header?: CarrierHeader;
  production_metadata?: Record<string, unknown>;
  total_claims: number;
  carried_forward_count: number;
  reopened_count: number;
  re_attested_count: number;
  unresolved_exception_count: number;
  items: ExceptionsScheduleItem[];
  unresolved_exceptions_schedule?: ExceptionsScheduleItem[];
  unresolved_exceptions?: ExceptionsScheduleItem[];
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
  retrieval_latency_ms?: number | null;
  retrieved_at?: string | null;
  call_id: string | null;
  is_degraded?: boolean | null;
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

export interface PlannedRevalidationRequest {
  request_id: string;
  stable_lineage_key: string;
  decision_id: string;
  query: string;
  reason_code: string;
  asset_type?: string;
  priority?: string;
  expected_stance?: EvidenceStance | null;
  rationale?: string;
  target_use_id?: string | null;
}

export interface RevalidationPlan {
  plan_id: string;
  target_version_id: string;
  planned_requests: PlannedRevalidationRequest[];
  skipped_lineage_keys: string[];
  total_claims_evaluated: number;
  planned_count: number;
  skipped_count: number;
  api_call_budget_enforced: boolean;
}

export interface EvidenceReconciliationResult {
  stable_lineage_key: string;
  decision_id: string;
  raw_stance: EvidenceStance;
  reconciled_stance: EvidenceStance;
  has_contract: boolean;
  contract_shield_applied: boolean;
  contract_id?: string | null;
  decision_state: DecisionState;
  revalidation_action: string;
  reason_code: string;
  explanation: string;
  evidence_snapshot?: PublicEvidenceSnapshot | null;
  citations?: Array<Record<string, string>>;
}

export type WorkflowRunResult = DriftEvaluationResult;

// ============================================================================
// Usability & Comprehension Aids Types (Sprint 4C)
// ============================================================================

export interface DeterministicLineageParity {
  carried_claims_count: number;
  total_claims_count: number;
  review_cost_dollars: number;
  savings_percentage: string;
  bit_for_bit_unchanged: boolean;
  external_queries_issued: number;
  explanation: string;
  carried_claim_keys: string[];
}

export interface ActiveClearanceBlocker {
  key: string;
  item_number: number;
  asset_name: string;
  asset_type: string;
  scene: string;
  timecode: string;
  reason_code: string;
  shift_type: string;
  shift_summary: string;
  blocker_details: string;
  resolution_path: string;
  suggested_action: string;
}

export interface LifecycleStage {
  stage: number;
  name: string;
  description: string;
}

export interface ClearanceDecisionLifecycle {
  stages: LifecycleStage[];
  underwriter_warranty_export_path: string;
  json_export_path: string;
  export_format: string;
}

export interface ComprehensionAids {
  deterministic_lineage_parity: DeterministicLineageParity;
  active_clearance_blockers: ActiveClearanceBlocker[];
  clearance_decision_lifecycle: ClearanceDecisionLifecycle;
}

// ============================================================================
// API Response & Fixture Contracts
// ============================================================================

export interface V7ClaimFixture {
  use_id: string;
  key: string;
  scene: string;
  timecode?: string;
  asset_type: string;
  description: string;
  prominence: string;
  status: string;
  reason_code?: string;
}

export interface V8ClaimFixture {
  use_id: string;
  key: string;
  scene: string;
  timecode?: string;
  asset_type: string;
  description: string;
  prominence: string;
  reason_code: string;
}

export interface FixturesResponse {
  v7_version: ProductionVersion;
  v8_version: ProductionVersion;
  v7_claims: V7ClaimFixture[];
  v8_claims?: V8ClaimFixture[];
  v7_uses?: CreativeUse[];
  v8_uses?: CreativeUse[];
  v7_decisions?: CounselDecision[];
  v8_evidence?: Record<string, PublicEvidenceSnapshot>;
  comprehension_aids?: ComprehensionAids;
  active_clearance_blockers?: ActiveClearanceBlocker[];
  deterministic_lineage_parity?: DeterministicLineageParity;
  clearance_decision_lifecycle?: ClearanceDecisionLifecycle;
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

// ============================================================================
// Sprint 3A: Counsel Checkpoint & Audit Trail Domain Types
// ============================================================================

export const ReviewAction = {
  RE_ATTEST: 're_attest',
  REJECT: 'reject',
  EXCEPTION: 'exception',
} as const;

export type ReviewAction = (typeof ReviewAction)[keyof typeof ReviewAction];

export const ReviewActionType = ReviewAction;
export type ReviewActionType = ReviewAction;

export const ActorType = {
  HUMAN_COUNSEL: 'HUMAN_COUNSEL',
  AI_SYSTEM_RECOMMENDATION: 'AI_SYSTEM_RECOMMENDATION',
} as const;

export type ActorType = (typeof ActorType)[keyof typeof ActorType];

/**
 * ReviewerIdentity represents the reviewing clearance counsel.
 * Strictly flagged as demo/fictional counsel under competition guidelines.
 */
export interface ReviewerIdentity {
  reviewer_id: string;
  name: string;
  title: string;
  organization: string;
  is_fictional_demo: boolean;
  disclaimer: string;
  disclaimers?: string[];
  bar_number?: string | null;
}

export type DemoReviewer = ReviewerIdentity;

/**
 * Historical counsel decision record from a prior script revision (e.g. Cut v7).
 */
export interface PriorDecisionDetails {
  decision_id: string;
  version_id?: string;
  applicable_version_id?: string;
  status: DecisionStatus | string;
  rationale: string;
  reviewer_display_name: string;
  reviewed_at: string;
  context_hash?: string;
  scope_or_conditions?: string | null;
}

/**
 * Four-dimensional explanation breakdown for counsel review.
 */
export interface FourDimensionalExplanation {
  stable_lineage_key: string;
  decision_id: string;
  creative_change: string;
  evidence_change: string;
  private_fact: string;
  policy_reason: string;
  system_recommendation?: string;
  creative_change_summary?: string;
  loc_public_domain_search_excerpt?: string;
  contract_absence?: string;
  statutory_policy_reason?: string;
}

/**
 * Detailed four-dimensional legal reasoning breakdown for counsel adjudication.
 */
export interface CreativeChangeDimension {
  has_changed: boolean;
  materiality: 'none' | 'low' | 'medium' | 'high' | string;
  scene: string;
  before_prominence: string;
  after_prominence: string;
  before_context?: string;
  after_context?: string;
  context_description: string;
  dialogue_shift?: string;
  reason_codes: string[];
}

export interface ExternalEvidenceDimension {
  has_changed: boolean;
  stance: EvidenceStance | string;
  source_title: string;
  source_url: string;
  excerpt: string;
  query_issued: string;
  provider: string;
  retrieved_at?: string | null;
  provider_call_id?: string | null;
  retrieval_latency_ms?: number | null;
  payload_hash?: string | null;
  is_degraded?: boolean | null;
  degraded_reason?: string | null;
}

export interface PrivateAgreementDimension {
  has_contract: boolean;
  agreement_id?: string | null;
  licensor?: string | null;
  licensee?: string | null;
  grant_scope?: string | null;
  scope?: string | null;
  term?: string | null;
  term_in_perpetuity?: boolean;
  section_205_e_status: string;
  contract_shield_applied: boolean;
  status_note: string;
}

export interface StatutoryPolicyDimension {
  reason_code: string;
  policy_rule: string;
  statutory_reference: string;
  doctrine: string;
  eo_risk_rating: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | string;
  statutory_exposure: string;
  explanation: string;
}

export interface ExplanationFourDimensions {
  creative_change: CreativeChangeDimension;
  external_evidence_change: ExternalEvidenceDimension;
  private_agreement_facts: PrivateAgreementDimension;
  statutory_policy_reason: StatutoryPolicyDimension;
}

/**
 * System clearance recommendation generated for counsel review.
 */
export interface SystemRecommendation {
  suggested_action: ReviewAction | string;
  suggested_status: DecisionStatus | string;
  confidence: number;
  rationale: string;
  counsel_briefing?: ClearanceBriefing | null;
}

/**
 * ReviewQueueItem models an individual claim awaiting counsel review.
 */
export interface ReviewQueueItem {
  stable_lineage_key: string;
  asset_type: string;
  description?: string;
  scene_or_timecode?: string;
  current_state: DecisionState;
  prior_decision: PriorDecisionDetails | CounselDecision | any;
  four_dimensions: ExplanationFourDimensions;
  system_recommendation: SystemRecommendation | string;
  creative_change_summary?: string;
  evidence_change_summary?: string;
  private_fact_summary?: string;
  statutory_policy_reason?: string;
  available_actions?: ReviewAction[];
  queue_id?: string;
  queue_item_id?: string;
  asset_name?: string;
  scene?: string;
  prior_decision_id?: string;
  current_status?: DecisionStatus;
  explanation_4d?: FourDimensionalExplanation;
  status?: 'pending' | 'resolved' | string;
  target_version_id?: string;
  created_at?: string;
}

/**
 * Append-only immutable supersession audit record.
 */
export interface SupersessionEvent {
  event_id: string;
  stable_lineage_key: string;
  action: ReviewAction | 'REVALIDATE' | string;
  prior_decision_id: string;
  event_hash: string;
  timestamp: string;
  actor_type?: ActorType | string;
  reviewer?: ReviewerIdentity | any;
  reviewer_name?: string;
  reviewer_title?: string;
  is_fictional_demo_reviewer?: boolean;
  counsel_rationale?: string;
  rationale?: string;
  resulting_state?: DecisionState | string;
  resulting_status?: DecisionStatus | string;
  new_state?: DecisionState;
  new_status?: DecisionStatus;
  prior_state?: DecisionState;
  prior_status?: DecisionStatus;
  new_decision_id?: string;
  superseding_decision_id?: string;
  system_recommendation?: string;
  target_version_id?: string;
  changed_dependencies?: string[];
  evidence_citations?: Array<Record<string, string>>;
  parent_hash?: string | null;
  parent_event_hash?: string | null;
  prior_decision?: CounselDecision | PriorDecisionDetails | null;
  new_decision?: CounselDecision | null;
  statutory_notes?: string;
  four_dimensions_snapshot?: ExplanationFourDimensions | null;
  metadata?: Record<string, unknown>;
}

/**
 * Request payload for submitting a counsel review decision.
 */
export interface ReviewActionRequest {
  action: ReviewAction;
  stable_lineage_key?: string;
  lineage_key?: string;
  counsel_rationale?: string;
  rationale?: string;
  decision_id?: string;
  reviewer?: ReviewerIdentity | Record<string, unknown>;
  reviewer_name?: string;
  version_id?: string;
  target_version_id?: string;
}

/**
 * Review Queue API response wrapper.
 */
export interface ReviewQueueResponse {
  items: ReviewQueueItem[];
  queue?: ReviewQueueItem[];
  total_count?: number;
  total_stale_count?: number;
  total_pending?: number;
  total_resolved?: number;
  base_version?: string;
  target_version?: string;
  target_version_id?: string;
  comprehension_aids?: ComprehensionAids;
  active_clearance_blockers?: ActiveClearanceBlocker[];
  deterministic_lineage_parity?: DeterministicLineageParity;
  clearance_decision_lifecycle?: ClearanceDecisionLifecycle;
}

/**
 * Audit Trail API response wrapper.
 */
export interface AuditTrailResponse {
  events: SupersessionEvent[];
  total_events: number;
  is_ledger_tamper_free?: boolean;
  chain_head_hash?: string;
  integrity_details?: string;
  lineage_key?: string | null;
}


