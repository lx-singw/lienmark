/**
 * policy_utils.ts
 * Utility helpers, preset configurations, and formatters for Studio Policy Governance.
 * Sprint 5.1 Studio Policy Engine & Governance Invariants.
 * Files <= 250 lines, functions <= 40 lines, zero-any TypeScript.
 */

import {
  LicensingScopeUI,
  TerritoryScopeUI,
  StudioProfileTypeUI,
  ProfilePresetDefinitionUI,
  ProductionPolicyOverrideUI,
  PolicyValidationResultUI,
} from './policy_types';

export const ALL_LICENSING_SCOPES: readonly LicensingScopeUI[] = [
  'theatrical',
  'svod',
  'avod',
  'linear_broadcast',
  'in_flight',
  'promotional_trailer',
] as const;

export const ALL_TERRITORY_SCOPES: readonly TerritoryScopeUI[] = [
  'worldwide',
  'north_america',
  'emea',
  'latam',
  'apac',
] as const;

export const PROFILE_PRESETS: Record<StudioProfileTypeUI, ProfilePresetDefinitionUI> = {
  major_theatrical: {
    profileType: 'major_theatrical',
    title: 'Major Theatrical',
    subtitle: 'Full Studio Worldwide Theatrical Window',
    description: 'Mandatory worldwide perpetual rights for music sync & theatrical, with zero tolerance for unvetted trademark fair use.',
    requiredMediaScopes: ['theatrical', 'svod', 'avod', 'linear_broadcast', 'in_flight', 'promotional_trailer'],
    distributionTerritories: ['worldwide', 'north_america', 'emea', 'latam', 'apac'],
    mandatoryPerpetualForTheatrical: true,
    prohibitUnvettedTrademarkFairUse: true,
    riskToleranceThreshold: 0.15,
  },
  streamer_exclusive: {
    profileType: 'streamer_exclusive',
    title: 'Streamer Exclusive',
    subtitle: 'Global SVOD/AVOD First-Window Distribution',
    description: 'Direct-to-platform digital release across global streaming territories, exempt from perpetual theatrical sync rules.',
    requiredMediaScopes: ['svod', 'avod', 'promotional_trailer'],
    distributionTerritories: ['worldwide', 'north_america', 'emea', 'latam', 'apac'],
    mandatoryPerpetualForTheatrical: false,
    prohibitUnvettedTrademarkFairUse: true,
    riskToleranceThreshold: 0.35,
  },
  festival_acquisition: {
    profileType: 'festival_acquisition',
    title: 'Festival Acquisition',
    subtitle: 'Limited Indie / Festival Circuit Screening',
    description: 'Staged market clearance focusing on key festival territories, allowing provisional trademark fair-use assertions.',
    requiredMediaScopes: ['theatrical', 'promotional_trailer'],
    distributionTerritories: ['north_america', 'emea'],
    mandatoryPerpetualForTheatrical: false,
    prohibitUnvettedTrademarkFairUse: false,
    riskToleranceThreshold: 0.60,
  },
  custom: {
    profileType: 'custom',
    title: 'Custom Studio Policy',
    subtitle: 'Bespoke Production Clearance Configuration',
    description: 'Tailored policy matrix configured manually by Legal Operations and Studio Administration.',
    requiredMediaScopes: ['theatrical', 'svod'],
    distributionTerritories: ['north_america'],
    mandatoryPerpetualForTheatrical: true,
    prohibitUnvettedTrademarkFairUse: true,
    riskToleranceThreshold: 0.25,
  },
};

export function formatLicensingScope(scope: LicensingScopeUI): {
  label: string;
  description: string;
  shortCode: string;
} {
  switch (scope) {
    case 'theatrical':
      return { label: 'Theatrical Release', description: 'Commercial cinema & festival exhibition', shortCode: 'THEATRICAL' };
    case 'svod':
      return { label: 'Subscription VOD (SVOD)', description: 'Paid subscription streaming platforms', shortCode: 'SVOD' };
    case 'avod':
      return { label: 'Ad-Supported VOD (AVOD)', description: 'Free/ad-supported streaming distribution', shortCode: 'AVOD' };
    case 'linear_broadcast':
      return { label: 'Linear Broadcast', description: 'Terrestrial, cable, and satellite television', shortCode: 'LINEAR' };
    case 'in_flight':
      return { label: 'In-Flight & Transportation', description: 'Airlines, cruise lines, and rail systems', shortCode: 'IN_FLIGHT' };
    case 'promotional_trailer':
      return { label: 'Promotional Trailer', description: 'Teaser, trailer, and digital marketing rights', shortCode: 'PROMO' };
  }
}

