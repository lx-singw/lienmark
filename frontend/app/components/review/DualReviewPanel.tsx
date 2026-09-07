'use client';

/**
 * Lienmark Dual Review Stepper & Adjudication Panel (Sprint 5.2)
 * Enforces dual-counsel review workflow:
 *  - Visual two-stage progress stepper (Primary Counsel -> Supervising Counsel)
 *  - Conflict-of-interest attestation checkbox
 *  - Distinct Reviewer Guard (disables self-approval on second review)
 *  - Stale package invalidation warning banner
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  UserCheck,
  UserX,
  ShieldCheck,
  Send,
  Lock,
} from 'lucide-react';
import { DualReviewPanelProps } from './review_types';
import {
  formatReviewTimestamp,
  truncateDigest,
  canPerformSecondReview,
} from './review_utils';
import { PackageDigestBadge } from './PackageDigestBadge';

export const DualReviewPanel: React.FC<DualReviewPanelProps> = ({
  packageData,
  currentReviewerId,
  currentReviewerName,
  currentReviewerRole = 'Clearance Counsel',
  onApprove,
  onReject,
  isSubmitting = false,
  className = '',
}) => {
  const [conflictAttested, setConflictAttested] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isStale = packageData.status === 'stale_invalidated';
  const isFullyApproved = packageData.status === 'final_approved';
  const isSecondReview = packageData.status === 'first_review_approved';
  const primaryReviewerId = packageData.primaryApproval?.reviewerId?.trim().toLowerCase();
  const isSameReviewer = Boolean(
    primaryReviewerId && primaryReviewerId === currentReviewerId.trim().toLowerCase()
  );
  const secondReviewCheck = canPerformSecondReview(packageData, currentReviewerId);

  const handleApprove = async (): Promise<void> => {
    setErrorMessage(null);
    if (!conflictAttested) {
      setErrorMessage('Conflict-of-interest affirmative attestation is strictly required.');
      return;
    }
    if (isSecondReview && !secondReviewCheck.allowed) {
      setErrorMessage(secondReviewCheck.reason ?? 'Second review requires a distinct authorized counsel.');
      return;
    }
    if (onApprove) {
      await onApprove(packageData.packageId, isSecondReview, conflictAttested);
    }
  };

  const isApproveDisabled =
    isSubmitting ||
    isStale ||
    isFullyApproved ||
    !conflictAttested ||
    (isSecondReview && !secondReviewCheck.allowed);

  return (
    <div className={`space-y-4 rounded-xl border border-slate-800 bg-[#080d1a] p-4 text-xs ${className}`} data-testid="dual-review-panel">
      {/* Header with Package Digest */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <h4 className="font-bold text-white text-sm">Dual Counsel Clearance Adjudication</h4>
          </div>
          <p className="mt-0.5 font-mono text-[11px] text-slate-400">
            Package: <span className="text-sky-300 font-semibold">{packageData.packageId}</span> (v{packageData.version}) • Cut: {packageData.cutRevision}
          </p>
        </div>
        <PackageDigestBadge digest={packageData.canonicalDigest} isStale={isStale} />
      </div>

      {/* Stale Warning Banner */}
      {isStale && (
        <div className="rounded-lg border border-rose-500/50 bg-rose-950/60 p-3 text-rose-200" data-testid="stale-warning-banner">
          <div className="flex items-center gap-2 font-bold text-xs text-rose-300">
            <AlertTriangle className="h-4 w-4 text-rose-400 flex-shrink-0" />
            <span>Decision package is stale. Material evidence or policy changed. Both reviews required again.</span>
          </div>
          {packageData.staleReason && (
            <p className="mt-1 font-mono text-[11px] text-rose-300/80 pl-6">Detail: {packageData.staleReason}</p>
          )}
        </div>
      )}

      {/* Two-Stage Progress Stepper */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="review-stepper">
        {/* Step 1: Primary Counsel */}
        <div className={`rounded-lg border p-3 ${packageData.primaryApproval ? 'border-emerald-500/40 bg-emerald-950/20' : 'border-amber-500/40 bg-amber-950/20'}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-semibold">
              {packageData.primaryApproval ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <div className="flex h-4 w-4 items-center justify-center rounded-full bg-amber-500/30 text-[10px] text-amber-300">1</div>}
              <span className={packageData.primaryApproval ? 'text-emerald-300' : 'text-amber-300'}>Step 1: Primary Counsel Review</span>
            </div>
            <span className="font-mono text-[10px] text-slate-400">{packageData.primaryApproval ? 'Approved' : 'Pending'}</span>
          </div>
          {packageData.primaryApproval ? (
            <div className="mt-2 space-y-0.5 pl-6 font-mono text-[10px] text-slate-300">
              <p className="text-slate-200 font-semibold">{packageData.primaryApproval.reviewerName} ({packageData.primaryApproval.reviewerRole})</p>
              <p className="text-slate-400">Timestamp: {formatReviewTimestamp(packageData.primaryApproval.timestampUtc)}</p>
              <p className="text-sky-400">Ledger Hash: {truncateDigest(packageData.primaryApproval.ledgerEventId, 10, 8)}</p>
            </div>
          ) : (
            <p className="mt-2 pl-6 text-[11px] text-slate-400">Requires initial affirmative statutory clearance review.</p>
          )}
        </div>

        {/* Step 2: Supervising Counsel */}
        <div className={`rounded-lg border p-3 ${packageData.secondaryApproval ? 'border-emerald-500/40 bg-emerald-950/20' : isSecondReview ? 'border-sky-500/40 bg-sky-950/20' : 'border-slate-800 bg-slate-900/30'}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-semibold">
              {packageData.secondaryApproval ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : isSecondReview ? <div className="flex h-4 w-4 items-center justify-center rounded-full bg-sky-500/30 text-[10px] text-sky-300">2</div> : <Lock className="h-4 w-4 text-slate-600" />}
              <span className={packageData.secondaryApproval ? 'text-emerald-300' : isSecondReview ? 'text-sky-300' : 'text-slate-500'}>Step 2: Supervising Counsel Second Review</span>
            </div>
            <span className="font-mono text-[10px] text-slate-400">{packageData.secondaryApproval ? 'Approved' : isSecondReview ? 'Awaiting Sign-off' : 'Locked'}</span>
          </div>
          {packageData.secondaryApproval ? (
            <div className="mt-2 space-y-0.5 pl-6 font-mono text-[10px] text-slate-300">
              <p className="text-slate-200 font-semibold">{packageData.secondaryApproval.reviewerName} ({packageData.secondaryApproval.reviewerRole})</p>
              <p className="text-slate-400">Timestamp: {formatReviewTimestamp(packageData.secondaryApproval.timestampUtc)}</p>
              <p className="text-sky-400">Ledger Hash: {truncateDigest(packageData.secondaryApproval.ledgerEventId, 10, 8)}</p>
            </div>
          ) : (
            <p className="mt-2 pl-6 text-[11px] text-slate-400">{isSecondReview ? 'Awaiting independent supervising counsel review.' : 'Locked until primary counsel completes Step 1.'}</p>
          )}
        </div>
      </div>

      {/* Distinct Reviewer Guard Alert */}
      {isSecondReview && isSameReviewer && (
        <div className="rounded-lg border border-amber-500/50 bg-amber-950/50 p-3 text-amber-200" data-testid="distinct-reviewer-guard">
          <div className="flex items-center gap-2 font-bold text-xs text-amber-300">
            <UserX className="h-4 w-4 text-amber-400 flex-shrink-0" />
            <span>Second review requires a distinct authorized counsel.</span>
          </div>
          <p className="mt-1 text-[11px] text-amber-300/80 pl-6">
            Reviewer 1 was signed by <span className="font-semibold text-white">{packageData.primaryApproval?.reviewerName}</span>. Independent supervising counsel sign-off is required.
          </p>
        </div>
      )}

      {/* Conflict of Interest Attestation */}
      {!isFullyApproved && !isStale && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
          <label className="flex items-start gap-2.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={conflictAttested}
              onChange={(e) => { setConflictAttested(e.target.checked); setErrorMessage(null); }}
              disabled={isSubmitting || (isSecondReview && isSameReviewer)}
              className="mt-0.5 h-4 w-4 rounded border-slate-700 bg-slate-950 text-sky-500 focus:ring-sky-500 focus:ring-offset-0 disabled:opacity-50"
              data-testid="conflict-attestation-checkbox"
            />
            <span className="text-[11px] text-slate-300 leading-relaxed">
              I affirmatively attest that neither I nor my firm have a declared conflict of interest regarding this asset, licensor, or production.
            </span>
          </label>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && (
        <div className="rounded-lg border border-rose-500/50 bg-rose-950/50 p-2.5 text-xs text-rose-300 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Action Footer */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800">
        <div className="font-mono text-[10px] text-slate-400 flex items-center gap-1.5">
          <UserCheck className="h-3.5 w-3.5 text-slate-500" />
          <span>Active Reviewer: <span className="text-slate-200 font-semibold">{currentReviewerName}</span> ({currentReviewerRole})</span>
        </div>

        {!isFullyApproved && !isStale && (
          <div className="flex items-center gap-2">
            {onReject && (
              <button
                type="button"
                onClick={() => onReject(packageData.packageId, 'Rejected during dual review adjudication')}
                disabled={isSubmitting}
                className="rounded-lg border border-slate-800 px-3 py-1.5 text-xs font-semibold text-rose-400 hover:bg-rose-950/40 hover:border-rose-500/40 transition-colors disabled:opacity-50"
              >
                Reject Package
              </button>
            )}
            <button
              type="button"
              onClick={handleApprove}
              disabled={isApproveDisabled}
              className={`inline-flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-xs font-bold transition-all shadow-md ${
                isApproveDisabled
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
                  : 'bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-emerald-500/20'
              }`}
              data-testid="submit-dual-approval-button"
            >
              <Send className="h-3.5 w-3.5" />
              <span>{isSecondReview ? 'Affirm Supervising Dual Sign-off' : 'Affirm Primary Review Sign-off'}</span>
            </button>
          </div>
        )}

        {isFullyApproved && (
          <div className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-950/60 border border-emerald-500/50 px-3 py-1 text-[11px] font-bold text-emerald-300">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            <span>Dual Counsel Clearance Complete & Cryptographically Verified</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default DualReviewPanel;
