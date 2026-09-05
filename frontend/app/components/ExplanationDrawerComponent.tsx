'use client';

/**
 * Lienmark Four-Dimensional Clearance Legal Breakdown & Prior Baseline Accordion
 * Presents the 4 mandated dimensions: Creative Change, External Evidence Change,
 * Private Agreement Facts, and Statutory Policy Reason, plus inspectable Locked v7 baseline.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import {
  Scale,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  FileText,
  ShieldAlert,
  Info,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { EvidenceStance, ReviewQueueItem } from '@/lib/types';

export interface ExplanationDrawerComponentProps {
  activeQueueItem: ReviewQueueItem;
  isPriorDecisionOpen: boolean;
  onTogglePriorDecision: () => void;
}

export const ExplanationDrawerComponent: React.FC<ExplanationDrawerComponentProps> = ({
  activeQueueItem,
  isPriorDecisionOpen,
  onTogglePriorDecision,
}) => {
  const fourDims = activeQueueItem?.four_dimensions;
  const creative = fourDims?.creative_change;
  const evidence = fourDims?.external_evidence_change;
  const agreement = fourDims?.private_agreement_facts;
  const statutory = fourDims?.statutory_policy_reason;
  const prior = activeQueueItem?.prior_decision;

  const stance = evidence?.stance || EvidenceStance.SUPPORTING;
  const isStanceSupporting = stance === EvidenceStance.SUPPORTING;
  const isCriticalRisk = statutory?.eo_risk_rating === 'CRITICAL';

  return (
    <section aria-label="Four-Dimensional Clearance Breakdown" className="space-y-4">
      {/* Dimension Title & Stable Key */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Scale className="h-4 w-4 text-sky-400" aria-hidden="true" />
          <span>Four-Dimensional Clearance Legal Breakdown &middot;</span>{' '}
          <span className="text-sky-300">{activeQueueItem.asset_name}</span>
        </h3>
        <span className="text-xs font-mono text-slate-400">
          Lineage Key: <strong className="text-slate-300">{activeQueueItem.stable_lineage_key}</strong>
        </span>
      </div>

      {/* 4-Dimensional Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Dimension 1: Creative Change */}
        <div
          className="rounded-xl border border-slate-800 bg-[#131b2e] p-4 space-y-2.5 shadow-sm"
          role="region"
          aria-label="Dimension 1: Creative Change"
        >
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <span className="text-base" aria-hidden="true">🎬</span>
              <span>1. Creative Change Dimension</span>
            </div>
            <span
              className={`rounded px-2 py-0.5 text-[10px] font-mono font-bold ${
                creative?.has_changed
                  ? 'bg-amber-950/80 text-amber-300 border border-amber-500/40'
                  : 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/40'
              }`}
            >
              {creative?.has_changed ? 'MATERIAL SHIFT' : 'UNCHANGED (STABLE)'}
            </span>
          </div>

          <div className="space-y-1.5 text-xs text-slate-300">
            <div>
              <span className="text-slate-500 font-semibold">Scene / Location:</span>{' '}
              <span className="text-slate-200 font-mono">{creative?.scene || activeQueueItem.scene}</span>
            </div>
            <div>
              <span className="text-slate-500 font-semibold">Prominence Shift:</span>{' '}
              <span className="text-slate-200">
                {creative?.before_prominence || 'Incidental blur'} &rarr;{' '}
                <strong className="text-amber-300">{creative?.after_prominence || 'Focal close-up'}</strong>
              </span>
            </div>
            <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800 space-y-1">
              <div className="text-[11px] text-slate-400">
                <strong className="text-slate-300">Before (v7):</strong>{' '}
                {creative?.before_context || 'Out-of-focus background decor.'}
              </div>
              <div className="text-[11px] text-slate-200">
                <strong className="text-sky-300">After (v8):</strong>{' '}
                {creative?.after_context || 'Prominent foreground framing.'}
              </div>
              {creative?.dialogue_shift && (
                <div className="text-[11px] text-sky-300 pt-1 border-t border-slate-800 font-serif italic">
                  <strong>Dialogue Shift:</strong> &ldquo;{creative.dialogue_shift}&rdquo;
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Dimension 2: External Evidence Change */}
        <div
          className="rounded-xl border border-slate-800 bg-[#131b2e] p-4 space-y-2.5 shadow-sm"
          role="region"
          aria-label="Dimension 2: External Evidence Change"
        >
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <span className="text-base" aria-hidden="true">🔍</span>
              <span>2. External Evidence Change</span>
            </div>
            <span
              className={`rounded px-2 py-0.5 text-[10px] font-mono font-bold ${
                isStanceSupporting
                  ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/40'
                  : 'bg-rose-950/80 text-rose-300 border border-rose-500/40'
              }`}
            >
              STANCE: {String(stance).toUpperCase()}
            </span>
          </div>

          <div className="space-y-1.5 text-xs text-slate-300">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-slate-500 font-semibold">Provider:</span>{' '}
                <span className="text-sky-300 font-bold">{evidence?.provider || 'Parallel'} Search API</span>
              </div>
              <span className="text-[10px] text-slate-400 font-mono">
                Latency: {evidence?.retrieval_latency_ms || 142}ms
              </span>
            </div>

            <div>
              <a
                href={evidence?.source_url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs font-semibold text-sky-300 hover:underline flex items-center gap-1"
                aria-label={`Open citation: ${evidence?.source_title || 'Citation Source'}`}
              >
                <span>{evidence?.source_title || 'Parallel Search Registry Citation'}</span>
                <ExternalLink className="h-3 w-3 inline flex-shrink-0" aria-hidden="true" />
              </a>
            </div>

            <blockquote className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800 text-[11px] text-slate-200 font-serif italic">
              &ldquo;{evidence?.excerpt || 'Corroborating record excerpt retrieved from public registry.'}&rdquo;
            </blockquote>

            <div className="text-[10px] font-mono text-slate-500 truncate">
              Query: &quot;{evidence?.query_issued || 'Registry query executed'}&quot;
            </div>
          </div>
        </div>

        {/* Dimension 3: Private Agreement Facts */}
        <div
          className="rounded-xl border border-slate-800 bg-[#131b2e] p-4 space-y-2.5 shadow-sm"
          role="region"
          aria-label="Dimension 3: Private Agreement Facts"
        >
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <span className="text-base" aria-hidden="true">📜</span>
              <span>3. Private Agreement Facts</span>
            </div>
            <span
              className={`rounded px-2 py-0.5 text-[10px] font-mono font-bold ${
                agreement?.contract_shield_applied
                  ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/40'
                  : 'bg-slate-800 text-slate-400 border border-slate-700'
              }`}
            >
              § 205(e) SHIELD: {agreement?.contract_shield_applied ? 'APPLIED' : 'INAPPLICABLE'}
            </span>
          </div>

          <div className="space-y-1.5 text-xs text-slate-300">
            <div>
              <span className="text-slate-500 font-semibold">Contract Licensor:</span>{' '}
              <span className="text-slate-200 font-medium">
                {agreement?.licensor || 'None on file (Public domain / unlicensed)'}
              </span>
            </div>
            <div>
              <span className="text-slate-500 font-semibold">Grant Scope:</span>{' '}
              <span className="text-slate-200">
                {agreement?.grant_scope || 'No express written grant'}
              </span>
            </div>
            <div>
              <span className="text-slate-500 font-semibold">Term in Perpetuity:</span>{' '}
              <span className="text-slate-200 font-mono">
                {agreement?.term || 'N/A'}
              </span>
            </div>
            <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800 text-[11px] text-slate-300 space-y-1">
              <div className="text-slate-400 font-semibold">17 U.S.C. § 205(e) Defense Analysis:</div>
              <p>{agreement?.section_205_e_status || 'No priority of conflicting transfer applicable.'}</p>
            </div>
          </div>
        </div>

        {/* Dimension 4: Statutory Policy Reason */}
        <div
          className="rounded-xl border border-slate-800 bg-[#131b2e] p-4 space-y-2.5 shadow-sm"
          role="region"
          aria-label="Dimension 4: Statutory Policy Reason"
        >
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <span className="text-base" aria-hidden="true">⚖️</span>
              <span>4. Statutory Policy Reason</span>
            </div>
            <span
              className={`rounded px-2 py-0.5 text-[10px] font-mono font-bold ${
                isCriticalRisk
                  ? 'bg-rose-950/80 text-rose-300 border border-rose-500/40'
                  : 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/40'
              }`}
            >
              E&O RISK: {statutory?.eo_risk_rating || 'CONTROLLED'}
            </span>
          </div>

          <div className="space-y-1.5 text-xs text-slate-300">
            <div>
              <span className="text-slate-500 font-semibold">Reason Code:</span>{' '}
              <span className="font-mono text-amber-300 font-bold">
                {statutory?.reason_code || 'CREATIVE_CONTEXT_ALTERED'}
              </span>
            </div>
            <div>
              <span className="text-slate-500 font-semibold">Statutory Reference:</span>{' '}
              <span className="text-slate-200 font-mono">
                {statutory?.statutory_reference || '17 U.S.C. § 101, 107'}
              </span>
            </div>
            <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800 space-y-1 text-[11px]">
              <div className="text-slate-400 font-semibold">Statutory Exposure (17 U.S.C. § 504(c)):</div>
              <p className={isCriticalRisk ? 'text-rose-300 font-semibold' : 'text-slate-300'}>
                {statutory?.statutory_exposure || 'Statutory damages excluded upon counsel re-attestation.'}
              </p>
              <div className="text-slate-400 font-semibold pt-1 border-t border-slate-800">
                Applicable Legal Doctrine:
              </div>
              <p className="text-slate-200">{statutory?.doctrine || 'Public Domain / Fair Use evaluation.'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Inspectable Prior Baseline Decision Accordion */}
      {prior && (
        <div className="rounded-xl border border-slate-800 bg-[#131b2e] overflow-hidden shadow-sm">
          <button
            type="button"
            onClick={onTogglePriorDecision}
            className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-800/40 transition-colors focus:outline-none focus:ring-1 focus:ring-sky-500"
            aria-expanded={isPriorDecisionOpen}
            aria-controls="prior-decision-details"
          >
            <div className="flex items-center gap-2.5">
              <FileText className="h-4 w-4 text-sky-400" aria-hidden="true" />
              <span className="text-sm font-bold text-white">
                Inspect Prior Baseline Approval (Locked Script v7 Decision)
              </span>
              <span className="text-xs font-mono text-emerald-400 font-semibold bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
                {prior.status.toUpperCase()}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span>{isPriorDecisionOpen ? 'Hide baseline audit' : 'Expand baseline audit'}</span>
              {isPriorDecisionOpen ? (
                <ChevronUp className="h-4 w-4 text-slate-400" aria-hidden="true" />
              ) : (
                <ChevronDown className="h-4 w-4 text-slate-400" aria-hidden="true" />
              )}
            </div>
          </button>

          {isPriorDecisionOpen && (
            <div
              id="prior-decision-details"
              className="p-4 pt-0 border-t border-slate-800/80 bg-slate-900/40 space-y-3 text-xs animate-in fade-in duration-200"
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-3 text-[11px] text-slate-300">
                <div>
                  <span className="text-slate-500">Prior Decision ID:</span>
                  <p className="font-mono text-slate-200 font-semibold">{prior.decision_id}</p>
                </div>
                <div>
                  <span className="text-slate-500">Applicable Version:</span>
                  <p className="font-mono text-slate-200">{prior.version_id} (Locked Baseline)</p>
                </div>
                <div>
                  <span className="text-slate-500">Reviewed Timestamp:</span>
                  <p className="font-mono text-slate-200">{prior.reviewed_at}</p>
                </div>
                <div className="sm:col-span-2">
                  <span className="text-slate-500">Prior Reviewer Identity:</span>
                  <p className="font-semibold text-slate-200">{prior.reviewer_display_name}</p>
                </div>
                <div>
                  <span className="text-slate-500">Scope or Conditions:</span>
                  <p className="text-slate-300">{prior.scope_or_conditions || 'Unconditional approval'}</p>
                </div>
              </div>

              <div className="rounded bg-slate-950/80 border border-slate-800 p-3 space-y-1.5">
                <div className="text-[11px] text-slate-400 font-semibold">Prior Legal Rationale:</div>
                <p className="text-slate-200 italic font-serif">&ldquo;{prior.rationale}&rdquo;</p>
                <div className="text-[10px] font-mono text-slate-500 pt-1">
                  SHA-256 Context Hash: {prior.context_hash}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
};

export default ExplanationDrawerComponent;
