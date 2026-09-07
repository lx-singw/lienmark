'use client';

/**
 * BudgetMeter Component
 * Visual spend gauge displaying spend limit, consumed spend, projected total,
 * remaining allowance, dynamic color transitions, run status, and out-of-budget alerts.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useMemo } from 'react';
import {
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  AlertOctagon,
  ArrowUpRight,
} from 'lucide-react';
import { RunStatus } from '@/lib/types';
import { formatUsd, getStatusBadgeConfig } from './budget_utils';

export interface BudgetMeterProps {
  totalBudgetLimitUsd: number;
  consumedSpendUsd: number;
  projectedTotalUsd?: number;
  runStatus?: RunStatus | 'investigating' | string;
  onRequestIncreaseBudget?: () => void;
  className?: string;
}

export const BudgetMeter: React.FC<BudgetMeterProps> = ({
  totalBudgetLimitUsd,
  consumedSpendUsd,
  projectedTotalUsd,
  runStatus = RunStatus.INITIALIZING,
  onRequestIncreaseBudget,
  className = '',
}) => {
  const projected = projectedTotalUsd ?? consumedSpendUsd;
  const remainingAllowance = Math.max(0, totalBudgetLimitUsd - consumedSpendUsd);

  const percentConsumed = useMemo(() => {
    if (totalBudgetLimitUsd <= 0) return 100;
    return (consumedSpendUsd / totalBudgetLimitUsd) * 100;
  }, [consumedSpendUsd, totalBudgetLimitUsd]);

  const clampedPercent = Math.min(Math.max(percentConsumed, 0), 100);
  const isOverBudget = percentConsumed >= 100 || runStatus === 'waiting_for_budget';
  const isWarning = percentConsumed >= 80 && percentConsumed < 100;

  const statusConfig = useMemo(() => getStatusBadgeConfig(runStatus), [runStatus]);

  const theme = useMemo(() => {
    if (isOverBudget) {
      return {
        barColor: 'bg-rose-500',
        textColor: 'text-rose-400',
        borderColor: 'border-rose-500/40',
        glowColor: 'shadow-[0_0_12px_rgba(244,63,94,0.35)]',
        Icon: AlertOctagon,
      };
    }
    if (isWarning) {
      return {
        barColor: 'bg-amber-500',
        textColor: 'text-amber-400',
        borderColor: 'border-amber-500/40',
        glowColor: 'shadow-[0_0_12px_rgba(245,158,11,0.25)]',
        Icon: AlertTriangle,
      };
    }
    return {
      barColor: 'bg-emerald-500',
      textColor: 'text-emerald-400',
      borderColor: 'border-emerald-500/40',
      glowColor: 'shadow-[0_0_12px_rgba(16,185,129,0.25)]',
      Icon: CheckCircle2,
    };
  }, [isOverBudget, isWarning]);

  return (
    <div
      className={`rounded-2xl border bg-slate-900/90 p-5 backdrop-blur-md transition-all duration-300 ${theme.borderColor} ${className}`}
      role="region"
      aria-label="Execution Budget Meter"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2.5">
          <div className={`p-2 rounded-xl bg-slate-800/90 border border-slate-700/80 ${theme.textColor}`}>
            <DollarSign className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
              <span>Execution Budget &amp; Spend Governor</span>
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-mono font-semibold border ${statusConfig.badgeClass}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${statusConfig.indicatorClass}`} />
                {statusConfig.label}
              </span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Form E&amp;O-2026 Non-Synthetic Spend Cap Policy</p>
          </div>
        </div>

        {onRequestIncreaseBudget && (
          <button
            type="button"
            onClick={onRequestIncreaseBudget}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-sky-600/20 hover:bg-sky-600/30 text-sky-300 border border-sky-500/40 transition-colors focus:outline-none focus:ring-2 focus:ring-sky-400"
          >
            <span>Request Budget Increase</span>
            <ArrowUpRight className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <div className="rounded-xl bg-slate-950/60 p-3 border border-slate-800">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block mb-1">Total Cap</span>
          <span className="text-base font-mono font-bold text-white tracking-tight">{formatUsd(totalBudgetLimitUsd)}</span>
        </div>
        <div className="rounded-xl bg-slate-950/60 p-3 border border-slate-800">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block mb-1">Consumed</span>
          <span className={`text-base font-mono font-bold tracking-tight ${theme.textColor}`}>{formatUsd(consumedSpendUsd)}</span>
        </div>
        <div className="rounded-xl bg-slate-950/60 p-3 border border-slate-800">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block mb-1 flex items-center gap-1">
            <span>Projected</span>
            <TrendingUp className="h-3 w-3 text-slate-500" />
          </span>
          <span className="text-base font-mono font-bold text-slate-200 tracking-tight">{formatUsd(projected)}</span>
        </div>
        <div className="rounded-xl bg-slate-950/60 p-3 border border-slate-800">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block mb-1">Remaining</span>
          <span className="text-base font-mono font-bold text-emerald-400 tracking-tight">{formatUsd(remainingAllowance)}</span>
        </div>
      </div>

      <div className="space-y-1.5">
        <div className="flex justify-between text-xs font-mono font-medium text-slate-400">
          <span>Spend Utilization</span>
          <span className={theme.textColor}>{percentConsumed.toFixed(1)}%</span>
        </div>
        <div
          className="h-2.5 w-full overflow-hidden rounded-full bg-slate-800 border border-slate-700/50"
          role="progressbar"
          aria-valuenow={Math.round(clampedPercent)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className={`h-full transition-all duration-500 ease-out ${theme.barColor} ${theme.glowColor}`}
            style={{ width: `${clampedPercent}%` }}
          />
        </div>
      </div>

      {isOverBudget && (
        <div className="mt-4 rounded-xl border border-rose-500/50 bg-rose-950/40 p-3 flex items-start gap-2.5">
          <AlertOctagon className="h-4 w-4 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-rose-200 space-y-1">
            <p className="font-semibold text-rose-300">Run Halted: Budget Exhausted</p>
            <p className="text-rose-200/90 leading-relaxed">
              Execution paused in <code className="font-mono bg-rose-950 px-1 py-0.5 rounded text-rose-200 font-bold">WAITING_FOR_BUDGET</code>. 100% of partial findings remain intact without synthetic completion.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default BudgetMeter;
