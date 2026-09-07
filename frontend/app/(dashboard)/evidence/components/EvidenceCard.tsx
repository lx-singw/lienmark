'use client';

/**
 * Evidence Card Component
 * Displays a single corroborated evidence artifact with cryptographic hash verification and stance tags.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import { ExternalLink, ShieldCheck, AlertCircle, FileCheck, Layers, Hash } from 'lucide-react';
import { EvidenceItem } from '../types';

interface EvidenceCardProps {
  readonly item: EvidenceItem;
  readonly onOpenCompare?: (claimId: string) => void;
}

function getStanceStyle(stance: string): { bg: string; text: string; border: string } {
  switch (stance?.toUpperCase()) {
    case 'SUPPORTING':
      return { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30' };
    case 'ADVERSE':
      return { bg: 'bg-rose-500/10', text: 'text-rose-400', border: 'border-rose-500/30' };
    default:
      return { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30' };
  }
}

export function EvidenceCard({ item, onOpenCompare }: EvidenceCardProps): React.JSX.Element {
  const stanceStyle = getStanceStyle(item.stance);
  const primaryClaim = item.linked_claims?.[0];

  return (
    <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 p-5 space-y-3 hover:border-slate-700/80 transition-all">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full px-2.5 py-0.5 text-[10px] font-mono font-bold uppercase border ${stanceStyle.bg} ${stanceStyle.text} ${stanceStyle.border}`}
            >
              {item.stance}
            </span>
            <span className="rounded-full bg-slate-900 border border-slate-800 px-2.5 py-0.5 text-[10px] font-mono text-slate-300">
              {item.confidence_tier.replace('_', ' ')}
            </span>
            {item.domain && (
              <span className="text-xs font-mono text-sky-400">{item.domain}</span>
            )}
          </div>
          <h3 className="text-sm font-bold text-white pt-1">{item.title}</h3>
        </div>

        <div className="flex items-center gap-2 self-start">
          {primaryClaim && onOpenCompare && (
            <button
              onClick={() => onOpenCompare(primaryClaim)}
              className="flex items-center gap-1 rounded-xl bg-sky-500/20 hover:bg-sky-500/30 border border-sky-500/40 px-2.5 py-1 text-xs font-medium text-sky-300 transition-colors"
            >
              <Layers className="h-3 w-3" />
              <span>Reconcile Shield</span>
            </button>
          )}
          {item.source_url && (
            <a
              href={item.source_url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white transition-colors"
            >
              <span>Source</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-slate-800/80 bg-slate-950/70 p-3">
        <p className="text-xs text-slate-300 font-mono leading-relaxed whitespace-pre-wrap">
          {item.snippet}
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono text-slate-400 pt-1 border-t border-slate-800/50">
        <div className="flex items-center gap-1.5">
          <Hash className="h-3 w-3 text-slate-500" />
          <span className="text-slate-500">SHA-256:</span>
          <span className="text-slate-300 font-mono">{item.payload_digest.slice(0, 16)}...</span>
        </div>

        <div className="flex items-center gap-2">
          {item.linked_claims?.length > 0 && (
            <span>
              Bound Claims: <span className="text-slate-200">{item.linked_claims.join(', ')}</span>
            </span>
          )}
          <span className="text-slate-600">·</span>
          <span>{new Date(item.retrieved_at).toLocaleDateString()}</span>
        </div>
      </div>
    </div>
  );
}
