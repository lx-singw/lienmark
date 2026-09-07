'use client';

/**
 * Lienmark Confidentiality Badge Component
 * Displays compliance with narrative spoiler trimming (< 20 words) for script baseline extraction.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { ShieldCheck, AlertTriangle, Lock } from 'lucide-react';
import { ConfidentialityBadgeProps, ConfidentialityLevel } from './types';
import { MAX_CONFIDENTIAL_WORDS } from './intake_utils';

export const ConfidentialityBadge: React.FC<ConfidentialityBadgeProps> = ({
  wordCount,
  maxWords = MAX_CONFIDENTIAL_WORDS,
  level = ConfidentialityLevel.STRICT_TRIMMED,
  className = '',
}) => {
  const isRedacted = level === ConfidentialityLevel.REDACTED;
  const isCompliant = wordCount <= maxWords && !isRedacted;

  if (isRedacted) {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded bg-slate-900/90 text-slate-400 border border-slate-700/80 px-1.5 py-0.5 text-[10px] font-mono font-semibold tracking-wider uppercase shadow-sm ${className}`}
        title="Dialogue and proprietary narrative terms redacted under studio legal protocol."
        aria-label="Confidentiality Status: Redacted"
      >
        <Lock className="h-3 w-3 text-slate-400" aria-hidden="true" />
        <span>REDACTED</span>
      </span>
    );
  }

  if (isCompliant) {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-500/50 px-1.5 py-0.5 text-[10px] font-mono font-semibold tracking-wider uppercase shadow-sm ${className}`}
        title={`Confidentiality filter compliant: ${wordCount} words (max ${maxWords}). Plot spoilers and narrative arcs stripped.`}
        aria-label={`Confidentiality Status: Trimmed (${wordCount} words)`}
      >
        <ShieldCheck className="h-3 w-3 text-emerald-400" aria-hidden="true" />
        <span>TRIMMED: {wordCount} WDS</span>
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1 rounded bg-amber-950/80 text-amber-200 border border-amber-500/70 px-1.5 py-0.5 text-[10px] font-mono font-bold tracking-wider uppercase shadow-sm animate-pulse ${className}`}
      title={`Warning: Description contains ${wordCount} words, exceeding ${maxWords} word limit. May leak plot spoilers.`}
      aria-label={`Confidentiality Warning: Excess Verbiage (${wordCount} words)`}
    >
      <AlertTriangle className="h-3 w-3 text-amber-400" aria-hidden="true" />
      <span>EXCESS VERBIAGE: {wordCount} WDS</span>
    </span>
  );
};

export default ConfidentialityBadge;
