'use client';

/**
 * Lienmark Interactive Decision List Component
 * Delegates to the High-Contrast Cinematic ClaimsTable matrix
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { DecisionState, EvaluatedClaim, UserRole } from '@/lib/types';
import ClaimsTable from './ClaimsTable';

export interface DecisionListComponentProps {
  claims: ReadonlyArray<EvaluatedClaim>;
  selectedClaimKey: string;
  onSelectClaim: (claimKey: string) => void;
  onOpenInGate?: (claimKey: string) => void;
  userRole?: UserRole;
}

export const DecisionListComponent: React.FC<DecisionListComponentProps> = ({
  claims,
  selectedClaimKey,
  onSelectClaim,
  onOpenInGate,
  userRole = UserRole.REVIEWER,
}) => {
  const carriedCount = claims.filter((c) => c.state === DecisionState.CARRIED_FORWARD).length;

  return (
    <div className="space-y-4" role="region" aria-label="12-Claim Production Lineage Ledger">
      {/* Deterministic Lineage Parity Banner */}
      {carriedCount > 0 && (
        <div
          className="rounded-xl border border-emerald-500/40 bg-emerald-950/30 p-3.5 flex items-start gap-3 text-xs shadow-sm"
          role="region"
          aria-label="Deterministic Lineage Parity Verification"
        >
          <div className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex-shrink-0 mt-0.5">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-bold text-emerald-300">
                Deterministic Lineage Parity ({carriedCount} of {claims.length} Claims Locked)
              </span>
              <span className="rounded bg-emerald-900/80 px-1.5 py-0.2 text-[10px] font-mono text-emerald-200 border border-emerald-500/40 font-semibold">
                $0 Review Cost
              </span>
            </div>
            <p className="text-slate-200 text-[11px] leading-relaxed">
              <strong>Lineage Parity Verified:</strong> Dialogue, prominence duration, and visual placement are bit-for-bit identical to Locked v7. Public copyright records re-verified unchanged. Autonomous pass under statutory clearance doctrine.
            </p>
          </div>
        </div>
      )}

      {/* High-Contrast Cinematic Claims Table Matrix */}
      <ClaimsTable
        claims={claims}
        selectedClaimKey={selectedClaimKey}
        onSelectClaim={onSelectClaim}
        onOpenInGate={onOpenInGate}
        userRole={userRole}
      />
    </div>
  );
};

export default DecisionListComponent;
