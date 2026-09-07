'use client';

/**
 * SecurityFlagBadge Component
 * High-visibility status pills for prompt injection defense and intake anomalies.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import { ShieldAlert, AlertTriangle, AlertOctagon } from 'lucide-react';
import { SecurityFlag, parseSecurityFlag } from './types';

export interface SecurityFlagBadgeProps {
  readonly flag?: SecurityFlag | null;
  readonly flaggedReason?: string | null;
  readonly size?: 'sm' | 'md';
  readonly className?: string;
}

function resolveBadgeStyles(type: SecurityFlag['type']): {
  readonly container: string;
  readonly dot: string;
} {
  switch (type) {
    case 'PROMPT_INJECTION':
      return {
        container:
          'bg-rose-950/60 text-rose-300 border-rose-500/60 shadow-sm shadow-rose-950/50',
        dot: 'bg-rose-400 animate-ping',
      };
    case 'ZERO_CLAIMS_ANOMALY':
      return {
        container:
          'bg-amber-950/60 text-amber-300 border-amber-500/60 shadow-sm shadow-amber-950/50',
        dot: 'bg-amber-400',
      };
    default:
      return {
        container:
          'bg-slate-900 text-slate-300 border-slate-700',
        dot: 'bg-slate-400',
      };
  }
}

function renderFlagIcon(type: SecurityFlag['type']): React.JSX.Element {
  if (type === 'PROMPT_INJECTION') {
    return <ShieldAlert className="h-3.5 w-3.5 shrink-0 text-rose-400" />;
  }
  if (type === 'ZERO_CLAIMS_ANOMALY') {
    return <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-400" />;
  }
  return <AlertOctagon className="h-3.5 w-3.5 shrink-0 text-slate-400" />;
}

export function SecurityFlagBadge({
  flag,
  flaggedReason,
  size = 'md',
  className = '',
}: SecurityFlagBadgeProps): React.JSX.Element | null {
  const resolvedFlag = flag ?? parseSecurityFlag(flaggedReason);
  if (!resolvedFlag) return null;

  const styles = resolveBadgeStyles(resolvedFlag.type);
  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-mono font-bold tracking-wider uppercase transition-all backdrop-blur-md ${sizeClass} ${styles.container} ${className}`}
    >
      <span className="relative flex h-2 w-2">
        <span
          className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${styles.dot}`}
        />
        <span
          className={`relative inline-flex h-2 w-2 rounded-full ${
            resolvedFlag.type === 'PROMPT_INJECTION' ? 'bg-rose-500' : 'bg-amber-500'
          }`}
        />
      </span>
      {renderFlagIcon(resolvedFlag.type)}
      <span>{resolvedFlag.label}</span>
    </span>
  );
}

export default SecurityFlagBadge;
