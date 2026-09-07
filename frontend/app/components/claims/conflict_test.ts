/**
 * conflict_test.ts
 * Unit tests verifying conflict comparison logic, diff detection,
 * stance badge styling, and authority tier resolution.
 * Sprint 3.3: Contradictory Evidence & Conflict Arbitration UI.
 */

import assert from 'node:assert/strict';
import {
  AuthorityTier,
  ConflictResolutionStance,
} from './conflict_types';
import {
  computeFieldDiffs,
  detectFieldConflict,
  formatDamages,
  getAuthorityTierStyle,
  getSeverityBadgeStyle,
  getStanceBadgeStyle,
} from './conflict_utils';
import { SAMPLE_APOLLO_CONFLICT_PAIR } from './conflict_fixtures';

function testDiffComputation(): void {
  const pair = SAMPLE_APOLLO_CONFLICT_PAIR;
  const diffs = computeFieldDiffs(pair.sourceA, pair.sourceB);

  assert.equal(diffs.length, 5, 'Should evaluate 5 canonical rights fields');

  const rightsDiff = diffs.find((d) => d.fieldKey === 'rightsStatus');
  assert.ok(rightsDiff, 'rightsStatus diff must exist');
  assert.equal(rightsDiff.isConflicting, true, 'rightsStatus must be conflicting');
  assert.equal(rightsDiff.severity, 'critical', 'rightsStatus conflict severity must be critical');

  const ownerDiff = diffs.find((d) => d.fieldKey === 'claimedOwner');
  assert.ok(ownerDiff, 'claimedOwner diff must exist');
  assert.equal(ownerDiff.isConflicting, true, 'claimedOwner must be conflicting');
  assert.equal(ownerDiff.severity, 'critical', 'claimedOwner conflict severity must be critical');

  const licenseDiff = diffs.find((d) => d.fieldKey === 'licenseType');
  assert.ok(licenseDiff, 'licenseType diff must exist');
  assert.equal(licenseDiff.isConflicting, true, 'licenseType must be conflicting');
  assert.equal(licenseDiff.severity, 'high', 'licenseType conflict severity must be high');

  const termDiff = diffs.find((d) => d.fieldKey === 'term');
  assert.ok(termDiff, 'term diff must exist');
  assert.equal(termDiff.isConflicting, true, 'term must be conflicting');
  assert.equal(termDiff.severity, 'medium', 'term conflict severity must be medium');

  const tierDiff = diffs.find((d) => d.fieldKey === 'authorityTier');
  assert.ok(tierDiff, 'authorityTier diff must exist');
  assert.equal(tierDiff.isConflicting, true, 'authorityTier must be conflicting');
  assert.equal(tierDiff.severity, 'info', 'authorityTier conflict severity must be info');
}

function testStanceStyling(): void {
  const contra = getStanceBadgeStyle(ConflictResolutionStance.CONTRADICTORY);
  assert.equal(contra.label, 'CONTRADICTORY');
  assert.equal(contra.iconName, 'AlertOctagon');
  assert.ok(contra.bg.includes('rose'), 'CONTRADICTORY should use rose bg');

  const corro = getStanceBadgeStyle(ConflictResolutionStance.CORROBORATING);
  assert.equal(corro.label, 'CORROBORATING');
  assert.equal(corro.iconName, 'CheckCircle2');
  assert.ok(corro.bg.includes('emerald'), 'CORROBORATING should use emerald bg');

  const uncert = getStanceBadgeStyle(ConflictResolutionStance.UNCERTAIN);
  assert.equal(uncert.label, 'UNCERTAIN');
  assert.equal(uncert.iconName, 'HelpCircle');
}

function testAuthorityTierStyling(): void {
  const tier1 = getAuthorityTierStyle(AuthorityTier.TIER_1_GOVERNMENT);
  assert.equal(tier1.iconName, 'ShieldCheck');
  assert.ok(tier1.text.includes('amber'));

  const tier2 = getAuthorityTierStyle(AuthorityTier.TIER_2_MEDIA_TRADE);
  assert.equal(tier2.iconName, 'Building2');
  assert.ok(tier2.text.includes('sky'));

  const tier3 = getAuthorityTierStyle(AuthorityTier.TIER_3_GENERAL_WEB);
  assert.equal(tier3.iconName, 'Globe');
}

function testConflictDetection(): void {
  assert.equal(detectFieldConflict('Public Domain', 'Public Domain'), false);
  assert.equal(detectFieldConflict('public domain  ', 'PUBLIC DOMAIN'), false);
  assert.equal(detectFieldConflict('Public Domain', 'Copyrighted Master'), true);
  assert.equal(detectFieldConflict('', 'Something'), true);
}

function testDamageFormatting(): void {
  assert.ok(formatDamages(150000).includes('$150,000'));
  assert.ok(formatDamages(150000).includes('17 U.S.C. § 504(c)'));
}

function runAllTests(): void {
  testDiffComputation();
  testStanceStyling();
  testAuthorityTierStyling();
  testConflictDetection();
  testDamageFormatting();
  console.log('ALL FRONTEND CONFLICT TESTS PASSED (5/5 suites)');
}

runAllTests();
