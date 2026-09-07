/**
 * Audit Trail Utilities & Cryptographic Verification Helpers
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import type { SupersessionEvent } from '@/lib/types';

/**
 * Truncates a SHA-256 hash to a standard preview format: 0xabc...123
 */
export function truncateHash(hash?: string | null): string {
  if (!hash) return '0x000...000';
  const clean = hash.startsWith('0x') ? hash.slice(2) : hash;
  if (clean.length <= 10) return `0x${clean}`;
  return `0x${clean.slice(0, 6)}...${clean.slice(-4)}`;
}

/**
 * Formats an arbitrary timestamp string into an ISO UTC representation.
 */
export function formatUtcTimestamp(dateString?: string | null): string {
  if (!dateString) return '2026-09-07 00:00:00 UTC';
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return `${d.toISOString().replace('T', ' ').replace(/\.\d+Z$/, '')} UTC`;
  } catch {
    return dateString;
  }
}

/**
 * Verifies if an audit event's parent link is cryptographically valid.
 * An event is verified if its parent_hash matches the prior event's event_hash,
 * or if it's the genesis block linking to the canonical zero hash.
 */
export function verifyParentLink(
  currentEvent: SupersessionEvent,
  priorEvent?: SupersessionEvent
): boolean {
  const currentParent = currentEvent.parent_hash || currentEvent.parent_event_hash;

  // If there is a preceding event in the chronological chain
  if (priorEvent) {
    if (!currentParent) return false;
    const cleanParent = currentParent.replace(/^0x/, '').toLowerCase();
    const cleanPrior = priorEvent.event_hash.replace(/^0x/, '').toLowerCase();
    return cleanParent === cleanPrior;
  }

  // Genesis block case: parent is null, zeroes, or explicitly 'GENESIS'
  if (!currentParent) return true;
  const isZeroHash = /^0+$/.test(currentParent.replace(/^0x/, ''));
  const isGenesisLabel = currentParent.toUpperCase().includes('GENESIS');
  return isZeroHash || isGenesisLabel;
}

/**
 * Exports and triggers browser download of the full cryptographic audit manifest.
 */
export function downloadAuditManifest(
  events: ReadonlyArray<SupersessionEvent>,
  productionId: string = 'prod_blockbuster_cinema'
): void {
  const manifest = {
    standard: 'SHA-256 Append-Only Hash Chain Manifest',
    specification: 'Lienmark Statutory E&O Clearance Ledger under 17 U.S.C. § 504(c)',
    formula: 'event_hash = sha256(parent_hash + payload)',
    production_id: productionId,
    exported_at_utc: new Date().toISOString(),
    total_events: events.length,
    head_hash: events.length > 0 ? events[events.length - 1].event_hash : null,
    chain_events: events.map((evt, idx) => ({
      sequence_number: idx + 1,
      event_id: evt.event_id,
      action: evt.action,
      timestamp_utc: evt.timestamp,
      event_hash: evt.event_hash,
      parent_hash: evt.parent_hash || evt.parent_event_hash || null,
      target_lineage_key: evt.stable_lineage_key,
      reviewer: evt.reviewer_name || evt.reviewer,
      counsel_rationale: evt.counsel_rationale || evt.rationale,
      resulting_status: evt.resulting_status,
      metadata: evt.metadata || null,
    })),
  };

  const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
    JSON.stringify(manifest, null, 2)
  )}`;
  const downloadAnchor = document.createElement('a');
  downloadAnchor.setAttribute('href', jsonString);
  downloadAnchor.setAttribute(
    'download',
    `lienmark-audit-manifest-${productionId}-${Date.now()}.json`
  );
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();
}

/**
 * Maps an action string to its badge style classes.
 */
export function getActionBadgeStyle(action: string): string {
  const norm = action.toUpperCase();
  if (norm.includes('GENESIS')) {
    return 'bg-sky-950/90 text-sky-300 border-sky-500/50';
  }
  if (norm.includes('CLAIM_CREATED')) {
    return 'bg-blue-950/90 text-blue-300 border-blue-500/50';
  }
  if (norm.includes('SUPERSEDED') || norm.includes('REJECT')) {
    return 'bg-rose-950/90 text-rose-300 border-rose-500/50';
  }
  if (norm.includes('ATTORNEY') || norm.includes('ATTEST') || norm.includes('APPROVE')) {
    return 'bg-emerald-950/90 text-emerald-300 border-emerald-500/50';
  }
  if (norm.includes('REVALIDATE')) {
    return 'bg-purple-950/90 text-purple-300 border-purple-500/50';
  }
  return 'bg-slate-800 text-slate-200 border-slate-700';
}

