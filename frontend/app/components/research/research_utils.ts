/**
 * research_utils.ts
 * Formatting, domain classification, syntax highlighting, and URL security
 * utilities for clearance research UI.
 * Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import {
  DomainAuthorityTier,
  type AuthorityBadgeStyle,
  type LatencyBadgeStyle,
  type HttpStatusBadgeStyle,
} from './types';

// ============================================================================
// Authority Styling & Classification
// ============================================================================

const AUTHORITY_STYLES: Record<DomainAuthorityTier, AuthorityBadgeStyle> = {
  [DomainAuthorityTier.TIER_1_GOVERNMENT]: {
    tier: DomainAuthorityTier.TIER_1_GOVERNMENT,
    label: 'Tier 1: Government Registry',
    shortLabel: 'Gov Registry',
    bg: 'bg-amber-950/40',
    text: 'text-amber-300',
    border: 'border-amber-500/40',
    iconName: 'ShieldCheck',
  },
  [DomainAuthorityTier.TIER_2_RIGHTS_ORG]: {
    tier: DomainAuthorityTier.TIER_2_RIGHTS_ORG,
    label: 'Tier 2: Rights Organization',
    shortLabel: 'Rights Org',
    bg: 'bg-sky-950/40',
    text: 'text-sky-300',
    border: 'border-sky-500/40',
    iconName: 'Building2',
  },
  [DomainAuthorityTier.TIER_3_WEB]: {
    tier: DomainAuthorityTier.TIER_3_WEB,
    label: 'Tier 3: Public Web Source',
    shortLabel: 'Web Source',
    bg: 'bg-slate-800/60',
    text: 'text-slate-300',
    border: 'border-slate-700/50',
    iconName: 'Globe',
  },
};

const RIGHTS_ORG_DOMAINS: ReadonlyArray<string> = [
  'ascap.com',
  'bmi.com',
  'sesac.com',
  'harryfox.com',
  'soundexchange.com',
  'prsformusic.com',
  'gema.de',
  'sacem.fr',
  'songview.com',
  'socan.com',
  'bmg.com',
  'warnerchappell.com',
  'sonymusicpub.com',
];

export function getAuthorityBadgeStyle(
  tier: DomainAuthorityTier | string
): AuthorityBadgeStyle {
  if (
    tier === DomainAuthorityTier.TIER_1_GOVERNMENT ||
    tier === DomainAuthorityTier.TIER_2_RIGHTS_ORG ||
    tier === DomainAuthorityTier.TIER_3_WEB
  ) {
    return AUTHORITY_STYLES[tier];
  }
  return AUTHORITY_STYLES[DomainAuthorityTier.TIER_3_WEB];
}

export function classifyDomainAuthority(
  domainOrUrl: string
): DomainAuthorityTier {
  const domain = extractDomain(domainOrUrl).toLowerCase();
  if (!domain) return DomainAuthorityTier.TIER_3_WEB;

  if (
    domain.endsWith('.gov') ||
    domain.endsWith('.mil') ||
    domain.includes('copyright.gov') ||
    domain.includes('uspto.gov') ||
    domain.includes('wipo.int') ||
    domain.includes('loc.gov') ||
    domain.includes('uspto.report')
  ) {
    return DomainAuthorityTier.TIER_1_GOVERNMENT;
  }

  const isRightsOrg = RIGHTS_ORG_DOMAINS.some(
    (rod) => domain === rod || domain.endsWith(`.${rod}`)
  );
  if (isRightsOrg) {
    return DomainAuthorityTier.TIER_2_RIGHTS_ORG;
  }

  return DomainAuthorityTier.TIER_3_WEB;
}

// ============================================================================
// Domain Extraction & URL Sanitization
// ============================================================================

export function extractDomain(rawUrl: string): string {
  if (!rawUrl || typeof rawUrl !== 'string') return '';
  const trimmed = rawUrl.trim();
  if (!trimmed) return '';

  try {
    const parsed = trimmed.includes('://')
      ? new URL(trimmed)
      : new URL(`https://${trimmed}`);
    return parsed.hostname.replace(/^www\./i, '');
  } catch {
    const fallbackMatch = trimmed.match(/^(?:https?:\/\/)?([^/:]+)/i);
    return fallbackMatch ? fallbackMatch[1].replace(/^www\./i, '') : '';
  }
}

export function sanitizeUrl(rawUrl: string): string | null {
  if (!rawUrl || typeof rawUrl !== 'string') return null;
  const trimmed = rawUrl.trim();
  if (!trimmed) return null;

  // Block control characters and null bytes
  if (/[\u0000-\u001f\u007f-\u009f]/.test(trimmed)) return null;

  try {
    const parsed = new URL(trimmed);
    const protocol = parsed.protocol.toLowerCase();
    if (protocol !== 'http:' && protocol !== 'https:') {
      return null;
    }
    return parsed.href;
  } catch {
    return null;
  }
}

// ============================================================================
// Latency & Status Formatters
// ============================================================================

export function formatLatency(latencyMs: number): string {
  if (!Number.isFinite(latencyMs) || latencyMs <= 0) return '0 ms';
  if (latencyMs < 1000) {
    return `${Math.round(latencyMs)} ms`;
  }
  return `${(latencyMs / 1000).toFixed(2)} s`;
}

export function getLatencyBadgeColor(latencyMs: number): LatencyBadgeStyle {
  if (!Number.isFinite(latencyMs) || latencyMs < 300) {
    return {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-400',
      border: 'border-emerald-500/30',
      label: 'Optimal',
    };
  }
  if (latencyMs < 1000) {
    return {
      bg: 'bg-amber-500/10',
      text: 'text-amber-400',
      border: 'border-amber-500/30',
      label: 'Moderate',
    };
  }
  return {
    bg: 'bg-rose-500/10',
    text: 'text-rose-400',
    border: 'border-rose-500/30',
    label: 'High Latency',
  };
}

export function getHttpStatusBadgeStyle(status: number): HttpStatusBadgeStyle {
  if (status >= 200 && status < 300) {
    return {
      bg: 'bg-emerald-500/10',
      text: 'text-emerald-400',
      border: 'border-emerald-500/30',
      label: `${status} OK`,
    };
  }
  if (status >= 300 && status < 400) {
    return {
      bg: 'bg-sky-500/10',
      text: 'text-sky-400',
      border: 'border-sky-500/30',
      label: `${status} Redirect`,
    };
  }
  if (status >= 400 && status < 500) {
    return {
      bg: 'bg-amber-500/10',
      text: 'text-amber-400',
      border: 'border-amber-500/30',
      label: `${status} Client Error`,
    };
  }
  if (status >= 500 && status < 600) {
    return {
      bg: 'bg-rose-500/10',
      text: 'text-rose-400',
      border: 'border-rose-500/30',
      label: `${status} Server Error`,
    };
  }
  return {
    bg: 'bg-slate-800/60',
    text: 'text-slate-400',
    border: 'border-slate-700/50',
    label: `${status}`,
  };
}

// ============================================================================
// Query String Tokenizer Re-export (SRP Separation)
// ============================================================================

export { tokenizeQueryString } from './query_tokenizer';

