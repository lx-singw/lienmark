/**
 * Lienmark HITL Resumption UI Test Suite: frontend/tests/resumption_ui.test.ts
 * Tests unblocked notifications, stepper stage calculations, badge transition formatters,
 * and session state progression.
 * Authored strictly under Google AntiGravity: defensive zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatConfidencePercent,
  getResumptionBadgeTheme,
  getStepStatusClasses,
  createDefaultResumptionSteps,
  formatUnblockedNotification,
  GOLDEN_AGREEMENT_MATCH,
  GOLDEN_RESUMPTION_SESSION,
} from '../app/components/hitl/resumption_utils';
import {
  ClaimResumptionStatus,
  ResumptionStepId,
} from '../app/components/hitl/resumption_types';

test('formatConfidencePercent: clamps and formats percentage strings accurately', () => {
  assert.equal(formatConfidencePercent(0.94), '94%');
  assert.equal(formatConfidencePercent(0.85), '85%');
  assert.equal(formatConfidencePercent(1.0), '100%');
  assert.equal(formatConfidencePercent(0.0), '0%');
  assert.equal(formatConfidencePercent(1.25), '100%');
  assert.equal(formatConfidencePercent(-0.15), '0%');
});

test('getResumptionBadgeTheme: maps WAITING_FOR_INFO state to amber pulsing theme', () => {
  const waiting = getResumptionBadgeTheme(ClaimResumptionStatus.WAITING_FOR_INFO);
  assert.equal(waiting.label, '[WAITING FOR INFO]');
  assert.ok(waiting.badgeClass.includes('text-amber-200'));
  assert.ok(waiting.badgeClass.includes('animate-pulse'));
  assert.equal(waiting.iconName, 'help');
});

test('getResumptionBadgeTheme: maps AGREEMENT_MATCHED to emerald pulsing glow', () => {
  const matched = getResumptionBadgeTheme(ClaimResumptionStatus.AGREEMENT_MATCHED);
  assert.equal(matched.label, '[AGREEMENT MATCHED]');
  assert.ok(matched.badgeClass.includes('text-emerald-200'));
  assert.ok(matched.badgeClass.includes('animate-pulse'));
  assert.equal(matched.iconName, 'match');
});

test('getResumptionBadgeTheme: maps READY_FOR_REVIEW to teal shield theme', () => {
  const ready = getResumptionBadgeTheme(ClaimResumptionStatus.READY_FOR_REVIEW);
  assert.equal(ready.label, '[READY FOR REVIEW]');
  assert.ok(ready.badgeClass.includes('text-teal-200'));
  assert.equal(ready.iconName, 'shield');
});

test('getResumptionBadgeTheme: fallback provides waiting for info defaults', () => {
  const fallback = getResumptionBadgeTheme('unknown_status' as any);
  assert.equal(fallback.label, '[WAITING FOR INFO]');
  assert.equal(fallback.iconName, 'help');
});

test('getStepStatusClasses: provides distinct styling for all lifecycle step states', () => {
  const completed = getStepStatusClasses('completed');
  assert.ok(completed.containerClass.includes('border-emerald-500'));
  assert.ok(completed.iconClass.includes('text-emerald-400'));

  const inProgress = getStepStatusClasses('in_progress');
  assert.ok(inProgress.containerClass.includes('ring-emerald-500'));
  assert.ok(inProgress.iconClass.includes('animate-spin'));

  const failed = getStepStatusClasses('failed');
  assert.ok(failed.containerClass.includes('border-rose-500'));
  assert.ok(failed.iconClass.includes('text-rose-400'));

  const pending = getStepStatusClasses('pending');
  assert.ok(pending.containerClass.includes('border-slate-800'));
  assert.ok(pending.iconClass.includes('text-slate-500'));
});

test('createDefaultResumptionSteps: computes active step status progression across 4 stages', () => {
  const step1Active = createDefaultResumptionSteps('autonomous', 1);
  assert.equal(step1Active.length, 4);
  assert.equal(step1Active[0].status, 'in_progress');
  assert.equal(step1Active[1].status, 'pending');
  assert.equal(step1Active[2].status, 'pending');
  assert.equal(step1Active[3].status, 'pending');

  const step3Active = createDefaultResumptionSteps('autonomous', 3);
  assert.equal(step3Active[0].status, 'completed');
  assert.equal(step3Active[1].status, 'completed');
  assert.equal(step3Active[2].status, 'in_progress');
  assert.equal(step3Active[3].status, 'pending');

  const step4Active = createDefaultResumptionSteps('autonomous', 4);
  assert.ok(step4Active.every((s) => s.status === 'completed'));
});

test('createDefaultResumptionSteps: differentiates autonomous vs manual resolution subtitles', () => {
  const autoSteps = createDefaultResumptionSteps('autonomous', 2);
  assert.ok(autoSteps[0].subtitle.includes('Autonomous: Sync agreement matched'));

  const manualSteps = createDefaultResumptionSteps('manual', 2);
  assert.ok(manualSteps[0].subtitle.includes('Manual: Production counsel attestation'));
});

test('formatUnblockedNotification: formats live upload alerts with cue context', () => {
  const simple = formatUnblockedNotification('sync_license_441.pdf');
  assert.equal(simple, 'Unblocked via Agreement Upload: sync_license_441.pdf');

  const withCue = formatUnblockedNotification('mock_sync_license.pdf', 'Diner Jazz Solo Cue');
  assert.equal(
    withCue,
    "Unblocked via Agreement Upload: mock_sync_license.pdf for 'Diner Jazz Solo Cue'"
  );
});

test('golden fixtures: validates autonomous agreement match and session contracts', () => {
  assert.ok(GOLDEN_AGREEMENT_MATCH.confidence >= 0.85);
  assert.equal(GOLDEN_AGREEMENT_MATCH.verifiedDetails.signaturesVerified, true);
  assert.equal(GOLDEN_AGREEMENT_MATCH.verifiedDetails.territoryScope, 'Worldwide, All Media');
  assert.equal(GOLDEN_AGREEMENT_MATCH.verifiedDetails.termExpiry, 'In Perpetuity');

  assert.equal(GOLDEN_RESUMPTION_SESSION.currentStep, 4);
  assert.equal(GOLDEN_RESUMPTION_SESSION.isCompleted, true);
  assert.equal(GOLDEN_RESUMPTION_SESSION.steps.length, 4);
  assert.equal(GOLDEN_RESUMPTION_SESSION.steps[0].id, ResumptionStepId.CLARIFICATION_RESOLVED);
  assert.equal(GOLDEN_RESUMPTION_SESSION.steps[1].id, ResumptionStepId.CHECKPOINT_HYDRATED);
  assert.equal(GOLDEN_RESUMPTION_SESSION.steps[2].id, ResumptionStepId.AGREEMENT_VERIFIED);
  assert.equal(GOLDEN_RESUMPTION_SESSION.steps[3].id, ResumptionStepId.CLEARANCE_UPDATED);
});
