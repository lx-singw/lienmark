'use client';

/**
 * ClearanceHealthMeter Component
 * Segmented progress bar reflecting Carried, Re-Attested, Stale, and Exception states.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';

interface ClearanceHealthMeterProps {
  readonly total: number;
  readonly carried: number;
  readonly reattested: number;
  readonly stale: number;
  readonly exception: number;
}

export const ClearanceHealthMeter: React.FC<ClearanceHealthMeterProps> = ({
  total,
  carried,
  reattested,
  stale,
  exception,
}) => {
  const safeTotal = total > 0 ? total : 1;
  const pCarried = (carried / safeTotal) * 100;
  const pReattested = (reattested / safeTotal) * 100;
  const pStale = (stale / safeTotal) * 100;
  const pException = (exception / safeTotal) * 100;

  const clearanceRate = Math.round(((carried + reattested) / safeTotal) * 100);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-400 font-medium">Clearance Readiness</span>
        <span className="font-mono font-bold text-white">{clearanceRate}% Cleared</span>
      </div>

      {/* Segmented Bar */}
      <div className="h-2.5 w-full bg-slate-900 rounded-full overflow-hidden flex ring-1 ring-white/10">
        <div style={{ width: `${pCarried}%` }} className="bg-emerald-500 transition-all duration-500" title={`Carried Forward: ${carried}`} />
        <div style={{ width: `${pReattested}%` }} className="bg-sky-400 transition-all duration-500" title={`Re-Attested: ${reattested}`} />
        <div style={{ width: `${pStale}%` }} className="bg-amber-400 transition-all duration-500" title={`Stale/Reopened: ${stale}`} />
        <div style={{ width: `${pException}%` }} className="bg-rose-500 transition-all duration-500" title={`Exception: ${exception}`} />
      </div>

      {/* Legend Pills */}
      <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono text-slate-400 pt-1">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-emerald-500" /> Carried: {carried}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-sky-400" /> Re-Attested: {reattested}
        </span>
        {stale > 0 && (
          <span className="flex items-center gap-1.5 text-amber-300 font-semibold">
            <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" /> Stale: {stale}
          </span>
        )}
        {exception > 0 && (
          <span className="flex items-center gap-1.5 text-rose-300">
            <span className="h-2 w-2 rounded-full bg-rose-500" /> Exception: {exception}
          </span>
        )}
      </div>
    </div>
  );
};

export default ClearanceHealthMeter;
