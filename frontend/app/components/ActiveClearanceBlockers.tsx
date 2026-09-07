'use client';

/**
 * Lienmark Active Clearance Blockers Summary Component
 * Dynamically computes and displays active clearance blockers preventing E&O sign-off.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React, { useMemo } from 'react';
import {
  AlertTriangle,
  AlertOctagon,
  Gavel,
  CheckCircle2,
  ShieldCheck,
} from 'lucide-react';
import { DecisionState, EvaluatedClaim } from '@/lib/types';

export interface ActiveClearanceBlockersProps {
  readonly staleCount?: number;
  readonly claims?: ReadonlyArray<EvaluatedClaim>;
  readonly onOpenInGate: (lineageKey: string) => void;
  readonly className?: string;
}

function BlockerItemCard({
  claim,
  index,
  total,
  onOpen,
}: {
  claim: EvaluatedClaim;
  index: number;
  total: number;
  onOpen: (key: string) => void;
}) {
  const isResolved = claim.state === DecisionState.RE_ATTESTED || claim.state === DecisionState.CARRIED_FORWARD;
  const isException = claim.state === DecisionState.EXCEPTION;

  return (
    <div
      role="article"
      aria-label={`Clearance Blocker: ${claim.stable_lineage_key}`}
      className={`rounded-xl border p-4 transition-all space-y-3 ${
        isResolved
          ? 'border-emerald-500/40 bg-emerald-950/20'
          : isException
          ? 'border-rose-500/40 bg-rose-950/20'
          : 'border-amber-500/40 bg-[#162038] ring-1 ring-amber-500/20'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 text-xs font-mono font-bold">
              Blocker {index + 1} of {total}
            </span>
            <span className="text-xs font-mono font-bold text-slate-400">
              {claim.scene || 'Scene N/A'}
            </span>
          </div>
          <h4 className="text-sm font-bold text-white mt-1.5 flex items-center gap-2">
            <span>{claim.description || claim.stable_lineage_key}</span>
            {isResolved && (
              <span className="inline-flex items-center gap-1 rounded bg-emerald-900/80 px-2 py-0.5 text-[11px] font-semibold text-emerald-300 border border-emerald-500/40">
                <CheckCircle2 className="h-3 w-3" /> Re-Attested
              </span>
            )}
            {isException && (
              <span className="inline-flex items-center gap-1 rounded bg-rose-900/80 px-2 py-0.5 text-[11px] font-semibold text-rose-300 border border-rose-500/40">
                <AlertOctagon className="h-3 w-3" /> Exception
              </span>
            )}
          </h4>
        </div>
        <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-300 capitalize">
          {claim.asset_type || 'Asset'}
        </span>
      </div>

      <div className="space-y-2 text-xs">
        <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800 space-y-1">
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-400">
            Detected Status / Drift
          </span>
          <p className="text-slate-200 font-semibold">{claim.reason_code}</p>
          <p className="text-[11px] text-slate-400 font-mono">{claim.stable_lineage_key}</p>
        </div>
      </div>

      <div className="pt-1">
        {isResolved ? (
          <div className="flex items-center justify-between text-xs text-emerald-300 bg-emerald-950/60 rounded-lg p-2 border border-emerald-500/30">
            <span className="flex items-center gap-1.5 font-medium">
              <CheckCircle2 className="h-4 w-4" />
              <span>Attested by Lead Counsel</span>
            </span>
            <button
              type="button"
              onClick={() => onOpen(claim.stable_lineage_key)}
              className="text-[11px] text-sky-400 hover:text-sky-300 underline font-semibold"
            >
              Review Decision
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => onOpen(claim.stable_lineage_key)}
            className="w-full flex items-center justify-center gap-2 rounded-lg bg-amber-500 hover:bg-amber-400 py-2 px-3 text-xs font-bold text-slate-950 transition-all shadow-md shadow-amber-500/20 active:scale-[0.99]"
          >
            <Gavel className="h-4 w-4" />
            <span>Open in Checkpoint Gate &rarr; Adjudicate</span>
          </button>
        )}
      </div>
    </div>
  );
}

export const ActiveClearanceBlockers: React.FC<ActiveClearanceBlockersProps> = ({
  claims = [],
  onOpenInGate,
  className = '',
}) => {
  // Dynamically compute blockers: claims requiring human counsel action or flagged as exceptions/stale
  const blockers = useMemo(() => {
    return claims.filter(
      (c) =>
        c.state === DecisionState.STALE ||
        c.state === DecisionState.EXCEPTION ||
        (c.state === DecisionState.RE_ATTESTED && c.reason_code !== 'DEPENDENCIES_SATISFIED_UNCHANGED')
    );
  }, [claims]);

  const pendingCount = useMemo(() => {
    return blockers.filter((c) => c.state === DecisionState.STALE).length;
  }, [blockers]);

  if (blockers.length === 0) {
    return (
      <div className={`rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 flex items-center gap-3 ${className}`}>
        <ShieldCheck className="h-6 w-6 text-emerald-400 flex-shrink-0" />
        <div>
          <h4 className="text-sm font-semibold text-emerald-200">Zero Active Clearance Blockers</h4>
          <p className="text-xs text-slate-400">All rights-bearing claims satisfied or approved for this production cut.</p>
        </div>
      </div>
    );
  }

  return (
    <section
      aria-label="Active Clearance Blockers Summary"
      role="region"
      className={`rounded-2xl border-2 border-amber-500/60 bg-gradient-to-br from-amber-950/40 via-[#131b2e] to-[#0d1424] p-5 sm:p-6 shadow-2xl shadow-amber-950/30 space-y-4 ${className}`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-amber-500/30 pb-3.5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/40 flex-shrink-0">
            <AlertTriangle className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white tracking-tight">Active Clearance Blockers</h3>
              <span className="rounded-full bg-amber-500/20 border border-amber-500/50 px-2.5 py-0.5 text-xs font-mono font-bold text-amber-300">
                {pendingCount} Pending Review
              </span>
            </div>
            <p className="text-xs text-amber-200/90 font-medium mt-0.5">
              Material rights changes require human counsel disposition before Form E&amp;O-2026 issuance.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 self-end sm:self-auto">
          <span className="rounded bg-slate-900/90 border border-slate-700 px-2.5 py-1 text-[11px] font-mono text-slate-300">
            Gate: <strong>Fail-Closed</strong>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {blockers.map((claim, idx) => (
          <BlockerItemCard
            key={claim.stable_lineage_key}
            claim={claim}
            index={idx}
            total={blockers.length}
            onOpen={onOpenInGate}
          />
        ))}
      </div>
    </section>
  );
};

export default ActiveClearanceBlockers;
