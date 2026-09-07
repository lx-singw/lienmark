/**
 * types.ts
 * TypeScript contracts for clearance research, search execution, query plans,
 * search findings, domain authority tiers, and citation badges.
 * Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript definitions.
 */

// ============================================================================
// Domain Authority Tiers
// ============================================================================

export const DomainAuthorityTier = {
  TIER_1_GOVERNMENT: 'tier_1_government',
  TIER_2_RIGHTS_ORG: 'tier_2_rights_org',
  TIER_3_WEB: 'tier_3_web',
} as const;

export type DomainAuthorityTier =
  (typeof DomainAuthorityTier)[keyof typeof DomainAuthorityTier];

// ============================================================================
// Citation & Badge Styling Models
// ============================================================================

export interface AuthorityBadgeStyle {
  readonly tier: DomainAuthorityTier;
  readonly label: string;
  readonly shortLabel: string;
  readonly bg: string;
  readonly text: string;
  readonly border: string;
  readonly iconName: 'ShieldCheck' | 'Building2' | 'Globe';
}

export interface LatencyBadgeStyle {
  readonly bg: string;
  readonly text: string;
  readonly border: string;
  readonly label: string;
}

export interface HttpStatusBadgeStyle {
  readonly bg: string;
  readonly text: string;
  readonly border: string;
  readonly label: string;
}

// ============================================================================
// Search Findings & Evidence
// ============================================================================

export interface SearchFinding {
  readonly id: string;
  readonly source_url: string;
  readonly source_title: string;
  readonly source_snippet: string;
  readonly domain_authority_tier: DomainAuthorityTier;
  readonly retrieval_timestamp_utc: string;
  readonly query_string: string;
  readonly cached?: boolean;
  readonly score?: number;
  readonly metadata?: Readonly<Record<string, string | number | boolean | null>>;
}

// ============================================================================
// Query Syntax Highlighting Tokens
// ============================================================================

export const QueryTokenType = {
  SITE: 'site',
  NEGATIVE: 'negative',
  QUOTE: 'quote',
  OPERATOR: 'operator',
  TERM: 'term',
} as const;

export type QueryTokenType =
  (typeof QueryTokenType)[keyof typeof QueryTokenType];

export interface QueryToken {
  readonly type: QueryTokenType;
  readonly value: string;
  readonly raw: string;
}

// ============================================================================
// Query Plans & Execution Telemetry
// ============================================================================

export const SearchMode = {
  STANDARD: 'standard',
  INVERSE_STEERING: 'inverse_steering',
  FALLBACK: 'fallback',
  MOCK: 'mock',
} as const;

export type SearchMode = (typeof SearchMode)[keyof typeof SearchMode];

export const StepExecutionStatus = {
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  SKIPPED: 'skipped',
} as const;

export type StepExecutionStatus =
  (typeof StepExecutionStatus)[keyof typeof StepExecutionStatus];

export interface QueryPlanStep {
  readonly step_id: string;
  readonly query_string: string;
  readonly target_registry?: string;
  readonly is_inverse_fallback: boolean;
  readonly status: StepExecutionStatus;
  readonly latency_ms?: number;
  readonly http_status?: number;
  readonly result_count?: number;
  readonly error_message?: string;
}

export interface QueryPlan {
  readonly plan_id: string;
  readonly asset_id: string;
  readonly claim_type: 'music' | 'trademark' | 'artwork' | 'likeness' | 'general';
  readonly steps: ReadonlyArray<QueryPlanStep>;
  readonly total_latency_ms: number;
  readonly created_at: string;
}

export interface SearchExecutionTelemetry {
  readonly query_string: string;
  readonly latency_ms: number;
  readonly http_status: number;
  readonly result_count: number;
  readonly is_inverse_steering: boolean;
  readonly inverse_reason?: string;
  readonly timestamp_utc: string;
  readonly endpoint_url?: string;
  readonly cache_hit?: boolean;
  readonly search_mode?: SearchMode;
}
