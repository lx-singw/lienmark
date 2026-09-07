/**
 * Frontend Types for Evidence Explorer
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

export type EvidenceSourceType =
  | 'public_search'
  | 'archived_snapshot'
  | 'private_contract'
  | 'document_record';

export type EvidenceConfidenceTier =
  | 'primary_statutory'
  | 'secondary_registry'
  | 'tertiary_web'
  | 'private_legal';

export interface EvidenceItem {
  readonly evidence_id: string;
  readonly source_type: EvidenceSourceType;
  readonly title: string;
  readonly source_url?: string | null;
  readonly domain?: string | null;
  readonly snippet: string;
  readonly retrieved_at: string;
  readonly confidence_tier: string;
  readonly stance: string;
  readonly asset_category: string;
  readonly http_status?: number | null;
  readonly liveness_status: string;
  readonly payload_digest: string;
  readonly linked_claims: ReadonlyArray<string>;
  readonly metadata: Record<string, unknown>;
}

export interface EvidenceFacets {
  readonly domains: Record<string, number>;
  readonly source_types: Record<string, number>;
  readonly stances: Record<string, number>;
  readonly tiers: Record<string, number>;
  readonly asset_categories: Record<string, number>;
}

export interface EvidenceSearchResponse {
  readonly items: ReadonlyArray<EvidenceItem>;
  readonly total_count: number;
  readonly page: number;
  readonly page_size: number;
  readonly facets: EvidenceFacets;
}

export interface EvidenceDetailResponse {
  readonly item: EvidenceItem;
  readonly raw_headers: Record<string, string>;
  readonly storage_path?: string | null;
  readonly linked_claims: ReadonlyArray<string>;
  readonly is_verified: boolean;
  readonly sha256_verified: boolean;
}

export interface EvidenceCompareResponse {
  readonly claim_id: string;
  readonly claim_title: string;
  readonly public_findings: ReadonlyArray<EvidenceItem>;
  readonly private_contract_clauses: ReadonlyArray<Record<string, unknown>>;
  readonly concordance_status: 'SHIELDED' | 'CONFLICT' | 'UNSHIELDED' | string;
  readonly legal_shield_active: boolean;
  readonly analysis: string;
}

export interface EvidenceFilterState {
  readonly query: string;
  readonly sourceType: string;
  readonly domain: string;
  readonly stance: string;
  readonly tier: string;
  readonly category: string;
}
