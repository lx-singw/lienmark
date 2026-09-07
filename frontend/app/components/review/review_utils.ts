/**
 * Lienmark Counsel Review Utilities & Formatting Rules (Sprint 5.2)
 * Provides directive shortcuts, citation templates, dual review guards, validation, and badge styling.
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import {
  CitationTemplateUI,
  CounselActionType,
  DecisionPackageUI,
  DecisionPayload,
  DualReviewStatusUI,
  ReviewValidationResult,
} from './review_types';

export { DIRECTIVE_SHORTCUTS, DEFAULT_CITATION_TEMPLATES } from './citation_templates';
import { DEFAULT_CITATION_TEMPLATES } from './citation_templates';

export function formatCounselAction(action: CounselActionType): {
  label: string;
  badgeClass: string;
  borderClass: string;
} {
  if (action === 'sign_off') {
    return {
      label: 'Sign-off / Clear Claim',
      badgeClass: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
      borderClass: 'border-emerald-500/50',
    };
  }
  return {
    label: 'Reject & Direct Re-investigation',
    badgeClass: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
    borderClass: 'border-rose-500/50',
  };
}

export function formatAttemptBadge(
  attemptNumber: number,
  action?: CounselActionType | 'investigating' | string
): { label: string; badgeClass: string } {
  if (action === 'reject') {
    return {
      label: `Attempt ${attemptNumber}: Rejected`,
      badgeClass: 'bg-rose-950/60 text-rose-300 border-rose-500/40',
    };
  }
  if (action === 'sign_off') {
    return {
      label: `Attempt ${attemptNumber}: Cleared`,
      badgeClass: 'bg-emerald-950/60 text-emerald-300 border-emerald-500/40',
    };
  }
  return {
    label: `Attempt ${attemptNumber}: Active Re-investigation`,
    badgeClass: 'bg-amber-950/60 text-amber-300 border-amber-500/40 animate-pulse',
  };
}

export function formatReviewTimestamp(isoString: string): string {
  if (!isoString) return 'Pending';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return isoString;
  }
}

export function truncateDigest(digest: string, head = 8, tail = 6): string {
  if (!digest) return 'N/A';
  const clean = digest.trim();
  if (!clean) return 'N/A';
  if (clean.length <= head + tail) return clean;
  return `${clean.slice(0, head)}...${clean.slice(-tail)}`;
}

export function formatDualReviewStatus(status: DualReviewStatusUI): {
  label: string;
  badgeClass: string;
  stepIndex: number;
  description: string;
} {
  switch (status) {
    case 'pending_first_review':
      return {
        label: 'Pending Primary Review',
        badgeClass: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
        stepIndex: 0,
        description: 'Awaiting primary counsel review and clearance attestation.',
      };
    case 'first_review_approved':
      return {
        label: 'First Review Approved',
        badgeClass: 'bg-sky-500/20 text-sky-300 border-sky-500/40',
        stepIndex: 1,
        description: 'Primary review passed. Pending distinct supervising counsel second review.',
      };
    case 'final_approved':
      return {
        label: 'Dual Approved',
        badgeClass: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
        stepIndex: 2,
        description: 'Dual review complete. Cryptographically locked to ledger.',
      };
    case 'stale_invalidated':
      return {
        label: 'Stale / Invalidation Detected',
        badgeClass: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
        stepIndex: -1,
        description: 'Decision package is stale. Material evidence or policy changed. Both reviews required again.',
      };
    case 'rejected':
      return {
        label: 'Package Rejected',
        badgeClass: 'bg-red-600/20 text-red-300 border-red-500/40',
        stepIndex: -1,
        description: 'Claim disposition rejected by counsel; re-investigation directed.',
      };
  }
}

export function canPerformSecondReview(
  packageData: DecisionPackageUI,
  currentReviewerId: string
): { allowed: boolean; reason?: string } {
  if (packageData.status === 'stale_invalidated') {
    return {
      allowed: false,
      reason: 'Decision package is stale. Material evidence or policy changed. Both reviews required again.',
    };
  }
  if (packageData.status === 'final_approved') {
    return { allowed: false, reason: 'Decision package has already received final dual approval.' };
  }
  if (packageData.status === 'rejected') {
    return { allowed: false, reason: 'Decision package has been rejected.' };
  }
  if (packageData.status === 'pending_first_review') {
    return { allowed: false, reason: 'Primary counsel review must be completed before secondary review.' };
  }
  const primaryId = packageData.primaryApproval?.reviewerId?.trim().toLowerCase();
  const currentId = currentReviewerId.trim().toLowerCase();
  if (primaryId && currentId && primaryId === currentId) {
    return { allowed: false, reason: 'Second review requires a distinct authorized counsel.' };
  }
  return { allowed: true };
}

export function validateDualReviewApproval(
  packageData: DecisionPackageUI,
  currentReviewerId: string,
  conflictAttested: boolean
): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];
  if (!conflictAttested) {
    errors.push('Conflict-of-interest affirmative attestation is strictly required.');
  }
  if (packageData.status === 'stale_invalidated') {
    errors.push('Decision package is stale. Material evidence or policy changed. Both reviews required again.');
  }
  if (packageData.status === 'first_review_approved') {
    const secondCheck = canPerformSecondReview(packageData, currentReviewerId);
    if (!secondCheck.allowed && secondCheck.reason) {
      errors.push(secondCheck.reason);
    }
  }
  return { isValid: errors.length === 0, errors };
}

export function validateDirectiveText(
  text: string,
  action: CounselActionType
): ReviewValidationResult {
  const trimmed = text.trim();
  const errors: string[] = [];
  if (action === 'reject' && trimmed.length === 0) {
    errors.push('Rejection requires a specific investigative directive for the research agent.');
  } else if (action === 'reject' && trimmed.length < 10) {
    errors.push('Rejection directive is too brief; provide actionable instructions (min 10 characters).');
  }
  if (trimmed.length > 1000) {
    errors.push('Directive text exceeds maximum limit of 1000 characters.');
  }
  return {
    isValid: errors.length === 0,
    errors,
    remainingChars: Math.max(0, 1000 - trimmed.length),
    charCount: trimmed.length,
  };
}

export function validateDecisionPayload(
  payload: Partial<DecisionPayload>
): ReviewValidationResult {
  const errors: string[] = [];
  if (!payload.action || (payload.action !== 'sign_off' && payload.action !== 'reject')) {
    errors.push('Valid counsel action (sign_off or reject) is required.');
  }
  if (!payload.counselId || !payload.counselId.trim()) {
    errors.push('Counsel reviewer ID is required for immutable audit logging.');
  }
  if (!payload.counselName || !payload.counselName.trim()) {
    errors.push('Counsel reviewer name is required.');
  }
  if (payload.action === 'reject') {
    const directiveResult = validateDirectiveText(payload.directiveText ?? '', 'reject');
    if (!directiveResult.isValid) {
      errors.push(...directiveResult.errors);
    }
  }
  if (payload.action === 'sign_off' && (!payload.citationText || !payload.citationText.trim())) {
    errors.push('Legal citation or statutory basis is required for affirmative sign-off.');
  }
  return {
    isValid: errors.length === 0,
    errors,
  };
}

export function getCitationByCategory(
  category: string,
  templates: ReadonlyArray<CitationTemplateUI> = DEFAULT_CITATION_TEMPLATES
): ReadonlyArray<CitationTemplateUI> {
  if (!category || category === 'All') return templates;
  return templates.filter((t) => t.category.toLowerCase() === category.toLowerCase());
}
