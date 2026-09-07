/**
 * Lienmark Dual Review UI Unit Test Suite: frontend/tests/dual_review_ui.test.ts
 * Tests PackageDigestBadge, DualReviewPanel step progression, conflict attestation
 * validation, distinct reviewer self-approval guard, and stale warning banner (Sprint 5.2).
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  truncateDigest,
  formatDualReviewStatus,
  canPerformSecondReview,
  validateDualReviewApproval,
} from '../app/components/review/review_utils';
import {
  DecisionPackageUI,
  DualReviewStatusUI,
  PackageApprovalRecordUI,
} from '../app/components/review/review_types';

const SAMPLE_PRIMARY_APPROVAL: PackageApprovalRecordUI = {
  approvalId: 'app_primary_001',
  packageId: 'pkg_asset_101',
  packageVersion: 1,
  packageDigest: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  reviewerId: 'counsel_sarah_jenkins',
  reviewerName: 'Sarah Jenkins, Esq.',
  reviewerRole: 'Lead Clearance Counsel',
  isPrimaryOrSecondary: 'primary',
  conflictAttestation: true,
  timestampUtc: '2026-09-07T10:00:00Z',
  ledgerEventId: 'ledger_evt_7749129048a1',
};

const BASE_PACKAGE: DecisionPackageUI = {
  packageId: 'pkg_asset_101',
  version: 1,
  claimId: 'claim_sync_042',
  cutRevision: 'Cut_v8.4_theatrical',
  intendedScope: 'Worldwide Theatrical & Streaming',
  proposedDisposition: 'sign_off',
  rationale: 'Public domain verified under 17 U.S.C. § 304 pre-1929 publication.',
  evidenceBundle: ['ev_snap_001', 'ev_snap_002'],
  policyVersion: 'pol_v2026.3',
  policyDigest: '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4',
  canonicalDigest: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  status: 'first_review_approved',
  primaryApproval: SAMPLE_PRIMARY_APPROVAL,
};

test('PackageDigestBadge: truncates canonical digest and handles edge cases', () => {
  const hash = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';
  assert.equal(truncateDigest(hash, 8, 6), 'e3b0c442...52b855');
  assert.equal(truncateDigest('short_hash', 10, 10), 'short_hash');
  assert.equal(truncateDigest(''), 'N/A');
  assert.equal(truncateDigest('   '), 'N/A');
});

test('DualReviewPanel step progression: maps stages from pending to dual approved', () => {
  const step0 = formatDualReviewStatus('pending_first_review');
  assert.equal(step0.stepIndex, 0);
  assert.equal(step0.label, 'Pending Primary Review');

  const step1 = formatDualReviewStatus('first_review_approved');
  assert.equal(step1.stepIndex, 1);
  assert.equal(step1.label, 'First Review Approved');

  const step2 = formatDualReviewStatus('final_approved');
  assert.equal(step2.stepIndex, 2);
  assert.equal(step2.label, 'Dual Approved');

  const stale = formatDualReviewStatus('stale_invalidated');
  assert.equal(stale.stepIndex, -1);
  assert.ok(stale.description.includes('Material evidence or policy changed'));
});

test('conflict attestation validation: blocks unconfirmed attestation on both stages', () => {
  const unconfirmed = validateDualReviewApproval(BASE_PACKAGE, 'counsel_marcus_vance', false);
  assert.equal(unconfirmed.isValid, false);
  assert.ok(unconfirmed.errors.some((e) => e.includes('Conflict-of-interest affirmative attestation')));

  const confirmed = validateDualReviewApproval(BASE_PACKAGE, 'counsel_marcus_vance', true);
  assert.equal(confirmed.isValid, true);
  assert.equal(confirmed.errors.length, 0);
});

test('distinct reviewer self-approval guard: prevents primary counsel self-approval on stage 2', () => {
  const selfApprovalAttempt = canPerformSecondReview(BASE_PACKAGE, 'counsel_sarah_jenkins');
  assert.equal(selfApprovalAttempt.allowed, false);
  assert.equal(selfApprovalAttempt.reason, 'Second review requires a distinct authorized counsel.');

  const validationResult = validateDualReviewApproval(BASE_PACKAGE, 'counsel_sarah_jenkins', true);
  assert.equal(validationResult.isValid, false);
  assert.ok(validationResult.errors.includes('Second review requires a distinct authorized counsel.'));

  const distinctCounselAttempt = canPerformSecondReview(BASE_PACKAGE, 'counsel_marcus_vance');
  assert.equal(distinctCounselAttempt.allowed, true);
});

test('stale warning banner: detects invalidation and blocks approvals with clear alert', () => {
  const stalePackage: DecisionPackageUI = {
    ...BASE_PACKAGE,
    status: 'stale_invalidated',
    staleReason: 'Master license expired in revised cut revision.',
  };

  const attempt = canPerformSecondReview(stalePackage, 'counsel_marcus_vance');
  assert.equal(attempt.allowed, false);
  assert.ok(attempt.reason?.includes('Decision package is stale'));

  const validation = validateDualReviewApproval(stalePackage, 'counsel_marcus_vance', true);
  assert.equal(validation.isValid, false);
  assert.ok(validation.errors.some((e) => e.includes('Decision package is stale')));
});

test('DecisionPackageUI & PackageApprovalRecordUI: validates complete contract structure', () => {
  assert.equal(BASE_PACKAGE.packageId, 'pkg_asset_101');
  assert.equal(BASE_PACKAGE.version, 1);
  assert.equal(BASE_PACKAGE.canonicalDigest.length, 64);
  assert.equal(BASE_PACKAGE.primaryApproval?.conflictAttestation, true);
  assert.equal(BASE_PACKAGE.primaryApproval?.isPrimaryOrSecondary, 'primary');
  assert.ok(BASE_PACKAGE.primaryApproval?.ledgerEventId.startsWith('ledger_evt_'));
});
