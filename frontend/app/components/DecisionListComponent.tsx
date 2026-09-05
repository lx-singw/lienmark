'use client';

/**
 * Lienmark Interactive Decision List Component
 * Renders the 12-claim production lineage list across Script Cut v7 -> v8,
 * with filterable tabs, explicit status badges, icons, text pills, and ARIA labels.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState, useMemo } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  Clock,
  Layers,
  ArrowRight,
  Filter,
  Check,
} from 'lucide-react';
import { DecisionState, EvaluatedClaim } from '@/lib/types';

export type DecisionFilterTab = 'all' | 'stale' | 'carried' | 'resolved';

export interface DecisionListComponentProps {
  claims: ReadonlyArray<EvaluatedClaim>;
  selectedClaimKey: string;
  onSelectClaim: (claimKey: string) => void;
  onOpenInGate?: (claimKey: string) => void;
}

export const DecisionListComponent: React.FC<DecisionListComponentProps> = ({
  claims,
  selectedClaimKey,
  onSelectClaim,
  onOpenInGate,
}) => {
  const [activeFilter, setActiveFilter] = useState<DecisionFilterTab>('all');

  // Dynamically compute counts to avoid stale synchronization
  const counts = useMemo(() => {
    let carried = 0;
    let stale = 0;
    let resolved = 0;

    claims.forEach((c) => {
      if (c.state === DecisionState.CARRIED_FORWARD) {
        carried++;
      } else if (c.state === DecisionState.STALE) {
        stale++;
      } else if (c.state === DecisionState.RE_ATTESTED || c.state === DecisionState.EXCEPTION) {
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

  // Filtered claim list
  const filteredClaims = useMemo(() => {
    switch (activeFilter) {
      case 'stale':
        return claims.filter((c) => c.state === DecisionState.STALE);
      case 'carried':
        return claims.filter((c) => c.state === DecisionState.CARRIED_FORWARD);
      case 'resolved':
        return claims.filter(
          (c) => c.state === DecisionState.RE_ATTESTED || c.state === DecisionState.EXCEPTION
        );
      case 'all':
      default:
        return claims;
    }
  }, [claims, activeFilter]);

  return (
    <div className="space-y-3" role="region" aria-label="12-Claim Production Lineage Ledger">
      {/* Header with Title and Filterable Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-1">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-sky-400" aria-hidden="true" />
          <h2 className="text-base font-semibold text-white">
            Production Lineage: Script Cut v7 &rarr; v8
          </h2>
          <span className="text-xs text-slate-400 font-mono">
            ({claims.length} Canonical Claims)
          </span>
        </div>

        {/* Filterable Tabs */}
        <div
          className="flex items-center gap-1 bg-slate-900/90 p-1 rounded-lg border border-slate-800 text-xs overflow-x-auto"
          role="tablist"
          aria-label="Filter Claims by Status"
        >
          <button
            type="button"
            role="tab"
            aria-selected={activeFilter === 'all'}
            onClick={() => setActiveFilter('all')}
            className={`px-2.5 py-1 rounded-md font-medium transition-all whitespace-nowrap ${
              activeFilter === 'all'
                ? 'bg-slate-700 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All Claims ({counts.all})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeFilter === 'stale'}
            onClick={() => setActiveFilter('stale')}
            className={`px-2.5 py-1 rounded-md font-medium transition-all whitespace-nowrap flex items-center gap-1 ${
              activeFilter === 'stale'
                ? 'bg-amber-900/70 text-amber-200 border border-amber-500/40 shadow-sm'
                : 'text-amber-400/80 hover:text-amber-300'
            }`}
          >
            <AlertTriangle className="h-3 w-3" aria-hidden="true" />
            <span>Stale / Reopened ({counts.stale})</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeFilter === 'carried'}
            onClick={() => setActiveFilter('carried')}
            className={`px-2.5 py-1 rounded-md font-medium transition-all whitespace-nowrap flex items-center gap-1 ${
              activeFilter === 'carried'
                ? 'bg-emerald-900/70 text-emerald-200 border border-emerald-500/40 shadow-sm'
                : 'text-emerald-400/80 hover:text-emerald-300'
            }`}
          >
            <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
            <span>Carried Forward ({counts.carried})</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeFilter === 'resolved'}
            onClick={() => setActiveFilter('resolved')}
            className={`px-2.5 py-1 rounded-md font-medium transition-all whitespace-nowrap flex items-center gap-1 ${
              activeFilter === 'resolved'
                ? 'bg-sky-900/70 text-sky-200 border border-sky-500/40 shadow-sm'
                : 'text-sky-400/80 hover:text-sky-300'
            }`}
          >
            <Check className="h-3 w-3" aria-hidden="true" />
            <span>Resolved ({counts.resolved})</span>
          </button>
        </div>
      </div>

      {/* Claims List Table / Cards */}
      <div className="rounded-xl border border-slate-800 bg-[#131b2e] overflow-hidden shadow-md">
        <div className="divide-y divide-slate-800/60 max-h-[660px] overflow-y-auto" role="list">
          {filteredClaims.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400">
              No claims match the active filter criteria.
            </div>
          ) : (
            filteredClaims.map((claim, idx) => {
              const isSelected = claim.stable_lineage_key === selectedClaimKey;
              const isItem11 = claim.stable_lineage_key === 'poster_noir_detective_magazine';
              const isItem12 = claim.stable_lineage_key === 'music_cue_midnight_serenade';

              return (
                <div
                  key={claim.stable_lineage_key}
                  onClick={() => onSelectClaim(claim.stable_lineage_key)}
                  className={`p-3.5 cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-[#1b2640] border-l-4 border-l-sky-400'
                      : 'hover:bg-slate-800/40 border-l-4 border-l-transparent'
                  }`}
                  role="listitem"
                  tabIndex={0}
                  aria-selected={isSelected}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onSelectClaim(claim.stable_lineage_key);
                    }
                  }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-xs font-mono font-bold text-slate-500">
                        #{String(idx + 1).padStart(2, '0')}
                      </span>
                      <h4 className="text-sm font-semibold text-white truncate">
                        {claim.stable_lineage_key.replace(/_/g, ' ')}
                      </h4>
                      <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-300 uppercase">
                        {claim.asset_type}
                      </span>
                    </div>

                    {/* Explicit Status Badges with ARIA labels */}
                    <div>
                      {claim.state === DecisionState.CARRIED_FORWARD && (
                        <span
                          className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-semibold badge-carried"
                          aria-label="[CARRIED FORWARD] - Unchanged from v7 baseline"
                        >
                          <CheckCircle2 className="h-3 w-3 text-emerald-400" aria-hidden="true" />
                          <span>[CARRIED FORWARD]</span>
                        </span>
                      )}
                      {claim.state === DecisionState.STALE && (
                        <span
                          className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-semibold badge-stale animate-pulse"
                          aria-label="[STALE - ACTION REQUIRED] - Material delta detected"
                        >
                          <AlertTriangle className="h-3 w-3 text-amber-400" aria-hidden="true" />
                          <span>[STALE - ACTION REQUIRED]</span>
                        </span>
                      )}
                      {claim.state === DecisionState.RE_ATTESTED && (
                        <span
                          className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-semibold badge-reattested"
                          aria-label="[RE-ATTESTED] - Approved under Public Domain"
                        >
                          <CheckCircle2 className="h-3 w-3 text-sky-400" aria-hidden="true" />
                          <span>[RE-ATTESTED]</span>
                        </span>
                      )}
                      {claim.state === DecisionState.EXCEPTION && (
                        <span
                          className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-semibold badge-exception"
                          aria-label="[EXCEPTION] - Excluded on Form E&O Schedule"
                        >
                          <AlertOctagon className="h-3 w-3 text-rose-400" aria-hidden="true" />
                          <span>[EXCEPTION]</span>
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="mt-1 text-xs text-slate-300 line-clamp-1">
                    {claim.description}
                  </p>

                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3 text-slate-500" aria-hidden="true" />
                      <span>{claim.scene}</span>
                      <span className="text-slate-600">&middot;</span>
                      <span className="text-slate-300">{claim.prominence}</span>
                    </span>

                    {/* Targeted CTA pill */}
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-slate-500 hidden sm:inline">
                        Reason: {claim.reason_code}
                      </span>

                      {isItem11 && claim.state === DecisionState.STALE && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onOpenInGate?.(claim.stable_lineage_key);
                          }}
                          className="rounded border border-amber-500/40 bg-amber-500/10 hover:bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold text-amber-300 transition-colors flex items-center gap-1"
                        >
                          <span>Inspect &rarr; Re-Attest</span>
                        </button>
                      )}

                      {isItem12 && claim.state === DecisionState.STALE && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onOpenInGate?.(claim.stable_lineage_key);
                          }}
                          className="rounded border border-rose-500/40 bg-rose-500/10 hover:bg-rose-500/20 px-2 py-0.5 text-[10px] font-semibold text-rose-300 transition-colors flex items-center gap-1"
                        >
                          <span>Inspect &rarr; Flag Exception</span>
                        </button>
                      )}

                      {claim.state === DecisionState.CARRIED_FORWARD && (
                        <span className="text-emerald-400/80 font-mono text-[10px]">
                          Audit Cost: $0.00
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

export default DecisionListComponent;
