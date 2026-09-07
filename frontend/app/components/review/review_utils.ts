/**
 * Lienmark Counsel Review Utilities & Formatting Rules (Sprint 4.3)
 * Provides directive shortcuts, citation templates, validation, and badge styling.
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import {
  CitationTemplateUI,
  CounselActionType,
  DecisionPayload,
  DirectiveShortcut,
  ReviewValidationResult,
} from './review_types';

export const DIRECTIVE_SHORTCUTS: ReadonlyArray<DirectiveShortcut> = [
  {
    id: 'master_recording_owner',
    label: 'Master Recording Owner',
    text: 'Check master recording owner',
    category: 'Music Rights',
  },
  {
    id: 'foreign_distribution_holdback',
    label: 'Foreign Holdback',
    text: 'Verify foreign distribution holdback',
    category: 'Distribution',
  },
  {
    id: 'ascap_1972_live',
    label: 'ASCAP 1972 Live Adaptation',
    text: 'Re-search ASCAP for 1972 live adaptation',
    category: 'Music Rights',
  },
  {
    id: 'fair_use_transformative',
    label: 'Fair Use 4-Factor',
    text: 'Confirm transformative use and market substitution under Campbell v. Acuff-Rose',
    category: 'Copyright',
  },
  {
    id: 'trademark_de_minimis',
    label: 'Trademark De Minimis',
    text: 'Investigate incidental background focal exposure duration under 15 U.S.C. § 1125',
    category: 'Trademark',
  },
  {
    id: 'public_domain_pre_1929',
    label: 'Pre-1929 Public Domain',
    text: 'Verify pre-1929 initial publication date and absence of renewed derivative claims',
    category: 'Public Domain',
  },
];

export const DEFAULT_CITATION_TEMPLATES: ReadonlyArray<CitationTemplateUI> = [
  {
    id: 'fair_use_107',
    category: 'Copyright',
    title: 'Fair Use Defense (17 U.S.C. § 107)',
    statute: '17 U.S.C. § 107',
    text: '17 U.S.C. § 107 Fair Use: Evaluated under four statutory factors: (1) purpose and character of use is transformative commentary; (2) nature of copyrighted work; (3) substantiality of portion used in relation to whole is strictly fleeting; (4) zero negative effect upon the potential market for original work.',
  },
  {
    id: 'sync_master_clause_4a',
    category: 'Music Rights',
    title: 'Sync & Master License (Clause 4(a))',
    statute: 'Standard Sync/Master Form Cl. 4(a)',
    text: 'Clause 4(a) Audiovisual Synchronization: Grantor confirms irrevocable, worldwide synchronization and master recording exploitation rights in all media now known or hereafter devised, in perpetuity, with warranties of non-infringement fully executed.',
  },
  {
    id: 'lanham_act_43a',
    category: 'Trademark',
    title: 'Lanham Act De Minimis (15 U.S.C. § 1125)',
    statute: '15 U.S.C. § 1125(a)',
    text: '15 U.S.C. § 1125(a): Incidental and out-of-focus background placement creates no likelihood of consumer confusion, false endorsement, or trademark tarnishment pursuant to Second Circuit Rogers v. Grimaldi standard.',
  },
  {
    id: 'public_domain_304',
    category: 'Public Domain',
    title: 'Public Domain Status (17 U.S.C. § 304)',
    statute: '17 U.S.C. § 304 / Sonny Bono CTEA',
    text: '17 U.S.C. § 304: Work published prior to January 1, 1929 has permanently entered the United States public domain; unrestricted exploitation permitted without statutory royalties or license requirements.',
  },
  {
    id: 'incidental_ephemeral_112',
    category: 'General Clearance',
    title: 'Ephemeral Reproduction (17 U.S.C. § 112)',
    statute: '17 U.S.C. § 112',
    text: '17 U.S.C. § 112: Transient reproduction solely for technical broadcast assembly and non-standalone display qualifies for statutory exemption from direct copyright liability.',
  },
];

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
