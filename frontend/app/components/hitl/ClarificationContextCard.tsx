'use client';

/**
 * Lienmark HITL Clarification Context Card
 * Displays the screenplay excerpt alongside the legal rationale explaining
 * why human-in-the-loop clarification is needed for clearance.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { Quote, AlertTriangle } from 'lucide-react';

export interface ClarificationContextCardProps {
  readonly scriptExcerpt: string;
  readonly rationale: string;
  readonly scene: string;
  readonly className?: string;
}

export const ClarificationContextCard: React.FC<ClarificationContextCardProps> = ({
  scriptExcerpt,
  rationale,
  scene,
  className = '',
}) => {
  return (
    <div className={`space-y-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4 ${className}`}>
      {/* Script Cut Excerpt Section */}
      <div className="space-y-1.5">
        <div className="flex items-center gap-1.5 text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-400">
          <Quote className="h-3.5 w-3.5 text-sky-400 flex-shrink-0" aria-hidden="true" />
          <span>Script Excerpt &middot; {scene}</span>
        </div>
        <div className="relative rounded-lg border border-slate-800/80 bg-slate-950/80 p-3 font-mono text-xs text-slate-200 leading-relaxed shadow-inner">
          <p className="whitespace-pre-wrap italic">&ldquo;{scriptExcerpt}&rdquo;</p>
        </div>
      </div>

      {/* Why Clarification is Needed Section */}
      <div className="rounded-lg border border-amber-500/30 bg-amber-950/20 p-3 space-y-1">
        <div className="flex items-center gap-1.5 text-xs font-bold text-amber-300">
          <AlertTriangle className="h-3.5 w-3.5 text-amber-400 flex-shrink-0" aria-hidden="true" />
          <span>Why Clarification is Needed (Legal Nexus):</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          {rationale}
        </p>
      </div>
    </div>
  );
};

export default ClarificationContextCard;
