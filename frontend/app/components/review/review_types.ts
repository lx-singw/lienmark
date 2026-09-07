/**
 * Lienmark Counsel Review & Override Data Contracts (Sprint 4.3)
 * Defines data contracts for attorney sign-off, rejection directives,
 * citation suggestions, and re-investigation attempt lineages.
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

export type CounselActionType = 'sign_off' | 'reject';

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

export interface AttorneyOverrideModalProps {
  readonly isOpen: boolean;
  readonly claimKey: string;
  readonly assetType?: string;
  readonly scene?: string;
  readonly description?: string;
  readonly initialAction?: CounselActionType;
  readonly reviewerName?: string;
  readonly reviewerId?: string;
  readonly lineageHistory?: ReadonlyArray<AttemptLineageItem>;
  readonly onClose: () => void;
  readonly onDecision: (payload: DecisionPayload) => Promise<void> | void;
  readonly isSubmitting?: boolean;
}