export function formatTerritoryScope(territory: TerritoryScopeUI): {
  label: string;
  code: string;
  tag: string;
} {
  switch (territory) {
    case 'worldwide':
      return { label: 'Worldwide (All Markets)', code: 'WW', tag: 'All Territories' };
    case 'north_america':
      return { label: 'North America (US / CA)', code: 'NA', tag: 'US & Canada' };
    case 'emea':
      return { label: 'EMEA (Europe, Middle East, Africa)', code: 'EMEA', tag: 'EMEA Region' };
    case 'latam':
      return { label: 'Latin America (LATAM)', code: 'LATAM', tag: 'LATAM Region' };
    case 'apac':
      return { label: 'Asia-Pacific (APAC)', code: 'APAC', tag: 'APAC Region' };
  }
}

export function getProfileBadgeStyles(profile: StudioProfileTypeUI): {
  badgeClass: string;
  borderClass: string;
  textClass: string;
  accentClass: string;
  label: string;
} {
  switch (profile) {
    case 'major_theatrical':
      return {
        badgeClass: 'bg-purple-950/70 border-purple-500/50 text-purple-200',
        borderClass: 'border-purple-500',
        textClass: 'text-purple-300',
        accentClass: 'bg-purple-500',
        label: 'Major Theatrical',
      };
    case 'streamer_exclusive':
      return {
        badgeClass: 'bg-cyan-950/70 border-cyan-500/50 text-cyan-200',
        borderClass: 'border-cyan-500',
        textClass: 'text-cyan-300',
        accentClass: 'bg-cyan-500',
        label: 'Streamer Exclusive',
      };
    case 'festival_acquisition':
      return {
        badgeClass: 'bg-amber-950/70 border-amber-500/50 text-amber-200',
        borderClass: 'border-amber-500',
        textClass: 'text-amber-300',
        accentClass: 'bg-amber-500',
        label: 'Festival Acquisition',
      };
    case 'custom':
    default:
      return {
        badgeClass: 'bg-slate-900/80 border-slate-700 text-slate-200',
        borderClass: 'border-slate-500',
        textClass: 'text-slate-300',
        accentClass: 'bg-slate-400',
        label: 'Custom Policy',
      };
  }
}

export function validatePolicyOverride(
  override: Partial<ProductionPolicyOverrideUI>
): PolicyValidationResultUI {
  const errors: string[] = [];

  if (!override.adminActorName || override.adminActorName.trim().length < 3) {
    errors.push('Admin signatory name/ID is required (min 3 characters).');
  }

  if (!override.rationale || override.rationale.trim().length < 15) {
    errors.push('Legal rationale must be detailed and at least 15 characters.');
  }

  if (
    (!override.overriddenMediaScopes || override.overriddenMediaScopes.length === 0) &&
    (!override.overriddenTerritories || override.overriddenTerritories.length === 0) &&
    !override.allowTrademarkFairUse
  ) {
    errors.push('At least one policy exemption (scope, territory, or fair-use) must be specified.');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

export function generateLedgerStamp(productionId: string, actor: string): string {
  const now = new Date().toISOString();
  const rawHash = `${productionId}:${actor}:${now}`;
  let hash = 0;
  for (let i = 0; i < rawHash.length; i++) {
    hash = (hash << 5) - hash + rawHash.charCodeAt(i);
    hash |= 0;
  }
  const hex = Math.abs(hash).toString(16).padStart(8, '0');
  return `LEDGER-WAV-${hex.toUpperCase()}-${productionId.slice(0, 6).toUpperCase()}`;
}

export function formatPolicyConflict(
  hasConflict: boolean,
  violations: readonly { severity: string; ruleCode: string }[] = []
): {
  badgeLabel: string;
  isCritical: boolean;
  themeClass: string;
  summaryText: string;
} {
  const isCritical = hasConflict || violations.some((v) => v.severity === 'critical');
  const badgeLabel = isCritical ? 'POLICY CONFLICT' : 'WAIVER REQUIRED';
  const themeClass = isCritical
    ? 'bg-rose-950/90 text-rose-300 border-rose-500/60'
    : 'bg-amber-950/90 text-amber-300 border-amber-500/60';
  const count = violations.length;
  const summaryText = count === 0
    ? badgeLabel
    : `${badgeLabel} (${count} ${count === 1 ? 'violation' : 'violations'})`;
  return { badgeLabel, isCritical, themeClass, summaryText };
}
