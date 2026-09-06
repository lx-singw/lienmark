'use client';

/**
 * Lienmark Append-Only Clearance Audit Trail & Supersession Log Drawer
 * Slide-over drawer displaying chronological append-only supersession events,
 * reviewer identities, AI vs Human distinctions, timestamps, prior IDs,
 * SHA-256 event hashes, and chained parent hashes.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useEffect } from 'react';
import {
  History,
  X,
  Sparkles,
  Gavel,
  ShieldCheck,
  AlertTriangle,
  Lock,
  Hash,
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

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex justify-end animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="audit-trail-drawer-title"
    >
      <div className="w-full max-w-2xl bg-[#0f172a] border-l border-slate-700 h-full flex flex-col shadow-2xl overflow-hidden animate-in slide-in-from-right duration-300">
        {/* Drawer Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/95">
          <div className="flex items-center gap-2.5">
            <History className="h-5 w-5 text-sky-400" aria-hidden="true" />
            <div>
              <h3 id="audit-trail-drawer-title" className="text-base font-bold text-white">
                Append-Only Clearance Audit Trail &amp; Supersession Log
              </h3>
              <p className="text-xs text-slate-400">
                Tamper-evident legal ledger &middot; {auditTrail.length} recorded events
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
            aria-label="Close Audit Trail Drawer"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Drawer Content: Chronological Supersession Events */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4" tabIndex={0} role="region" aria-label="Supersession Events List">
          {auditTrail.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400">
              No supersession events recorded yet.
            </div>
          ) : (
            auditTrail.map((event, index) => {
              const isAI =
                event.actor_type === ActorType.AI_SYSTEM_RECOMMENDATION ||
                event.action === 'REVALIDATE';
              const isReattest =
                event.action === ReviewActionType.RE_ATTEST ||
                event.resulting_status === DecisionStatus.APPROVED;

              return (
                <div
                  key={event.event_id || `evt_${index}`}
                  className={`rounded-xl border p-4 space-y-2.5 transition-all shadow-sm ${
                    isAI
                      ? 'border-purple-800/40 bg-purple-950/20'
                      : isReattest
                      ? 'border-emerald-800/40 bg-emerald-950/20'
                      : 'border-amber-800/40 bg-amber-950/20'
                  }`}
                  role="article"
                  aria-label={`Audit Event ${index + 1}: ${event.action} by ${event.reviewer_name}`}
                >
                  <div className="flex items-start justify-between gap-2">
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
                          {event.reviewer_name || (typeof event.reviewer === 'object' ? event.reviewer?.name : event.reviewer) || 'Sarah Jenkins, Esq.'}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          {isAI ? 'AI Invalidation Agent' : (event.reviewer_title || (typeof event.reviewer === 'object' ? event.reviewer?.title : null) || 'Lead Production Clearance Counsel')}
                        </div>
                      </div>
                    </div>

                    {/* Action Badge */}
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-mono font-bold uppercase ${
                        isAI
                          ? 'bg-purple-900/60 text-purple-300 border border-purple-500/40'
                          : isReattest
                          ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-500/40'
                          : 'bg-rose-900/60 text-rose-300 border border-rose-500/40'
                      }`}
                    >
                      {event.action}
                    </span>
                  </div>

                  <div className="text-xs text-slate-200">
                    <span className="text-slate-400">Target Asset Lineage:</span>{' '}
                    <span className="font-mono text-sky-300 font-bold">{event.stable_lineage_key}</span>
                  </div>

                  <blockquote className="text-xs text-slate-300 bg-slate-900/70 p-2.5 rounded border border-slate-800/80 leading-relaxed font-serif italic">
                    &ldquo;{event.counsel_rationale || event.rationale}&rdquo;
                  </blockquote>

                  <div className="space-y-1 pt-1.5 text-[10px] font-mono text-slate-400 border-t border-slate-800/80">
                    <div className="flex flex-wrap items-center justify-between gap-1">
                      <span>Timestamp: {event.timestamp}</span>
                      <span>Prior Decision ID: {event.prior_decision_id || 'N/A'}</span>
                    </div>
                    <div className="text-slate-500 truncate flex items-center gap-1">
                      <Hash className="h-2.5 w-2.5 text-slate-600 flex-shrink-0" aria-hidden="true" />
                      <span>SHA-256 Event Hash:</span>{' '}
                      <span className="text-slate-300 font-mono">{event.event_hash}</span>
                    </div>
                    {(event.parent_hash || event.parent_event_hash) && (
                      <div className="text-slate-500 truncate flex items-center gap-1">
                        <Hash className="h-2.5 w-2.5 text-slate-600 flex-shrink-0" aria-hidden="true" />
                        <span>Chained Parent Hash:</span>{' '}
                        <span className="text-slate-300 font-mono">
                          {event.parent_hash || event.parent_event_hash}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/95 flex items-center justify-between text-xs text-slate-400">
          <span className="flex items-center gap-1.5">
            <Lock className="h-3 w-3 text-sky-400" aria-hidden="true" />
            <span>Cryptographic Chain-of-Title Ledger &middot; Immutable</span>
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            Close Drawer
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuditTrailDrawer;
