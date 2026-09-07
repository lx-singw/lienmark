'use client';

/**
 * Lienmark Claims Table Toolbar Component
 * Matrix header, search input, and filter controls for production clearance claims.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import {
  Film,
  Search,
  AlertTriangle,
  CheckCircle2,
  Check,
  HelpCircle,
} from 'lucide-react';

export type ClaimFilterType = 'all' | 'stale' | 'carried' | 'resolved' | 'waiting_info';

export interface ClaimsTableToolbarProps {
  readonly title: string;
  readonly totalClaimsCount: number;
  readonly filteredClaimsCount: number;
  readonly showFilters?: boolean;
  readonly searchQuery: string;
  readonly onSearchChange: (query: string) => void;
  readonly activeFilter: ClaimFilterType;
  readonly onFilterChange: (filter: ClaimFilterType) => void;
  readonly counts: {
    readonly all: number;
    readonly carried: number;
    readonly stale: number;
    readonly resolved: number;
    readonly waitingInfo?: number;
  };
}

export const ClaimsTableToolbar: React.FC<ClaimsTableToolbarProps> = ({
  title,
  totalClaimsCount,
  filteredClaimsCount,
  showFilters = true,
  searchQuery,
  onSearchChange,
  activeFilter,
  onFilterChange,
  counts,
}) => {
  return (
    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 px-1">
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/20 text-sky-400 border border-sky-500/30">
          <Film className="h-4 w-4" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
            <span>{title}</span>
            <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-300 font-semibold border border-slate-700">
              {filteredClaimsCount} of {totalClaimsCount}
            </span>
          </h2>
          <p className="text-xs text-slate-400 font-mono">
            High-contrast cinematic clearance matrix &middot; Instant 4D inspector synchronization
          </p>
        </div>
      </div>

      {showFilters && (
        <div className="flex flex-wrap items-center gap-2">
          {/* Quick Search */}
          <div className="relative">
            <Search
              className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500"
              aria-hidden="true"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search claims or timecodes..."
              className="rounded-lg border border-slate-700 bg-slate-900/90 pl-8 pr-3 py-1 text-xs text-slate-200 placeholder-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 w-44 sm:w-56 font-sans transition-colors"
              aria-label="Search claims by keyword, scene, or timecode"
            />
          </div>

          {/* Filterable Pills */}
          <div
            className="flex items-center gap-1 bg-slate-900/90 p-1 rounded-lg border border-slate-800 text-xs overflow-x-auto"
            role="tablist"
            aria-label="Filter Matrix Claims"
          >
            <button
              type="button"
              role="tab"
              aria-selected={activeFilter === 'all'}
              onClick={() => onFilterChange('all')}
              className={`px-2.5 py-1 rounded font-medium transition-all whitespace-nowrap text-xs ${
                activeFilter === 'all'
                  ? 'bg-slate-700 text-white shadow-sm font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All ({counts.all})
            </button>

            {Boolean(counts.waitingInfo && counts.waitingInfo > 0) && (
              <button
                type="button"
                role="tab"
                aria-selected={activeFilter === 'waiting_info'}
                onClick={() => onFilterChange('waiting_info')}
                className={`px-2.5 py-1 rounded font-medium transition-all whitespace-nowrap text-xs flex items-center gap-1 ${
                  activeFilter === 'waiting_info'
                    ? 'bg-amber-950 text-amber-200 border border-amber-500/80 shadow-sm font-semibold animate-pulse'
                    : 'text-amber-400 hover:text-amber-300'
                }`}
              >
                <HelpCircle className="h-3 w-3" aria-hidden="true" />
                <span>Waiting Info ({counts.waitingInfo})</span>
              </button>
            )}

            <button
              type="button"
              role="tab"
              aria-selected={activeFilter === 'stale'}
              onClick={() => onFilterChange('stale')}
              className={`px-2.5 py-1 rounded font-medium transition-all whitespace-nowrap text-xs flex items-center gap-1 ${
                activeFilter === 'stale'
                  ? 'bg-amber-900/80 text-amber-200 border border-amber-500/50 shadow-sm font-semibold'
                  : 'text-amber-400/90 hover:text-amber-300'
              }`}
            >
              <AlertTriangle className="h-3 w-3" aria-hidden="true" />
              <span>Stale ({counts.stale})</span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={activeFilter === 'carried'}
              onClick={() => onFilterChange('carried')}
              className={`px-2.5 py-1 rounded font-medium transition-all whitespace-nowrap text-xs flex items-center gap-1 ${
                activeFilter === 'carried'
                  ? 'bg-emerald-900/80 text-emerald-200 border border-emerald-500/50 shadow-sm font-semibold'
                  : 'text-emerald-400/90 hover:text-emerald-300'
              }`}
            >
              <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
              <span>Carried ({counts.carried})</span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={activeFilter === 'resolved'}
              onClick={() => onFilterChange('resolved')}
              className={`px-2.5 py-1 rounded font-medium transition-all whitespace-nowrap text-xs flex items-center gap-1 ${
                activeFilter === 'resolved'
                  ? 'bg-sky-900/80 text-sky-200 border border-sky-500/50 shadow-sm font-semibold'
                  : 'text-sky-400/90 hover:text-sky-300'
              }`}
            >
              <Check className="h-3 w-3" aria-hidden="true" />
              <span>Resolved ({counts.resolved})</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ClaimsTableToolbar;
