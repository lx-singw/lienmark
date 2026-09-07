'use client';

/**
 * TriageCard Component
 * Actionable triage card for claims, clarifications, budget requests, and security flags.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React, { useState } from 'react';
import {
  AlertTriangle,
  HelpCircle,
  DollarSign,
  Gavel,
  CheckCircle2,
  XCircle,
  AlertOctagon,
  Clock,
} from 'lucide-react';
import { TriageItem } from '../types';
import {
  SecurityFlag,
  SecurityFlagBadge,
  SecurityWarningBanner,
  parseSecurityFlag,
} from '@/components/security';

interface TriageCardProps {
  readonly item: TriageItem;
  readonly onAction: (itemId: string, action: string, extra?: string) => void;
  readonly isSubmitting?: boolean;
}

function SeverityBadge({ severity }: { readonly severity: TriageItem['severity'] }) {
  const styles = {
    blocker: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
    high: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    medium: 'bg-sky-500/20 text-sky-300 border-sky-500/40',
    low: 'bg-slate-500/20 text-slate-300 border-slate-500/40',
  }[severity];

  return (
    <span className={`rounded-md border px-2 py-0.5 text-[10px] font-mono font-bold uppercase ${styles}`}>
      {severity}
    </span>
  );
}

function ClaimActions({
  item,
  onAction,
  disabled,
}: {
  readonly item: TriageItem;
  readonly onAction: (id: string, act: string) => void;
  readonly disabled: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/80">
      <button
        type="button"
        disabled={disabled}
        onClick={() => onAction(item.id, 're_attest')}
        className="flex items-center gap-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/40 px-3 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
      >
        <CheckCircle2 className="h-3.5 w-3.5" /> Re-Attest (PD)
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onAction(item.id, 'exception')}
        className="flex items-center gap-1.5 rounded-lg bg-rose-500/20 border border-rose-500/40 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-500/30 transition-colors disabled:opacity-50"
      >
        <AlertOctagon className="h-3.5 w-3.5" /> Schedule Exception
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onAction(item.id, 'reject')}
        className="flex items-center gap-1.5 rounded-lg bg-slate-800 border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 transition-colors disabled:opacity-50"
      >
        <XCircle className="h-3.5 w-3.5" /> Reject Asset
      </button>
    </div>
  );
}

function ClarificationActions({
  item,
  onAction,
  disabled,
}: {
  readonly item: TriageItem;
  readonly onAction: (id: string, act: string, opt?: string) => void;
  readonly disabled: boolean;
}) {
  const [selected, setSelected] = useState<string>(item.options?.[0] || '');

  return (
    <div className="space-y-2.5 pt-2 border-t border-slate-800/80">
      {item.options && (
        <div className="flex flex-wrap gap-2">
          {item.options.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => setSelected(opt)}
              className={`rounded-lg px-2.5 py-1 text-xs font-medium border transition-colors ${
                selected === opt
                  ? 'border-sky-500/50 bg-sky-950/50 text-sky-300 ring-1 ring-sky-500/30'
                  : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200'
              }`}
            >
              {opt}
            </button>
          ))}
        </div>
      )}
      <button
        type="button"
        disabled={disabled}
        onClick={() => onAction(item.id, 'answer', selected)}
        className="flex items-center gap-1.5 rounded-lg bg-sky-500/20 border border-sky-500/40 px-3.5 py-1.5 text-xs font-semibold text-sky-300 hover:bg-sky-500/30 transition-colors disabled:opacity-50"
      >
        <Gavel className="h-3.5 w-3.5" /> Submit Clarification Response
      </button>
    </div>
  );
}

function BudgetActions({
  item,
  onAction,
  disabled,
}: {
  readonly item: TriageItem;
  readonly onAction: (id: string, act: string) => void;
  readonly disabled: boolean;
}) {
  return (
    <div className="flex items-center gap-2 pt-2 border-t border-slate-800/80">
      <button
        type="button"
        disabled={disabled}
        onClick={() => onAction(item.id, 'authorize')}
        className="flex items-center gap-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/40 px-3 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
      >
        <DollarSign className="h-3.5 w-3.5" /> Authorize +{item.requestedAmount || '$25.00'}
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onAction(item.id, 'defer')}
        className="rounded-lg bg-slate-800 border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-400 hover:bg-slate-700 transition-colors disabled:opacity-50"
      >
        Defer / Cap Spend
      </button>
    </div>
  );
}

function renderCardHeader(item: TriageItem, securityFlag: SecurityFlag | null): React.JSX.Element {
  const Icon = item.type === 'claim' ? AlertTriangle : item.type === 'clarification' ? HelpCircle : DollarSign;
  const iconColor = item.type === 'claim' ? 'text-amber-400' : item.type === 'clarification' ? 'text-sky-400' : 'text-emerald-400';

  return (
    <div className="flex items-start justify-between gap-3">
      <div className="flex items-start gap-3">
        <div className={`mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 border border-slate-800 ${iconColor} shrink-0`}>
          <Icon className="h-4 w-4" />
        </div>
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-sm font-bold text-white">{item.title}</h4>
            <SeverityBadge severity={item.severity} />
            {securityFlag && <SecurityFlagBadge flag={securityFlag} size="sm" />}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">{item.subtitle}</p>
        </div>
      </div>
      {item.sceneOrTimecode && (
        <span className="flex items-center gap-1 rounded bg-slate-900 border border-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-400 shrink-0">
          <Clock className="h-3 w-3 text-slate-500" /> {item.sceneOrTimecode}
        </span>
      )}
    </div>
  );
}

export const TriageCard: React.FC<TriageCardProps> = ({ item, onAction, isSubmitting = false }) => {
  const securityFlag = item.securityFlag ?? parseSecurityFlag(item.flaggedReason);
  const borderHighlight = securityFlag?.type === 'PROMPT_INJECTION'
    ? 'border-rose-500/60 bg-[#16080e]/70 shadow-rose-950/30 ring-1 ring-rose-500/30'
    : securityFlag?.type === 'ZERO_CLAIMS_ANOMALY'
    ? 'border-amber-500/60 bg-[#161006]/70 shadow-amber-950/30 ring-1 ring-amber-500/30'
    : 'border-slate-800 bg-[#0e1424]/80 hover:border-slate-700/80';

  return (
    <div className={`rounded-xl border backdrop-blur-md p-4 space-y-3 transition-all hover:shadow-xl shadow-black/40 ${borderHighlight}`}>
      {renderCardHeader(item, securityFlag)}
      {securityFlag && (
        <div className="pl-11">
          <SecurityWarningBanner
            flag={securityFlag}
            anomaly={item.anomalyPayload ?? { rawSnippet: item.description, sceneRef: item.sceneOrTimecode }}
          />
        </div>
      )}
      <p className="text-xs text-slate-300 leading-relaxed pl-11">{item.description}</p>
      <div className="pl-11">
        {item.type === 'claim' && <ClaimActions item={item} onAction={onAction} disabled={isSubmitting} />}
        {item.type === 'clarification' && <ClarificationActions item={item} onAction={onAction} disabled={isSubmitting} />}
        {item.type === 'budget' && <BudgetActions item={item} onAction={onAction} disabled={isSubmitting} />}
      </div>
    </div>
  );
};

export default TriageCard;
