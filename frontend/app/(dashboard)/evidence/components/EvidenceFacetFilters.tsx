'use client';

/**
 * Evidence Facet Filters Component
 * Multi-facet filtering toolbar for domain, source type, stance, and confidence tier.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import { Search, Filter, X } from 'lucide-react';
import { EvidenceFacets, EvidenceFilterState } from '../types';

interface EvidenceFacetFiltersProps {
  readonly filters: EvidenceFilterState;
  readonly facets: EvidenceFacets;
  readonly onFilterChange: (filters: EvidenceFilterState) => void;
  readonly onReset: () => void;
}

export function EvidenceFacetFilters({
  filters,
  facets,
  onFilterChange,
  onReset,
}: EvidenceFacetFiltersProps): React.JSX.Element {
  const hasActiveFilters = Boolean(
    filters.query ||
      filters.sourceType ||
      filters.stance ||
      filters.tier ||
      filters.category
  );

  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ ...filters, query: e.target.value });
  };

  const handleSourceTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFilterChange({ ...filters, sourceType: e.target.value });
  };

  const handleStanceChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFilterChange({ ...filters, stance: e.target.value });
  };

  const handleTierChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFilterChange({ ...filters, tier: e.target.value });
  };

  return (
    <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 p-4 space-y-3">
      <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={filters.query}
            onChange={handleQueryChange}
            placeholder="Search evidence snippets, citations, doctrines, SHA-256 hashes..."
            className="w-full rounded-xl bg-slate-950/70 border border-slate-800 pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500/50"
          />
        </div>

        {hasActiveFilters && (
          <button
            onClick={onReset}
            className="flex items-center gap-1 px-3 py-2 text-xs font-semibold text-rose-400 hover:text-rose-300 transition-colors"
          >
            <X className="h-3.5 w-3.5" />
            <span>Clear</span>
          </button>
        )}
      </div>

      <div className="flex flex-wrap gap-2.5 items-center pt-1 border-t border-slate-800/60">
        <div className="flex items-center gap-1 text-[11px] font-mono text-slate-400 mr-1">
          <Filter className="h-3 w-3 text-sky-400" />
          <span>Facets:</span>
        </div>

        <select
          value={filters.sourceType}
          onChange={handleSourceTypeChange}
          className="rounded-lg bg-slate-900 border border-slate-800 px-2.5 py-1 text-xs text-slate-300 focus:outline-none focus:border-sky-500/40"
        >
          <option value="">All Sources ({Object.values(facets.source_types || {}).reduce((a, b) => a + b, 0)})</option>
          {Object.entries(facets.source_types || {}).map(([st, count]) => (
            <option key={st} value={st}>
              {st.replace('_', ' ')} ({count})
            </option>
          ))}
        </select>

        <select
          value={filters.stance}
          onChange={handleStanceChange}
          className="rounded-lg bg-slate-900 border border-slate-800 px-2.5 py-1 text-xs text-slate-300 focus:outline-none focus:border-sky-500/40"
        >
          <option value="">All Stances ({Object.values(facets.stances || {}).reduce((a, b) => a + b, 0)})</option>
          {Object.entries(facets.stances || {}).map(([st, count]) => (
            <option key={st} value={st}>
              {st} ({count})
            </option>
          ))}
        </select>

        <select
          value={filters.tier}
          onChange={handleTierChange}
          className="rounded-lg bg-slate-900 border border-slate-800 px-2.5 py-1 text-xs text-slate-300 focus:outline-none focus:border-sky-500/40"
        >
          <option value="">All Tiers ({Object.values(facets.tiers || {}).reduce((a, b) => a + b, 0)})</option>
          {Object.entries(facets.tiers || {}).map(([tr, count]) => (
            <option key={tr} value={tr}>
              {tr.replace('_', ' ')} ({count})
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
