'use client';

/**
 * Lienmark High-Contrast Cinematic ClaimRow Component
 * Hollywood Studio Legal Ops UI/UX Overhaul - Component 4
 * Renders an individual rights-bearing claim with formatted scene timecode (e.g. SC 42 (00:41:12)),
 * asset category badges, confidentiality badges, and instant selection for the adjacent 4D Inspector.
 * Integrated with HITL Waiting For Info clarification badge.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState } from 'react';
import {
  Clock,
  Eye,
  Zap,
  Link as LinkIcon,
  Lock,
  ChevronDown,
  ChevronUp,
  HelpCircle,
} from 'lucide-react';
import { DecisionState, EvaluatedClaim, UserRole, hasClearanceAuthority } from '@/lib/types';
import { ProvenancePanel } from './claims/ProvenancePanel';
import { ShiftExplanationAlert } from './claims/ShiftExplanationAlert';
import { ConfidentialityBadge } from './intake/ConfidentialityBadge';
import { validateConfidentiality } from './intake/intake_utils';
import { ClarificationBadge } from './hitl';
import {
  formatCinematicTimecode,
  renderAssetCategoryBadge,
  renderClearanceStatusIndicator,
} from './claims/claim_formatters';

export {
  formatCinematicTimecode,
  renderAssetCategoryBadge,
  renderClearanceStatusIndicator,
};

export interface ClaimRowProps {
  claim: EvaluatedClaim;
  index: number;
  isSelected: boolean;
  onSelect: (claimKey: string) => void;
  onOpenInGate?: (claimKey: string) => void;
  userRole?: UserRole;
  onViewProvenance?: (claimKey: string) => void;
  hasActiveClarification?: boolean;
  onOpenClarification?: (claimKey: string) => void;
}

export const ClaimRow: React.FC<ClaimRowProps> = ({
  claim,
  index,
  isSelected,
  onSelect,
  onOpenInGate,
  userRole = UserRole.REVIEWER,
  onViewProvenance,
  hasActiveClarification = false,
  onOpenClarification,
}) => {
  const [showProvenance, setShowProvenance] = useState<boolean>(false);
  const isItem11 = claim.stable_lineage_key === 'poster_noir_detective_magazine' || claim.stable_lineage_key.includes('noir_detective');
  const isItem12 = claim.stable_lineage_key === 'music_cue_midnight_serenade' || claim.stable_lineage_key.includes('midnight_serenade');
  const cinematicTimecode = formatCinematicTimecode(claim.scene, claim.stable_lineage_key, index);
  const canAdjudicate = hasClearanceAuthority(userRole);
  const confidentiality = validateConfidentiality(claim.description);
  const isWaitingForInfo = hasActiveClarification || Boolean(claim.has_active_clarification);

  return (
    <tr
      onClick={() => onSelect(claim.stable_lineage_key)}
      className={`group cursor-pointer border-b border-slate-800/80 transition-all ${
        isSelected
          ? 'bg-[#1b2745] text-white border-l-4 border-l-sky-400 shadow-md ring-1 ring-sky-500/20'
          : 'hover:bg-slate-800/40 text-slate-300 border-l-4 border-l-transparent'
      }`}
      role="row"
      aria-selected={isSelected}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(claim.stable_lineage_key);
        }
      }}
    >
      <td className="py-2.5 px-2.5 text-center font-mono text-xs font-bold text-slate-500 group-hover:text-slate-300 whitespace-nowrap">
        {isSelected ? (
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-sky-500 text-slate-950 font-bold text-[10px]">
            {index + 1}
          </span>
        ) : (
          String(index + 1).padStart(2, '0')
        )}
      </td>

      <td className="py-2.5 px-2.5 whitespace-nowrap">
        <div className="flex items-center gap-1.5 font-mono text-xs font-bold text-amber-300 bg-amber-950/40 border border-amber-500/30 px-2 py-0.5 rounded w-fit">
          <Clock className="h-3 w-3 text-amber-400 flex-shrink-0" aria-hidden="true" />
          <span>{cinematicTimecode}</span>
        </div>
      </td>

      <td className="py-2.5 px-2.5 min-w-[240px]">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="font-semibold text-sm text-white group-hover:text-sky-200 transition-colors">
              {claim.stable_lineage_key.replace(/_/g, ' ')}
            </span>
            {renderAssetCategoryBadge(claim.asset_type)}
            <ConfidentialityBadge wordCount={confidentiality.wordCount} />
            {isWaitingForInfo && (
              <ClarificationBadge
                isInteractive={Boolean(onOpenClarification)}
                onClick={() => onOpenClarification?.(claim.stable_lineage_key)}
              />
            )}
          </div>
          <span className="text-[11px] text-slate-400 line-clamp-1 font-sans">
            {claim.description}
          </span>

          {claim.state === DecisionState.CARRIED_FORWARD && (
            <div className="mt-0.5">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowProvenance(!showProvenance);
                  onViewProvenance?.(claim.stable_lineage_key);
                }}
                className="inline-flex items-center gap-1 text-[10px] font-mono text-emerald-400 hover:text-emerald-300 underline decoration-emerald-500/50 bg-emerald-950/40 hover:bg-emerald-950/70 px-1.5 py-0.5 rounded border border-emerald-500/30 transition-colors"
                title="View locked v7 baseline provenance"
              >
                <LinkIcon className="h-2.5 w-2.5 text-emerald-400" aria-hidden="true" />
                <span>v7 Provenance (dec_v7_{claim.stable_lineage_key.slice(0, 10)})</span>
                {showProvenance ? <ChevronUp className="h-2.5 w-2.5" /> : <ChevronDown className="h-2.5 w-2.5" />}
              </button>
              {showProvenance && <ProvenancePanel stableLineageKey={claim.stable_lineage_key} />}
            </div>
          )}

          {claim.state === DecisionState.STALE && (
            <ShiftExplanationAlert claim={claim} isItem11={isItem11} isItem12={isItem12} />
          )}
        </div>
      </td>

      <td className="py-2.5 px-2.5 hidden 2xl:table-cell text-xs text-slate-300 max-w-[200px]">
        <div className="space-y-0.5">
          <div className="font-mono text-[11px] text-slate-200 truncate">{claim.prominence}</div>
          <div className="text-[10px] font-mono text-slate-500 truncate">Reason: {claim.reason_code}</div>
        </div>
      </td>

      <td className="py-2.5 px-2.5 whitespace-nowrap">
        {isWaitingForInfo ? (
          <div className="flex flex-col gap-1">
            <ClarificationBadge
              isInteractive={Boolean(onOpenClarification)}
              onClick={() => onOpenClarification?.(claim.stable_lineage_key)}
            />
            <span className="text-[10px] font-mono text-amber-400/80">Pending Clarification</span>
          </div>
        ) : (
          renderClearanceStatusIndicator(claim.state)
        )}
      </td>

      <td className="py-2.5 px-2.5 text-right whitespace-nowrap">
        <div className="flex items-center justify-end gap-1.5">
          {isWaitingForInfo && onOpenClarification && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onOpenClarification(claim.stable_lineage_key);
              }}
              className="inline-flex items-center gap-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 px-2 py-1 text-[10px] font-mono font-bold transition-all focus:outline-none focus:ring-1 focus:ring-amber-400"
              title="Answer Clarification Question for this asset"
            >
              <HelpCircle className="h-3 w-3 text-amber-400" aria-hidden="true" />
              <span>Clarify</span>
            </button>
          )}

          {claim.state === DecisionState.STALE && onOpenInGate && (
            canAdjudicate ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenInGate(claim.stable_lineage_key);
                }}
                className="inline-flex items-center gap-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 px-2 py-1 text-[10px] font-mono font-bold transition-all focus:outline-none focus:ring-1 focus:ring-amber-400"
                title="Open directly in Counsel Checkpoint Gate"
              >
                <Zap className="h-3 w-3 text-amber-400" aria-hidden="true" />
                <span>{isItem11 ? 'Re-Attest' : isItem12 ? 'Flag Exception' : 'Adjudicate'}</span>
              </button>
            ) : (
              <span
                className="inline-flex items-center gap-1 rounded bg-slate-900/90 border border-slate-800 px-2 py-1 text-[10px] font-mono text-slate-500 cursor-not-allowed"
                title={`Clearance adjudication action hidden for ${userRole}: Reviewer role required`}
              >
                <Lock className="h-3 w-3 text-slate-500" aria-hidden="true" />
                <span>Reviewer Gated</span>
              </span>
            )
          )}

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onSelect(claim.stable_lineage_key);
            }}
            className={`inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-semibold transition-all focus:outline-none focus:ring-1 focus:ring-sky-400 ${
              isSelected ? 'bg-sky-500 text-slate-950 font-bold shadow-sm' : 'text-sky-400 hover:text-sky-300 hover:bg-slate-800'
            }`}
            aria-label={`Inspect 4D clearance breakdown for ${claim.stable_lineage_key}`}
          >
            <Eye className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="hidden sm:inline">{isSelected ? 'Active in 4D' : 'Inspect 4D'}</span>
          </button>
        </div>
      </td>
    </tr>
  );
};

export default ClaimRow;
