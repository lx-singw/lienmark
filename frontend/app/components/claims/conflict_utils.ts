/**
 * conflict_utils.ts
 * Formatters, stance styling palettes, and diff computation helpers.
 * Sprint 3.3: Contradictory Evidence & Conflict Arbitration UI.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import {
  AuthorityTier,
  type AuthorityTierStyle,
  type ConflictFieldDiff,
  type ConflictFieldKey,
  ConflictResolutionStance,
  type DiffSeverity,
  type EvidenceSourceRecord,
  type StanceBadgeStyle,
} from './conflict_types';

export function getStanceBadgeStyle(stance: ConflictResolutionStance): StanceBadgeStyle {
  switch (stance) {
    case ConflictResolutionStance.CONTRADICTORY:
      return {
        stance,
        label: 'CONTRADICTORY',
        bg: 'bg-rose-950/90',
        border: 'border-rose-500/80',
        text: 'text-rose-200',
        iconName: 'AlertOctagon',
      };
    case ConflictResolutionStance.CORROBORATING:
      return {
        stance,
        label: 'CORROBORATING',
        bg: 'bg-emerald-950/90',
        border: 'border-emerald-500/80',
        text: 'text-emerald-200',
        iconName: 'CheckCircle2',
      };
    case ConflictResolutionStance.UNCERTAIN:
    default:
      return {
        stance: ConflictResolutionStance.UNCERTAIN,
        label: 'UNCERTAIN',
        bg: 'bg-slate-800/90',
        border: 'border-slate-600',
        text: 'text-slate-200',
        iconName: 'HelpCircle',
      };
  }
}

export function getAuthorityTierStyle(tier: AuthorityTier): AuthorityTierStyle {
  switch (tier) {
    case AuthorityTier.TIER_1_GOVERNMENT:
      return {
        tier,
        label: 'Tier 1: Government / Official Public Registry',
        shortLabel: 'Tier 1 Government',
        bg: 'bg-amber-950/70',
        border: 'border-amber-500/70',
        text: 'text-amber-300',
        iconName: 'ShieldCheck',
      };
    case AuthorityTier.TIER_2_MEDIA_TRADE:
      return {
        tier,
        label: 'Tier 2: Media / Trade Rights Registry',
        shortLabel: 'Tier 2 Media/Trade',
        bg: 'bg-sky-950/70',
        border: 'border-sky-500/70',
        text: 'text-sky-300',
        iconName: 'Building2',
      };
    case AuthorityTier.TIER_3_GENERAL_WEB:
    default:
      return {
        tier: AuthorityTier.TIER_3_GENERAL_WEB,
        label: 'Tier 3: General Web Source',
        shortLabel: 'Tier 3 Web',
        bg: 'bg-slate-800/80',
        border: 'border-slate-700',
        text: 'text-slate-300',
        iconName: 'Globe',
      };
  }
}

export function getSeverityBadgeStyle(severity: DiffSeverity): {
  bg: string;
  text: string;
  border: string;
} {
  switch (severity) {
    case 'critical':
      return { bg: 'bg-rose-950/90', text: 'text-rose-300', border: 'border-rose-600/80' };
    case 'high':
      return { bg: 'bg-amber-950/90', text: 'text-amber-300', border: 'border-amber-600/80' };
    case 'medium':
      return { bg: 'bg-yellow-950/80', text: 'text-yellow-200', border: 'border-yellow-600/60' };
    case 'info':
    default:
      return { bg: 'bg-slate-800/80', text: 'text-slate-300', border: 'border-slate-700' };
  }
}

export function detectFieldConflict(valA: string, valB: string): boolean {
  const normA = valA.trim().toLowerCase();
  const normB = valB.trim().toLowerCase();
  if (!normA || !normB) return true;
  return normA !== normB;
}

function buildFieldDiff(
  fieldKey: ConflictFieldKey,
  fieldLabel: string,
  sourceAVal: string,
  sourceBVal: string,
  defaultSeverity: DiffSeverity,
  statutoryNote?: string
): ConflictFieldDiff {
  const isConflicting = detectFieldConflict(sourceAVal, sourceBVal);
  return {
    fieldKey,
    fieldLabel,
    sourceAValue: sourceAVal,
    sourceBValue: sourceBVal,
    isConflicting,
    severity: isConflicting ? defaultSeverity : 'info',
    statutoryNote,
  };
}

interface FieldSpec {
  readonly key: ConflictFieldKey;
  readonly label: string;
  readonly getA: (s: EvidenceSourceRecord) => string;
  readonly getB: (s: EvidenceSourceRecord) => string;
  readonly severity: DiffSeverity;
  readonly note: string;
}

const FIELD_SPECS: readonly FieldSpec[] = [
  {
    key: 'rightsStatus',
    label: 'Rights Status',
    getA: (s) => s.rightsStatus,
    getB: (s) => s.rightsStatus,
    severity: 'critical',
    note: 'Conflict between statutory public domain status and claimed commercial master rights.',
  },
  {
    key: 'claimedOwner',
    label: 'Claimed Owner',
    getA: (s) => s.claimedOwner,
    getB: (s) => s.claimedOwner,
    severity: 'critical',
    note: 'Competing legal entities claiming exclusive ownership rights over identical material.',
  },
  {
    key: 'licenseType',
    label: 'License Type',
    getA: (s) => s.licenseType,
    getB: (s) => s.licenseType,
    severity: 'high',
    note: 'Incompatible licensing models: open public domain grant vs. proprietary commercial broadcast sync.',
  },
  {
    key: 'term',
    label: 'Term',
    getA: (s) => s.term,
    getB: (s) => s.term,
    severity: 'medium',
    note: 'Discrepancy between perpetual non-expiring status and active commercial license window.',
  },
  {
    key: 'authorityTier',
    label: 'Authority Tier',
    getA: (s) => getAuthorityTierStyle(s.authorityTier).shortLabel,
    getB: (s) => getAuthorityTierStyle(s.authorityTier).shortLabel,
    severity: 'info',
    note: 'Tier 1 government registry evidence carries statutory presumption over Tier 2 commercial registry.',
  },
];

export function computeFieldDiffs(
  sourceA: EvidenceSourceRecord,
  sourceB: EvidenceSourceRecord
): ConflictFieldDiff[] {
  return FIELD_SPECS.map((spec) =>
    buildFieldDiff(
      spec.key,
      spec.label,
      spec.getA(sourceA),
      spec.getB(sourceB),
      spec.severity,
      spec.note
    )
  );
}

export function formatDamages(amount?: number): string {
  if (amount === undefined || amount === null) return 'Statutory Exposure Pending';
  return `$${amount.toLocaleString()} Statutory Damages Exposure (17 U.S.C. § 504(c))`;
}
