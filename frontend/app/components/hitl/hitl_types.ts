/**
 * Lienmark Human-in-the-Loop (HITL) Clarification Types
 * Defines data contracts for clarifying questions, user responses,
 * status states, and document attachments for production rights clearance.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript definitions.
 */

import { UserRole } from '@/lib/types';

export const ClarificationStatus = {
  PENDING: 'pending',
  WAITING_FOR_INFO: 'waiting_for_info',
  IN_REVIEW: 'in_review',
  RESOLVED: 'resolved',
  ESCALATED: 'escalated',
} as const;

export type ClarificationStatus =
  (typeof ClarificationStatus)[keyof typeof ClarificationStatus];

export const QuestionCategory = {
  CHAIN_OF_TITLE: 'chain_of_title',
  MUSIC_RIGHTS: 'music_rights',
  TRADEMARK_BRAND: 'trademark_brand',
  SCRIPT_DIALECT: 'script_dialect',
  LOCATION_RELEASE: 'location_release',
  TALENT_LIKENESS: 'talent_likeness',
  PROPRIETARY_DESIGN: 'proprietary_design',
  GENERAL_CLEARANCE: 'general_clearance',
} as const;

export type QuestionCategory =
  (typeof QuestionCategory)[keyof typeof QuestionCategory];

export type ClarificationPriority = 'low' | 'medium' | 'high' | 'urgent';

export interface AttachedDocument {
  readonly id: string;
  readonly name: string;
  readonly sizeBytes: number;
  readonly mimeType: string;
  readonly uploadedAt: string;
}

export interface ClarificationRequestUI {
  readonly id: string;
  readonly claimKey: string;
  readonly scene: string;
  readonly timecode?: string;
  readonly assetType: string;
  readonly assetName: string;
  readonly category: QuestionCategory;
  readonly assignedRole: UserRole;
  readonly scriptExcerpt: string;
  readonly rationale: string;
  readonly questionText: string;
  readonly suggestedOptions: ReadonlyArray<string>;
  readonly status: ClarificationStatus;
  readonly createdAt?: string;
  readonly priority?: ClarificationPriority;
  readonly requiredDocumentTypes?: ReadonlyArray<string>;
}

export interface ClarificationResponsePayload {
  readonly requestId: string;
  readonly claimKey: string;
  readonly responseText: string;
  readonly selectedOption?: string | null;
  readonly action: 'submit' | 'escalate';
  readonly attachments: ReadonlyArray<AttachedDocument>;
  readonly submittedByRole: UserRole;
  readonly submittedAt: string;
}

export interface ClarificationValidationResult {
  readonly isValid: boolean;
  readonly error: string | null;
  readonly remainingChars: number;
  readonly charCount: number;
}

export interface DocumentValidationResult {
  readonly isValid: boolean;
  readonly error: string | null;
}
