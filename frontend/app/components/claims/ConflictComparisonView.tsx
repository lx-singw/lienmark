'use client';

/**
 * ConflictComparisonView.tsx
 * Side-by-side comparative panel contrasting contradictory sources,
 * highlighted conflicting fields, stance badges, and mandatory counsel elevation.
 * Sprint 3.3: Contradictory Evidence & Conflict Arbitration UI.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import {
  AlertOctagon,
  ArrowRightLeft,
  CheckCircle2,
  HelpCircle,
  Scale,
} from 'lucide-react';
import {
  type ConflictEvidencePair,
  type ConflictFieldDiff,
  ConflictResolutionStance,
} from './conflict_types';
import {
  getSeverityBadgeStyle,
  getStanceBadgeStyle,
} from './conflict_utils';
import { SAMPLE_APOLLO_CONFLICT_PAIR } from './conflict_fixtures';
import { ConflictSourceCard } from './ConflictSourceCard';
import { ConflictRiskAlert } from './ConflictRiskAlert';

export interface ConflictComparisonViewProps {
  readonly pair?: ConflictEvidencePair;
  readonly onAdjudicate?: (pairId: string, action: 're_attest' | 'exception' | 'reject') => void;
  readonly isReadOnly?: boolean;
  readonly className?: string;
}

function renderStanceBadge(stance: ConflictResolutionStance): React.ReactElement {
  const style = getStanceBadgeStyle(stance);
  const icon =
    style.iconName === 'AlertOctagon' ? (
      <AlertOctagon className="h-4 w-4 text-rose-400 animate-pulse" aria-hidden="true" />
    ) : style.iconName === 'CheckCircle2' ? (
      <CheckCircle2 className="h-4 w-4 text-emerald-400" aria-hidden="true" />
    ) : (
      <HelpCircle className="h-4 w-4 text-slate-400" aria-hidden="true" />
    );

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold font-mono border shadow-md ${style.bg} ${style.border} ${style.text}`}
      role="status"
      aria-label={`Conflict Stance: ${style.label}`}
    >
      {icon}
      <span>[{style.label}]</span>
    </span>
  );
}

function renderDiffValues(sourceAValue: string, sourceBValue: string): React.ReactElement {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
      <div className="p-2 rounded bg-black/40 border border-slate-800/80">
        <span className="text-[9px] font-mono text-cyan-400 block uppercase">Source A:</span>
        <span className="font-medium text-slate-200">{sourceAValue}</span>
      </div>
      <div className="p-2 rounded bg-black/40 border border-slate-800/80">
        <span className="text-[9px] font-mono text-rose-400 block uppercase">Source B:</span>
        <span className="font-medium text-slate-200">{sourceBValue}</span>
      </div>
    </div>
  );
}

function renderDiffRow(diff: ConflictFieldDiff): React.ReactElement {
  const sevStyle = getSeverityBadgeStyle(diff.severity);
  const badgeClasses = diff.isConflicting
    ? `${sevStyle.bg} ${sevStyle.border} ${sevStyle.text}`
    : 'bg-emerald-950/70 text-emerald-300 border-emerald-600/60';
  const rowBg = diff.isConflicting
    ? 'bg-rose-950/20 border-rose-500/40 hover:border-rose-500/70'
    : 'bg-slate-900/40 border-slate-800';

  return (
    <div key={diff.fieldKey} className={`p-3 rounded-lg border text-xs transition-colors ${rowBg}`}>
      <div className="flex items-center justify-between mb-1.5">
        <span className="font-bold text-slate-200 font-mono text-[11px] uppercase tracking-wider">
          {diff.fieldLabel}
        </span>
        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${badgeClasses}`}>
          {diff.isConflicting ? `[CONFLICT - ${diff.severity.toUpperCase()}]` : '[MATCH]'}
        </span>
      </div>
      {renderDiffValues(diff.sourceAValue, diff.sourceBValue)}
      {diff.isConflicting && diff.statutoryNote && (
        <p className="mt-1.5 text-[10px] text-amber-300/90 italic font-mono leading-tight">
          &bull; Legal Note: {diff.statutoryNote}
        </p>
      )}
    </div>
  );
}

function renderPanelHeader(pair: ConflictEvidencePair): React.ReactElement {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
      <div className="flex items-center gap-2.5">
        <Scale className="h-5 w-5 text-amber-400 shrink-0" aria-hidden="true" />
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-slate-100">{pair.assetName}</h3>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
              {pair.sceneTimecode}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-mono">
            Conflict Investigation ID: {pair.id}
          </p>
        </div>
      </div>
      {renderStanceBadge(pair.stance)}
    </div>
  );
}

export const ConflictComparisonView: React.FC<ConflictComparisonViewProps> = ({
  pair = SAMPLE_APOLLO_CONFLICT_PAIR,
  onAdjudicate,
  isReadOnly = false,
  className = '',
}) => {
  const conflictingCount = pair.fieldDiffs.filter((d) => d.isConflicting).length;

  return (
    <div
      className={`rounded-2xl bg-[#080d1a] border border-slate-800 p-4 md:p-6 space-y-5 shadow-2xl ${className}`}
      role="region"
      aria-label="Contradictory Evidence and Conflict Comparison Panel"
    >
      {renderPanelHeader(pair)}

      <div className="relative">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ConflictSourceCard source={pair.sourceA} sideTag="SOURCE A" />
          <ConflictSourceCard source={pair.sourceB} sideTag="SOURCE B" />
        </div>
        <div className="hidden md:flex absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-8 w-8 rounded-full bg-slate-900 border border-slate-700 items-center justify-center shadow-lg text-slate-300 text-[10px] font-bold font-mono">
          <ArrowRightLeft className="h-3.5 w-3.5 text-amber-400" />
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono">
            Highlighted Conflicting Fields Matrix
          </h4>
          <span className="text-[10px] font-mono text-slate-400">
            {conflictingCount} of {pair.fieldDiffs.length} fields conflicting
          </span>
        </div>
        <div className="space-y-2">
          {pair.fieldDiffs.map((diff) => renderDiffRow(diff))}
        </div>
      </div>

      <ConflictRiskAlert pair={pair} onAdjudicate={onAdjudicate} isReadOnly={isReadOnly} />
    </div>
  );
};

export default ConflictComparisonView;
