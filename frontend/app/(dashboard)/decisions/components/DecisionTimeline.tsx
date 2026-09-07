'use client';

/**
 * Decision Timeline Component
 * Chronological immutable ledger event chain renderer with supersession lineage and verification hooks.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import { Gavel, Clock, User, ArrowRight, ShieldAlert, History } from 'lucide-react';
import { DecisionTimelineEvent } from '../types';
import { CryptoVerificationBadge } from './CryptoVerificationBadge';

interface DecisionTimelineProps {
  readonly events: ReadonlyArray<DecisionTimelineEvent>;
  readonly onVerifyEvent: (eventId: string) => void;
}

function getStatusBadge(status?: string | null): { text: string; bg: string; border: string } {
  switch (status?.toUpperCase()) {
    case 'APPROVED':
      return { text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' };
    case 'REJECTED':
      return { text: 'text-rose-400', bg: 'bg-rose-500/10', border: 'border-rose-500/30' };
    case 'EXCEPTION':
      return { text: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' };
    default:
      return { text: 'text-sky-400', bg: 'bg-sky-500/10', border: 'border-sky-500/30' };
  }
}

export function DecisionTimeline({
  events,
  onVerifyEvent,
}: DecisionTimelineProps): React.JSX.Element {
  if (events.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/60 p-12 text-center text-xs font-mono text-slate-400">
        No decision ledger events recorded matching the selected filter.
      </div>
    );
  }

  return (
    <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
      {events.map((evt) => {
        const badge = getStatusBadge(evt.decision_status);
        return (
          <div key={evt.event_id} className="relative group">
            <div className="absolute -left-[27px] top-1.5 h-3.5 w-3.5 rounded-full border-2 border-slate-900 bg-sky-400 ring-4 ring-[#0e1424]" />

            <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 p-5 space-y-3 hover:border-slate-700/80 transition-all">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/60 pb-3">
                <div className="flex flex-wrap items-center gap-2">
                  <CryptoVerificationBadge
                    eventId={evt.event_id}
                    sequenceNumber={evt.sequence_number}
                    onVerify={onVerifyEvent}
                  />
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[10px] font-mono font-bold uppercase border ${badge.bg} ${badge.text} ${badge.border}`}
                  >
                    {evt.decision_status || evt.action_type}
                  </span>
                  {evt.is_superseded && (
                    <span className="rounded-full bg-purple-500/10 border border-purple-500/30 px-2 py-0.5 text-[10px] font-mono text-purple-300">
                      Superseded
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400">
                  <Clock className="h-3 w-3 text-slate-500" />
                  <span>{new Date(evt.timestamp_utc).toLocaleString()}</span>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-bold text-white">
                  {evt.claim_title || evt.action_type.replace('_', ' ')}
                </h3>
                {evt.claim_id && (
                  <span className="text-[11px] font-mono text-sky-400">
                    Lineage Key: {evt.claim_id}
                  </span>
                )}
              </div>

              {evt.counsel_rationale && (
                <div className="rounded-xl border border-slate-800/80 bg-slate-950/70 p-3">
                  <p className="text-xs text-slate-300 font-mono leading-relaxed">
                    &ldquo;{evt.counsel_rationale}&rdquo;
                  </p>
                </div>
              )}

              <div className="flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono text-slate-400 pt-1">
                <div className="flex items-center gap-1.5">
                  <User className="h-3 w-3 text-slate-500" />
                  <span className="text-slate-300">{evt.actor_name}</span>
                  <span className="text-slate-600">({evt.actor_id})</span>
                </div>

                {evt.superseded_event_id && (
                  <div className="flex items-center gap-1 text-amber-400/90 text-[10px]">
                    <History className="h-3 w-3" />
                    <span>Overrides prior event: {evt.superseded_event_id.slice(0, 14)}...</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
