'use client';

/**
 * Lienmark Clearance Status Badge Component
 * Displays clearance decision states (Carried Forward, Stale, Re-Attested, Exception) with high contrast.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { CheckCircle2, AlertTriangle, AlertOctagon } from 'lucide-react';
import { DecisionState } from '@/lib/types';

export interface ClearanceStatusBadgeProps {
  readonly state: DecisionState;
  readonly className?: string;
}

export const ClearanceStatusBadge: React.FC<ClearanceStatusBadgeProps> = ({
  state,
  className = '',
}) => {
  switch (state) {
    case DecisionState.CARRIED_FORWARD:
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold font-mono text-emerald-300 bg-emerald-950/90 border border-emerald-500/60 shadow-sm ${className}`}
          aria-label="Status: Carried Forward (Lineage Parity Verified)"
          title="Deterministic Parity Verified: Bit-for-bit identical to locked baseline cut."
        >
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
          <span>[CARRIED FORWARD]</span>
        </span>
      );
    case DecisionState.STALE:
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold font-mono text-amber-200 bg-amber-950/90 border border-amber-500/80 shadow-md animate-pulse ${className}`}
          aria-label="Status: Stale (Clearance Blocked)"
          title="Clearance Blocked: Material creative or evidence shift detected."
        >
          <AlertTriangle className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
          <span>[STALE - ACTION REQUIRED]</span>
        </span>
      );
    case DecisionState.RE_ATTESTED:
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold font-mono text-sky-200 bg-sky-950/90 border border-sky-500/60 shadow-sm ${className}`}
          aria-label="Status: Re-Attested by Clearance Counsel"
        >
          <CheckCircle2 className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
          <span>[RE-ATTESTED]</span>
        </span>
      );
    case DecisionState.EXCEPTION:
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold font-mono text-rose-200 bg-rose-950/90 border border-rose-500/70 shadow-sm ${className}`}
          aria-label="Status: Designated as Unresolved Exception"
        >
          <AlertOctagon className="h-3.5 w-3.5 text-rose-400" aria-hidden="true" />
          <span>[EXCEPTION]</span>
        </span>
      );
    default:
      return (
        <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-mono text-slate-300 bg-slate-800 border border-slate-700 ${className}`}>
          <span>[{String(state).toUpperCase()}]</span>
        </span>
      );
  }
};

export default ClearanceStatusBadge;
