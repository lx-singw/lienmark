'use client';

/**
 * Lienmark High-Contrast Cinematic ClaimsTable Component
 * Hollywood Studio Legal Ops UI/UX Overhaul - Component 4
 * High-contrast cinematic clearance matrix displaying script revision claims,
 * scene timecodes (e.g. SC 42 (00:41:12)), asset category badges, and clearance status indicators.
 * Instant row selection updates the adjacent 4D Inspector without modal popups.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState, useMemo, useCallback } from 'react';
import {
  Film,
  Filter,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  Check,
  Search,
  ShieldCheck,
  Layers,
  ArrowUpDown,
} from 'lucide-react';
import { DecisionState, EvaluatedClaim, UserRole } from '@/lib/types';
import ClaimRow from './ClaimRow';

export type ClaimFilterType = 'all' | 'stale' | 'carried' | 'resolved';

export interface ClaimsTableProps {
  claims: ReadonlyArray<EvaluatedClaim>;
  selectedClaimKey: string;
  onSelectClaim: (claimKey: string) => void;
  onOpenInGate?: (claimKey: string) => void;
  userRole?: UserRole;
  title?: string;
  showFilters?: boolean;
  className?: string;
}

export const ClaimsTable: React.FC<ClaimsTableProps> = ({
  claims,
  selectedClaimKey,
  onSelectClaim,
  onOpenInGate,
  userRole = UserRole.REVIEWER,
  title = 'Production Rights Clearance Matrix (Script Cut v7 → v8)',
  showFilters = true,
  className = '',
}) => {
  const [activeFilter, setActiveFilter] = useState<ClaimFilterType>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Dynamically calculate counts to prevent stale synchronization
  const counts = useMemo(() => {
    let carried = 0;
    let stale = 0;
    let resolved = 0;

    claims.forEach((claim) => {
      if (claim.state === DecisionState.CARRIED_FORWARD) {
        carried++;
      } else if (claim.state === DecisionState.STALE) {
        stale++;
      } else if (
        claim.state === DecisionState.RE_ATTESTED ||
        claim.state === DecisionState.EXCEPTION
      ) {
        resolved++;
      }
    });

    return {
      all: claims.length,
      carried,
      stale,
      resolved,
    };
  }, [claims]);

  // Filter and search claims
  const filteredClaims = useMemo(() => {
    return claims.filter((claim) => {
      // 1. Status Filter
      if (activeFilter === 'stale' && claim.state !== DecisionState.STALE) return false;
      if (activeFilter === 'carried' && claim.state !== DecisionState.CARRIED_FORWARD) return false;
      if (
        activeFilter === 'resolved' &&
        claim.state !== DecisionState.RE_ATTESTED &&
        claim.state !== DecisionState.EXCEPTION
      )
        return false;

      // 2. Search Query Filter
      if (searchQuery.trim().length > 0) {
        const query = searchQuery.toLowerCase();
        const keyMatch = claim.stable_lineage_key.toLowerCase().includes(query);
        const descMatch = claim.description.toLowerCase().includes(query);
        const sceneMatch = claim.scene.toLowerCase().includes(query);
        const assetMatch = claim.asset_type.toLowerCase().includes(query);
        const reasonMatch = claim.reason_code.toLowerCase().includes(query);
        if (!keyMatch && !descMatch && !sceneMatch && !assetMatch && !reasonMatch) {
          return false;
        }
      }

      return true;
    });
  }, [claims, activeFilter, searchQuery]);

  // Keyboard navigation handler for table rows
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (filteredClaims.length === 0) return;

      const currentIndex = filteredClaims.findIndex(
        (c) => c.stable_lineage_key === selectedClaimKey
      );

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const nextIndex = (currentIndex + 1) % filteredClaims.length;
        onSelectClaim(filteredClaims[nextIndex].stable_lineage_key);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const prevIndex =
          currentIndex <= 0 ? filteredClaims.length - 1 : currentIndex - 1;
        onSelectClaim(filteredClaims[prevIndex].stable_lineage_key);
      }
    },
    [filteredClaims, selectedClaimKey, onSelectClaim]
  );

  return (
    <section
      aria-label="High-Contrast Cinematic Claims Matrix"
      className={`space-y-3.5 ${className}`}
      onKeyDown={handleKeyDown}
    >
      {/* Matrix Header Toolbar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 px-1">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/20 text-sky-400 border border-sky-500/30">
            <Film className="h-4 w-4" aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
              <span>{title}</span>
              <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-300 font-semibold border border-slate-700">
                {filteredClaims.length} of {claims.length}
              </span>
            </h2>
            <p className="text-xs text-slate-400 font-mono">
              High-contrast cinematic clearance matrix &middot; Instant 4D inspector synchronization
            </p>
          </div>
        </div>

        {/* Search & Filter Controls */}
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
                onChange={(e) => setSearchQuery(e.target.value)}
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
                onClick={() => setActiveFilter('all')}
                className={`px-2.5 py-1 rounded font-medium transition-all whitespace-nowrap text-xs ${
                  activeFilter === 'all'
                    ? 'bg-slate-700 text-white shadow-sm font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                All ({counts.all})
              </button>

              <button
                type="button"
                role="tab"
                aria-selected={activeFilter === 'stale'}
                onClick={() => setActiveFilter('stale')}
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
                onClick={() => setActiveFilter('carried')}
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
                onClick={() => setActiveFilter('resolved')}
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

      {/* Cinematic Table Matrix Container */}
      <div className="rounded-xl border border-slate-800 bg-[#0f172a] shadow-xl overflow-hidden">
        <div className="overflow-x-auto max-h-[640px] overflow-y-auto">
          <table
            className="w-full text-left border-collapse"
            role="grid"
            aria-label="Claims Rights Matrix"
          >
            {/* Table Matrix Header */}
            <thead className="sticky top-0 z-10 bg-[#131d33] border-b border-slate-700/80 text-[11px] font-mono uppercase tracking-wider text-slate-300">
              <tr>
                <th scope="col" className="py-2.5 px-2.5 text-center w-12 font-bold">
                  #
                </th>
                <th scope="col" className="py-2.5 px-2.5 w-40 font-bold">
                  Scene Timecode
                </th>
                <th scope="col" className="py-2.5 px-2.5 font-bold">
                  Asset &amp; Category
                </th>
                <th scope="col" className="py-2.5 px-2.5 hidden 2xl:table-cell font-bold">
                  Prominence &amp; Context
                </th>
                <th scope="col" className="py-2.5 px-2.5 w-48 font-bold">
                  Clearance Status
                </th>
                <th scope="col" className="py-2.5 px-2.5 text-right w-28 font-bold">
                  4D Action
                </th>
              </tr>
            </thead>

            {/* Table Matrix Body */}
            <tbody className="divide-y divide-slate-800/60 bg-[#0c1322]">
              {filteredClaims.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-xs text-slate-400">
                    <div className="max-w-sm mx-auto space-y-2">
                      <Filter className="h-6 w-6 text-slate-600 mx-auto" aria-hidden="true" />
                      <p className="font-semibold text-slate-300">No claims match the active filter</p>
                      <p className="text-[11px] text-slate-500">
                        Try clearing search terms or selecting &lsquo;All&rsquo; to display all 12 production claims.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredClaims.map((claim, idx) => (
                  <ClaimRow
                    key={claim.stable_lineage_key}
                    claim={claim}
                    index={idx}
                    isSelected={claim.stable_lineage_key === selectedClaimKey}
                    onSelect={onSelectClaim}
                    onOpenInGate={onOpenInGate}
                    userRole={userRole}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Table Matrix Footer Info */}
        <div className="p-3 bg-[#131d33]/90 border-t border-slate-800 flex flex-wrap items-center justify-between text-[11px] font-mono text-slate-400">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" aria-hidden="true" />
            <span>Autonomous Invariant Engine: Fail-Closed Standard Applied</span>
          </div>
          <div className="flex items-center gap-3">
            <span>Click any row to inspect in adjacent 4D Inspector (No Modal)</span>
            <span className="text-slate-600">&middot;</span>
            <span className="text-sky-300 font-bold">
              Selected: {selectedClaimKey || 'None'}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ClaimsTable;
