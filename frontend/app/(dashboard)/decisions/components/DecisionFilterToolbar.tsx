'use client';

/**
 * Decision Filter Toolbar Component
 * Filter by action type, text search, and view cryptographic continuity state.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import { Search, Filter, Lock, CheckCircle2 } from 'lucide-react';

interface DecisionFilterToolbarProps {
  readonly searchQuery: string;
  readonly onSearchChange: (query: string) => void;
  readonly activeStatus: string;
  readonly onStatusChange: (status: string) => void;
  readonly isChainValid: boolean;
  readonly chainLength: number;
}

const STATUS_FILTERS = ['ALL', 'APPROVED', 'REJECTED', 'EXCEPTION', 'SUPERSEDED'] as const;

export function DecisionFilterToolbar({
  searchQuery,
  onSearchChange,
  activeStatus,
  onStatusChange,
  isChainValid,
  chainLength,
}: DecisionFilterToolbarProps): React.JSX.Element {
  return (
    <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 p-4 space-y-3">
      <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search decisions by claim title, counsel rationale, actor, or SHA-256 hash..."
            className="w-full rounded-xl bg-slate-950/70 border border-slate-800 pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500/50"
          />
        </div>

        <div className="flex items-center gap-2 self-start md:self-auto">
          <div
            className={`flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-mono font-bold border ${
              isChainValid
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
            }`}
          >
            <Lock className="h-3.5 w-3.5" />
            <span>{isChainValid ? 'Ledger Valid' : 'Ledger Broken'}</span>
            <span className="text-slate-500">({chainLength} blocks)</span>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 items-center pt-2 border-t border-slate-800/60">
        <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1 mr-1">
          <Filter className="h-3 w-3 text-sky-400" />
          <span>Status:</span>
        </span>
        {STATUS_FILTERS.map((st) => (
          <button
            key={st}
            onClick={() => onStatusChange(st)}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
              activeStatus === st
                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            {st}
          </button>
        ))}
      </div>
    </div>
  );
}
