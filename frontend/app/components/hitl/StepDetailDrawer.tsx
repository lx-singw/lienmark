'use client';

/**
 * StepDetailDrawer Component
 * Displays verified proof drawers and counsel action buttons for the selected resumption step.
 * Authored strictly under Google AntiGravity architectural guidelines.
 */

import React from 'react';
import { FileCheck, ShieldCheck, ChevronRight } from 'lucide-react';
import { ResumptionStepDetail } from './resumption_types';

export interface StepDetailDrawerProps {
  readonly activeStep: ResumptionStepDetail;
  readonly isAllComplete: boolean;
  readonly onOpenAgreementViewer?: () => void;
  readonly onSignOff?: () => void;
}

export const StepDetailDrawer: React.FC<StepDetailDrawerProps> = ({
  activeStep,
  isAllComplete,
  onOpenAgreementViewer,
  onSignOff,
}) => (
  <div className="rounded-xl border border-slate-800 bg-[#090e18] p-4 text-xs">
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
      <div className="space-y-0.5">
        <span className="text-[10px] font-mono uppercase text-emerald-400 tracking-wider">
          Verification Proofs &middot; Step {activeStep.stepNumber} Details
        </span>
        <p className="text-slate-200 font-medium">
          {activeStep.summaryNotes || 'Step parameters verified.'}
        </p>
      </div>
      <div className="flex items-center gap-2">
        {activeStep.stepNumber === 3 && onOpenAgreementViewer && (
          <button
            type="button"
            onClick={onOpenAgreementViewer}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/50 px-2.5 py-1 text-xs font-mono font-bold text-emerald-300 transition-colors"
          >
            <FileCheck className="h-3.5 w-3.5" />
            <span>Inspect Verified Clauses</span>
          </button>
        )}
        {isAllComplete && onSignOff && (
          <button
            type="button"
            onClick={onSignOff}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 px-3 py-1 text-xs font-bold text-slate-950 shadow-md transition-all active:scale-95"
          >
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>Counsel Sign-off</span>
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </div>
    {activeStep.stepNumber === 3 && (
      <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
        <div className="rounded bg-slate-900/80 border border-slate-800 p-2">
          <span className="text-slate-500 block">Signatures:</span>
          <span className="text-emerald-300 font-bold">Dual Authenticated</span>
        </div>
        <div className="rounded bg-slate-900/80 border border-slate-800 p-2">
          <span className="text-slate-500 block">Territory:</span>
          <span className="text-emerald-300 font-bold">Worldwide</span>
        </div>
        <div className="rounded bg-slate-900/80 border border-slate-800 p-2">
          <span className="text-slate-500 block">Rights Scope:</span>
          <span className="text-emerald-300 font-bold">Sync + Master</span>
        </div>
        <div className="rounded bg-slate-900/80 border border-slate-800 p-2">
          <span className="text-slate-500 block">Term / Expiry:</span>
          <span className="text-emerald-300 font-bold">In Perpetuity</span>
        </div>
      </div>
    )}
  </div>
);

export default StepDetailDrawer;
