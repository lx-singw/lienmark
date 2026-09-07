'use client';

/**
 * Lienmark Direct Override Form Component (Sprint 5.2)
 * Form for direct attorney sign-off or reinvestigation rejection.
 * Extracted from AttorneyOverrideModal along SRP lines.
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import React, { useState } from 'react';
import { CheckCircle2, AlertTriangle, Send } from 'lucide-react';
import { CounselActionType, DecisionPayload, DirectOverrideFormProps } from './review_types';
import { DIRECTIVE_SHORTCUTS, validateDecisionPayload } from './review_utils';
import { CitationSuggestionPicker } from './CitationSuggestionPicker';

export const DirectOverrideForm: React.FC<DirectOverrideFormProps> = ({
  initialAction = 'sign_off',
  reviewerName,
  reviewerId,
  onDecision,
  onClose,
  isSubmitting = false,
}) => {
  const [action, setAction] = useState<CounselActionType>(initialAction);
  const [directiveText, setDirectiveText] = useState<string>('');
  const [citationText, setCitationText] = useState<string>('');
  const [conditions, setConditions] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleShortcutClick = (text: string): void => {
    setDirectiveText((prev) => (prev ? `${prev.trim()}; ${text}` : text));
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

  return (
    <form onSubmit={handleSubmit} className="space-y-4" data-testid="direct-override-form">
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => { setAction('sign_off'); setErrorMessage(null); }}
          className={`flex items-center justify-center gap-2 rounded-xl border p-2.5 text-xs font-bold transition-all ${
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
          className={`flex items-center justify-center gap-2 rounded-xl border p-2.5 text-xs font-bold transition-all ${
            action === 'reject'
              ? 'border-rose-500 bg-rose-950/70 text-rose-200 ring-2 ring-rose-500/50 shadow-lg'
              : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700'
          }`}
        >
          <AlertTriangle className="h-4 w-4 text-rose-400" />
          <span>Reject & Direct Re-investigation</span>
        </button>
      </div>

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
          placeholder={action === 'reject' ? 'e.g. Re-search ASCAP for 1972 live adaptation...' : 'Optional directives for production team...'}
          className="w-full rounded-lg border border-slate-800 bg-slate-950/80 p-2 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none"
        />
      </div>

      <div className="space-y-1.5">
        <CitationSuggestionPicker onSelectCitation={(text) => setCitationText(text)} selectedCitationText={citationText} />
        <label className="block text-xs font-semibold text-slate-200 mt-1">
          Affirmative Legal Citation / Statutory Basis {action === 'sign_off' && <span className="text-emerald-400">*</span>}
        </label>
        <textarea
          value={citationText}
          onChange={(e) => setCitationText(e.target.value)}
          rows={2}
          placeholder="Statutory citation (e.g. 17 U.S.C. § 107 Fair Use analysis)..."
          className="w-full rounded-lg border border-slate-800 bg-slate-950/80 p-2 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-1">Clearance Conditions (Optional)</label>
        <input
          type="text"
          value={conditions}
          onChange={(e) => setConditions(e.target.value)}
          placeholder="e.g. Subject to North American theatrical delivery only..."
          className="w-full rounded-lg border border-slate-800 bg-slate-950/80 p-2 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none"
        />
      </div>

      {errorMessage && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-950/50 p-2 text-xs text-rose-300 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      <div className="flex items-center justify-between pt-2 border-t border-slate-800">
        <div className="text-[11px] font-mono text-slate-400">Signer: <span className="text-slate-200 font-semibold">{reviewerName}</span></div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={onClose} disabled={isSubmitting} className="rounded-lg border border-slate-800 px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-800">Cancel</button>
          <button
            type="submit"
            disabled={isSubmitting}
            className={`inline-flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-xs font-bold transition-all shadow-md ${
              action === 'sign_off' ? 'bg-emerald-500 hover:bg-emerald-400 text-slate-950' : 'bg-rose-500 hover:bg-rose-400 text-white'
            }`}
          >
            <Send className="h-3.5 w-3.5" />
            <span>{action === 'sign_off' ? 'Sign-off & Clear Claim' : 'Reject & Direct Re-investigation'}</span>
          </button>
        </div>
      </div>
    </form>
  );
};

export default DirectOverrideForm;
