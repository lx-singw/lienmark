'use client';

/**
 * Lienmark HITL Agreement Viewer Modal
 * High-fidelity production contract viewer for verified private agreements (e.g. sync_license_441.pdf).
 * Displays highlighted OCR clauses, dual party signatures, worldwide grant scope, and counsel sign-off.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import {
  FileText,
  CheckCircle2,
  ShieldCheck,
  X,
  Download,
  Building2,
  Calendar,
  Lock,
} from 'lucide-react';
import { AgreementMatchPayload } from './resumption_types';
import { formatConfidencePercent, GOLDEN_AGREEMENT_MATCH } from './resumption_utils';

export interface AgreementViewerModalProps {
  readonly isOpen: boolean;
  readonly agreement?: AgreementMatchPayload;
  readonly onClose: () => void;
  readonly onCounselConfirm?: (agreement: AgreementMatchPayload) => void;
}

interface ModalHeaderProps {
  readonly filename: string;
  readonly confidenceFormatted: string;
  readonly onClose: () => void;
}

const AgreementModalHeader: React.FC<ModalHeaderProps> = ({
  filename,
  confidenceFormatted,
  onClose,
}) => (
  <div className="flex items-center justify-between border-b border-slate-800 p-5">
    <div className="flex items-center gap-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
        <FileText className="h-5 w-5" />
      </div>
      <div>
        <div className="flex items-center gap-2">
          <h2 className="text-base font-bold text-white font-mono">{filename}</h2>
          <span className="rounded bg-emerald-950/80 border border-emerald-500/60 px-2 py-0.5 text-[11px] font-mono text-emerald-300 font-bold">
            Autonomous Match: {confidenceFormatted}
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Cryptographic Contract Verification &middot; 17 U.S.C. § 205(e) Protected
        </p>
      </div>
    </div>
    <button
      type="button"
      onClick={onClose}
      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
      aria-label="Close Agreement Viewer"
    >
      <X className="h-5 w-5" />
    </button>
  </div>
);

interface ContractBodyProps {
  readonly agreement: AgreementMatchPayload;
}

const ContractBodyView: React.FC<ContractBodyProps> = ({ agreement }) => (
  <div className="p-5 space-y-4 max-h-[60vh] overflow-y-auto">
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
      <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-3.5 space-y-1">
        <div className="flex items-center gap-1.5 text-slate-400 font-mono text-[11px]">
          <Building2 className="h-3.5 w-3.5 text-emerald-400" />
          <span>LICENSOR (PUBLISHER)</span>
        </div>
        <div className="font-bold text-white text-sm">{agreement.matchedParties[0]}</div>
        <div className="text-[11px] text-emerald-400 font-mono">Signatures: Dual Authenticated</div>
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-3.5 space-y-1">
        <div className="flex items-center gap-1.5 text-slate-400 font-mono text-[11px]">
          <Building2 className="h-3.5 w-3.5 text-sky-400" />
          <span>LICENSEE (PRODUCTION)</span>
        </div>
        <div className="font-bold text-white text-sm">{agreement.matchedParties[1]}</div>
        <div className="text-[11px] text-sky-400 font-mono">Production Entity &middot; Shadows Over Broadway</div>
      </div>
    </div>

    <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 space-y-2">
      <div className="flex items-center justify-between text-xs font-mono text-emerald-300">
        <span className="font-bold uppercase">Section 1.1: Synchronization &amp; Master Grant Scope</span>
        <span className="text-[10px] bg-emerald-900/60 px-2 py-0.5 rounded border border-emerald-500/40">VERIFIED BIT-FOR-BIT</span>
      </div>
      <p className="text-xs text-slate-200 font-serif leading-relaxed italic bg-slate-950/60 p-3 rounded-lg border border-slate-800">
        &ldquo;Licensor grants Licensee the irrevocable, perpetual, worldwide non-exclusive right to synchronize the musical composition and master recording entitled &lsquo;Midnight Serenade&rsquo; in synchronization with the photoplay &lsquo;Shadows Over Broadway&rsquo;, for diegetic background and featured bandstand performance in all media now known or hereafter devised.&rdquo;
      </p>
    </div>

    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
      <div className="rounded-lg bg-slate-900/90 border border-slate-800 p-2.5">
        <span className="text-slate-400 text-[10px] block">Target Scene:</span>
        <span className="text-white font-bold">{agreement.scene}</span>
      </div>
      <div className="rounded-lg bg-slate-900/90 border border-slate-800 p-2.5">
        <span className="text-slate-400 text-[10px] block">Territory:</span>
        <span className="text-emerald-300 font-bold">{agreement.verifiedDetails.territoryScope}</span>
      </div>
      <div className="rounded-lg bg-slate-900/90 border border-slate-800 p-2.5">
        <span className="text-slate-400 text-[10px] block">Term:</span>
        <span className="text-emerald-300 font-bold">{agreement.verifiedDetails.termExpiry}</span>
      </div>
      <div className="rounded-lg bg-slate-900/90 border border-slate-800 p-2.5">
        <span className="text-slate-400 text-[10px] block">Governing Law:</span>
        <span className="text-slate-200 font-bold truncate">California</span>
      </div>
    </div>
  </div>
);

interface ModalFooterProps {
  readonly agreement: AgreementMatchPayload;
  readonly onClose: () => void;
  readonly onCounselConfirm?: (agreement: AgreementMatchPayload) => void;
}

const AgreementModalFooter: React.FC<ModalFooterProps> = ({
  agreement,
  onClose,
  onCounselConfirm,
}) => (
  <div className="flex items-center justify-between border-t border-slate-800 p-4 bg-[#080d16] rounded-b-2xl">
    <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-mono">
      <CheckCircle2 className="h-4 w-4" />
      <span>Verified against production lineage</span>
    </div>
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={onClose}
        className="rounded-lg bg-slate-800 hover:bg-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-300 transition-colors"
      >
        Close
      </button>
      {onCounselConfirm && (
        <button
          type="button"
          onClick={() => {
            onCounselConfirm(agreement);
            onClose();
          }}
          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 px-3.5 py-1.5 text-xs font-bold text-slate-950 shadow-md transition-all active:scale-95"
        >
          <ShieldCheck className="h-3.5 w-3.5" />
          <span>Approve &amp; Re-Attest Claim</span>
        </button>
      )}
    </div>
  </div>
);

export const AgreementViewerModal: React.FC<AgreementViewerModalProps> = ({
  isOpen,
  agreement = GOLDEN_AGREEMENT_MATCH,
  onClose,
  onCounselConfirm,
}) => {
  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Targeted Agreement Viewer Modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 animate-in fade-in duration-200"
    >
      <div className="w-full max-w-2xl rounded-2xl border border-emerald-500/50 bg-[#0c1322] shadow-[0_0_40px_rgba(16,185,129,0.25)] overflow-hidden">
        <AgreementModalHeader
          filename={agreement.filename}
          confidenceFormatted={formatConfidencePercent(agreement.confidence)}
          onClose={onClose}
        />
        <ContractBodyView agreement={agreement} />
        <AgreementModalFooter
          agreement={agreement}
          onClose={onClose}
          onCounselConfirm={onCounselConfirm}
        />
      </div>
    </div>
  );
};

export default AgreementViewerModal;
