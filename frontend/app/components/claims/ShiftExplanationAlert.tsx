'use client';

/**
 * Lienmark Invalidated Claim Shift Explanation Component
 * Explains creative context shifts, external evidence shifts, or clearance drift.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { EvaluatedClaim } from '@/lib/types';

export interface ShiftExplanationAlertProps {
  readonly claim: EvaluatedClaim;
  readonly isItem11?: boolean;
  readonly isItem12?: boolean;
  readonly className?: string;
}

function getShiftTitle(isItem11: boolean, isItem12: boolean): string {
  if (isItem11) return 'Creative Context Shift (Scene 42)';
  if (isItem12) return 'External Evidence Shift (Scene 18)';
  return 'Clearance Drift Invalidation';
}

function getShiftExplanation(
  claim: EvaluatedClaim,
  isItem11: boolean,
  isItem12: boolean
): string {
  if (isItem11) {
    return '2s background blur \u2192 14s close-up focal dialogue recitation. Prior de minimis fair use defense collapsed; counsel re-attestation required under 17 U.S.C. \u00a7 304 public domain doctrine.';
  }
  if (isItem12) {
    return 'Vanguard Media Holdings LLC recorded exclusive worldwide sync rights August 2026. Prior cue sheet PD notation invalidated; underwriting exception required.';
  }
  return `Invalidated: ${claim.reason_code} \u00b7 Revalidation action: ${claim.revalidation_action}. Counsel adjudication required.`;
}

export const ShiftExplanationAlert: React.FC<ShiftExplanationAlertProps> = ({
  claim,
  isItem11 = false,
  isItem12 = false,
  className = '',
}) => {
  const title = getShiftTitle(isItem11, isItem12);
  const explanation = getShiftExplanation(claim, isItem11, isItem12);

  return (
    <div
      className={`mt-1 flex items-start gap-1.5 rounded-lg bg-amber-950/60 border border-amber-500/50 p-2 text-[10px] font-mono text-amber-200 shadow-sm ${className}`}
      role="alert"
      aria-label="Invalidated Claim Clearance Shift Explanation"
    >
      <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0 mt-0.5" aria-hidden="true" />
      <div className="space-y-0.5">
        <span className="font-bold text-amber-300 block uppercase tracking-wider text-[9px]">
          {title}
        </span>
        <p className="font-sans text-[11px] text-amber-100/95 leading-snug">
          {explanation}
        </p>
      </div>
    </div>
  );
};

export default ShiftExplanationAlert;
