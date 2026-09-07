'use client';

/**
 * Lienmark High-Contrast Cinematic ClaimRow Component
 * Integrated with Counsel Review & Attorney Override Modal (Sprint 4.3).
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import React, { useState } from 'react';
import { Clock, Eye, Zap, Link as LinkIcon, Lock, ChevronDown, ChevronUp, HelpCircle, Scale } from 'lucide-react';
import { DecisionState, EvaluatedClaim, UserRole, hasClearanceAuthority } from '@/lib/types';
import { ProvenancePanel } from './claims/ProvenancePanel';
import { ShiftExplanationAlert } from './claims/ShiftExplanationAlert';
import { ConfidentialityBadge } from './intake/ConfidentialityBadge';
import { validateConfidentiality } from './intake/intake_utils';
import { ClarificationBadge, ClaimResumptionStatus } from './hitl';
import { formatCinematicTimecode, renderAssetCategoryBadge, renderClearanceStatusIndicator } from './claims/claim_formatters';

export { formatCinematicTimecode, renderAssetCategoryBadge, renderClearanceStatusIndicator };

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
  resumptionStatus?: ClaimResumptionStatus;
  onOpenOverride?: (claimKey: string) => void;
  attemptNumber?: number;
}

function renderAdjudicateBtn(
  claim: EvaluatedClaim,
  canAdjudicate: boolean,
  isItem11: boolean,
  isItem12: boolean,
  onOpenInGate?: (k: string) => void
): React.ReactNode {
  if (claim.state !== DecisionState.STALE || !onOpenInGate) return null;
  if (!canAdjudicate) {
    return (
      <span className="inline-flex items-center gap-1 rounded bg-slate-900 border border-slate-800 px-2 py-1 text-[10px] font-mono text-slate-500 cursor-not-allowed">
        <Lock className="h-3 w-3 text-slate-500" /> Reviewer Gated
      </span>
    );
  }
  return (
    <button
      type="button"
      onClick={(e) => { e.stopPropagation(); onOpenInGate(claim.stable_lineage_key); }}
      className="inline-flex items-center gap-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 px-2 py-1 text-[10px] font-mono font-bold"
    >
      <Zap className="h-3 w-3 text-amber-400" />
      <span>{isItem11 ? 'Re-Attest' : isItem12 ? 'Flag Exception' : 'Adjudicate'}</span>
    </button>
  );
}

interface DetailsProps {
  claim: EvaluatedClaim;
  wordCount: number;
  attemptNumber?: number;
  showProvenance: boolean;
  setShowProvenance: (v: boolean) => void;
  onViewProvenance?: (k: string) => void;
  activeRes?: ClaimResumptionStatus;
  onOpenClarification?: (k: string) => void;
}

function renderClaimDetails(p: DetailsProps): React.ReactNode {
  const isItem11 = p.claim.stable_lineage_key.includes('noir_detective');
  const isItem12 = p.claim.stable_lineage_key.includes('midnight_serenade');
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="font-semibold text-sm text-white group-hover:text-sky-200">{p.claim.stable_lineage_key.replace(/_/g, ' ')}</span>
        {renderAssetCategoryBadge(p.claim.asset_type)}
        <ConfidentialityBadge wordCount={p.wordCount} />
        {p.attemptNumber && p.attemptNumber > 1 && (
          <span className="font-mono text-[9px] rounded bg-amber-950/80 text-amber-300 border border-amber-500/40 px-1.5 py-0.5 font-bold">
            Attempt {p.attemptNumber}
          </span>
        )}
        {p.activeRes && <ClarificationBadge status={p.activeRes} isInteractive={Boolean(p.onOpenClarification)} onClick={() => p.onOpenClarification?.(p.claim.stable_lineage_key)} />}
      </div>
      <span className="text-[11px] text-slate-400 line-clamp-1">{p.claim.description}</span>
      {p.claim.state === DecisionState.CARRIED_FORWARD && (
        <div className="mt-0.5">
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); p.setShowProvenance(!p.showProvenance); p.onViewProvenance?.(p.claim.stable_lineage_key); }}
            className="inline-flex items-center gap-1 text-[10px] font-mono text-emerald-400 underline bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-500/30"
          >
            <LinkIcon className="h-2.5 w-2.5 text-emerald-400" />
            <span>v7 Provenance (dec_v7_{p.claim.stable_lineage_key.slice(0, 10)})</span>
            {p.showProvenance ? <ChevronUp className="h-2.5 w-2.5" /> : <ChevronDown className="h-2.5 w-2.5" />}
          </button>
          {p.showProvenance && <ProvenancePanel stableLineageKey={p.claim.stable_lineage_key} />}
        </div>
      )}
      {p.claim.state === DecisionState.STALE && <ShiftExplanationAlert claim={p.claim} isItem11={isItem11} isItem12={isItem12} />}
    </div>
  );
}

interface ActionButtonsProps {
  claim: EvaluatedClaim;
  canAdjudicate: boolean;
  isSelected: boolean;
  isWaiting: boolean;
  onSelect: (k: string) => void;
  onOpenInGate?: (k: string) => void;
  onOpenClarification?: (k: string) => void;
  onOpenOverride?: (k: string) => void;
}

function renderActionButtons(p: ActionButtonsProps): React.ReactNode {
  const isItem11 = p.claim.stable_lineage_key.includes('noir_detective');
  const isItem12 = p.claim.stable_lineage_key.includes('midnight_serenade');
  return (
    <div className="flex items-center justify-end gap-1.5">
      {p.isWaiting && p.onOpenClarification && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); p.onOpenClarification?.(p.claim.stable_lineage_key); }}
          className="inline-flex items-center gap-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 px-2 py-1 text-[10px] font-mono font-bold"
        >
          <HelpCircle className="h-3 w-3 text-amber-400" /> <span>Clarify</span>
        </button>
      )}
      {p.canAdjudicate && p.onOpenOverride && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); p.onOpenOverride?.(p.claim.stable_lineage_key); }}
          className="inline-flex items-center gap-1 rounded bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/40 px-2 py-1 text-[10px] font-mono font-bold"
          title="Open Counsel Review & Re-investigation Override"
        >
          <Scale className="h-3 w-3 text-purple-400" /> <span>Override</span>
        </button>
      )}
      {renderAdjudicateBtn(p.claim, p.canAdjudicate, isItem11, isItem12, p.onOpenInGate)}
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); p.onSelect(p.claim.stable_lineage_key); }}
        className={`inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-semibold ${p.isSelected ? 'bg-sky-500 text-slate-950 font-bold' : 'text-sky-400 hover:text-sky-300 hover:bg-slate-800'}`}
      >
        <Eye className="h-3.5 w-3.5" /> <span className="hidden sm:inline">{p.isSelected ? 'Active in 4D' : 'Inspect 4D'}</span>
      </button>
    </div>
  );
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
  resumptionStatus,
  onOpenOverride,
  attemptNumber,
}) => {
  const [showProvenance, setShowProvenance] = useState<boolean>(false);
  const timecode = formatCinematicTimecode(claim.scene, claim.stable_lineage_key, index);
  const canAdjudicate = hasClearanceAuthority(userRole);
  const confidentiality = validateConfidentiality(claim.description);
  const isWaiting = hasActiveClarification || Boolean(claim.has_active_clarification);
  const activeRes = resumptionStatus ?? (claim.resumption_status as ClaimResumptionStatus | undefined) ?? (isWaiting ? ClaimResumptionStatus.WAITING_FOR_INFO : undefined);

  return (
    <tr
      onClick={() => onSelect(claim.stable_lineage_key)}
      className={`group cursor-pointer border-b border-slate-800/80 transition-all ${isSelected ? 'bg-[#1b2745] text-white border-l-4 border-l-sky-400 shadow-md' : 'hover:bg-slate-800/40 text-slate-300 border-l-4 border-l-transparent'}`}
      role="row"
      aria-selected={isSelected}
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(claim.stable_lineage_key); } }}
    >
      <td className="py-2.5 px-2.5 text-center font-mono text-xs font-bold text-slate-500 group-hover:text-slate-300 whitespace-nowrap">
        {isSelected ? <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-sky-500 text-slate-950 font-bold text-[10px]">{index + 1}</span> : String(index + 1).padStart(2, '0')}
      </td>
      <td className="py-2.5 px-2.5 whitespace-nowrap">
        <div className="flex items-center gap-1.5 font-mono text-xs font-bold text-amber-300 bg-amber-950/40 border border-amber-500/30 px-2 py-0.5 rounded w-fit">
          <Clock className="h-3 w-3 text-amber-400 flex-shrink-0" /> <span>{timecode}</span>
        </div>
      </td>
      <td className="py-2.5 px-2.5 min-w-[240px]">
        {renderClaimDetails({ claim, wordCount: confidentiality.wordCount, attemptNumber, showProvenance, setShowProvenance, onViewProvenance, activeRes, onOpenClarification })}
      </td>
      <td className="py-2.5 px-2.5 hidden 2xl:table-cell text-xs text-slate-300 max-w-[200px]">
        <div className="space-y-0.5"><div className="font-mono text-[11px] text-slate-200 truncate">{claim.prominence}</div><div className="text-[10px] font-mono text-slate-500 truncate">Reason: {claim.reason_code}</div></div>
      </td>
      <td className="py-2.5 px-2.5 whitespace-nowrap">
        {activeRes ? <div className="flex flex-col gap-1"><ClarificationBadge status={activeRes} isInteractive={Boolean(onOpenClarification)} onClick={() => onOpenClarification?.(claim.stable_lineage_key)} /><span className="text-[10px] font-mono text-slate-400">{activeRes === ClaimResumptionStatus.AGREEMENT_MATCHED ? 'Contract Matched' : activeRes === ClaimResumptionStatus.READY_FOR_REVIEW ? 'Ready for Review' : 'Pending Clarification'}</span></div> : renderClearanceStatusIndicator(claim.state)}
      </td>
      <td className="py-2.5 px-2.5 text-right whitespace-nowrap">
        {renderActionButtons({ claim, canAdjudicate, isSelected, isWaiting, onSelect, onOpenInGate, onOpenClarification, onOpenOverride })}
      </td>
    </tr>
  );
};

export default ClaimRow;
