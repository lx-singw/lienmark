/**
 * Lienmark Human-in-the-Loop (HITL) Resumption & Resolution Types
 * Defines data contracts for autonomous agreement matching, checkpoint hydration,
 * multi-step pipeline resumption telemetry, and clearance badge transitions.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript definitions.
 */

export const ClaimResumptionStatus = {
  WAITING_FOR_INFO: 'waiting_for_info',
  AGREEMENT_MATCHED: 'agreement_matched',
  READY_FOR_REVIEW: 'ready_for_review',
} as const;

export type ClaimResumptionStatus =
  (typeof ClaimResumptionStatus)[keyof typeof ClaimResumptionStatus];

export const ResumptionStepId = {
  CLARIFICATION_RESOLVED: 'clarification_resolved',
  CHECKPOINT_HYDRATED: 'checkpoint_hydrated',
  AGREEMENT_VERIFIED: 'agreement_verified',
  CLEARANCE_UPDATED: 'clearance_updated',
} as const;

export type ResumptionStepId =
  (typeof ResumptionStepId)[keyof typeof ResumptionStepId];

export type ResumptionStepStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

export type ResolutionMethod = 'autonomous' | 'manual';

export interface AgreementVerificationDetails {
  readonly signaturesVerified: boolean;
  readonly territoryScope: string;
  readonly rightsScope: string;
  readonly termExpiry: string;
  readonly governingLaw?: string;
  readonly confidenceScore: number;
}

export interface AgreementMatchPayload {
  readonly documentId: string;
  readonly filename: string;
  readonly confidence: number;
  readonly matchedParties: ReadonlyArray<string>;
  readonly assetCue: string;
  readonly claimKey: string;
  readonly scene: string;
  readonly rightsScope: string;
  readonly verifiedDetails: AgreementVerificationDetails;
  readonly matchedAt: string;
  readonly agreementViewerUrl?: string;
}

export interface ResumptionStepDetail {
  readonly id: ResumptionStepId;
  readonly stepNumber: 1 | 2 | 3 | 4;
  readonly title: string;
  readonly subtitle: string;
  readonly status: ResumptionStepStatus;
  readonly resolutionMethod?: ResolutionMethod;
  readonly completedAt?: string;
  readonly summaryNotes?: string;
}

export interface ResumptionSession {
  readonly runId: string;
  readonly checkpointId: string;
  readonly resumeToken: string;
  readonly claimKey: string;
  readonly currentStep: 1 | 2 | 3 | 4;
  readonly isCompleted: boolean;
  readonly agreementMatch: AgreementMatchPayload;
  readonly steps: ReadonlyArray<ResumptionStepDetail>;
  readonly startedAt: string;
  readonly completedAt?: string;
}

export interface ResumptionBadgeStyle {
  readonly badgeClass: string;
  readonly dotClass: string;
  readonly label: string;
  readonly iconName: 'help' | 'match' | 'shield';
}
