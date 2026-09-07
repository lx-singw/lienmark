/**
 * frontend/app/components/intake/types.ts
 *
 * TypeScript types and interfaces for the Multimodal Intake Stepper,
 * Category Badges, and Confidentiality Indicators (Sprint 2.3).
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript.
 */

export type IntakeStage =
  | 'IDLE'
  | 'PARSING'
  | 'EXTRACTING_PRIMARY'
  | 'SELF_REFLECTION'
  | 'BASELINE_COMMITTED'
  | 'ERROR';

export type StepStatus = 'completed' | 'active' | 'upcoming' | 'error';

export interface StepperStep {
  readonly id: string;
  readonly stage: IntakeStage;
  readonly label: string;
  readonly description: string;
}

export const ExtractionStageId = {
  STAGE_1_TOKENIZATION_AST: 'stage_1_tokenization_ast',
  STAGE_2_MULTIMODAL_EXTRACTION: 'stage_2_multimodal_extraction',
  STAGE_3_SELF_REFLECTION: 'stage_3_self_reflection',
  STAGE_4_CONFIDENTIALITY_SNAPSHOT: 'stage_4_confidentiality_snapshot',
} as const;
export type ExtractionStageId = (typeof ExtractionStageId)[keyof typeof ExtractionStageId];

export const StageStatus = {
  PENDING: 'pending',
  ACTIVE: 'active',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const;
export type StageStatus = (typeof StageStatus)[keyof typeof StageStatus];

export interface StageDefinition {
  readonly id: ExtractionStageId;
  readonly stageNumber: 1 | 2 | 3 | 4;
  readonly title: string;
  readonly modelSubtitle: string;
  readonly description: string;
  readonly iconName: string;
}

export interface StageTelemetry {
  readonly stageId: ExtractionStageId;
  readonly status: StageStatus;
  readonly progressPercent: number;
  readonly elapsedMs: number;
  readonly tokensProcessed: number;
  readonly claimsDiscovered: number;
  readonly currentAction: string;
  readonly errorMessage?: string;
}

export interface ExtractionProgressData {
  readonly runId: string;
  readonly documentName: string;
  readonly overallStatus: StageStatus;
  readonly overallProgress: number;
  readonly elapsedSeconds: number;
  readonly totalTokensProcessed: number;
  readonly activeStageId: ExtractionStageId;
  readonly totalClaimsExtracted: number;
  readonly backgroundClaimsCount: number;
  readonly stageDetails: Record<ExtractionStageId, StageTelemetry>;
  readonly baselineSnapshotKey?: string;
  readonly errorMessage?: string;
}

export interface ExtractionProgressStepperProps {
  readonly progressData: ExtractionProgressData;
  readonly onRetry?: () => void;
  readonly onViewBaseline?: (snapshotKey: string) => void;
  readonly className?: string;
}

export interface ExtractionStageItemProps {
  readonly stage: StageDefinition;
  readonly telemetry: StageTelemetry;
  readonly isActive: boolean;
  readonly isLast: boolean;
}

export interface ExtractionTelemetryCardProps {
  readonly elapsedSeconds: number;
  readonly totalTokens: number;
  readonly claimsCount: number;
  readonly backgroundClaimsCount: number;
  readonly overallProgress: number;
  readonly className?: string;
}

export interface CategoryBadgeProps {
  readonly label: string;
  readonly bg: string;
  readonly text: string;
  readonly border: string;
  readonly iconName: string;
}

export const ConfidentialityLevel = {
  STRICT_TRIMMED: 'strict_trimmed',
  FLAGGED_EXCESS: 'flagged_excess',
  REDACTED: 'redacted',
} as const;
export type ConfidentialityLevel = (typeof ConfidentialityLevel)[keyof typeof ConfidentialityLevel];

export interface ConfidentialityBadgeProps {
  readonly wordCount: number;
  readonly maxWords?: number;
  readonly level?: ConfidentialityLevel;
  readonly className?: string;
  readonly isConfidential?: boolean;
  readonly label?: string;
  readonly bg?: string;
  readonly text?: string;
  readonly border?: string;
  readonly iconName?: string;
  readonly hasDialogue?: boolean;
}
