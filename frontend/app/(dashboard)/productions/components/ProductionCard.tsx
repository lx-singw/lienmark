'use client';

/**
 * ProductionCard Component
 * Portfolio card for motion picture/TV production with clearance health and revision tags.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import Link from 'next/link';
import { Film, GitBranch, FileText, ArrowUpRight, Activity } from 'lucide-react';
import { ProductionItem } from '../types';
import { ClearanceHealthMeter } from './ClearanceHealthMeter';

export const ProductionCard: React.FC<{ readonly production: ProductionItem }> = ({ production }) => {
  return (
    <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 backdrop-blur-md p-5 space-y-4 hover:border-slate-700/80 transition-all shadow-xl shadow-black/40">
      {/* Header Info */}
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="rounded bg-sky-500/10 border border-sky-500/30 px-2 py-0.5 text-[10px] font-mono text-sky-400">
              {production.imprint}
            </span>
            <span className="text-xs text-slate-400">{production.genre}</span>
          </div>
          <h3 className="text-base font-bold text-white tracking-tight">{production.title}</h3>
        </div>

        {/* Active Revision Tag */}
        <div className="flex items-center gap-1.5 rounded-lg bg-slate-900 border border-slate-700/60 px-2.5 py-1 text-xs font-mono text-slate-300">
          <GitBranch className="h-3.5 w-3.5 text-sky-400" />
          <span>{production.activeRevision}</span>
        </div>
      </div>

      {/* Clearance Health Progress Meter */}
      <ClearanceHealthMeter
        total={production.totalClaims}
        carried={production.carriedCount}
        reattested={production.reattestedCount}
        stale={production.staleCount}
        exception={production.exceptionCount}
      />

      {/* Claim Breakdown Stats */}
      <div className="grid grid-cols-4 gap-2 pt-2 border-t border-slate-800/80 text-center text-xs">
        <div className="rounded-lg bg-slate-900/60 p-2 border border-slate-800/60">
          <span className="text-[10px] text-slate-400 font-mono block">Props/Art</span>
          <span className="font-mono font-bold text-slate-200">{production.claimBreakdown.props}</span>
        </div>
        <div className="rounded-lg bg-slate-900/60 p-2 border border-slate-800/60">
          <span className="text-[10px] text-slate-400 font-mono block">Music</span>
          <span className="font-mono font-bold text-slate-200">{production.claimBreakdown.music}</span>
        </div>
        <div className="rounded-lg bg-slate-900/60 p-2 border border-slate-800/60">
          <span className="text-[10px] text-slate-400 font-mono block">Brands</span>
          <span className="font-mono font-bold text-slate-200">{production.claimBreakdown.brands}</span>
        </div>
        <div className="rounded-lg bg-slate-900/60 p-2 border border-slate-800/60">
          <span className="text-[10px] text-slate-400 font-mono block">Persons</span>
          <span className="font-mono font-bold text-slate-200">{production.claimBreakdown.persons}</span>
        </div>
      </div>

      {/* Actions Footer */}
      <div className="flex items-center justify-between pt-1">
        <Link
          href="/"
          className="flex items-center gap-1.5 text-xs font-semibold text-sky-400 hover:text-sky-300 transition-colors"
        >
          <Activity className="h-3.5 w-3.5" />
          <span>Open Reviewer Dashboard</span>
          <ArrowUpRight className="h-3 w-3" />
        </Link>
        <Link
          href={`/report/${production.reportSlug}`}
          className="flex items-center gap-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 px-3 py-1.5 text-xs font-medium text-amber-300 hover:bg-amber-500/20 transition-colors"
        >
          <FileText className="h-3.5 w-3.5" />
          <span>Form E&amp;O-2026</span>
        </Link>
      </div>
    </div>
  );
};

export default ProductionCard;
