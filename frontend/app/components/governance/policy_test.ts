/**
 * policy_test.ts
 * Unit tests verifying Studio Policy Governance presets, formatters,
 * override validations, and ledger stamping invariants.
 * Sprint 5.1 Studio Policy Engine & Governance Invariants.
 * Files <= 250 lines, functions <= 40 lines, zero-any TypeScript.
 */

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
} from './policy_utils';

function testProfilePresets(): void {
  const theatrical = PROFILE_PRESETS.major_theatrical;
  assert.equal(theatrical.mandatoryPerpetualForTheatrical, true);
  assert.equal(theatrical.prohibitUnvettedTrademarkFairUse, true);
  assert.equal(theatrical.requiredMediaScopes.length, 6);
  assert.equal(theatrical.distributionTerritories.length, 5);

  const streamer = PROFILE_PRESETS.streamer_exclusive;
  assert.equal(streamer.mandatoryPerpetualForTheatrical, false);
  assert.equal(streamer.prohibitUnvettedTrademarkFairUse, true);
  assert.ok(streamer.requiredMediaScopes.includes('svod'));
  assert.ok(streamer.requiredMediaScopes.includes('avod'));

  const festival = PROFILE_PRESETS.festival_acquisition;
  assert.equal(festival.mandatoryPerpetualForTheatrical, false);
  assert.equal(festival.prohibitUnvettedTrademarkFairUse, false);
  assert.equal(festival.distributionTerritories.length, 2);
}

function testFormatters(): void {
  for (const scope of ALL_LICENSING_SCOPES) {
    const formatted = formatLicensingScope(scope);
    assert.ok(formatted.label.length > 0, `Scope ${scope} should have label`);
    assert.ok(formatted.shortCode.length > 0, `Scope ${scope} should have shortCode`);
  }

  for (const territory of ALL_TERRITORY_SCOPES) {
    const formatted = formatTerritoryScope(territory);
    assert.ok(formatted.label.length > 0, `Territory ${territory} should have label`);
    assert.ok(formatted.code.length > 0, `Territory ${territory} should have code`);
  }
}

function testProfileBadgeStyles(): void {
  const theatrical = getProfileBadgeStyles('major_theatrical');
  assert.ok(theatrical.badgeClass.includes('purple'), 'Theatrical should have purple styling');

  const streamer = getProfileBadgeStyles('streamer_exclusive');
  assert.ok(streamer.badgeClass.includes('cyan'), 'Streamer should have cyan styling');

  const festival = getProfileBadgeStyles('festival_acquisition');
  assert.ok(festival.badgeClass.includes('amber'), 'Festival should have amber styling');
}

function testOverrideValidation(): void {
  const invalid = validatePolicyOverride({});
  assert.equal(invalid.isValid, false, 'Empty override must be invalid');
  assert.ok(invalid.errors.length >= 3, 'Must report missing admin, rationale, and exemptions');

  const valid = validatePolicyOverride({
    adminActorName: 'E. Vance, VP Legal Ops',
    rationale: 'Independent distribution agreement negotiated with territory exclusions under standard festival carveouts.',
    allowTrademarkFairUse: true,
  });
  assert.equal(valid.isValid, true, 'Fully specified override must be valid');
  assert.equal(valid.errors.length, 0);
}

function testLedgerStamping(): void {
  const stamp = generateLedgerStamp('prod_noir_detective_2026', 'E. Vance');
  assert.ok(stamp.startsWith('LEDGER-WAV-'), 'Stamp must start with LEDGER-WAV-');
  assert.ok(stamp.includes('PROD_N'), 'Stamp must include uppercase production prefix');
}

export function runAllPolicyTests(): void {
  testProfilePresets();
  testFormatters();
  testProfileBadgeStyles();
  testOverrideValidation();
  testLedgerStamping();
  // eslint-disable-next-line no-console
  console.log('✓ All Studio Policy Governance tests passed successfully.');
}

if (typeof require !== 'undefined' && require.main === module) {
  runAllPolicyTests();
}
