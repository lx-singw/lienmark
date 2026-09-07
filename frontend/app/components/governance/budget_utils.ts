/**
 * budget_utils.ts
 * Formatting, status badges, and capacity calculation helpers for budget governance.
 * Sprint 1.3 / Form E&O-2026.
 */

export const CLAIM_COST_USD = 0.04;
export const PAGE_COST_USD = 0.015;
export const PRESET_AMOUNTS = [5, 10, 25, 50, 100];

export function formatUsd(amount: number): string {
  if (isNaN(amount) || amount < 0) return '$0.00';
  if (amount > 0 && amount < 0.01) {
    return `$${amount.toFixed(4)}`;
  }
  return `$${amount.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function getStatusBadgeConfig(status?: string): {
  label: string;
  badgeClass: string;
  indicatorClass: string;
} {
  const norm = (status || '').toLowerCase();
  if (norm === 'waiting_for_budget') {
    return {
      label: 'WAITING FOR BUDGET',
      badgeClass: 'bg-rose-950/80 text-rose-300 border-rose-500/50',
      indicatorClass: 'bg-rose-400 animate-pulse',
    };
  }
  if (norm === 'investigating' || norm === 'evaluating' || norm === 'extracting') {
    return {
      label: norm.toUpperCase(),
      badgeClass: 'bg-sky-950/80 text-sky-300 border-sky-500/50',
      indicatorClass: 'bg-sky-400 animate-ping',
    };
  }
  if (norm === 'ready_for_review' || norm === 'completed') {
    return {
      label: norm === 'ready_for_review' ? 'READY FOR REVIEW' : 'COMPLETED',
      badgeClass: 'bg-emerald-950/80 text-emerald-300 border-emerald-500/50',
      indicatorClass: 'bg-emerald-400',
    };
  }
  if (norm === 'failed') {
    return {
      label: 'FAILED',
      badgeClass: 'bg-rose-950/80 text-rose-300 border-rose-500/50',
      indicatorClass: 'bg-rose-400',
    };
  }
  return {
    label: (status || 'INITIALIZING').toUpperCase(),
    badgeClass: 'bg-slate-800 text-slate-300 border-slate-700',
    indicatorClass: 'bg-slate-400',
  };
}

export function calculateCapacityUnlock(amount: number, currentLimit: number): {
  claims: number;
  pages: number;
  newTotalLimit: number;
} {
  const safeAmount = isNaN(amount) || amount <= 0 ? 0 : amount;
  return {
    claims: Math.floor(safeAmount / CLAIM_COST_USD),
    pages: Math.floor(safeAmount / PAGE_COST_USD),
    newTotalLimit: currentLimit + safeAmount,
  };
}
