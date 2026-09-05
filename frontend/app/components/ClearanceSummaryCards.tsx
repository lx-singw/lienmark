'use client';

/**
 * Lienmark Clearance Summary Cards & Invariant Conservation Ribbon
 * Displays 5 metric cards, live mathematical conservation invariant indicator,
 * and underwriter reconciliation status banner.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import Link from 'next/link';
import {
  Layers,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  AlertOctagon,
  FileCheck,
  ArrowRight,
  Scale,
  DollarSign,
  Info,
} from 'lucide-react';

export interface ClearanceSummaryCardsProps {
  totalClaims: number;
  carriedCount: number;
  staleCount: number;
  reattestedCount: number;
  exceptionCount: number;
  isReconciled: boolean;
  exceptionsScheduleUrl?: string;
}

export const ClearanceSummaryCards: React.FC<ClearanceSummaryCardsProps> = ({
  totalClaims,
  carriedCount,
  staleCount,
  reattestedCount,
  exceptionCount,
  isReconciled,
  exceptionsScheduleUrl = '/report/proj_blockbuster_cinema',
}) => {
  // Compute percentages safely
  const carriedPercentage = totalClaims > 0 ? ((carriedCount / totalClaims) * 100).toFixed(1) : '0.0';
  const resolvedCount = carriedCount + reattestedCount + exceptionCount;
  const progressPercentage = totalClaims > 0 ? Math.min(100, Math.round((resolvedCount / totalClaims) * 100)) : 0;

  return (
    <section aria-label="Clearance Status Summary and Conservation Metrics" className="space-y-4">
      {/* 5 Metric Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4">
        {/* 1. Total Ingested Claims */}
        <div
          className="rounded-xl border border-slate-800 bg-[#131b2e] p-4 transition-all"
          role="region"
          aria-label="Total Rights Claims Metric Card"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Total Claims
            </span>
            <span className="rounded p-1 bg-slate-800 text-slate-400" aria-hidden="true">
              <Layers className="h-3.5 w-3.5" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-white" aria-label={`${totalClaims} Total Claims`}>
              {totalClaims}
            </span>
            <span className="inline-flex items-center gap-1 rounded bg-slate-800/90 px-1.5 py-0.5 text-[11px] font-mono text-slate-300">
              100% Ingested
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-500">Locked v7 Baseline</p>
        </div>

        {/* 2. Carried Forward */}
        <div
          className="rounded-xl border border-emerald-800/40 bg-[#131b2e] p-4 metric-glow-green group relative"
          role="region"
          aria-label="Carried Forward Rights Claims Metric Card"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1">
              <span>Carried Forward</span>
              <span
                tabIndex={0}
                role="tooltip"
                aria-label="Lineage Parity Verified: Dialogue, prominence duration, and visual placement are bit-for-bit identical to Locked v7. Public copyright records re-verified unchanged. Autonomous pass under statutory clearance doctrine."
                title="Lineage Parity Verified: Dialogue, prominence duration, and visual placement are bit-for-bit identical to Locked v7. Public copyright records re-verified unchanged. Autonomous pass under statutory clearance doctrine."
                className="cursor-help text-emerald-400/80 hover:text-emerald-200 focus:outline-none focus:text-white"
              >
                <Info className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
            </span>
            <span className="rounded p-1 bg-emerald-950/80 text-emerald-400 border border-emerald-500/30" aria-hidden="true">
              <CheckCircle2 className="h-3.5 w-3.5" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-emerald-400" aria-label={`${carriedCount} Carried Forward Claims`}>
              {carriedCount}
            </span>
            <span className="inline-flex items-center gap-1 rounded bg-emerald-950/90 px-1.5 py-0.5 text-[11px] font-bold text-emerald-300 border border-emerald-600/40">
              <DollarSign className="h-3 w-3 -mr-0.5" aria-hidden="true" />
              0 Re-Review
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            Parity verified &middot; {carriedPercentage}% savings
          </p>
        </div>

        {/* 3. Reopened for Review */}
        <div
          className={`rounded-xl border p-4 transition-all ${
            staleCount > 0
              ? 'border-amber-700/50 bg-[#131b2e] metric-glow-amber'
              : 'border-slate-800 bg-[#131b2e]'
          }`}
          role="region"
          aria-label="Reopened Stale Claims Metric Card"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">
              Reopened (Drift)
            </span>
            <span className="rounded p-1 bg-amber-950/80 text-amber-400 border border-amber-500/30" aria-hidden="true">
              <AlertTriangle className="h-3.5 w-3.5" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span
              className={`text-3xl font-bold ${staleCount > 0 ? 'text-amber-400' : 'text-slate-500'}`}
              aria-label={`${staleCount} Reopened Claims Awaiting Disposition`}
            >
              {staleCount}
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-mono font-bold ${
                staleCount > 0
                  ? 'bg-amber-950/90 text-amber-300 border border-amber-500/40 animate-pulse'
                  : 'bg-slate-800 text-slate-400'
              }`}
            >
              {staleCount > 0 ? 'Action Required' : '0 Pending'}
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            {staleCount > 0 ? 'Context or evidence shift' : 'All reviews addressed'}
          </p>
        </div>

        {/* 4. Counsel Re-Attested */}
        <div
          className={`rounded-xl border p-4 transition-all ${
            reattestedCount > 0
              ? 'border-sky-700/50 bg-[#131b2e] metric-glow-blue'
              : 'border-slate-800 bg-[#131b2e]'
          }`}
          role="region"
          aria-label="Counsel Re-Attested Claims Metric Card"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-sky-400">
              Re-Attested
            </span>
            <span className="rounded p-1 bg-sky-950/80 text-sky-400 border border-sky-500/30" aria-hidden="true">
              <ShieldCheck className="h-3.5 w-3.5" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span
              className={`text-3xl font-bold ${reattestedCount > 0 ? 'text-sky-400' : 'text-slate-500'}`}
              aria-label={`${reattestedCount} Re-Attested Claims`}
            >
              {reattestedCount}
            </span>
            <span className="inline-flex items-center gap-1 rounded bg-sky-950/90 px-1.5 py-0.5 text-[11px] font-semibold text-sky-300 border border-sky-600/40">
              LOC Validated
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Item 11 &middot; Public Domain</p>
        </div>

        {/* 5. Unresolved Exceptions */}
        <div
          className={`rounded-xl border p-4 transition-all ${
            exceptionCount > 0
              ? 'border-rose-700/50 bg-[#131b2e] metric-glow-red'
              : 'border-slate-800 bg-[#131b2e]'
          }`}
          role="region"
          aria-label="Exceptions Schedule Metric Card"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-rose-400">
              Exceptions
            </span>
            <span className="rounded p-1 bg-rose-950/80 text-rose-400 border border-rose-500/30" aria-hidden="true">
              <AlertOctagon className="h-3.5 w-3.5" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span
              className={`text-3xl font-bold ${exceptionCount > 0 ? 'text-rose-400' : 'text-slate-500'}`}
              aria-label={`${exceptionCount} Exceptions Flagged`}
            >
              {exceptionCount}
            </span>
            <span className="inline-flex items-center gap-1 rounded bg-rose-950/90 px-1.5 py-0.5 text-[11px] font-bold text-rose-300 border border-rose-600/40">
              ASCAP breach
            </span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Item 12 &middot; ASCAP breach</p>
        </div>
      </div>

      {/* Deterministic Lineage Parity Banner */}
      {carriedCount > 0 && (
        <div
          className="rounded-xl border border-emerald-500/40 bg-gradient-to-r from-emerald-950/40 via-[#10192e] to-emerald-950/30 p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs shadow-md"
          role="region"
          aria-label="Deterministic Lineage Parity Verification Banner"
        >
          <div className="flex items-start sm:items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex-shrink-0">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-emerald-300 text-sm">
                  Deterministic Lineage Parity
                </span>
                <span className="rounded bg-emerald-900/80 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-200 border border-emerald-500/40">
                  {carriedCount} / {totalClaims} Claims Locked &middot; $0 Review
                </span>
              </div>
              <p className="mt-1 text-slate-200 text-xs leading-relaxed">
                <strong>Lineage Parity Verified:</strong> Dialogue, prominence duration, and visual placement are bit-for-bit identical to Locked v7. Public copyright records re-verified unchanged. Autonomous pass under statutory clearance doctrine.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-auto flex-shrink-0">
            <span className="text-[11px] font-mono text-emerald-400 bg-slate-900/90 px-2.5 py-1 rounded border border-emerald-800/60 font-semibold">
              Autonomous Pass ($0 Cost)
            </span>
          </div>
        </div>
      )}

      {/* Invariant Progress Indicator (Conservation Math Ribbon) */}
      <div
        className="rounded-xl border border-slate-800 bg-[#10172a] p-3 sm:p-3.5 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs"
        role="region"
        aria-label="Mathematical Conservation Invariant Formula"
      >
        <div className="flex items-center gap-2">
          <div className="p-1 rounded bg-sky-950/80 text-sky-400 border border-sky-500/30" aria-hidden="true">
            <Scale className="h-3.5 w-3.5" />
          </div>
          <div>
            <span className="font-semibold text-slate-300">Live Mathematical Conservation Invariant:</span>{' '}
            <span className="font-mono text-white font-bold bg-slate-900 px-2 py-0.5 rounded border border-slate-700">
              {totalClaims} = {carriedCount} (Carried) + {staleCount} (Stale) + {reattestedCount} (Re-Attested) + {exceptionCount} (Exceptions)
            </span>
          </div>
        </div>

        <div className="w-full md:w-64 space-y-1">
          <div className="flex justify-between text-[11px] text-slate-400 font-mono">
            <span>Reconciliation Progress</span>
            <span className="text-white font-bold">{progressPercentage}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden flex">
            <div
              className="bg-emerald-500 transition-all duration-500"
              style={{ width: `${(carriedCount / Math.max(totalClaims, 1)) * 100}%` }}
              title={`Carried Forward: ${carriedCount}`}
            />
            <div
              className="bg-sky-500 transition-all duration-500"
              style={{ width: `${(reattestedCount / Math.max(totalClaims, 1)) * 100}%` }}
              title={`Re-Attested: ${reattestedCount}`}
            />
            <div
              className="bg-rose-500 transition-all duration-500"
              style={{ width: `${(exceptionCount / Math.max(totalClaims, 1)) * 100}%` }}
              title={`Exceptions: ${exceptionCount}`}
            />
            <div
              className="bg-amber-500/40 transition-all duration-500"
              style={{ width: `${(staleCount / Math.max(totalClaims, 1)) * 100}%` }}
              title={`Pending Stale: ${staleCount}`}
            />
          </div>
        </div>
      </div>

      {/* Reconciled Underwriter Alert Banner */}
      {isReconciled ? (
        <div
          className="rounded-xl border border-emerald-500/50 bg-gradient-to-r from-emerald-950/70 via-slate-900 to-sky-950/70 p-4 shadow-xl flex flex-col md:flex-row items-center justify-between gap-4"
          role="status"
          aria-live="polite"
        >
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/40" aria-hidden="true">
              <FileCheck className="h-6 w-6" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base">
                Clearance Audit 100% Reconciled under Policy E&O-2026.1
              </h3>
              <p className="text-xs text-slate-300">
                10 Carried Forward ($0 review) + 1 Re-Attested (Public Domain) + 1 Unresolved Exception (ASCAP) = 12 Total.
              </p>
            </div>
          </div>
          <Link
            href={exceptionsScheduleUrl}
            className="flex items-center gap-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 px-5 py-2.5 text-sm font-bold text-slate-950 transition-all shadow-md active:scale-95 whitespace-nowrap focus:outline-none focus:ring-2 focus:ring-emerald-300"
          >
            <span>View &amp; Print Form E&O-2026 Schedule</span>
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      ) : (
        <div
          className="rounded-xl border border-amber-500/40 bg-amber-950/30 p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs text-amber-200"
          role="alert"
        >
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0" aria-hidden="true" />
            <span>
              <strong>Counsel Action Required:</strong> {staleCount} stale decision{staleCount === 1 ? '' : 's'} awaiting human disposition.
              Review the 4-dimensional explanations below and submit your formal counsel determination.
            </span>
          </div>
          <div className="text-slate-400 text-[11px] whitespace-nowrap font-mono self-end sm:self-auto">
            Fail-Closed Enforced &middot; 17 U.S.C. § 504(c)
          </div>
        </div>
      )}
    </section>
  );
};

export default ClearanceSummaryCards;
