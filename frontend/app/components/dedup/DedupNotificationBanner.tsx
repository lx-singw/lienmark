'use client';

/**
 * DedupNotificationBanner.tsx
 * Visual alert banner rendered when an ingested file matches an existing revision.
 * Displays green emerald cache-hit confirmation, zero API spend, and rename invariance.
 * Sprint 2.2: Content Digesting, Deduplication & Rename Invariance.
 */

import React from 'react';
import { CheckCircle2, Sparkles, X, FileCheck2, ShieldCheck } from 'lucide-react';
import type { DedupNotificationProps } from './types';
import { formatCacheHitSavings } from './dedup_utils';

interface DetailsPillsProps {
  originalFilename: string;
  apiSpendSavedUsd: number;
}

const DetailsPills: React.FC<DetailsPillsProps> = ({
  originalFilename,
  apiSpendSavedUsd,
}) => {
  return (
    <div className="mt-2.5 flex flex-wrap items-center gap-2 text-xs">
      <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-900/40 px-2.5 py-0.5 text-emerald-200">
        <FileCheck2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
        <span>
          Original: <strong className="font-mono text-emerald-100">{originalFilename}</strong>
        </span>
      </span>
      <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-900/30 px-2.5 py-0.5 text-[11px] text-emerald-300">
        <ShieldCheck className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
        <span>Rename Invariance Confirmed</span>
      </span>
      {apiSpendSavedUsd > 0 && (
        <span className="inline-flex items-center rounded bg-emerald-900/50 px-2 py-0.5 font-mono text-[11px] text-emerald-300">
          Saved ${apiSpendSavedUsd.toFixed(2)}
        </span>
      )}
    </div>
  );
};

export const DedupNotificationBanner: React.FC<DedupNotificationProps> = ({
  isVisible,
  matchedRevision,
  originalFilename,
  claimsReused,
  apiSpendSavedUsd,
  latencyMs,
  onDismiss,
}) => {
  if (!isVisible) return null;

  const savingsSubtext = formatCacheHitSavings(0, claimsReused, latencyMs);

  return (
    <div
      role="alert"
      className="relative rounded-lg border border-emerald-500/30 bg-emerald-950/40 p-4 text-emerald-200 shadow-lg shadow-emerald-950/20 backdrop-blur-sm"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" />
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-emerald-100">
                Identical Document Detected ({matchedRevision})
              </h4>
              <Sparkles className="h-4 w-4 text-emerald-400 shrink-0" aria-hidden="true" />
            </div>
            <p className="mt-1 text-xs font-medium text-emerald-300/90">
              {savingsSubtext}
            </p>
            <DetailsPills
              originalFilename={originalFilename}
              apiSpendSavedUsd={apiSpendSavedUsd}
            />
          </div>
        </div>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss notification"
            className="rounded p-1 text-emerald-400 transition-colors hover:bg-emerald-900/40 hover:text-emerald-200 focus:outline-none focus:ring-2 focus:ring-emerald-400/50"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
};
