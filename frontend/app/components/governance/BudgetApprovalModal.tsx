'use client';

/**
 * BudgetApprovalModal Component
 * Modal dialog for Line Producer / Production Accountant to authorize budget increases.
 * Displays real-time estimates of additional claims and script pages unlocked.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  DollarSign,
  ShieldAlert,
  X,
  PlusCircle,
  FileText,
  Sparkles,
  Lock,
  ArrowRight,
} from 'lucide-react';
import {
  PRESET_AMOUNTS,
  calculateCapacityUnlock,
  formatUsd,
} from './budget_utils';

export interface BudgetApprovalModalProps {
  isOpen: boolean;
  currentBudgetLimitUsd: number;
  currentSpendUsd: number;
  onApprove: (amount: number, reason: string) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export const BudgetApprovalModal: React.FC<BudgetApprovalModalProps> = ({
  isOpen,
  currentBudgetLimitUsd,
  currentSpendUsd,
  onApprove,
  onCancel,
  isSubmitting = false,
}) => {
  const [additionalBudget, setAdditionalBudget] = useState<string>('25.00');
  const [justificationNote, setJustificationNote] = useState<string>('');
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isSubmitting) onCancel();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isSubmitting, onCancel]);

  const numAmount = useMemo(() => {
    const parsed = parseFloat(additionalBudget);
    return isNaN(parsed) || parsed <= 0 ? 0 : parsed;
  }, [additionalBudget]);

  const estimates = useMemo(
    () => calculateCapacityUnlock(numAmount, currentBudgetLimitUsd),
    [numAmount, currentBudgetLimitUsd]
  );

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (numAmount <= 0) {
        setValidationError('Please enter an authorization amount greater than $0.00');
        return;
      }
      onApprove(numAmount, justificationNote.trim());
    },
    [numAmount, justificationNote, onApprove]
  );

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="budget-approval-title"
    >
      <div className="relative w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl space-y-5 animate-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <h2 id="budget-approval-title" className="text-base font-bold text-white">Authorize Budget Extension</h2>
              <p className="text-xs text-slate-400">Line Producer E&amp;O Fiscal Authorization</p>
            </div>
          </div>
          <button type="button" onClick={onCancel} className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800" aria-label="Close modal">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="additional-amount" className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Additional Spending Cap (USD)
            </label>
            <div className="relative">
              <DollarSign className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                id="additional-amount"
                type="number"
                step="0.50"
                min="0.50"
                value={additionalBudget}
                onChange={(e) => { setAdditionalBudget(e.target.value); if (validationError) setValidationError(null); }}
                className="w-full rounded-xl border border-slate-700 bg-slate-950/80 pl-9 pr-4 py-2 text-sm font-mono text-white focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                placeholder="25.00"
                autoFocus
              />
            </div>
            {validationError && <p className="mt-1 text-xs text-rose-400">{validationError}</p>}
          </div>

          <div className="flex flex-wrap gap-2">
            {PRESET_AMOUNTS.map((amt) => (
              <button
                key={amt}
                type="button"
                onClick={() => { setAdditionalBudget(amt.toFixed(2)); setValidationError(null); }}
                className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium border transition-colors ${
                  numAmount === amt
                    ? 'bg-sky-600/30 text-sky-300 border-sky-400/60 shadow-sm'
                    : 'bg-slate-800/80 text-slate-300 border-slate-700 hover:bg-slate-800'
                }`}
              >
                +${amt}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3 p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs">
            <div>
              <span className="text-slate-400 block mb-0.5">Unlocked Claims</span>
              <span className="font-mono font-bold text-sky-400 text-sm">~{estimates.claims} claims</span>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Unlocked Pages</span>
              <span className="font-mono font-bold text-purple-400 text-sm">~{estimates.pages} pages</span>
            </div>
            <div className="col-span-2 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono">
              <span className="text-slate-400">New Approved Cap:</span>
              <span className="font-bold text-emerald-400">{formatUsd(estimates.newTotalLimit)}</span>
            </div>
          </div>

          <div>
            <label htmlFor="justification-note" className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Production Justification Note (Optional)
            </label>
            <textarea
              id="justification-note"
              value={justificationNote}
              onChange={(e) => setJustificationNote(e.target.value)}
              rows={2}
              placeholder="e.g. Authorized 2nd unit screenplay revision dialogue scan."
              className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-xs text-white focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onCancel}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || numAmount <= 0}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              <PlusCircle className="h-4 w-4" />
              <span>{isSubmitting ? 'Authorizing...' : `Authorize +${formatUsd(numAmount)}`}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default BudgetApprovalModal;
