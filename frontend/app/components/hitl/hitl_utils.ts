/**
 * Lienmark Human-in-the-Loop (HITL) Clarification Utilities
 * Status formatting, role badge styling, and validation helpers.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import { UserRole } from '@/lib/types';
import {
  ClarificationStatus,
  ClarificationValidationResult,
  DocumentValidationResult,
  QuestionCategory,
} from './hitl_types';

export interface StatusBadgeStyle {
  readonly label: string;
  readonly badgeClass: string;
  readonly iconName: 'clock' | 'alert' | 'check' | 'shield' | 'help';
  readonly description: string;
}

export function formatClarificationStatus(status: ClarificationStatus): StatusBadgeStyle {
  switch (status) {
    case ClarificationStatus.WAITING_FOR_INFO:
      return {
        label: 'WAITING FOR INFO',
        badgeClass: 'bg-amber-950/90 text-amber-300 border-amber-500/70 animate-pulse',
        iconName: 'clock',
        description: 'Waiting for production or counsel clarification',
      };
    case ClarificationStatus.IN_REVIEW:
      return {
        label: 'IN REVIEW',
        badgeClass: 'bg-sky-950/90 text-sky-300 border-sky-500/60',
        iconName: 'help',
        description: 'Under active evaluation by legal counsel',
      };
    case ClarificationStatus.RESOLVED:
      return {
        label: 'RESOLVED',
        badgeClass: 'bg-emerald-950/90 text-emerald-300 border-emerald-500/60',
        iconName: 'check',
        description: 'Clarification accepted and applied to clearance matrix',
      };
    case ClarificationStatus.ESCALATED:
      return {
        label: 'ESCALATED TO COUNSEL',
        badgeClass: 'bg-rose-950/90 text-rose-300 border-rose-500/70',
        iconName: 'shield',
        description: 'Escalated to supervising legal counsel',
      };
    default:
      return {
        label: 'PENDING',
        badgeClass: 'bg-slate-900 text-slate-300 border-slate-700',
        iconName: 'clock',
        description: 'Pending review submission',
      };
  }
}

export interface RoleBadgeStyle {
  readonly label: string;
  readonly bgClass: string;
  readonly textClass: string;
  readonly borderClass: string;
}

export function getRoleBadgeStyle(role: UserRole | string): RoleBadgeStyle {
  switch (role) {
    case UserRole.REVIEWER:
      return {
        label: 'Clearance Counsel',
        bgClass: 'bg-purple-950/60',
        textClass: 'text-purple-300',
        borderClass: 'border-purple-500/40',
      };
    case UserRole.PRODUCER:
      return {
        label: 'Production Lead',
        bgClass: 'bg-amber-950/60',
        textClass: 'text-amber-300',
        borderClass: 'border-amber-500/40',
      };
    case UserRole.ADMIN:
      return {
        label: 'Studio Administrator',
        bgClass: 'bg-rose-950/60',
        textClass: 'text-rose-300',
        borderClass: 'border-rose-500/40',
      };
    default:
      return {
        label: 'Legal Analyst',
        bgClass: 'bg-sky-950/60',
        textClass: 'text-sky-300',
        borderClass: 'border-sky-500/40',
      };
  }
}

export interface CategoryBadgeStyle {
  readonly label: string;
  readonly iconName: string;
  readonly colorClass: string;
}

export function getCategoryBadgeStyle(category: QuestionCategory): CategoryBadgeStyle {
  switch (category) {
    case QuestionCategory.CHAIN_OF_TITLE:
      return { label: 'Chain of Title', iconName: 'FileCheck', colorClass: 'text-emerald-400' };
    case QuestionCategory.MUSIC_RIGHTS:
      return { label: 'Music Rights', iconName: 'Music', colorClass: 'text-indigo-400' };
    case QuestionCategory.TRADEMARK_BRAND:
      return { label: 'Trademark & Brand', iconName: 'Tag', colorClass: 'text-cyan-400' };
    case QuestionCategory.SCRIPT_DIALECT:
      return { label: 'Script & Dialogue', iconName: 'FileText', colorClass: 'text-purple-400' };
    case QuestionCategory.LOCATION_RELEASE:
      return { label: 'Location Release', iconName: 'MapPin', colorClass: 'text-rose-400' };
    case QuestionCategory.TALENT_LIKENESS:
      return { label: 'Talent & Likeness', iconName: 'User', colorClass: 'text-amber-400' };
    case QuestionCategory.PROPRIETARY_DESIGN:
      return { label: 'Proprietary Design', iconName: 'Palette', colorClass: 'text-pink-400' };
    default:
      return { label: 'General Clearance', iconName: 'Shield', colorClass: 'text-slate-300' };
  }
}

export function validateClarificationResponse(
  text: string,
  minLength = 10,
  maxLength = 1000
): ClarificationValidationResult {
  const trimmed = text.trim();
  const charCount = trimmed.length;
  const remainingChars = maxLength - charCount;

  if (charCount === 0) {
    return {
      isValid: false,
      error: 'Clarification response cannot be empty.',
      remainingChars,
      charCount,
    };
  }

  if (charCount < minLength) {
    return {
      isValid: false,
      error: `Response is too brief. Please provide at least ${minLength} characters of context.`,
      remainingChars,
      charCount,
    };
  }

  if (charCount > maxLength) {
    return {
      isValid: false,
      error: `Response exceeds maximum limit of ${maxLength} characters.`,
      remainingChars,
      charCount,
    };
  }

  return { isValid: true, error: null, remainingChars, charCount };
}

export function validateAttachedDocument(
  file: { name: string; size: number },
  allowedExtensions: ReadonlyArray<string> = ['.pdf', '.docx'],
  maxSizeBytes = 15 * 1024 * 1024
): DocumentValidationResult {
  const lowerName = file.name.toLowerCase();
  const hasValidExt = allowedExtensions.some((ext) => lowerName.endsWith(ext));

  if (!hasValidExt) {
    return {
      isValid: false,
      error: `Invalid file format: "${file.name}". Only ${allowedExtensions.join(', ')} files are permitted.`,
    };
  }

  if (file.size > maxSizeBytes) {
    const maxMb = Math.round(maxSizeBytes / (1024 * 1024));
    return {
      isValid: false,
      error: `File size exceeds ${maxMb}MB limit (${(file.size / (1024 * 1024)).toFixed(1)}MB).`,
    };
  }

  return { isValid: true, error: null };
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
