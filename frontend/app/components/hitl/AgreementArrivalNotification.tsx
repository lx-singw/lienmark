'use client';

/**
 * Lienmark HITL Agreement Arrival Notification
 * Toast and banner alert triggered when a private agreement is autonomously matched,
 * unblocking clearance pipeline execution without full-page refresh.
 * Displays matched parties, cue details, verification confidence, and agreement viewer link.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import {
  FileCheck,
  ExternalLink,
  ShieldCheck,
  Sparkles,
  X,
  ArrowRight,
  Music,
} from 'lucide-react';
import { AgreementMatchPayload } from './resumption_types';
import { formatConfidencePercent, GOLDEN_AGREEMENT_MATCH } from './resumption_utils';

export interface AgreementArrivalNotificationProps {
  readonly agreement?: AgreementMatchPayload;
  readonly onViewAgreement?: (agreement: AgreementMatchPayload) => void;
  readonly onViewResumption?: (claimKey: string) => void;
  readonly onDismiss?: () => void;
  readonly isDismissed?: boolean;
  readonly className?: string;
}

interface NotificationHeaderProps {
  readonly filename: string;
  readonly confidenceFormatted: string;
  readonly assetCue: string;
  readonly scene: string;
  readonly partiesString: string;
}

const NotificationHeader: React.FC<NotificationHeaderProps> = ({
  filename,
  confidenceFormatted,
  assetCue,
  scene,
  partiesString,
}) => (
  <div className="flex items-start sm:items-center gap-3.5">
    <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-300 border border-emerald-400/50 flex-shrink-0 shadow-[0_0_15px_rgba(16,185,129,0.4)]">
      <FileCheck className="h-5 w-5" aria-hidden="true" />
      <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-emerald-500 border border-slate-900" />
      </span>
    </div>
    <div className="space-y-1">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-bold text-sm text-white tracking-tight">
          Unblocked via Agreement Upload:{' '}
          <span className="font-mono text-emerald-300 underline decoration-emerald-500/60">
            {filename}
          </span>{' '}
          <span className="text-emerald-400 font-mono font-semibold">
            (Confidence: {confidenceFormatted})
          </span>
        </span>
        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/20 border border-emerald-400/50 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-300 shadow-sm">
          <Sparkles className="h-2.5 w-2.5 text-emerald-300 animate-spin" aria-hidden="true" />
          AUTONOMOUS MATCH
        </span>
      </div>
      <div className="flex items-center gap-3 flex-wrap text-xs text-slate-300">
        <span className="inline-flex items-center gap-1 font-medium text-slate-200">
          <Music className="h-3 w-3 text-sky-400" aria-hidden="true" />
          <span>Cue:</span>
          <strong className="text-white font-mono">{assetCue}</strong>
          <span className="text-slate-400 font-mono">({scene})</span>
        </span>
        <span className="text-slate-600">&middot;</span>
        <span className="text-slate-300">
          Parties: <span className="font-mono text-emerald-200">{partiesString}</span>
        </span>
      </div>
    </div>
  </div>
);

interface NotificationActionsProps {
  readonly agreement: AgreementMatchPayload;
  readonly onViewAgreement?: (agreement: AgreementMatchPayload) => void;
  readonly onViewResumption?: (claimKey: string) => void;
  readonly onDismiss?: () => void;
}

const NotificationActions: React.FC<NotificationActionsProps> = ({
  agreement,
  onViewAgreement,
  onViewResumption,
  onDismiss,
}) => (
  <div className="flex items-center gap-2.5 self-end lg:self-center flex-shrink-0">
    {onViewResumption && (
      <button
        type="button"
        onClick={() => onViewResumption(agreement.claimKey)}
        className="inline-flex items-center gap-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-700 border border-emerald-500/40 px-3 py-1.5 text-xs font-semibold text-emerald-300 shadow-sm hover:border-emerald-400 transition-all focus:outline-none focus:ring-2 focus:ring-emerald-400 active:scale-95"
      >
        <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
        <span>Resumption Flow</span>
        <ArrowRight className="h-3 w-3 text-emerald-400" />
      </button>
    )}
    <button
      type="button"
      onClick={() => onViewAgreement?.(agreement)}
      className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 px-3.5 py-1.5 text-xs font-bold text-slate-950 shadow-md shadow-emerald-500/20 transition-all focus:outline-none focus:ring-2 focus:ring-emerald-300 active:scale-95"
      title="Open agreement viewer and verify OCR clauses"
    >
      <span>View Agreement</span>
      <ExternalLink className="h-3.5 w-3.5 text-slate-950" aria-hidden="true" />
    </button>
    {onDismiss && (
      <button
        type="button"
        onClick={onDismiss}
        className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors focus:outline-none focus:ring-1 focus:ring-emerald-400 ml-1"
        aria-label="Dismiss agreement arrival notification"
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </button>
    )}
  </div>
);

export const AgreementArrivalNotification: React.FC<AgreementArrivalNotificationProps> = ({
  agreement = GOLDEN_AGREEMENT_MATCH,
  onViewAgreement,
  onViewResumption,
  onDismiss,
  isDismissed = false,
  className = '',
}) => {
  if (isDismissed) return null;

  return (
    <aside
      aria-label="Agreement Autonomous Match Arrival Alert"
      role="alert"
      className={`relative overflow-hidden rounded-xl border border-emerald-500/70 bg-gradient-to-r from-emerald-950/95 via-slate-900/95 to-teal-950/90 p-4 shadow-[0_0_30px_rgba(16,185,129,0.25)] backdrop-blur-md animate-in fade-in slide-in-from-top-3 duration-300 ${className}`}
    >
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-emerald-400 via-teal-300 to-sky-400 shadow-sm" />
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <NotificationHeader
          filename={agreement.filename}
          confidenceFormatted={formatConfidencePercent(agreement.confidence)}
          assetCue={agreement.assetCue}
          scene={agreement.scene}
          partiesString={agreement.matchedParties.join(' ↔ ')}
        />
        <NotificationActions
          agreement={agreement}
          onViewAgreement={onViewAgreement}
          onViewResumption={onViewResumption}
          onDismiss={onDismiss}
        />
      </div>
    </aside>
  );
};

export default AgreementArrivalNotification;
