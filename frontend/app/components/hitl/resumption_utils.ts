/**
 * Lienmark Human-in-the-Loop (HITL) Resumption & Resolution Utilities
 * Helper functions and deterministic fixtures for autonomous agreement matching
 * and live execution resumption pipelines.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import {
  AgreementMatchPayload,
  ClaimResumptionStatus,
  ResolutionMethod,
  ResumptionBadgeStyle,
  ResumptionSession,
  ResumptionStepDetail,
  ResumptionStepId,
  ResumptionStepStatus,
} from './resumption_types';

export function formatConfidencePercent(confidence: number): string {
  const clamped = Math.max(0, Math.min(1, confidence));
  return `${Math.round(clamped * 100)}%`;
}

export function getResumptionBadgeTheme(
  status: ClaimResumptionStatus = ClaimResumptionStatus.WAITING_FOR_INFO
): ResumptionBadgeStyle {
  switch (status) {
    case ClaimResumptionStatus.AGREEMENT_MATCHED:
      return {
        badgeClass:
          'text-emerald-200 bg-emerald-950/90 border-emerald-500/90 shadow-[0_0_12px_rgba(16,185,129,0.35)] animate-pulse',
        dotClass: 'bg-emerald-400',
        label: '[AGREEMENT MATCHED]',
        iconName: 'match',
      };
    case ClaimResumptionStatus.READY_FOR_REVIEW:
      return {
        badgeClass:
          'text-teal-200 bg-teal-950/90 border-teal-400/90 shadow-[0_0_10px_rgba(20,184,166,0.3)]',
        dotClass: 'bg-teal-400',
        label: '[READY FOR REVIEW]',
        iconName: 'shield',
      };
    case ClaimResumptionStatus.WAITING_FOR_INFO:
    default:
      return {
        badgeClass:
          'text-amber-200 bg-amber-950/90 border-amber-500/80 shadow-md animate-pulse',
        dotClass: 'bg-amber-400',
        label: '[WAITING FOR INFO]',
        iconName: 'help',
      };
  }
}

export function getStepStatusClasses(status: ResumptionStepStatus): {
  containerClass: string;
  iconClass: string;
  badgeClass: string;
} {
  switch (status) {
    case 'completed':
      return {
        containerClass: 'border-emerald-500/60 bg-emerald-950/30 text-emerald-300',
        iconClass: 'text-emerald-400 border-emerald-500/60 bg-emerald-950/80',
        badgeClass: 'text-emerald-400 bg-emerald-950/60 border-emerald-500/40',
      };
    case 'in_progress':
      return {
        containerClass:
          'border-emerald-400 bg-slate-900/90 text-white ring-2 ring-emerald-500/40 shadow-[0_0_15px_rgba(16,185,129,0.25)]',
        iconClass: 'text-emerald-300 border-emerald-400 bg-slate-900 animate-spin',
        badgeClass: 'text-emerald-300 bg-emerald-950/80 border-emerald-400/60 animate-pulse',
      };
    case 'failed':
      return {
        containerClass: 'border-rose-500/60 bg-rose-950/30 text-rose-300',
        iconClass: 'text-rose-400 border-rose-500/60 bg-rose-950/80',
        badgeClass: 'text-rose-400 bg-rose-950/60 border-rose-500/40',
      };
    case 'pending':
    default:
      return {
        containerClass: 'border-slate-800 bg-slate-900/40 text-slate-500',
        iconClass: 'text-slate-500 border-slate-700 bg-slate-800',
        badgeClass: 'text-slate-500 bg-slate-900/60 border-slate-800',
      };
  }
}

export const GOLDEN_AGREEMENT_MATCH: AgreementMatchPayload = {
  documentId: 'doc_sync_license_441',
  filename: 'sync_license_441.pdf',
  confidence: 0.94,
  matchedParties: ['Vanguard Music Publishing', 'Cinema Soundworks LLC'],
  assetCue: 'Midnight Serenade Cue',
  claimKey: 'music_cue_midnight_serenade',
  scene: 'SC 18 (00:19:40)',
  rightsScope: 'Worldwide Sync & Master Recording',
  verifiedDetails: {
    signaturesVerified: true,
    territoryScope: 'Worldwide, All Media',
    rightsScope: 'Diegetic & Non-Diegetic Synchronization',
    termExpiry: 'In Perpetuity',
    governingLaw: 'State of California / Entertainment Standard',
    confidenceScore: 0.94,
  },
  matchedAt: '2026-09-07T10:15:30.000Z',
  agreementViewerUrl: '#viewer-sync_license_441',
};

export function createDefaultResumptionSteps(
  method: ResolutionMethod = 'autonomous',
  activeStep: 1 | 2 | 3 | 4 = 4
): ReadonlyArray<ResumptionStepDetail> {
  return [
    {
      id: ResumptionStepId.CLARIFICATION_RESOLVED,
      stepNumber: 1,
      title: 'Step 1: Clarification Resolved',
      subtitle:
        method === 'autonomous'
          ? 'Autonomous: Sync agreement matched via doc intake'
          : 'Manual: Production counsel attestation recorded',
      status: activeStep > 1 ? 'completed' : activeStep === 1 ? 'in_progress' : 'pending',
      resolutionMethod: method,
      completedAt: '10:15:31 UTC',
      summaryNotes: 'Ingested sync_license_441.pdf with 94% confidence match.',
    },
    {
      id: ResumptionStepId.CHECKPOINT_HYDRATED,
      stepNumber: 2,
      title: 'Step 2: Checkpoint Hydrated',
      subtitle: 'State restored from durable checkpoint (chk_9a12c)',
      status: activeStep > 2 ? 'completed' : activeStep === 2 ? 'in_progress' : 'pending',
      completedAt: '10:15:32 UTC',
      summaryNotes: 'Loaded agent memory graph; 0 tokens wasted.',
    },
    {
      id: ResumptionStepId.AGREEMENT_VERIFIED,
      stepNumber: 3,
      title: 'Step 3: Targeted Agreement Verification',
      subtitle: 'Verified Signatures, Worldwide Territory & Sync Rights',
      status: activeStep > 3 ? 'completed' : activeStep === 3 ? 'in_progress' : 'pending',
      completedAt: '10:15:33 UTC',
      summaryNotes: 'Clauses 4.1 & 7.2 verified. Both licensor signatures authentic.',
    },
    {
      id: ResumptionStepId.CLEARANCE_UPDATED,
      stepNumber: 4,
      title: 'Step 4: Claim Clearance Updated',
      subtitle: 'Ready for Counsel Sign-off on E&O exceptions schedule',
      status: activeStep >= 4 ? 'completed' : 'pending',
      completedAt: activeStep >= 4 ? '10:15:34 UTC' : undefined,
      summaryNotes: 'Updated claim state from WAITING FOR INFO to READY FOR REVIEW.',
    },
  ];
}

export const GOLDEN_RESUMPTION_SESSION: ResumptionSession = {
  runId: 'run_adk_pipeline_9921',
  checkpointId: 'chk_9a12c',
  resumeToken: '7e2b9c3f1d8a4e6052bb7a81c34d09ea',
  claimKey: 'music_cue_midnight_serenade',
  currentStep: 4,
  isCompleted: true,
  agreementMatch: GOLDEN_AGREEMENT_MATCH,
  steps: createDefaultResumptionSteps('autonomous', 4),
  startedAt: '2026-09-07T10:15:30.000Z',
  completedAt: '2026-09-07T10:15:34.000Z',
};

export function formatUnblockedNotification(filename: string, cueName?: string): string {
  const cleanName = filename.trim();
  if (cueName) {
    return `Unblocked via Agreement Upload: ${cleanName} for '${cueName}'`;
  }
  return `Unblocked via Agreement Upload: ${cleanName}`;
}

