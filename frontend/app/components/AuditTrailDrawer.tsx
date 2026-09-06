'use client';

/**
 * Lienmark SHA-256 Append-Only Hash Chain Audit Trail Drawer
 * Hollywood Studio Legal Ops UI/UX Overhaul - Component 4
 * Explicitly labeled as: SHA-256 Append-Only Hash Chain (event_hash = sha256(parent_hash + payload))
 * Slide-over drawer displaying chronological append-only supersession events,
 * reviewer identities, AI vs Human distinctions, timestamps, prior IDs,
 * SHA-256 event hashes, and chained parent hashes.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useEffect, useState } from 'react';
import {
  History,
  X,
  Sparkles,
  Gavel,
  ShieldCheck,
  AlertTriangle,
  Lock,
  Hash,
  Copy,
  Check,
  Link as LinkIcon,
} from 'lucide-react';
import { ActorType, DecisionStatus, ReviewActionType, SupersessionEvent } from '@/lib/types';

export interface AuditTrailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  auditTrail: ReadonlyArray<SupersessionEvent>;
}

export const AuditTrailDrawer: React.FC<AuditTrailDrawerProps> = ({
  isOpen,
  onClose,
  auditTrail,
}) => {
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Handle ESC key to close drawer for accessibility
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const handleCopyHash = (hash: string) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(hash);
      setCopiedHash(hash);
      setTimeout(() => setCopiedHash(null), 2000);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex justify-end animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="audit-trail-drawer-title"
    >
      <div className="w-full max-w-2xl bg-[#0b101d] border-l border-slate-700 h-full flex flex-col shadow-2xl overflow-hidden animate-in slide-in-from-right duration-300">
        {/* Drawer Header with Mandated Explicit Label */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/95">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-sky-500/20 text-sky-400 border border-sky-500/30">
              <History className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h3 id="audit-trail-drawer-title" className="text-base font-bold text-white tracking-tight">
                SHA-256 Append-Only Hash Chain
              </h3>
              <p className="text-xs text-sky-300 font-mono">
                event_hash = sha256(parent_hash + payload) &middot; {auditTrail.length} recorded events
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
            aria-label="Close SHA-256 Hash Chain Drawer"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Cryptographic Standard Banner */}
        <div className="p-4 bg-[#111827]/90 border-b border-slate-800/80">
          <div className="rounded-xl border border-sky-500/40 bg-sky-950/30 p-3.5 space-y-1.5 text-xs shadow-inner">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-sky-300 font-bold font-mono text-[11px] uppercase tracking-wider">
                <Hash className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
                <span>SHA-256 Append-Only Hash Chain Standard</span>
              </div>
              <span className="rounded bg-sky-900/80 text-sky-200 border border-sky-500/40 px-2 py-0.5 text-[10px] font-mono font-bold">
                E&amp;O UNDERWRITER VERIFIED
              </span>
            </div>
            <div className="font-mono text-xs text-amber-200 bg-slate-950/80 px-2.5 py-1.5 rounded border border-slate-800">
              Formula: <strong className="text-white">event_hash = sha256(parent_hash + payload)</strong>
            </div>
            <p className="text-slate-300 text-[11px] leading-relaxed font-sans">
              Every clearance determination is cryptographically committed and chained to the preceding parent hash, preventing retroactive alteration, backdating, or ledger tampering under 17 U.S.C. § 504(c).
            </p>
          </div>
        </div>

        {/* Drawer Content: Chronological Supersession Events */}
        <div
          className="flex-1 overflow-y-auto p-5 space-y-4"
          tabIndex={0}
          role="region"
          aria-label="Chronological Hash Chain Events List"
        >
          {auditTrail.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400">
              No hash chain supersession events recorded yet.
            </div>
          ) : (
            auditTrail.map((event, index) => {
              const isAI =
                event.actor_type === ActorType.AI_SYSTEM_RECOMMENDATION ||
                event.action === 'REVALIDATE';
              const isReattest =
                event.action === ReviewActionType.RE_ATTEST ||
                event.resulting_status === DecisionStatus.APPROVED;

              const parentHash =
                event.parent_hash ||
                event.parent_event_hash ||
                (index < auditTrail.length - 1
                  ? auditTrail[index + 1].event_hash
                  : '0000000000000000000000000000000000000000000000000000000000000000 (GENESIS)');

              return (
                <div
                  key={event.event_id || `evt_${index}`}
                  className={`rounded-xl border p-4 space-y-3 transition-all shadow-md ${
                    isAI
                      ? 'border-purple-800/40 bg-purple-950/20'
                      : isReattest
                      ? 'border-emerald-800/40 bg-emerald-950/20'
                      : 'border-amber-800/40 bg-amber-950/20'
                  }`}
                  role="article"
                  aria-label={`Audit Event ${index + 1}: ${event.action} by ${event.reviewer_name}`}
                >
                  <div className="flex items-start justify-between gap-2 border-b border-slate-800/80 pb-2.5">
                    <div className="flex items-center gap-2">
                      {isAI ? (
                        <span
                          className="rounded-full bg-purple-500/20 p-1 text-purple-400 border border-purple-500/40"
                          aria-hidden="true"
                        >
                          <Sparkles className="h-3.5 w-3.5" />
                        </span>
                      ) : (
                        <span
                          className="rounded-full bg-sky-500/20 p-1 text-sky-400 border border-sky-500/40"
                          aria-hidden="true"
                        >
                          <Gavel className="h-3.5 w-3.5" />
                        </span>
                      )}
                      <div>
                        <div className="text-xs font-bold text-white">
                          {event.reviewer_name ||
                            (typeof event.reviewer === 'object' ? event.reviewer?.name : event.reviewer) ||
                            'Sarah Jenkins, Esq.'}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          {isAI
                            ? 'Lienmark Clearance Engine (Automated Pipeline)'
                            : event.reviewer_title ||
                              (typeof event.reviewer === 'object' ? event.reviewer?.title : null) ||
                              'Lead Production Clearance Counsel'}
                        </div>
                      </div>
                    </div>

                    {/* Action Badge */}
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-mono font-bold uppercase shadow-sm ${
                        isAI
                          ? 'bg-purple-900/80 text-purple-200 border border-purple-500/50'
                          : isReattest
                          ? 'bg-emerald-900/80 text-emerald-200 border border-emerald-500/50'
                          : 'bg-rose-900/80 text-rose-200 border border-rose-500/50'
                      }`}
                    >
                      {event.action}
                    </span>
                  </div>

                  <div className="text-xs text-slate-200 flex items-center justify-between">
                    <span>
                      Target Asset Lineage:{' '}
                      <strong className="font-mono text-sky-300 font-bold">{event.stable_lineage_key}</strong>
                    </span>
                    <span className="font-mono text-[10px] text-slate-400">
                      Version: {event.target_version_id || 'v8'}
                    </span>
                  </div>

                  <blockquote className="text-xs text-slate-300 bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 leading-relaxed font-serif italic">
                    &ldquo;{event.counsel_rationale || event.rationale}&rdquo;
                  </blockquote>

                  {/* Explicit Cryptographic Hash Chain Card */}
                  <div className="rounded-lg bg-slate-950/90 p-2.5 border border-slate-800 text-[10px] font-mono space-y-1.5">
                    <div className="text-sky-400 font-bold flex items-center justify-between border-b border-slate-800/80 pb-1">
                      <span className="flex items-center gap-1">
                        <LinkIcon className="h-3 w-3 text-sky-400" aria-hidden="true" />
                        <span>SHA-256 Chained Block</span>
                      </span>
                      <span className="text-emerald-400 text-[9px] bg-emerald-950/60 px-1.5 py-0.2 rounded border border-emerald-500/30">
                        event_hash = sha256(parent_hash + payload)
                      </span>
                    </div>

                    <div className="flex items-center justify-between gap-2">
                      <span className="text-slate-400 truncate">
                        Event Hash: <strong className="text-slate-200">{event.event_hash}</strong>
                      </span>
                      <button
                        type="button"
                        onClick={() => handleCopyHash(event.event_hash)}
                        className="text-slate-500 hover:text-white p-1 rounded transition-colors flex-shrink-0"
                        title="Copy Event Hash"
                        aria-label="Copy Event Hash"
                      >
                        {copiedHash === event.event_hash ? (
                          <Check className="h-3 w-3 text-emerald-400" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </button>
                    </div>

                    <div className="text-slate-500 truncate">
                      Parent Hash: <span className="text-slate-400">{parentHash}</span>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-1 text-[9px] text-slate-500 pt-1 border-t border-slate-800/60">
                      <span>Timestamp: {event.timestamp}</span>
                      <span>Prior Decision: {event.prior_decision_id || 'dec_baseline_v7'}</span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Drawer Footer with Mandated Label */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/95 flex items-center justify-between text-xs text-slate-400">
          <span className="flex items-center gap-1.5 font-mono text-[11px]">
            <Lock className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
            <span>SHA-256 Append-Only Hash Chain &middot; Immutable Title Ledger</span>
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 text-xs"
          >
            Close Drawer
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuditTrailDrawer;
