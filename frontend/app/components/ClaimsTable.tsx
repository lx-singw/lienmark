'use client';

/**
 * Lienmark High-Contrast Cinematic ClaimsTable Component
 * Hollywood Studio Legal Ops UI/UX Overhaul - Component 4
 * High-contrast cinematic clearance matrix displaying script revision claims,
 * scene timecodes (e.g. SC 42 (00:41:12)), asset category badges, and clearance status indicators.
 * Integrated with HITL Waiting For Info clarification badge.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState, useMemo, useCallback } from 'react';
import { Filter } from 'lucide-react';
import { DecisionState, EvaluatedClaim, UserRole } from '@/lib/types';
import ClaimRow from './ClaimRow';
import {
  ClaimsTableToolbar,
  ClaimFilterType,
} from './claims/ClaimsTableToolbar';
import { ClarificationRequestUI } from './hitl';

export type { ClaimFilterType };

export interface ClaimsTableProps {
  claims: ReadonlyArray<EvaluatedClaim>;
  selectedClaimKey: string;
  onSelectClaim: (claimKey: string) => void;
  onOpenInGate?: (claimKey: string) => void;
  userRole?: UserRole;
  title?: string;
  showFilters?: boolean;
  className?: string;
  activeClarifications?: ReadonlyArray<ClarificationRequestUI>;
  activeClarificationKeys?: ReadonlyArray<string>;
  onOpenClarification?: (claimKey: string) => void;
  onOpenOverride?: (claimKey: string) => void;
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
  activeClarifications = [],
  activeClarificationKeys = [],
  onOpenClarification,
  onOpenOverride,
}) => {
  const [activeFilter, setActiveFilter] = useState<ClaimFilterType>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const activeKeySet = useMemo(() => {
    const set = new Set<string>(activeClarificationKeys);
    activeClarifications.forEach((c) => set.add(c.claimKey));
    return set;
  }, [activeClarifications, activeClarificationKeys]);

  // Dynamically calculate counts to prevent stale synchronization
  const counts = useMemo(() => {
    let carried = 0;
    let stale = 0;
    let resolved = 0;
    let waitingInfo = 0;

    claims.forEach((claim) => {
      const isWaiting =
        activeKeySet.has(claim.stable_lineage_key) ||
        Boolean(claim.has_active_clarification);

      if (isWaiting) waitingInfo++;

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

    return { all: claims.length, carried, stale, resolved, waitingInfo };
  }, [claims, activeKeySet]);

  // Filter and search claims
  const filteredClaims = useMemo(() => {
    return claims.filter((claim) => {
      const isWaiting =
        activeKeySet.has(claim.stable_lineage_key) ||
        Boolean(claim.has_active_clarification);

      if (activeFilter === 'waiting_info' && !isWaiting) return false;
      if (activeFilter === 'stale' && claim.state !== DecisionState.STALE) return false;
      if (activeFilter === 'carried' && claim.state !== DecisionState.CARRIED_FORWARD) return false;
      if (
        activeFilter === 'resolved' &&
        claim.state !== DecisionState.RE_ATTESTED &&
        claim.state !== DecisionState.EXCEPTION
      ) {
        return false;
      }

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
  }, [claims, activeFilter, searchQuery, activeKeySet]);

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
      <ClaimsTableToolbar
        title={title}
        totalClaimsCount={claims.length}
        filteredClaimsCount={filteredClaims.length}
        showFilters={showFilters}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        activeFilter={activeFilter}
        onFilterChange={setActiveFilter}
        counts={counts}
      />

      {/* Cinematic Table Matrix Container */}
      <div className="rounded-xl border border-slate-800 bg-[#0f172a] shadow-xl overflow-hidden">
        <div className="overflow-x-auto max-h-[640px] overflow-y-auto">
          <table
            className="w-full text-left border-collapse"
            role="grid"
            aria-label="Claims Rights Matrix"
          >
            <thead className="sticky top-0 z-10 bg-[#131d33] border-b border-slate-700/80 text-[11px] font-mono uppercase tracking-wider text-slate-300">
              <tr>
                <th scope="col" className="py-2.5 px-2.5 text-center w-12 font-bold">#</th>
                <th scope="col" className="py-2.5 px-2.5 w-40 font-bold">Scene Timecode</th>
                <th scope="col" className="py-2.5 px-2.5 font-bold">Asset &amp; Category</th>
                <th scope="col" className="py-2.5 px-2.5 hidden 2xl:table-cell font-bold">Prominence &amp; Context</th>
                <th scope="col" className="py-2.5 px-2.5 w-48 font-bold">Clearance Status</th>
                <th scope="col" className="py-2.5 px-2.5 text-right w-28 font-bold">4D Action</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-800/60 bg-[#0c1322]">
              {filteredClaims.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-xs text-slate-400">
                    <div className="max-w-sm mx-auto space-y-2">
                      <Filter className="h-6 w-6 text-slate-600 mx-auto" aria-hidden="true" />
                      <p className="font-semibold text-slate-300">No claims match the active filter</p>
                      <p className="text-[11px] text-slate-500">
                        Try clearing search terms or selecting &lsquo;All&rsquo; to display all claims.
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
                    hasActiveClarification={
                      activeKeySet.has(claim.stable_lineage_key) ||
                      Boolean(claim.has_active_clarification)
                    }
                    onOpenClarification={onOpenClarification}
                    onOpenOverride={onOpenOverride}
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
            <span className="text-sky-300 font-bold">Selected: {selectedClaimKey || 'None'}</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ClaimsTable;
