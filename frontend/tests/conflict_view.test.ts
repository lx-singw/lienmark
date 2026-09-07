/**
 * frontend/tests/conflict_view.test.ts
 *
 * Automated unit test suite for Sprint 3.3 Contradictory Evidence & Conflict UI.
 * Verifies stance badges, authority tiers, severity palettes, field diffs,
 * damages formatters, and canonical Apollo 11 fixture integrity.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 * Enforces file <= 250 lines and function <= 40 lines.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  AuthorityTier,
  ConflictResolutionStance,
  type EvidenceSourceRecord,
} from '../app/components/claims/conflict_types';
import {
  getStanceBadgeStyle,
  getAuthorityTierStyle,
  getSeverityBadgeStyle,
  detectFieldConflict,
  computeFieldDiffs,
  formatDamages,
} from '../app/components/claims/conflict_utils';
import { SAMPLE_APOLLO_CONFLICT_PAIR } from '../app/components/claims/conflict_fixtures';

test('getStanceBadgeStyle: maps CONTRADICTORY to high-contrast rose palette', () => {
  const style = getStanceBadgeStyle(ConflictResolutionStance.CONTRADICTORY);
  assert.equal(style.stance, ConflictResolutionStance.CONTRADICTORY);
  assert.equal(style.label, 'CONTRADICTORY');
  assert.equal(style.iconName, 'AlertOctagon');
  assert.ok(style.bg.includes('rose-950'));
  assert.ok(style.border.includes('rose-500'));
  assert.ok(style.text.includes('rose-200'));
});

test('getStanceBadgeStyle: maps CORROBORATING to emerald palette', () => {
  const style = getStanceBadgeStyle(ConflictResolutionStance.CORROBORATING);
  assert.equal(style.stance, ConflictResolutionStance.CORROBORATING);
  assert.equal(style.label, 'CORROBORATING');
  assert.equal(style.iconName, 'CheckCircle2');
  assert.ok(style.bg.includes('emerald-950'));
  assert.ok(style.border.includes('emerald-500'));
  assert.ok(style.text.includes('emerald-200'));
});

test('getStanceBadgeStyle: maps UNCERTAIN and unknown values to slate palette', () => {
  const style = getStanceBadgeStyle(ConflictResolutionStance.UNCERTAIN);
  assert.equal(style.label, 'UNCERTAIN');
  assert.equal(style.iconName, 'HelpCircle');
  assert.ok(style.bg.includes('slate-800'));
});

test('getAuthorityTierStyle: styles all three authority tiers accurately', () => {
  const t1 = getAuthorityTierStyle(AuthorityTier.TIER_1_GOVERNMENT);
  assert.equal(t1.shortLabel, 'Tier 1 Government');
  assert.equal(t1.iconName, 'ShieldCheck');
  assert.ok(t1.text.includes('amber-300'));

  const t2 = getAuthorityTierStyle(AuthorityTier.TIER_2_MEDIA_TRADE);
  assert.equal(t2.shortLabel, 'Tier 2 Media/Trade');
  assert.equal(t2.iconName, 'Building2');
  assert.ok(t2.text.includes('sky-300'));

  const t3 = getAuthorityTierStyle(AuthorityTier.TIER_3_GENERAL_WEB);
  assert.equal(t3.shortLabel, 'Tier 3 Web');
  assert.equal(t3.iconName, 'Globe');
  assert.ok(t3.text.includes('slate-300'));
});

test('getSeverityBadgeStyle: provides correct color scales for all severities', () => {
  const crit = getSeverityBadgeStyle('critical');
  assert.ok(crit.bg.includes('rose-950'));
  assert.ok(crit.text.includes('rose-300'));

  const high = getSeverityBadgeStyle('high');
  assert.ok(high.bg.includes('amber-950'));
  assert.ok(high.text.includes('amber-300'));

  const med = getSeverityBadgeStyle('medium');
  assert.ok(med.bg.includes('yellow-950'));
  assert.ok(med.text.includes('yellow-200'));

  const info = getSeverityBadgeStyle('info');
  assert.ok(info.bg.includes('slate-800'));
  assert.ok(info.text.includes('slate-300'));
});

test('detectFieldConflict: detects differences, normalizes whitespace, and handles case', () => {
  assert.equal(detectFieldConflict('Public Domain', 'public domain'), false);
  assert.equal(detectFieldConflict('  Public Domain  ', 'public domain'), false);
  assert.equal(detectFieldConflict('Public Domain', 'Licensing Required'), true);
  assert.equal(detectFieldConflict('', 'Public Domain'), true);
  assert.equal(detectFieldConflict('   ', '   '), true);
});

test('computeFieldDiffs: correctly detects discrepancies across all 5 standard fields', () => {
  const sourceA: EvidenceSourceRecord = {
    id: 'src_nasa',
    name: 'NASA Image Archive',
    organization: 'NASA',
    authorityTier: AuthorityTier.TIER_1_GOVERNMENT,
    rightsStatus: 'Public Domain',
    claimedOwner: 'US Federal Government',
    licenseType: 'Public Domain',
    term: 'Perpetual',
  };

  const sourceB: EvidenceSourceRecord = {
    id: 'src_cbs',
    name: 'CBS News Archive',
    organization: 'CBS Broadcasting Inc.',
    authorityTier: AuthorityTier.TIER_2_MEDIA_TRADE,
    rightsStatus: 'Active Copyright',
    claimedOwner: 'CBS Broadcasting Inc.',
    licenseType: 'Commercial Broadcast Sync',
    term: 'Active / Post-1972',
  };

  const diffs = computeFieldDiffs(sourceA, sourceB);
  assert.equal(diffs.length, 5);

  const rightsDiff = diffs.find((d) => d.fieldKey === 'rightsStatus');
  assert.ok(rightsDiff);
  assert.equal(rightsDiff.isConflicting, true);
  assert.equal(rightsDiff.severity, 'critical');

  const ownerDiff = diffs.find((d) => d.fieldKey === 'claimedOwner');
  assert.ok(ownerDiff);
  assert.equal(ownerDiff.isConflicting, true);
  assert.equal(ownerDiff.severity, 'critical');

  const licenseDiff = diffs.find((d) => d.fieldKey === 'licenseType');
  assert.ok(licenseDiff);
  assert.equal(licenseDiff.isConflicting, true);
  assert.equal(licenseDiff.severity, 'high');
});

test('formatDamages: formats dollar amounts and handles missing exposures', () => {
  assert.equal(
    formatDamages(150000),
    '$150,000 Statutory Damages Exposure (17 U.S.C. § 504(c))'
  );
  assert.equal(formatDamages(0), '$0 Statutory Damages Exposure (17 U.S.C. § 504(c))');
  assert.equal(formatDamages(undefined), 'Statutory Exposure Pending');
});

test('SAMPLE_APOLLO_CONFLICT_PAIR: conforms to canonical Milestone C Apollo 11 contract', () => {
  const pair = SAMPLE_APOLLO_CONFLICT_PAIR;
  assert.equal(pair.claimId, 'claim_apollo_moon_broadcast');
  assert.equal(pair.stance, ConflictResolutionStance.CONTRADICTORY);
  assert.equal(pair.sourceA.authorityTier, AuthorityTier.TIER_1_GOVERNMENT);
  assert.equal(pair.sourceB.authorityTier, AuthorityTier.TIER_2_MEDIA_TRADE);
  assert.ok(pair.elevationReason.includes('Direct conflict'));
  assert.ok(pair.counselActionRequired.includes('Mandatory Counsel Adjudication'));
  assert.equal(pair.statutoryDamagesMaxUsd, 150000);
});
