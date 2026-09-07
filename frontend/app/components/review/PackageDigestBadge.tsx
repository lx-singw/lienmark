'use client';

/**
 * Lienmark Package Digest Badge Component (Sprint 5.2)
 * Displays canonical SHA-256 package digest with truncation, 1-click copy,
 * and cryptographic tamper indicators.
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import React, { useState, useCallback } from 'react';
import { Shield, ShieldCheck, ShieldAlert, Copy, Check } from 'lucide-react';
import { PackageDigestBadgeProps } from './review_types';
import { truncateDigest } from './review_utils';

export const PackageDigestBadge: React.FC<PackageDigestBadgeProps> = ({
  digest,
  label = 'Package Digest',
  isStale = false,
  isTampered = false,
  className = '',
}) => {
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = useCallback(async (): Promise<void> => {
    if (!digest) return;
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(digest);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Defensive fallback if clipboard write is blocked
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [digest]);

  const getShieldIcon = (): React.ReactNode => {
    if (isTampered) {
      return <ShieldAlert className="h-4 w-4 text-rose-400 flex-shrink-0 animate-pulse" aria-hidden="true" />;
    }
    if (isStale) {
      return <ShieldAlert className="h-4 w-4 text-amber-400 flex-shrink-0" aria-hidden="true" />;
    }
    return <ShieldCheck className="h-4 w-4 text-emerald-400 flex-shrink-0" aria-hidden="true" />;
  };

  const getContainerStyle = (): string => {
    if (isTampered) {
      return 'border-rose-500/50 bg-rose-950/40 text-rose-200 ring-1 ring-rose-500/40';
    }
    if (isStale) {
      return 'border-amber-500/50 bg-amber-950/40 text-amber-200 ring-1 ring-amber-500/40';
    }
    return 'border-slate-800 bg-slate-900/80 text-slate-300 hover:border-slate-700';
  };

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-lg border px-2.5 py-1 text-xs transition-colors ${getContainerStyle()} ${className}`}
      title={`Canonical SHA-256 Digest: ${digest || 'Unset'}`}
      data-testid="package-digest-badge"
    >
      {getShieldIcon()}

      <div className="flex items-center gap-1.5 font-mono text-[11px]">
        {label && <span className="text-slate-400 font-sans text-[10px] uppercase tracking-wider">{label}:</span>}
        <span className="font-semibold text-slate-200 tracking-tight" data-testid="truncated-digest">
          {truncateDigest(digest, 8, 6)}
        </span>
      </div>

      {isTampered && (
        <span className="rounded bg-rose-500/30 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-rose-300 border border-rose-500/50">
          Tamper Detected
        </span>
      )}

      {isStale && !isTampered && (
        <span className="rounded bg-amber-500/30 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-amber-300 border border-amber-500/50">
          Stale
        </span>
      )}

      <button
        type="button"
        onClick={handleCopy}
        className="ml-1 inline-flex items-center gap-1 rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors focus:outline-none focus:ring-1 focus:ring-sky-500"
        aria-label={copied ? 'Copied package digest to clipboard' : 'Copy canonical package digest'}
        title="Copy canonical SHA-256 digest"
      >
        {copied ? (
          <>
            <Check className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
            <span className="text-[10px] text-emerald-300 font-sans">Copied!</span>
          </>
        ) : (
          <Copy className="h-3.5 w-3.5" aria-hidden="true" />
        )}
      </button>
    </div>
  );
};

export default PackageDigestBadge;
