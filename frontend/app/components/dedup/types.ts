/**
 * types.ts
 * Type definitions for deduplication notifications and document format badges.
 * Sprint 2.2: Content Digesting, Deduplication & Rename Invariance.
 */

export type DocumentFormat =
  | 'pdf'
  | 'fdx'
  | 'fountain'
  | 'edl'
  | 'plaintext'
  | 'unknown';

export interface DedupNotificationProps {
  isVisible: boolean;
  matchedRevision: string;
  originalFilename: string;
  claimsReused: number;
  apiSpendSavedUsd: number;
  latencyMs: number;
  onDismiss?: () => void;
}

export interface DocumentFormatBadgeProps {
  format: DocumentFormat;
  pageCount?: number;
  sceneCount?: number;
  frameRate?: number;
  className?: string;
}

export interface FormatBadgeStyle {
  bg: string;
  text: string;
  border: string;
  label: string;
  iconName: string;
}
