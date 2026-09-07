/**
 * frontend/tests/policy_ui.test.ts
 * Unit tests for Studio Policy UI helpers, presets, formatters, validation, and badges.
 * Sprint 5.1 Studio Policy Engine & Governance Invariants.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero-any.
 */

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  ALL_LICENSING_SCOPES,
  ALL_TERRITORY_SCOPES,
  PROFILE_PRESETS,
  formatLicensingScope,
  formatTerritoryScope,
  getProfileBadgeStyles,
  validatePolicyOverride,
  generateLedgerStamp,
  formatPolicyConflict,
} from '../app/components/governance/policy_utils';
import {
  LicensingScopeUI,
  TerritoryScopeUI,
  StudioProfileTypeUI,
} from '../app/components/governance/policy_types';

test('ALL_SCOPES: exposes canonical licensing and territory enumeration constants', () => {
  assert.equal(ALL_LICENSING_SCOPES.length, 6);
  assert.ok(ALL_LICENSING_SCOPES.includes('theatrical'));
  assert.ok(ALL_LICENSING_SCOPES.includes('svod'));
  assert.ok(ALL_LICENSING_SCOPES.includes('in_flight'));

  assert.equal(ALL_TERRITORY_SCOPES.length, 5);
  assert.ok(ALL_TERRITORY_SCOPES.includes('worldwide'));
  assert.ok(ALL_TERRITORY_SCOPES.includes('north_america'));
  assert.ok(ALL_TERRITORY_SCOPES.includes('emea'));
});

test('PROFILE_PRESETS: defines studio archetypes with correct default clearance rules', () => {
  // 1. Major Theatrical
  const major = PROFILE_PRESETS.major_theatrical;
  assert.equal(major.profileType, 'major_theatrical');
  assert.ok(major.requiredMediaScopes.includes('theatrical'));
  assert.ok(major.distributionTerritories.includes('worldwide'));
  assert.equal(major.mandatoryPerpetualForTheatrical, true);
  assert.equal(major.prohibitUnvettedTrademarkFairUse, true);

  // 2. Streamer Exclusive
  const streamer = PROFILE_PRESETS.streamer_exclusive;
  assert.equal(streamer.profileType, 'streamer_exclusive');
  assert.ok(!streamer.requiredMediaScopes.includes('theatrical'));
  assert.ok(streamer.requiredMediaScopes.includes('svod'));
  assert.equal(streamer.mandatoryPerpetualForTheatrical, false);

  // 3. Festival Acquisition
  const festival = PROFILE_PRESETS.festival_acquisition;
  assert.equal(festival.profileType, 'festival_acquisition');
  assert.ok(festival.distributionTerritories.includes('north_america'));
  assert.ok(festival.distributionTerritories.includes('emea'));
  assert.equal(festival.prohibitUnvettedTrademarkFairUse, false);
});

test('formatLicensingScope: formats all licensing scopes to human labels and shortCodes', () => {
  const scopes: LicensingScopeUI[] = [
    'theatrical', 'svod', 'avod', 'linear_broadcast', 'in_flight', 'promotional_trailer',
  ];
  for (const s of scopes) {
    const formatted = formatLicensingScope(s);
    assert.ok(formatted.label.length > 3);
    assert.ok(formatted.description.length > 5);
    assert.ok(formatted.shortCode.length >= 3);
  }

  assert.equal(formatLicensingScope('theatrical').shortCode, 'THEATRICAL');
  assert.equal(formatLicensingScope('svod').shortCode, 'SVOD');
  assert.equal(formatLicensingScope('in_flight').shortCode, 'IN_FLIGHT');
});

test('formatTerritoryScope: returns labels, 2-to-4 letter codes, and region tags', () => {
  const territories: TerritoryScopeUI[] = [
    'worldwide', 'north_america', 'emea', 'latam', 'apac',
  ];
  for (const t of territories) {
    const res = formatTerritoryScope(t);
    assert.ok(res.label.length > 0);
    assert.ok(res.code.length >= 2);
    assert.ok(res.tag.length >= 4);
  }

  assert.equal(formatTerritoryScope('worldwide').code, 'WW');
  assert.equal(formatTerritoryScope('north_america').code, 'NA');
  assert.equal(formatTerritoryScope('emea').code, 'EMEA');
});

test('getProfileBadgeStyles: returns distinct styling classes for studio profiles', () => {
  const profiles: StudioProfileTypeUI[] = [
    'major_theatrical', 'streamer_exclusive', 'festival_acquisition', 'custom',
  ];
  for (const p of profiles) {
    const styles = getProfileBadgeStyles(p);
    assert.ok(styles.badgeClass.includes('border-'));
    assert.ok(styles.textClass.includes('text-'));
    assert.ok(styles.label.length > 3);
  }

  assert.equal(getProfileBadgeStyles('major_theatrical').label, 'Major Theatrical');
  assert.equal(getProfileBadgeStyles('streamer_exclusive').label, 'Streamer Exclusive');
  assert.equal(getProfileBadgeStyles('festival_acquisition').label, 'Festival Acquisition');
});

test('validatePolicyOverride: enforces admin name, rationale, and exemption invariants', () => {
  // Invalid: missing admin actor name and rationale
  const resEmpty = validatePolicyOverride({});
  assert.equal(resEmpty.isValid, false);
  assert.ok(resEmpty.errors.some((e) => e.includes('Admin signatory')));
  assert.ok(resEmpty.errors.some((e) => e.includes('Legal rationale')));
  assert.ok(resEmpty.errors.some((e) => e.includes('At least one policy exemption')));

  // Invalid: short rationale
  const resShortRationale = validatePolicyOverride({
    adminActorName: 'Studio Counsel',
    rationale: 'Too short',
    overriddenMediaScopes: ['theatrical'],
  });
  assert.equal(resShortRationale.isValid, false);
  assert.ok(resShortRationale.errors.some((e) => e.includes('at least 15 characters')));

  // Valid override
  const resValid = validatePolicyOverride({
    adminActorName: 'EVP Business Affairs',
    rationale: 'Approved legal waiver for festival screening distribution rights',
    overriddenMediaScopes: ['theatrical'],
  });
  assert.equal(resValid.isValid, true);
  assert.equal(resValid.errors.length, 0);
});

test('generateLedgerStamp & formatPolicyConflict: generates stamps and formats badge conflicts', () => {
  const stamp = generateLedgerStamp('prod_oppenheimer', 'admin_donna');
  assert.ok(stamp.startsWith('LEDGER-WAV-'));
  assert.ok(stamp.includes('PROD_O'));

  // Critical conflict
  const crit = formatPolicyConflict(true, [{ ruleCode: 'THEATRICAL_PERPETUAL_REQUIRED', severity: 'critical' }]);
  assert.equal(crit.isCritical, true);
  assert.equal(crit.badgeLabel, 'POLICY CONFLICT');
  assert.ok(crit.themeClass.includes('rose'));
  assert.ok(crit.summaryText.includes('1 violation'));

  // Non-critical waiver required
  const warn = formatPolicyConflict(false, [{ ruleCode: 'POL-WAIVER', severity: 'warning' }]);
  assert.equal(warn.isCritical, false);
  assert.equal(warn.badgeLabel, 'WAIVER REQUIRED');
  assert.ok(warn.themeClass.includes('amber'));
});
