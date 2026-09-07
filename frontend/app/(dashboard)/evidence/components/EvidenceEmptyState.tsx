'use client';

/**
 * Evidence Explorer Empty State Component
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import { Database, SearchX, RotateCcw } from 'lucide-react';

interface EvidenceEmptyStateProps {
  readonly hasActiveFilters: boolean;
  readonly onResetFilters?: () => void;
}

export function EvidenceEmptyState({
  hasActiveFilters,
  onResetFilters,
}: EvidenceEmptyStateProps): React.JSX.Element {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-slate-800 bg-[#0e1424]/60 p-12 text-center">
      <div className="rounded-full bg-slate-900 border border-slate-800 p-4 text-slate-500 mb-4">
        {hasActiveFilters ? (
          <SearchX className="h-8 w-8 text-amber-400" />
        ) : (
          <Database className="h-8 w-8 text-sky-400" />
        )}
      </div>

      <h3 className="text-base font-semibold text-white">
        {hasActiveFilters ? 'No Matching Evidence Artifacts' : 'No Corroborated Evidence Yet'}
      </h3>

      <p className="mt-1.5 max-w-md text-xs text-slate-400 leading-relaxed">
        {hasActiveFilters
          ? 'No evidence records match your current search query or facet criteria. Try widening your filters.'
          : 'No statutory registrations, LOC records, or contract shields have been ingested for this production.'}
      </p>

      {hasActiveFilters && onResetFilters && (
        <button
          onClick={onResetFilters}
          className="mt-5 flex items-center gap-2 rounded-xl bg-sky-500/20 hover:bg-sky-500/30 border border-sky-500/40 px-4 py-2 text-xs font-semibold text-sky-300 transition-colors"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          <span>Reset All Filters</span>
        </button>
      )}
    </div>
  );
}
