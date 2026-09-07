'use client';

/**
 * SecurityWarningBanner Component
 * Prominent high-contrast security warning banner with expandable forensic snippet
 * and direct navigation to the immutable audit ledger.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React, { useState } from 'react';
import Link from 'next/link';
import {
  ShieldAlert,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Terminal,
  ArrowUpRight,
  Lock,
  Code2,
  FileCheck2,
} from 'lucide-react';
import { SecurityWarningProps, parseSecurityFlag } from './types';

function renderBannerHeader(
  flagType: string,
  description: string,
  ledgerHref: string
): React.JSX.Element {
  const isInjection = flagType === 'PROMPT_INJECTION';
  return (
    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
      <div className="flex items-start gap-3">
        <div
          className={`p-2 rounded-lg shrink-0 mt-0.5 ${
            isInjection
              ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
              : 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
          }`}
        >
          {isInjection ? (
            <ShieldAlert className="h-5 w-5" />
          ) : (
            <AlertTriangle className="h-5 w-5" />
          )}
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h4 className="text-xs font-bold font-mono uppercase tracking-wider text-white">
              {isInjection
                ? 'SECURITY INTERVENTION: PROMPT INJECTION TRAPPED'
                : 'SECURITY ANOMALY: STATISTICALLY IMPROBABLE SCRIPT'}
            </h4>
            <span
              className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border uppercase ${
                isInjection
                  ? 'bg-rose-500/20 border-rose-500/40 text-rose-300'
                  : 'bg-amber-500/20 border-amber-500/40 text-amber-300'
              }`}
            >
              {isInjection ? 'Layer-1 Trapped' : 'Gate Blocked'}
            </span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">{description}</p>
        </div>
      </div>

      <Link
        href={ledgerHref}
        className="flex items-center gap-1.5 rounded-lg bg-slate-900 border border-slate-700/80 px-3 py-1.5 text-xs font-mono font-semibold text-sky-300 hover:text-white hover:border-sky-500/50 hover:bg-slate-800 transition-colors shrink-0 shadow-sm"
      >
        <Lock className="h-3.5 w-3.5 text-emerald-400" />
        <span>Audit Ledger Proof</span>
        <ArrowUpRight className="h-3 w-3 text-slate-400" />
      </Link>
    </div>
  );
}

function renderForensicDetails(
  rawSnippet?: string,
  matchedRules?: ReadonlyArray<string>,
  confidenceScore?: number,
  sceneRef?: string
): React.JSX.Element {
  return (
    <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-2.5 font-mono text-xs">
      <div className="flex items-center justify-between text-[11px] text-slate-400">
        <span className="flex items-center gap-1 text-slate-300">
          <Code2 className="h-3.5 w-3.5 text-sky-400" />
          <span>FORENSIC SNIPPET CAPTURE</span>
        </span>
        <span>
          Confidence: <strong className="text-emerald-400">{confidenceScore ?? 1.0}</strong> · Ref: {sceneRef || 'Intake'}
        </span>
      </div>

      <div className="rounded-lg bg-black/70 border border-slate-800 p-3 text-rose-300 break-all select-all text-[11px] leading-relaxed">
        {rawSnippet || 'Adversarial instruction directive isolated and quarantined in sandbox.'}
      </div>

      {matchedRules && matchedRules.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
          <span className="text-slate-500">TRIPWIRE MATCH:</span>
          {matchedRules.map((rule, i) => (
            <span key={i} className="rounded bg-rose-500/10 border border-rose-500/30 px-1.5 py-0.5 text-rose-300">
              {rule}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 pt-0.5">
        <FileCheck2 className="h-3 w-3" />
        <span>Containment Invariant: Instruction hierarchy enforced; model jailbreak prevented.</span>
      </div>
    </div>
  );
}

export function SecurityWarningBanner({
  flag,
  anomaly,
  ledgerHref = '/decisions',
  className = '',
}: SecurityWarningProps): React.JSX.Element {
  const [expanded, setExpanded] = useState<boolean>(false);
  const isInjection = flag.type === 'PROMPT_INJECTION';

  const containerClass = isInjection
    ? 'border-rose-500/50 bg-[#16080e]/90 shadow-rose-950/40'
    : 'border-amber-500/50 bg-[#161006]/90 shadow-amber-950/40';

  return (
    <div
      className={`rounded-xl border backdrop-blur-md p-4 space-y-3 transition-all shadow-lg ${containerClass} ${className}`}
    >
      {renderBannerHeader(flag.type, flag.description, ledgerHref)}

      <div className="flex items-center justify-between pt-1">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-xs font-mono font-medium text-slate-400 hover:text-slate-200 transition-colors"
        >
          <Terminal className="h-3.5 w-3.5 text-sky-400" />
          <span>{expanded ? 'Hide Forensic Payload Details' : 'Inspect Forensic Payload Details'}</span>
          {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>

        <span className="text-[10px] font-mono text-slate-500 uppercase">
          Autonomous Defense Layer 1
        </span>
      </div>

      {expanded &&
        renderForensicDetails(
          anomaly?.rawSnippet,
          anomaly?.matchedRules,
          anomaly?.confidenceScore,
          anomaly?.sceneRef
        )}
    </div>
  );
}

export default SecurityWarningBanner;
