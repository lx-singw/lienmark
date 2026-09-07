/**
 * dedup_utils.ts
 * Formatting utilities and styling configuration for deduplication UI.
 * Sprint 2.2: Content Digesting, Deduplication & Rename Invariance.
 */

import type { FormatBadgeStyle } from './types';

/**
 * Mapping table of format metadata conforming to Open/Closed configuration principles.
 */
const FORMAT_STYLE_MAP: Record<string, FormatBadgeStyle> = {
  pdf: {
    bg: 'bg-rose-950/60',
    text: 'text-rose-300',
    border: 'border-rose-500/40',
    label: 'PDF',
    iconName: 'FileText',
  },
  fdx: {
    bg: 'bg-sky-950/60',
    text: 'text-sky-300',
    border: 'border-sky-500/40',
    label: 'FINAL DRAFT (FDX)',
    iconName: 'FileCode',
  },
  fountain: {
    bg: 'bg-emerald-950/60',
    text: 'text-emerald-300',
    border: 'border-emerald-500/40',
    label: 'FOUNTAIN',
    iconName: 'PenTool',
  },
  edl: {
    bg: 'bg-amber-950/60',
    text: 'text-amber-300',
    border: 'border-amber-500/40',
    label: 'CMX 3600 EDL',
    iconName: 'Film',
  },
  plaintext: {
    bg: 'bg-slate-800/80',
    text: 'text-slate-300',
    border: 'border-slate-700/50',
    label: 'PLAIN TEXT',
    iconName: 'AlignLeft',
  },
  txt: {
    bg: 'bg-slate-800/80',
    text: 'text-slate-300',
    border: 'border-slate-700/50',
    label: 'PLAIN TEXT',
    iconName: 'AlignLeft',
  },
};

const DEFAULT_FORMAT_STYLE: FormatBadgeStyle = {
  bg: 'bg-zinc-800/80',
  text: 'text-zinc-400',
  border: 'border-zinc-700/50',
  label: 'UNKNOWN FORMAT',
  iconName: 'FileQuestion',
};

/**
 * Formats cache-hit savings metrics into a user-facing status message.
 * Example output: "Incurred $0.00 API spend; loaded 14 existing claims in 42ms."
 *
 * @param spendUsd Incurred API spend in USD.
 * @param claimsCount Number of existing claims loaded from cache.
 * @param latencyMs Elapsed latency in milliseconds.
 * @returns Human-readable summary string.
 */
export function formatCacheHitSavings(
  spendUsd: number,
  claimsCount: number,
  latencyMs: number
): string {
  const safeSpend = isNaN(spendUsd) || spendUsd < 0 ? 0 : spendUsd;
  const safeClaims = isNaN(claimsCount) || claimsCount < 0 ? 0 : Math.floor(claimsCount);
  const safeLatency = isNaN(latencyMs) || latencyMs < 0 ? 0 : Math.round(latencyMs);
  const claimLabel = safeClaims === 1 ? 'claim' : 'claims';

  return `Incurred $${safeSpend.toFixed(2)} API spend; loaded ${safeClaims} existing ${claimLabel} in ${safeLatency}ms.`;
}

/**
 * Returns Tailwind CSS classes, display label, and Lucide icon name for document formats.
 * Supports PDF, Final Draft (FDX), Fountain, CMX 3600 EDL, Plain Text, and Unknown.
 *
 * @param format Format identifier string.
 * @returns Badge styling, label, and icon identifier.
 */
export function getFormatBadgeStyle(format: string): FormatBadgeStyle {
  const normalized = (format || '').toLowerCase().trim();
  const matched = FORMAT_STYLE_MAP[normalized];
  if (matched) {
    return matched;
  }
  return DEFAULT_FORMAT_STYLE;
}
