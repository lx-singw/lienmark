'use client';

/**
 * Lienmark Clarifying Question Modal
 * Hollywood Studio Legal Ops HITL Clearance Component
 * Modern glassmorphism modal presenting clearance context, legal rationale,
 * suggested option pills, character-validated response input, and agreement dropzone.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { HelpCircle, ShieldAlert, Send } from 'lucide-react';
import {
  ClarificationRequestUI,
  ClarificationResponsePayload,
  AttachedDocument,
} from './hitl_types';
import { validateClarificationResponse } from './hitl_utils';
import ClarificationModalHeader from './ClarificationModalHeader';
import ClarificationContextCard from './ClarificationContextCard';
import ClarificationOptionsPicker from './ClarificationOptionsPicker';
import ClarificationDropzone from './ClarificationDropzone';

export interface ClarifyingQuestionModalProps {
  readonly isOpen: boolean;
  readonly request: ClarificationRequestUI | null;
  readonly onClose: () => void;
  readonly onSubmit: (payload: ClarificationResponsePayload) => void;
  readonly onEscalate?: (payload: ClarificationResponsePayload) => void;
  readonly isSubmitting?: boolean;
}

export const ClarifyingQuestionModal: React.FC<ClarifyingQuestionModalProps> = ({
  isOpen,
  request,
  onClose,
  onSubmit,
  onEscalate,
  isSubmitting = false,
}) => {
  const [responseText, setResponseText] = useState<string>('');
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<ReadonlyArray<AttachedDocument>>([]);
  const [hasInteracted, setHasInteracted] = useState<boolean>(false);

  useEffect(() => {
    if (request && isOpen) {
      setResponseText('');
      setSelectedOption(null);
      setAttachments([]);
      setHasInteracted(false);
    }
  }, [request, isOpen]);

  const validation = validateClarificationResponse(responseText);

  const handleOptionSelect = useCallback((option: string | null) => {
    setSelectedOption(option);
    if (option && responseText.trim().length === 0) {
      setResponseText(option);
    }
  }, [responseText]);

  const handleAddAttachment = useCallback((doc: AttachedDocument) => {
    setAttachments((prev) => [...prev, doc]);
  }, []);

  const handleRemoveAttachment = useCallback((id: string) => {
    setAttachments((prev) => prev.filter((d) => d.id !== id));
  }, []);

  const buildPayload = (action: 'submit' | 'escalate'): ClarificationResponsePayload | null => {
    if (!request) return null;
    return {
      requestId: request.id,
      claimKey: request.claimKey,
      responseText: responseText.trim(),
      selectedOption,
      action,
      attachments,
      submittedByRole: request.assignedRole,
      submittedAt: new Date().toISOString(),
    };
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setHasInteracted(true);
    if (!validation.isValid) return;
    const payload = buildPayload('submit');
    if (payload) onSubmit(payload);
  };

  const handleEscalateAction = () => {
    setHasInteracted(true);
    const payload = buildPayload('escalate');
    if (!payload) return;
    if (onEscalate) onEscalate(payload);
    else onSubmit(payload);
  };

  if (!isOpen || !request) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="clarification-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 sm:p-6 overflow-y-auto animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-700/60 bg-gradient-to-b from-[#131b2e] via-[#0d1424] to-[#0a0f1d] p-6 shadow-2xl space-y-5 border-t-2 border-t-sky-400">
        <ClarificationModalHeader
          request={request}
          onClose={onClose}
          isSubmitting={isSubmitting}
        />

        <ClarificationContextCard
          scriptExcerpt={request.scriptExcerpt}
          rationale={request.rationale}
          scene={request.scene}
        />

        {/* Specific Question Text with Clear Visual Emphasis */}
        <div className="rounded-xl border border-sky-500/50 bg-gradient-to-r from-sky-950/40 via-indigo-950/30 to-slate-900/60 p-4 shadow-lg space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-sky-300 font-mono">
            <HelpCircle className="h-4 w-4 text-sky-400 flex-shrink-0" aria-hidden="true" />
            <span>Target Clarification Question:</span>
          </div>
          <p className="text-sm font-semibold text-white leading-relaxed">
            {request.questionText}
          </p>
        </div>

        <ClarificationOptionsPicker
          options={request.suggestedOptions}
          selectedOption={selectedOption}
          onSelectOption={handleOptionSelect}
          disabled={isSubmitting}
        />

        <form onSubmit={handleFormSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-400">
              <label htmlFor="clarification-response-text" className="text-slate-300">
                Clarification Response:
              </label>
              <span className={validation.remainingChars < 0 ? 'text-rose-400 font-bold' : 'text-slate-400'}>
                {validation.charCount} / 1000 characters
              </span>
            </div>
            <textarea
              id="clarification-response-text"
              rows={3}
              value={responseText}
              onChange={(e) => setResponseText(e.target.value)}
              placeholder="Enter factual clarification, work-for-hire status, or agreement execution details..."
              disabled={isSubmitting}
              className="w-full rounded-xl border border-slate-700 bg-slate-900/90 p-3 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500 font-sans transition-colors"
            />
            {hasInteracted && !validation.isValid && validation.error && (
              <p className="text-[11px] text-rose-400 font-medium">{validation.error}</p>
            )}
          </div>

          <ClarificationDropzone
            attachments={attachments}
            onAddAttachment={handleAddAttachment}
            onRemoveAttachment={handleRemoveAttachment}
            disabled={isSubmitting}
          />

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-800/80 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="rounded-lg border border-slate-700 bg-slate-900/80 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
            >
              Cancel
            </button>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={handleEscalateAction}
                disabled={isSubmitting}
                className="inline-flex items-center gap-1.5 rounded-lg border border-amber-500/50 bg-amber-950/30 px-3.5 py-2 text-xs font-bold text-amber-300 hover:bg-amber-900/40 hover:text-amber-200 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400"
                title="Escalate directly to Clearance Counsel"
              >
                <ShieldAlert className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
                <span>Escalate to Counsel</span>
              </button>

              <button
                type="submit"
                disabled={isSubmitting || (hasInteracted && !validation.isValid)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 px-4 py-2 text-xs font-bold text-slate-950 shadow-lg shadow-sky-500/20 transition-all focus:outline-none focus:ring-2 focus:ring-sky-400 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="h-3.5 w-3.5" aria-hidden="true" />
                <span>{isSubmitting ? 'Submitting...' : 'Submit Clarification'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ClarifyingQuestionModal;
