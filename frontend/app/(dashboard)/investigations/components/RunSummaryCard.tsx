'use client';

/**
 * RunSummaryCard Component
 * Displays run metadata, live execution status, and spend guard metrics.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import { Compass, Sparkles, Search, DollarSign, Clock, CheckCircle2, AlertTriangle } from 'lucide-react';
import { InvestigationRun } from '../types';

export const RunSummaryCard: React.FC<{ readonly run: InvestigationRun }> = ({ run }) => {
  const isRunning = run.status === 'running';

  return (
    <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 backdrop-blur-md p-5 space-y-4">
      {/* Title & Status */}
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-sky-400">{run.id}</span>
            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-mono font-bold uppercase ${
              isRunning
                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 animate-pulse'
                : run.status === 'completed'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
            }`}>
              {run.status}
            </span>
          </div>
          <h3 className="text-base font-bold text-white tracking-tight">{run.name}</h3>
          <p className="text-xs text-slate-400">Target Asset: <strong className="text-slate-200">{run.targetAsset}</strong></p>
        </div>

        <div className="flex items-center gap-1 text-xs font-mono text-slate-400">
          <Clock className="h-3.5 w-3.5 text-slate-500" />
          <span>{(run.elapsedMs / 1000).toFixed(2)}s</span>
        </div>
      </div>

      {/* Telemetry Metrics Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
        <div className="rounded-xl bg-slate-900/60 p-2.5 border border-slate-800/80">
          <div className="flex items-center justify-center gap-1 text-[10px] text-slate-400">
            <Sparkles className="h-3 w-3 text-sky-400" /> Model
          </div>
          <p className="font-mono font-bold text-slate-200 mt-0.5">{run.modelUsed}</p>
        </div>
        <div className="rounded-xl bg-slate-900/60 p-2.5 border border-slate-800/80">
          <div className="flex items-center justify-center gap-1 text-[10px] text-slate-400">
            <Search className="h-3 w-3 text-cyan-400" /> Search Provider
          </div>
          <p className="font-mono font-bold text-slate-200 mt-0.5">{run.searchProvider}</p>
        </div>
        <div className="rounded-xl bg-slate-900/60 p-2.5 border border-slate-800/80">
          <div className="flex items-center justify-center gap-1 text-[10px] text-slate-400">
            <Compass className="h-3 w-3 text-purple-400" /> Multi-Hop Queries
          </div>
          <p className="font-mono font-bold text-slate-200 mt-0.5">{run.apiCallsCount} calls</p>
        </div>
        <div className="rounded-xl bg-slate-900/60 p-2.5 border border-slate-800/80">
          <div className="flex items-center justify-center gap-1 text-[10px] text-slate-400">
            <DollarSign className="h-3 w-3 text-emerald-400" /> USD Spend
          </div>
          <p className="font-mono font-bold text-emerald-400 mt-0.5">${run.spendUsd.toFixed(2)}</p>
        </div>
      </div>
    </div>
  );
};

export default RunSummaryCard;
