/**
 * Lienmark Counsel Review & Override Data Contracts (Sprint 5.2)
 * Defines data contracts for attorney sign-off, rejection directives,
 * citation suggestions, re-investigation lineages, and dual review packages.
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

export type CounselActionType = 'sign_off' | 'reject';

export type DualReviewStatusUI =
  | 'pending_first_review'
  | 'first_review_approved'
  | 'final_approved'
  | 'stale_invalidated'
  | 'rejected';

export interface PackageApprovalRecordUI {
  readonly approvalId: string;
  readonly packageId: string;
  readonly packageVersion: number;
  readonly packageDigest: string;
  readonly reviewerId: string;
  readonly reviewerName: string;
  readonly reviewerRole: string;
  readonly isPrimaryOrSecondary: 'primary' | 'secondary';
  readonly conflictAttestation: boolean;
  readonly timestampUtc: string;
  readonly ledgerEventId: string;
}

export interface DecisionPackageUI {
  readonly packageId: string;
  readonly version: number;
  readonly claimId: string;
  readonly cutRevision: string;
  readonly intendedScope: string;
  readonly proposedDisposition: string;
  readonly rationale: string;
  readonly conditions?: string;
  readonly evidenceBundle: ReadonlyArray<string>;
  readonly policyVersion: string;
  readonly policyDigest: string;
  readonly canonicalDigest: string;
  readonly status: DualReviewStatusUI;
  readonly primaryApproval?: PackageApprovalRecordUI | null;
  readonly secondaryApproval?: PackageApprovalRecordUI | null;
  readonly staleReason?: string;
}

export interface CitationTemplateUI {
  readonly id: string;
  readonly category: string;
  readonly title: string;
  readonly statute: string;
  readonly text: string;
}

export interface AttemptLineageItem {
  readonly attemptNumber: number;
  readonly action: CounselActionType | 'investigating';
  readonly counselName: string;
  readonly directiveText: string;
  readonly timestamp: string;
  readonly finding?: string;
  readonly evidenceSummary?: string;
  readonly status?: 'completed' | 'rejected' | 'in_progress' | 'pending';
}

export interface DecisionPayload {
  readonly action: CounselActionType;
  readonly counselId: string;
  readonly counselName: string;
  readonly directiveText: string;
  readonly citationText: string;
  readonly conditions?: string;
}

export interface DirectiveShortcut {
  readonly id: string;
  readonly label: string;
  readonly text: string;
  readonly category?: string;
}

export interface ReviewValidationResult {
  readonly isValid: boolean;
  readonly errors: ReadonlyArray<string>;
  readonly remainingChars?: number;
  readonly charCount?: number;
}

export interface CitationSuggestionPickerProps {
  readonly onSelectCitation: (citationText: string, template?: CitationTemplateUI) => void;
  readonly selectedCitationText?: string;
  readonly templates?: ReadonlyArray<CitationTemplateUI>;
  readonly className?: string;
}

export interface AttemptLineageTimelineProps {
  readonly attempts: ReadonlyArray<AttemptLineageItem>;
  readonly claimKey?: string;
  readonly className?: string;
  readonly activeAttemptNumber?: number;
}

export interface PackageDigestBadgeProps {
  readonly digest: string;
  readonly label?: string;
  readonly isStale?: boolean;
  readonly isTampered?: boolean;
  readonly className?: string;
}

export interface DualReviewPanelProps {
  readonly packageData: DecisionPackageUI;
  readonly currentReviewerId: string;
  readonly currentReviewerName: string;
  readonly currentReviewerRole?: string;
  readonly onApprove?: (packageId: string, isSecondary: boolean, conflictAttestation: boolean) => Promise<void> | void;
  readonly onReject?: (packageId: string, reason: string) => Promise<void> | void;
  readonly isSubmitting?: boolean;
  readonly className?: string;
}

export interface AttorneyOverrideModalProps {
  readonly isOpen: boolean;
  readonly claimKey: string;
  readonly assetType?: string;
  readonly scene?: string;
  readonly description?: string;
  readonly initialAction?: CounselActionType;
  readonly reviewerName?: string;
  readonly reviewerId?: string;
  readonly reviewerRole?: string;
  readonly lineageHistory?: ReadonlyArray<AttemptLineageItem>;
  readonly decisionPackage?: DecisionPackageUI;
  readonly onClose: () => void;
  readonly onDecision: (payload: DecisionPayload) => Promise<void> | void;
  readonly onDualReviewApprove?: (packageId: string, isSecondary: boolean, conflictAttestation: boolean) => Promise<void> | void;
  readonly isSubmitting?: boolean;
}

export interface DirectOverrideFormProps {
  readonly initialAction?: CounselActionType;
  readonly reviewerName: string;
  readonly reviewerId: string;
  readonly onDecision: (payload: DecisionPayload) => Promise<void> | void;
  readonly onClose: () => void;
  readonly isSubmitting?: boolean;
}
