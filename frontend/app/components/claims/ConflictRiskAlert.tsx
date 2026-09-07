'use client';

/**
 * ConflictRiskAlert.tsx
 * Elevation of Risk Alert: clearly explains why counsel adjudication is mandatory
 * under statutory clearance rules, fail-closed protocols, and E&O risk exposure.
 * Sprint 3.3: Contradictory Evidence & Conflict Arbitration UI.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { ShieldAlert } from 'lucide-react';
import { type ConflictEvidencePair } from './conflict_types';
import { formatDamages } from './conflict_utils';

export interface ConflictRiskAlertProps {
  readonly pair: ConflictEvidencePair;
  readonly onAdjudicate?: (pairId: string, action: 're_attest' | 'exception' | 'reject') => void;
  readonly isReadOnly?: boolean;
  readonly className?: string;
}

function renderActionButtons(
  pairId: string,
  onAdjudicate: (pairId: string, action: 're_attest' | 'exception' | 'reject') => void
): React.ReactElement {
  return (
    <div className="flex flex-wrap gap-2 pt-2">
      <button
        type="button"
        onClick={() => onAdjudicate(pairId, 're_attest')}
        className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold font-mono transition-colors shadow"
      >
        Re-Attest (PD Defense)
      </button>
      <button
        type="button"
        onClick={() => onAdjudicate(pairId, 'exception')}
        className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold font-mono transition-colors shadow"
      >
        Designate Exception
      </button>
      <button
        type="button"
        onClick={() => onAdjudicate(pairId, 'reject')}
        className="px-3 py-1.5 rounded-lg bg-rose-700 hover:bg-rose-600 text-white text-xs font-bold font-mono transition-colors shadow"
      >
        Reject Clearance
      </button>
    </div>
  );
}

export const ConflictRiskAlert: React.FC<ConflictRiskAlertProps> = ({
  pair,
  onAdjudicate,
  isReadOnly = false,
  className = '',
}) => {
  return (
    <div
      className={`rounded-xl bg-gradient-to-r from-rose-950/80 via-amber-950/60 to-rose-950/80 border border-rose-500/70 p-4 shadow-xl ${className}`}
      role="alert"
      aria-label="Elevation of Risk: Mandatory Counsel Adjudication"
    >
      <div className="flex items-start gap-3">
        <ShieldAlert className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" aria-hidden="true" />
        <div className="space-y-1.5 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-xs font-bold text-rose-200 uppercase tracking-wider font-mono">
              Elevation of Risk: Mandatory Counsel Adjudication
            </h4>
            <span className="text-[10px] font-mono font-bold bg-rose-900/80 text-rose-100 px-2 py-0.5 rounded border border-rose-400/60">
              {formatDamages(pair.statutoryDamagesMaxUsd)}
            </span>
          </div>

          <p className="text-xs text-rose-100/90 leading-relaxed font-sans">
            {pair.elevationReason}
          </p>

          <div className="text-[11px] text-amber-200 bg-black/40 p-2.5 rounded border border-amber-500/40 font-mono">
            <strong>Mandatory Directive:</strong> {pair.counselActionRequired}
          </div>

          {!isReadOnly && onAdjudicate && renderActionButtons(pair.id, onAdjudicate)}
        </div>
      </div>
    </div>
  );
};

export default ConflictRiskAlert;
