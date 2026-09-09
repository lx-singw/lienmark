import { readableLabel } from './labels';

export type ClaimStatus = 'preserved' | 'reopened' | 'exception' | 'reviewed' | 'removed' | 'new';
export interface WorkspaceClaim {
  id: string; decisionId?: string; title: string; category: string; scene: string; status: ClaimStatus;
  evidenceIds?: string[];
  sources?: { id: string; title: string; url: string; excerpt: string; provider: string; retrievedAt?: string }[];
  reason: string; nextAction: string; owner: string; before: string; after: string;
  evidence?: { title: string; url: string; excerpt: string; provider: string; retrievedAt?: string };
}
export interface WorkspaceUser {
  display_name: string; email: string; role: string; tenant_id: string; production_id: string;
  production_name?: string; organization_name?: string;
}
export interface ActiveAudit {
  id: string; revisionId: string; statusUrl: string; status: string;
  snapshotId?: string; result?: Record<string, unknown>; error?: string;
  progress?: Record<string, unknown>;
}
export const statusLabels: Record<ClaimStatus, string> = {
  preserved: 'Preserved', reopened: 'Reopened', exception: 'Exception',
  reviewed: 'Re-attested', removed: 'Removed', new: 'New use',
};
const states: Record<string, ClaimStatus> = {
  carried_forward: 'preserved', stale: 'reopened', exception: 'exception',
  re_attested: 'reviewed', removed: 'removed', new: 'new',
};
export function normalizeClaim(value: unknown): WorkspaceClaim {
  const claim = record(value);
  const citation = Array.isArray(claim.evidence_citations) ? record(claim.evidence_citations[0]) : {};
  const evidence = Object.keys(record(claim.evidence)).length ? record(claim.evidence) : citation;
  const text = (field: string, fallback: string) => typeof claim[field] === 'string' ? String(claim[field]) : fallback;
  if (!text('stable_lineage_key', '')) throw new Error('A clearance record is missing its asset identifier.');
  return {
    id: text('stable_lineage_key', ''), decisionId: text('claim_id', '') || undefined,
    evidenceIds: Array.isArray(claim.evidence_citations) ? claim.evidence_citations.map(e => String(record(e).evidence_id || '')).filter(Boolean) : [],
    sources: Array.isArray(claim.evidence_citations) ? claim.evidence_citations.map(e => { const source = record(e); return {
      id: String(source.evidence_id || ''), title: String(source.title || source.source_title || 'Supporting source'),
      url: String(source.url || source.source_url || ''), excerpt: String(source.excerpt || ''),
      provider: String(source.provider || 'Recorded source'), retrievedAt: typeof source.retrieved_at === 'string' ? source.retrieved_at : undefined,
    }; }) : [],
    title: text('description', 'Untitled asset'), category: readableLabel(claim.asset_type, 'Uncategorized'),
    scene: text('scene', 'Occurrence not supplied'), status: states[text('state', '')] || 'new',
    reason: text('reason_code', text('counsel_action', 'Inspect the recorded decision and supporting evidence.')).replace(/_/g, ' '),
    nextAction: text('revalidation_action', Array.isArray(record(claim.investigation).missing_facts) ? (record(claim.investigation).missing_facts as string[]).join('; ') || 'Review the supporting evidence.' : 'Review the supporting evidence.'),
    owner: 'Unassigned', before: text('before', 'Refer to the recorded baseline decision.'),
    after: text('prominence', 'Refer to current revision facts.'),
    evidence: Object.keys(evidence).length ? {
      title: String(evidence.source_title || evidence.title || 'Supporting source'), url: String(evidence.source_url || evidence.url || ''),
      excerpt: String(evidence.excerpt || ''), provider: String(evidence.provider || 'Recorded source'),
      retrievedAt: typeof evidence.retrieved_at === 'string' ? evidence.retrieved_at : undefined,
    } : undefined,
  };
}
export function countClaims(claims: WorkspaceClaim[]) {
  return {
    total: claims.length,
    preserved: claims.filter(c => c.status === 'preserved').length,
    reopened: claims.filter(c => c.status === 'reopened' || c.status === 'new').length,
    exceptions: claims.filter(c => c.status === 'exception').length,
    reviewed: claims.filter(c => c.status === 'reviewed').length,
  };
}
export function record(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown> : {};
}
export function safeUrl(value: string): string | undefined {
  if (/^\/api\/clearance\/productions\/[A-Za-z0-9_-]+\/documents\/[a-f0-9]{64}$/.test(value)) return value;
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined; }
  catch { return undefined; }
}
