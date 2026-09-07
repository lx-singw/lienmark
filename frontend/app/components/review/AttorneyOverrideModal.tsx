'use client';

/**
 * Lienmark Attorney Override Modal Component (Sprint 5.2)
 * High-contrast glassmorphism modal integrating:
 *  1. Dual Review Stepper adjudication (Step 1 Primary -> Step 2 Supervising)
 *  2. Canonical Package Digest Badge
 *  3. 'Sign-off / Clear Claim' (emerald) & 'Reject & Direct Re-investigation' (rose)
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import React, { useState, useEffect } from 'react';
import { X, CheckCircle2, AlertTriangle, Shield, History, Send } from 'lucide-react';
import { CounselActionType, DecisionPayload, AttorneyOverrideModalProps } from './review_types';
import { DIRECTIVE_SHORTCUTS, validateDecisionPayload } from './review_utils';
import { CitationSuggestionPicker } from './CitationSuggestionPicker';
import { AttemptLineageTimeline } from './AttemptLineageTimeline';
import { PackageDigestBadge } from './PackageDigestBadge';
import { DualReviewPanel } from './DualReviewPanel';
import { DirectOverrideForm } from './DirectOverrideForm';

export const AttorneyOverrideModal: React.FC<AttorneyOverrideModalProps> = ({
  isOpen,
  claimKey,
  assetType,
  scene,
  initialAction = 'sign_off',
  reviewerName = 'Sarah Jenkins, Esq. (Lead Clearance Counsel)',
  reviewerId = 'counsel_sarah_jenkins',
  reviewerRole = 'Clearance Counsel',
  lineageHistory = [],
  decisionPackage,
  onClose,
  onDecision,
  onDualReviewApprove,
  isSubmitting = false,
}) => {
  const [showLineage, setShowLineage] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'dual' | 'override'>('override');

  useEffect(() => {
    if (isOpen) {
      setActiveTab(decisionPackage ? 'dual' : 'override');
    }
  }, [isOpen, decisionPackage]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md" role="dialog" aria-modal="true">
      <div className="relative w-full max-w-2xl max-h-[92vh] overflow-y-auto rounded-2xl border border-slate-800 bg-[#0a101f] p-5 shadow-2xl space-y-4">
        {/* Header with Package Digest */}
        <div className="flex items-start justify-between border-b border-slate-800/80 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-sky-400" />
              <h3 className="text-base font-bold text-white">Attorney Clearance Adjudication</h3>
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <p className="font-mono text-xs text-slate-400">
                Claim: <span className="font-semibold text-sky-300">{claimKey}</span>
                {scene && <span className="ml-2 text-amber-300">({scene})</span>}
                {assetType && <span className="ml-2 uppercase text-slate-500">• {assetType}</span>}
              </p>
              {decisionPackage && (
                <PackageDigestBadge
                  digest={decisionPackage.canonicalDigest}
                  isStale={decisionPackage.status === 'stale_invalidated'}
                />
              )}
            </div>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white" aria-label="Close modal">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab Navigation if decisionPackage exists */}
        {decisionPackage && (
          <div className="flex gap-2 border-b border-slate-800 pb-1 text-xs">
            <button
              type="button"
              onClick={() => setActiveTab('dual')}
              className={`rounded-t px-3 py-1 font-semibold transition-colors ${activeTab === 'dual' ? 'border-b-2 border-sky-400 text-sky-300 bg-slate-900/60' : 'text-slate-400 hover:text-white'}`}
            >
              Dual Review Workflow
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('override')}
              className={`rounded-t px-3 py-1 font-semibold transition-colors ${activeTab === 'override' ? 'border-b-2 border-sky-400 text-sky-300 bg-slate-900/60' : 'text-slate-400 hover:text-white'}`}
            >
              Direct Override Form
            </button>
          </div>
        )}

        {/* Dual Review Panel View */}
        {decisionPackage && activeTab === 'dual' ? (
          <DualReviewPanel
            packageData={decisionPackage}
            currentReviewerId={reviewerId}
            currentReviewerName={reviewerName}
            currentReviewerRole={reviewerRole}
            onApprove={onDualReviewApprove}
            isSubmitting={isSubmitting}
          />
        ) : (
          <DirectOverrideForm
            initialAction={initialAction}
            reviewerName={reviewerName}
            reviewerId={reviewerId}
            onDecision={onDecision}
            onClose={onClose}
            isSubmitting={isSubmitting}
          />
        )}

        {/* Lineage History Accordion Toggle */}
        {lineageHistory.length > 0 && (
          <div className="border-t border-slate-800/80 pt-2">
            <button
              type="button"
              onClick={() => setShowLineage(!showLineage)}
              className="flex items-center gap-1.5 font-mono text-[11px] text-sky-400 hover:text-sky-300 underline decoration-sky-500/40"
            >
              <History className="h-3 w-3" />
              <span>{showLineage ? 'Hide Lineage' : `View Lineage History (${lineageHistory.length} attempts)`}</span>
            </button>
            {showLineage && <div className="mt-2"><AttemptLineageTimeline attempts={lineageHistory} claimKey={claimKey} /></div>}
          </div>
        )}
      </div>
    </div>
  );
};

export default AttorneyOverrideModal;
