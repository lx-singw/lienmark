'use client';

/**
 * ConflictSourceCard.tsx
 * Evidentiary source card for contradictory evidence side-by-side comparison.
 * Displays authority tier badge, organization, excerpt quotation, and verification link.
 * Sprint 3.3: Contradictory Evidence & Conflict Arbitration UI.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { Building2, ExternalLink, Globe, Quote, ShieldCheck } from 'lucide-react';
import { AuthorityTier, type EvidenceSourceRecord } from './conflict_types';
import { getAuthorityTierStyle } from './conflict_utils';

export interface ConflictSourceCardProps {
  readonly source: EvidenceSourceRecord;
  readonly sideTag: 'SOURCE A' | 'SOURCE B';
  readonly className?: string;
}

function renderTierIcon(tier: AuthorityTier): React.ReactElement {
  switch (tier) {
    case AuthorityTier.TIER_1_GOVERNMENT:
      return <ShieldCheck className="h-3.5 w-3.5 text-amber-400 shrink-0" aria-hidden="true" />;
    case AuthorityTier.TIER_2_MEDIA_TRADE:
      return <Building2 className="h-3.5 w-3.5 text-sky-400 shrink-0" aria-hidden="true" />;
    case AuthorityTier.TIER_3_GENERAL_WEB:
    default:
      return <Globe className="h-3.5 w-3.5 text-slate-400 shrink-0" aria-hidden="true" />;
  }
}

function renderSourceHeader(
  source: EvidenceSourceRecord,
  sideTag: 'SOURCE A' | 'SOURCE B'
): React.ReactElement {
  const tierStyle = getAuthorityTierStyle(source.authorityTier);
  return (
    <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2.5 mb-3">
      <div className="flex items-center gap-2">
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-slate-800 text-slate-300">
          {sideTag}
        </span>
        <h4 className="text-xs font-bold text-slate-100 truncate max-w-[200px]" title={source.name}>
          {source.name}
        </h4>
      </div>
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold border ${tierStyle.bg} ${tierStyle.border} ${tierStyle.text}`}
      >
        {renderTierIcon(source.authorityTier)}
        <span>{tierStyle.shortLabel}</span>
      </span>
    </div>
  );
}

function renderSourceFooter(source: EvidenceSourceRecord): React.ReactElement {
  return (
    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 font-mono">
      <span>Confidence: {Math.round((source.confidenceScore ?? 0.9) * 100)}%</span>
      {source.url && (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300 transition-colors"
        >
          <span>Verify Source</span>
          <ExternalLink className="h-3 w-3" />
        </a>
      )}
    </div>
  );
}

export const ConflictSourceCard: React.FC<ConflictSourceCardProps> = ({
  source,
  sideTag,
  className = '',
}) => {
  const isSourceA = sideTag === 'SOURCE A';
  const cardBorder = isSourceA
    ? 'bg-[#0b1329]/80 border-cyan-500/40 hover:border-cyan-500/60'
    : 'bg-[#150e24]/80 border-rose-500/40 hover:border-rose-500/60';

  return (
    <div className={`flex-1 rounded-xl p-4 border transition-all ${cardBorder} ${className}`}>
      {renderSourceHeader(source, sideTag)}
      <div className="text-[11px] text-slate-400 mb-2 font-mono">
        Org: <span className="text-slate-200 font-semibold">{source.organization}</span>
      </div>
      {source.excerpt && (
        <div className="relative pl-3 py-2 my-2 bg-black/40 rounded-lg border-l-2 border-slate-700 text-[11px] text-slate-300 italic">
          <Quote className="h-3 w-3 text-slate-500 absolute top-1 left-0.5" aria-hidden="true" />
          <p className="line-clamp-3 leading-relaxed">{source.excerpt}</p>
        </div>
      )}
      {renderSourceFooter(source)}
    </div>
  );
};

export default ConflictSourceCard;
