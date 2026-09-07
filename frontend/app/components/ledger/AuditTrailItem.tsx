'use client';

/**
 * AuditTrailItem Component
 * Renders a single cryptographic audit event in the append-only ledger.
 * Features sequence numbering, action badge, UTC timestamp, truncated hashes with copy,
 * parent link verification status, and expandable payload JSON viewer.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useMemo } from 'react';
import {
  CheckCircle2,
  ShieldAlert,
  Copy,
  Check,
  Sparkles,
  Gavel,
  Link as LinkIcon,
} from 'lucide-react';
import { SupersessionEvent, ActorType } from '@/lib/types';
import { truncateHash, formatUtcTimestamp, getActionBadgeStyle } from './audit_utils';
import { PayloadViewer } from './PayloadViewer';

export interface AuditTrailItemProps {
  event: SupersessionEvent;
  sequenceNumber: number;
  isLinkVerified: boolean;
  copiedHash: string | null;
  onCopyHash: (hash: string) => void;
}

export const AuditTrailItem: React.FC<AuditTrailItemProps> = ({
  event,
  sequenceNumber,
  isLinkVerified,
  copiedHash,
  onCopyHash,
}) => {


  const isAI =
    event.actor_type === ActorType.AI_SYSTEM_RECOMMENDATION ||
    event.action === 'REVALIDATE';

  const reviewerName =
    event.reviewer_name ||
    (typeof event.reviewer === 'object' && event.reviewer !== null ? event.reviewer.name : null) ||
    (typeof event.reviewer === 'string' ? event.reviewer : 'Sarah Jenkins, Esq.');

  const parentHashValue =
    event.parent_hash ||
    event.parent_event_hash ||
    '0000000000000000000000000000000000000000000000000000000000000000 (GENESIS)';

  const formattedPayload = useMemo(() => {
    return JSON.stringify(event, null, 2);
  }, [event]);

  return (
    <div
      className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 space-y-3 transition-all hover:border-slate-700 shadow-md"
      role="article"
      aria-label={`Audit event sequence #${sequenceNumber}`}
    >
      {/* Top Bar: Sequence Number, Action Badge, and Link Status Icon */}
      <div className="flex items-center justify-between gap-2 border-b border-slate-800/70 pb-2.5">
        <div className="flex items-center gap-2">
          {/* Sequence Number */}
          <span className="inline-flex items-center justify-center px-2 py-0.5 rounded-md bg-slate-800 border border-slate-700 text-xs font-mono font-bold text-sky-400">
            #{sequenceNumber}
          </span>

          {/* Action Type Badge */}
          <span
            className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold uppercase tracking-wider border ${getActionBadgeStyle(
              event.action
            )}`}
          >
            {event.action}
          </span>
        </div>

        {/* Link Status Badge with Green Check or Red Shield */}
        <div className="flex items-center gap-1.5">
          {isLinkVerified ? (
            <span
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-500/40 text-[10px] font-mono font-semibold"
              title="Parent link cryptographic hash verified"
            >
              <CheckCircle2 className="h-3 w-3 text-emerald-400" aria-hidden="true" />
              <span>LINK VERIFIED</span>
            </span>
          ) : (
            <span
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-950/80 text-rose-400 border border-rose-500/40 text-[10px] font-mono font-semibold"
              title="Cryptographic chain break detected: parent hash does not match prior block"
            >
              <ShieldAlert className="h-3 w-3 text-rose-400" aria-hidden="true" />
              <span>LINK BROKEN</span>
            </span>
          )}
        </div>
      </div>

      {/* Metadata Row: Actor, Lineage Key, Timestamp */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-1.5 text-slate-300">
          {isAI ? (
            <Sparkles className="h-3.5 w-3.5 text-purple-400" aria-hidden="true" />
          ) : (
            <Gavel className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
          )}
          <span className="font-semibold text-white">{reviewerName}</span>
          <span className="text-slate-400 font-mono text-[10px]">
            ({isAI ? 'Automated Engine' : 'Clearance Counsel'})
          </span>
        </div>

        <div className="text-[11px] font-mono text-slate-400">
          {formatUtcTimestamp(event.timestamp)}
        </div>
      </div>

      {/* Stable Lineage Key & Rationale Preview */}
      <div className="space-y-1">
        <div className="text-[11px] text-slate-400 font-mono">
          Asset Lineage:{' '}
          <span className="text-sky-300 font-bold">{event.stable_lineage_key}</span>
        </div>
        {(event.counsel_rationale || event.rationale) && (
          <p className="text-xs text-slate-300 italic bg-slate-950/60 p-2 rounded-lg border border-slate-850 line-clamp-2">
            &ldquo;{event.counsel_rationale || event.rationale}&rdquo;
          </p>
        )}
      </div>

      {/* Cryptographic SHA-256 Hash Card with Truncated Previews & Click-to-Copy */}
      <div className="rounded-lg bg-slate-950/90 p-2.5 border border-slate-800 text-[11px] font-mono space-y-1.5">
        {/* Event Hash */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1 text-slate-400 truncate">
            <span className="text-slate-400">Event Hash:</span>
            <span className="text-sky-300 font-bold" title={event.event_hash}>
              {truncateHash(event.event_hash)}
            </span>
          </div>
          <button
            type="button"
            onClick={() => onCopyHash(event.event_hash)}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors flex-shrink-0"
            title="Copy Event Hash"
            aria-label={`Copy Event Hash for sequence #${sequenceNumber}`}
          >
            {copiedHash === event.event_hash ? (
              <Check className="h-3.5 w-3.5 text-emerald-400" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
          </button>
        </div>

        {/* Parent Hash */}
        <div className="flex items-center justify-between gap-2 border-t border-slate-900 pt-1">
          <div className="flex items-center gap-1 text-slate-400 truncate">
            <span className="text-slate-400">Parent Hash:</span>
            <span className="text-slate-300" title={parentHashValue}>
              {truncateHash(parentHashValue)}
            </span>
          </div>
          <button
            type="button"
            onClick={() => onCopyHash(parentHashValue)}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors flex-shrink-0"
            title="Copy Parent Hash"
            aria-label={`Copy Parent Hash for sequence #${sequenceNumber}`}
          >
            {copiedHash === parentHashValue ? (
              <Check className="h-3.5 w-3.5 text-emerald-400" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* Expandable Payload JSON Viewer */}
      <PayloadViewer
        payload={formattedPayload}
        copiedHash={copiedHash}
        onCopy={onCopyHash}
      />
    </div>
  );
};

export default AuditTrailItem;
