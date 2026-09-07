/**
 * Ingestion Utilities & Validation Functions
 * Provides GCS path regex validation, file size formatting, and status badge styling.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import type { GcsTargetValidation, StatusBadgeStyle } from './types';

/**
 * Authoritative regular expression matching the canonical GCS locked milestone folder path.
 * Format: organizations/<orgId>/productions/<prodId>/locked/<filename>.pdf
 */
export const LOCKED_FOLDER_REGEX =
  /^organizations\/([a-zA-Z0-9_-]+)\/productions\/([a-zA-Z0-9_-]+)\/locked\/([a-zA-Z0-9_.-]+\.pdf)$/;

/**
 * Default Cloud Storage intake bucket for milestone script uploads.
 */
export const DEFAULT_INTAKE_BUCKET = 'lienmark-intake-storage';

/**
 * Maximum permitted script file size: 50 Megabytes (52,428,800 bytes).
 */
export const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024;

/**
 * Validates a GCS target path against the canonical locked milestone folder schema.
 * Supports relative paths, paths with leading slashes, and full gs:// URI schemes.
 */
export function validateGcsTargetPath(path: string): GcsTargetValidation {
  if (!path || typeof path !== 'string' || path.trim() === '') {
    return { isValid: false, error: 'Target path cannot be empty.' };
  }

  // Strip gs://<bucket>/ prefix and any leading slashes
  const normalized = path
    .trim()
    .replace(/^gs:\/\/[^/]+\//, '')
    .replace(/^\/+/, '');

  const match = LOCKED_FOLDER_REGEX.exec(normalized);
  if (match) {
    return {
      isValid: true,
      orgId: match[1],
      prodId: match[2],
      filename: match[3],
    };
  }

  return diagnosePathError(normalized);
}

/**
 * Internal helper to diagnose and return specific error explanations for invalid paths.
 */
function diagnosePathError(normalized: string): GcsTargetValidation {
  if (!normalized.toLowerCase().endsWith('.pdf')) {
    return {
      isValid: false,
      error: 'Only PDF documents (.pdf) are permitted in the locked milestone folder.',
    };
  }
  if (!normalized.includes('/locked/')) {
    return {
      isValid: false,
      error: 'Target path must reside in the /locked/ milestone folder.',
    };
  }
  if (!normalized.startsWith('organizations/')) {
    return {
      isValid: false,
      error: 'Target path must start with organizations/{orgId}.',
    };
  }
  if (!normalized.includes('/productions/')) {
    return {
      isValid: false,
      error: 'Target path must contain /productions/{prodId}.',
    };
  }
  return {
    isValid: false,
    error:
      'Path does not conform to organizations/{orgId}/productions/{prodId}/locked/{filename}.pdf',
  };
}

/**
 * Formats a byte count into a human-readable file size string (e.g. "1.4 MB", "520 KB", "0 B").
 */
export function formatFileSize(bytes: number): string {
  if (typeof bytes !== 'number' || isNaN(bytes) || bytes <= 0) {
    return '0 B';
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const kb = bytes / 1024;
  if (kb < 1024) {
    const formatted =
      kb % 1 === 0 ? kb.toFixed(0) : kb < 10 ? kb.toFixed(1) : Math.round(kb).toString();
    return `${formatted} KB`;
  }
  const mb = bytes / (1024 * 1024);
  if (mb < 1024) {
    const formatted = mb % 1 === 0 ? mb.toFixed(0) : mb.toFixed(1);
    return `${formatted} MB`;
  }
  const gb = bytes / (1024 * 1024 * 1024);
  return `${gb.toFixed(2)} GB`;
}

/**
 * Returns Tailwind CSS styling and display label for an ingestion lifecycle status.
 */
export function getStatusBadgeStyle(status: string): StatusBadgeStyle {
  const norm = (status || '').trim().toUpperCase();

  switch (norm) {
    case 'QUEUED':
      return {
        bg: 'bg-amber-950/40',
        text: 'text-amber-300',
        border: 'border-amber-500/30',
        label: 'QUEUED',
      };
    case 'PROCESSING':
    case 'INITIALIZING':
    case 'EVALUATING':
      return {
        bg: 'bg-sky-950/40',
        text: 'text-sky-300',
        border: 'border-sky-500/30',
        label: 'PROCESSING',
      };
    case 'COMPLETED':
    case 'READY_FOR_REVIEW':
      return {
        bg: 'bg-emerald-950/40',
        text: 'text-emerald-300',
        border: 'border-emerald-500/30',
        label: 'COMPLETED',
      };
    case 'REJECTED_OUT_OF_SCOPE':
    case 'REJECTED':
    case 'OUT_OF_SCOPE':
      return {
        bg: 'bg-rose-950/40',
        text: 'text-rose-300',
        border: 'border-rose-500/30',
        label: 'REJECTED_OUT_OF_SCOPE',
      };
    case 'FAILED':
      return {
        bg: 'bg-rose-950/40',
        text: 'text-rose-300',
        border: 'border-rose-500/30',
        label: 'FAILED',
      };
    default:
      return {
        bg: 'bg-slate-800/60',
        text: 'text-slate-300',
        border: 'border-slate-700/50',
        label: norm || 'UNKNOWN',
      };
  }
}

/**
 * Assembles a canonical GCS URI given bucket, orgId, prodId, and filename.
 */
export function buildGcsUri(
  bucket: string,
  orgId: string,
  prodId: string,
  filename: string
): string {
  const cleanBucket = bucket.trim() || DEFAULT_INTAKE_BUCKET;
  const cleanOrg = orgId.trim() || '{orgId}';
  const cleanProd = prodId.trim() || '{prodId}';
  const cleanFile = filename.trim() || '{filename}.pdf';
  return `gs://${cleanBucket}/organizations/${cleanOrg}/productions/${cleanProd}/locked/${cleanFile}`;
}
