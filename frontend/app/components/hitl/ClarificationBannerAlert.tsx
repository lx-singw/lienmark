'use client';

/**
 * Lienmark HITL Clarification Banner Alert
 * High-visibility banner across the top of the production dashboard indicating
 * pending Human-in-the-Loop blocker count and direct action triggers.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { AlertTriangle, ArrowRight, ShieldAlert, X } from 'lucide-react';
import { ClarificationRequestUI } from './hitl_types';

export interface ClarificationBannerAlertProps {
  readonly pendingRequests: ReadonlyArray<ClarificationRequestUI>;
  readonly onOpenClarification: (claimKey: string) => void;
  readonly onDismiss?: () => void;
  readonly isDismissed?: boolean;
  readonly className?: string;
}

export const ClarificationBannerAlert: React.FC<ClarificationBannerAlertProps> = ({
  pendingRequests,
  onOpenClarification,
  onDismiss,
  isDismissed = false,
  className = '',
}) => {
  if (isDismissed || pendingRequests.length === 0) {
    return null;
  }

  const blockerCount = pendingRequests.length;
  const primaryRequest = pendingRequests[0];

  return (
    <aside
      aria-label="Pending Human-in-the-Loop Clarification Blockers Alert"
      role="alert"
      className={`relative overflow-hidden rounded-xl border border-amber-500/50 bg-gradient-to-r from-amber-950/80 via-slate-900/90 to-amber-950/70 p-4 shadow-xl backdrop-blur-md animate-in fade-in slide-in-from-top-2 ${className}`}
    >
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        {/* Left Section: Icon and Title */}
        <div className="flex items-start sm:items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/40 flex-shrink-0 animate-pulse">
            <AlertTriangle className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold text-sm text-white">
                {blockerCount} Pending Clearance {blockerCount === 1 ? 'Blocker' : 'Blockers'} Requiring Clarification
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/20 border border-amber-500/40 px-2 py-0.5 text-[10px] font-mono font-bold text-amber-300">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-ping" />
                ACTION REQUIRED
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-0.5">
              Production script revisions contain unresolved rights questions. E&amp;O policy delivery remains locked until answered.
            </p>
          </div>
        </div>

        {/* Right Section: Interactive Action Buttons */}
        <div className="flex items-center gap-2 self-end md:self-center flex-shrink-0">
          <button
            type="button"
            onClick={() => onOpenClarification(primaryRequest.claimKey)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 px-3 py-1.5 text-xs font-bold text-slate-950 shadow-md transition-all focus:outline-none focus:ring-2 focus:ring-amber-300 active:scale-95"
          >
            <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Review Blocker ({primaryRequest.assetName})</span>
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </button>

          {onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors focus:outline-none focus:ring-1 focus:ring-amber-400"
              aria-label="Dismiss clarification banner"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {/* Sub-item pills for multiple blockers */}
      {blockerCount > 1 && (
        <div className="mt-2.5 pt-2 border-t border-amber-500/20 flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-mono uppercase text-amber-400/80 font-semibold">
            Active Blockers:
          </span>
          {pendingRequests.map((req) => (
            <button
              key={req.id}
              type="button"
              onClick={() => onOpenClarification(req.claimKey)}
              className="inline-flex items-center gap-1 rounded bg-slate-900/80 hover:bg-slate-800 border border-slate-700 hover:border-amber-400/60 px-2 py-0.5 text-[11px] font-mono text-slate-200 transition-colors"
            >
              <span className="text-amber-400 font-bold">{req.scene}:</span>
              <span>{req.assetName}</span>
            </button>
          ))}
        </div>
      )}
    </aside>
  );
};

export default ClarificationBannerAlert;
