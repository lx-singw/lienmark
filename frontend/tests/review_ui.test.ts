/**
 * Lienmark Counsel Review UI Unit Test Suite: frontend/tests/review_ui.test.ts
 * Tests modal validation, citation suggestions, directive shortcuts,
 * attempt lineage formatting, and payload validation (Sprint 4.3).
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatCounselAction,
  formatAttemptBadge,
  formatReviewTimestamp,
  validateDirectiveText,
  validateDecisionPayload,
  getCitationByCategory,
  DIRECTIVE_SHORTCUTS,
  DEFAULT_CITATION_TEMPLATES,
} from '../app/components/review/review_utils';
import {
  CounselActionType,
  DecisionPayload,
  AttemptLineageItem,
  CitationTemplateUI,
} from '../app/components/review/review_types';

test('formatCounselAction: maps sign_off and reject to cinematic semantic styling', () => {
  const signOff = formatCounselAction('sign_off');
  assert.equal(signOff.label, 'Sign-off / Clear Claim');
  assert.ok(signOff.badgeClass.includes('text-emerald-300'));
  assert.ok(signOff.borderClass.includes('border-emerald-500'));

  const reject = formatCounselAction('reject');
  assert.equal(reject.label, 'Reject & Direct Re-investigation');
  assert.ok(reject.badgeClass.includes('text-rose-300'));
  assert.ok(reject.borderClass.includes('border-rose-500'));
});

test('DIRECTIVE_SHORTCUTS: contains all required standard clearance directives', () => {
  const shortcutTexts = DIRECTIVE_SHORTCUTS.map((s) => s.text);
  assert.ok(shortcutTexts.includes('Check master recording owner'));
  assert.ok(shortcutTexts.includes('Verify foreign distribution holdback'));
  assert.ok(shortcutTexts.includes('Re-search ASCAP for 1972 live adaptation'));

  // Ensure unique IDs
  const ids = DIRECTIVE_SHORTCUTS.map((s) => s.id);
  const uniqueIds = new Set(ids);
  assert.equal(ids.length, uniqueIds.size);
});

test('DEFAULT_CITATION_TEMPLATES: provides statutory citations across categories', () => {
  assert.ok(DEFAULT_CITATION_TEMPLATES.length >= 4);

  const fairUse = DEFAULT_CITATION_TEMPLATES.find((t) => t.id === 'fair_use_107');
  assert.ok(fairUse !== undefined);
  assert.equal(fairUse?.statute, '17 U.S.C. § 107');
  assert.ok(fairUse?.text.includes('transformative commentary'));

  const syncMaster = DEFAULT_CITATION_TEMPLATES.find((t) => t.id === 'sync_master_clause_4a');
  assert.ok(syncMaster !== undefined);
  assert.ok(syncMaster?.text.includes('Clause 4(a) Audiovisual Synchronization'));

  // Category filtering
  const musicCitations = getCitationByCategory('Music Rights');
  assert.ok(musicCitations.length > 0);
  assert.ok(musicCitations.every((c) => c.category === 'Music Rights'));

  const allCitations = getCitationByCategory('All');
  assert.equal(allCitations.length, DEFAULT_CITATION_TEMPLATES.length);
});

test('validateDirectiveText: enforces length constraints and rejection directive requirement', () => {
  const emptyReject = validateDirectiveText('   ', 'reject');
  assert.equal(emptyReject.isValid, false);
  assert.ok(emptyReject.errors[0]?.includes('requires a specific investigative directive'));

  const shortReject = validateDirectiveText('Check it', 'reject');
  assert.equal(shortReject.isValid, false);
  assert.ok(shortReject.errors[0]?.includes('too brief'));

  const validReject = validateDirectiveText('Re-search ASCAP for 1972 live adaptation record', 'reject');
  assert.equal(validReject.isValid, true);
  assert.equal(validReject.errors.length, 0);
  assert.ok((validReject.charCount ?? 0) > 10);
  assert.ok((validReject.remainingChars ?? 0) < 1000);

  // Sign-off allows empty directive
  const emptySignOff = validateDirectiveText('', 'sign_off');
  assert.equal(emptySignOff.isValid, true);

  const oversized = validateDirectiveText('X'.repeat(1005), 'reject');
  assert.equal(oversized.isValid, false);
  assert.ok(oversized.errors[0]?.includes('exceeds maximum limit'));
});

test('validateDecisionPayload: validates dual-action decision submission contracts', () => {
  // 1. Valid Sign-off
  const validSignOff: DecisionPayload = {
    action: 'sign_off',
    counselId: 'counsel_sarah_jenkins',
    counselName: 'Sarah Jenkins, Esq.',
    directiveText: '',
    citationText: '17 U.S.C. § 107 Fair Use 4-factor statutory defense confirmed.',
    conditions: 'Limited to North American theatrical cut.',
  };
  const signOffValidation = validateDecisionPayload(validSignOff);
  assert.equal(signOffValidation.isValid, true);
  assert.equal(signOffValidation.errors.length, 0);

  // 2. Sign-off missing citation fails
  const missingCitation = validateDecisionPayload({
    ...validSignOff,
    citationText: '   ',
  });
  assert.equal(missingCitation.isValid, false);
  assert.ok(missingCitation.errors.some((e) => e.includes('Legal citation')));

  // 3. Valid Rejection
  const validReject: DecisionPayload = {
    action: 'reject',
    counselId: 'counsel_sarah_jenkins',
    counselName: 'Sarah Jenkins, Esq.',
    directiveText: 'Verify foreign distribution holdback with label representatives.',
    citationText: '',
  };
  const rejectValidation = validateDecisionPayload(validReject);
  assert.equal(rejectValidation.isValid, true);

  // 4. Rejection missing directive fails
  const missingDirective = validateDecisionPayload({
    ...validReject,
    directiveText: '',
  });
  assert.equal(missingDirective.isValid, false);
  assert.ok(missingDirective.errors.some((e) => e.includes('investigative directive')));

  // 5. Missing counsel name / ID fails
  const missingCounsel = validateDecisionPayload({
    ...validReject,
    counselName: '',
  });
  assert.equal(missingCounsel.isValid, false);
  assert.ok(missingCounsel.errors.some((e) => e.includes('reviewer name is required')));
});

test('formatAttemptBadge & formatReviewTimestamp: formats attempt lineage details', () => {
  const attempt1 = formatAttemptBadge(1, 'reject');
  assert.equal(attempt1.label, 'Attempt 1: Rejected');
  assert.ok(attempt1.badgeClass.includes('text-rose-300'));

  const attempt2 = formatAttemptBadge(2, 'investigating');
  assert.equal(attempt2.label, 'Attempt 2: Active Re-investigation');
  assert.ok(attempt2.badgeClass.includes('text-amber-300'));
  assert.ok(attempt2.badgeClass.includes('animate-pulse'));

  const cleared = formatAttemptBadge(2, 'sign_off');
  assert.equal(cleared.label, 'Attempt 2: Cleared');
  assert.ok(cleared.badgeClass.includes('text-emerald-300'));

  const formattedTime = formatReviewTimestamp('2026-09-07T10:30:00.000Z');
  assert.ok(formattedTime.length > 0);
  assert.notEqual(formattedTime, 'Pending');
});

test('AttemptLineageItem comparison: simulates Attempt 1 Rejected -> Attempt 2 Active Re-investigation', () => {
  const lineage: ReadonlyArray<AttemptLineageItem> = [
    {
      attemptNumber: 1,
      action: 'reject',
      counselName: 'Sarah Jenkins, Esq.',
      directiveText: 'Re-search ASCAP for 1972 live adaptation rights holder',
      timestamp: '2026-09-07T09:00:00Z',
      finding: 'Direct license unverified; missing mechanical rights.',
      status: 'rejected',
    },
    {
      attemptNumber: 2,
      action: 'investigating',
      counselName: 'Sarah Jenkins, Esq.',
      directiveText: 'Parallel Search agent query in progress across ASCAP live registry',
      timestamp: '2026-09-07T10:15:00Z',
      finding: 'Pending Parallel Search API response',
      evidenceSummary: 'Queried ASCAP Work ID #849201; analyzing Vanguard catalog acquisition.',
      status: 'in_progress',
    },
  ];

  assert.equal(lineage.length, 2);
  assert.equal(lineage[0].attemptNumber, 1);
  assert.equal(lineage[0].action, 'reject');
  assert.ok(lineage[0].directiveText.includes('ASCAP for 1972 live adaptation'));

  assert.equal(lineage[1].attemptNumber, 2);
  assert.equal(lineage[1].action, 'investigating');
  assert.ok(lineage[1].evidenceSummary?.includes('ASCAP Work ID'));
});
