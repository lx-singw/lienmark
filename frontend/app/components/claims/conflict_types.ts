/**
 * conflict_types.ts
 * TypeScript contracts for contradictory evidence comparison, field diffs,
 * authority tier evaluation, and counsel risk elevation.
 * Sprint 3.3: Contradictory Evidence & Conflict Arbitration UI.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript definitions.
 */

export const ConflictResolutionStance = {
  CONTRADICTORY: 'CONTRADICTORY',
  CORROBORATING: 'CORROBORATING',
  UNCERTAIN: 'UNCERTAIN',
} as const;

export type ConflictResolutionStance =
  (typeof ConflictResolutionStance)[keyof typeof ConflictResolutionStance];

export const AuthorityTier = {
  TIER_1_GOVERNMENT: 'TIER_1_GOVERNMENT',
  TIER_2_MEDIA_TRADE: 'TIER_2_MEDIA_TRADE',
  TIER_3_GENERAL_WEB: 'TIER_3_GENERAL_WEB',
} as const;

export type AuthorityTier = (typeof AuthorityTier)[keyof typeof AuthorityTier];

export interface EvidenceSourceRecord {
  readonly id: string;
  readonly name: string;
  readonly organization: string;
  readonly authorityTier: AuthorityTier;
  readonly rightsStatus: string;
  readonly claimedOwner: string;
  readonly licenseType: string;
  readonly term: string;
  readonly url?: string;
  readonly excerpt?: string;
  readonly retrievedAt?: string;
  readonly confidenceScore?: number;
}

export type ConflictFieldKey =
  | 'rightsStatus'
  | 'claimedOwner'
  | 'licenseType'
  | 'term'
  | 'authorityTier';

export type DiffSeverity = 'critical' | 'high' | 'medium' | 'info';

export interface ConflictFieldDiff {
  readonly fieldKey: ConflictFieldKey;
  readonly fieldLabel: string;
  readonly sourceAValue: string;
  readonly sourceBValue: string;
  readonly isConflicting: boolean;
  readonly severity: DiffSeverity;
  readonly statutoryNote?: string;
}

export interface ConflictEvidencePair {
  readonly id: string;
  readonly claimId: string;
  readonly assetName: string;
  readonly sceneTimecode: string;
  readonly stance: ConflictResolutionStance;
  readonly sourceA: EvidenceSourceRecord;
  readonly sourceB: EvidenceSourceRecord;
  readonly fieldDiffs: readonly ConflictFieldDiff[];
  readonly elevationReason: string;
  readonly counselActionRequired: string;
  readonly statutoryDoctrine?: string;
  readonly statutoryDamagesMaxUsd?: number;
  readonly detectedAt?: string;
}

export interface StanceBadgeStyle {
  readonly stance: ConflictResolutionStance;
  readonly label: string;
  readonly bg: string;
  readonly border: string;
  readonly text: string;
  readonly iconName: 'AlertOctagon' | 'CheckCircle2' | 'HelpCircle';
}

export interface AuthorityTierStyle {
  readonly tier: AuthorityTier;
  readonly label: string;
  readonly shortLabel: string;
  readonly bg: string;
  readonly border: string;
  readonly text: string;
  readonly iconName: 'ShieldCheck' | 'Building2' | 'Globe';
}
