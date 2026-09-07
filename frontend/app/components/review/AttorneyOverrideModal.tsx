'use client';

/**
 * Lienmark Attorney Override Modal Component (Sprint 4.3)
 * High-contrast glassmorphism modal with dual actions:
 *  1. 'Sign-off / Clear Claim' (emerald/green)
 *  2. 'Reject & Direct Re-investigation' (rose/amber)
 * Integrates pre-populated legal citation picker and directive template shortcuts.
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { X, CheckCircle2, AlertTriangle, Shield, History, Send } from 'lucide-react';
import { CounselActionType, DecisionPayload, AttorneyOverrideModalProps } from './review_types';
import { DIRECTIVE_SHORTCUTS, validateDecisionPayload } from './review_utils';
import { CitationSuggestionPicker } from './CitationSuggestionPicker';
import { AttemptLineageTimeline } from './AttemptLineageTimeline';

export const AttorneyOverrideModal: React.FC<AttorneyOverrideModalProps> = ({
  isOpen,
  claimKey,
  assetType,
  scene,
  description,
  initialAction = 'sign_off',
  reviewerName = 'Sarah Jenkins, Esq. (Lead Clearance Counsel)',
  reviewerId = 'counsel_sarah_jenkins',
  lineageHistory = [],
  onClose,
  onDecision,
  isSubmitting = false,
}) => {
  const [action, setAction] = useState<CounselActionType>(initialAction);
  const [directiveText, setDirectiveText] = useState<string>('');
  const [citationText, setCitationText] = useState<string>('');
  const [conditions, setConditions] = useState<string>('');
  const [showLineage, setShowLineage] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setAction(initialAction);
      setErrorMessage(null);
    }
  }, [isOpen, initialAction]);

  const handleShortcutClick = (shortcutText: string): void => {
    setDirectiveText((prev) => (prev ? `${prev.trim()}; ${shortcutText}` : shortcutText));
  };

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    setErrorMessage(null);
    const payload: DecisionPayload = {
      action,
      counselId: reviewerId,
      counselName: reviewerName,
      directiveText: directiveText.trim(),
      citationText: citationText.trim(),
      conditions: conditions.trim() || undefined,
    };
    const validation = validateDecisionPayload(payload);
    if (!validation.isValid) {
      setErrorMessage(validation.errors[0] ?? 'Please check required fields.');
      return;
    }
    await onDecision(payload);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md" role="dialog" aria-modal="true">
      <div className="relative w-full max-w-2xl max-h-[92vh] overflow-y-auto rounded-2xl border border-slate-800 bg-[#0a101f] p-5 shadow-2xl space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-800/80 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-sky-400" />
              <h3 className="text-base font-bold text-white">Attorney Clearance Adjudication</h3>
            </div>
            <p className="mt-0.5 font-mono text-xs text-slate-400">
              Claim: <span className="font-semibold text-sky-300">{claimKey}</span>
              {scene && <span className="ml-2 text-amber-300">({scene})</span>}
              {assetType && <span className="ml-2 uppercase text-slate-500">• {assetType}</span>}
            </p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white" aria-label="Close modal">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Dual Actions Toggle */}
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => { setAction('sign_off'); setErrorMessage(null); }}
            className={`flex items-center justify-center gap-2 rounded-xl border p-3 text-xs font-bold transition-all ${
              action === 'sign_off'
                ? 'border-emerald-500 bg-emerald-950/70 text-emerald-200 ring-2 ring-emerald-500/50 shadow-lg'
                : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700'
            }`}
          >
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            <span>Sign-off / Clear Claim</span>
          </button>

          <button
            type="button"
            onClick={() => { setAction('reject'); setErrorMessage(null); }}
            className={`flex items-center justify-center gap-2 rounded-xl border p-3 text-xs font-bold transition-all ${
              action === 'reject'
                ? 'border-rose-500 bg-rose-950/70 text-rose-200 ring-2 ring-rose-500/50 shadow-lg'
                : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700'
            }`}
          >
            <AlertTriangle className="h-4 w-4 text-rose-400" />
            <span>Reject & Direct Re-investigation</span>
          </button>
        </div>

        {/* Lineage History Accordion Toggle */}
        {lineageHistory.length > 0 && (
          <div>
            <button
              type="button"
              onClick={() => setShowLineage(!showLineage)}
              className="flex items-center gap-1.5 font-mono text-[11px] text-sky-400 hover:text-sky-300 underline decoration-sky-500/40"
            >
              <History className="h-3 w-3" />
              <span>{showLineage ? 'Hide Investigation Lineage' : `View Lineage History (${lineageHistory.length} attempts)`}</span>
            </button>
            {showLineage && <div className="mt-2"><AttemptLineageTimeline attempts={lineageHistory} claimKey={claimKey} /></div>}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Directive Input with Shortcuts (Prominent on Reject) */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-200">
              Counsel Directive for Re-investigation {action === 'reject' && <span className="text-rose-400">*</span>}
            </label>
            <div className="flex flex-wrap gap-1.5 mb-1.5">
              {DIRECTIVE_SHORTCUTS.map((sc) => (
                <button
                  key={sc.id}
                  type="button"
                  onClick={() => handleShortcutClick(sc.text)}
                  className="rounded bg-slate-800/80 hover:bg-slate-700 border border-slate-700 px-2 py-0.5 text-[10px] font-mono text-slate-300 transition-colors"
                >
                  + {sc.label}
                </button>
              ))}
            </div>
            <textarea
              value={directiveText}
              onChange={(e) => setDirectiveText(e.target.value)}
              rows={2}
              placeholder={action === 'reject' ? 'e.g. Re-search ASCAP for 1972 live adaptation; verify foreign distribution holdback...' : 'Optional directives for production team...'}
              className="w-full rounded-lg border border-slate-800 bg-slate-950/80 p-2.5 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </div>

          {/* Citation Picker & Textarea */}
          <div className="space-y-2">
            <CitationSuggestionPicker onSelectCitation={(text) => setCitationText(text)} selectedCitationText={citationText} />
            <div>
              <label className="block text-xs font-semibold text-slate-200 mb-1">
                Affirmative Legal Citation / Statutory Basis {action === 'sign_off' && <span className="text-emerald-400">*</span>}
              </label>
              <textarea
                value={citationText}
                onChange={(e) => setCitationText(e.target.value)}
                rows={2}
                placeholder="Statutory citation (e.g. 17 U.S.C. § 107 Fair Use analysis or executed license clause)..."
                className="w-full rounded-lg border border-slate-800 bg-slate-950/80 p-2.5 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              />
            </div>
          </div>

          {/* Conditions Input (Optional for conditional sign-offs) */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Clearance Conditions / Underwriter Riders (Optional)
            </label>
            <input
              type="text"
              value={conditions}
              onChange={(e) => setConditions(e.target.value)}
              placeholder="e.g. Subject to North American theatrical delivery only; requires end-credit attribution."
              className="w-full rounded-lg border border-slate-800 bg-slate-950/80 p-2 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none"
            />
          </div>

          {/* Error display */}
          {errorMessage && (
            <div className="rounded-lg border border-rose-500/40 bg-rose-950/50 p-2.5 text-xs text-rose-300 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Footer & Submit */}
          <div className="flex items-center justify-between pt-2 border-t border-slate-800">
            <div className="text-[11px] font-mono text-slate-400">
              Signer: <span className="text-slate-200 font-semibold">{reviewerName}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="rounded-lg border border-slate-800 px-3 py-1.5 text-xs font-medium text-slate-400 hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className={`inline-flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-xs font-bold transition-all shadow-md ${
                  action === 'sign_off'
                    ? 'bg-emerald-500 hover:bg-emerald-400 text-slate-950'
                    : 'bg-rose-500 hover:bg-rose-400 text-white'
                }`}
              >
                <Send className="h-3.5 w-3.5" />
                <span>{action === 'sign_off' ? 'Sign-off & Clear Claim' : 'Reject & Direct Re-investigation'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AttorneyOverrideModal;
