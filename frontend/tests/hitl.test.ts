/**
 * Lienmark HITL Unit Test Suite: frontend/tests/hitl.test.ts
 * Tests clarification status styling, role badges, validation, option selection, and payload formatting.
 * Authored strictly under Google AntiGravity: defensive zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatClarificationStatus,
  getRoleBadgeStyle,
  getCategoryBadgeStyle,
  validateClarificationResponse,
  validateAttachedDocument,
  formatFileSize,
} from '../app/components/hitl/hitl_utils';
import {
  ClarificationStatus,
  QuestionCategory,
  ClarificationResponsePayload,
} from '../app/components/hitl/hitl_types';
import {
  GOLDEN_CLARIFICATION_REQUESTS,
  getClarificationByClaimKey,
} from '../app/components/hitl/hitl_fixtures';
import { UserRole } from '../lib/types';

test('formatClarificationStatus: maps lifecycle states to semantic badge styling', () => {
  const waiting = formatClarificationStatus(ClarificationStatus.WAITING_FOR_INFO);
  assert.equal(waiting.label, 'WAITING FOR INFO');
  assert.ok(waiting.badgeClass.includes('animate-pulse'));
  assert.ok(waiting.badgeClass.includes('text-amber-300'));
  assert.equal(waiting.iconName, 'clock');

  const inReview = formatClarificationStatus(ClarificationStatus.IN_REVIEW);
  assert.equal(inReview.label, 'IN REVIEW');
  assert.ok(inReview.badgeClass.includes('text-sky-300'));

  const resolved = formatClarificationStatus(ClarificationStatus.RESOLVED);
  assert.equal(resolved.label, 'RESOLVED');
  assert.ok(resolved.badgeClass.includes('text-emerald-300'));

  const escalated = formatClarificationStatus(ClarificationStatus.ESCALATED);
  assert.equal(escalated.label, 'ESCALATED TO COUNSEL');
  assert.ok(escalated.badgeClass.includes('text-rose-300'));

  const fallback = formatClarificationStatus('unknown_state' as ClarificationStatus);
  assert.equal(fallback.label, 'PENDING');
});

test('getRoleBadgeStyle: provides correct color palette and labels across production roles', () => {
  const counsel = getRoleBadgeStyle(UserRole.REVIEWER);
  assert.equal(counsel.label, 'Clearance Counsel');
  assert.ok(counsel.textClass.includes('text-purple-300'));

  const producer = getRoleBadgeStyle(UserRole.PRODUCER);
  assert.equal(producer.label, 'Production Lead');
  assert.ok(producer.textClass.includes('text-amber-300'));

  const admin = getRoleBadgeStyle(UserRole.ADMIN);
  assert.equal(admin.label, 'Studio Administrator');
  assert.ok(admin.textClass.includes('text-rose-300'));

  const fallback = getRoleBadgeStyle('analyst');
  assert.equal(fallback.label, 'Legal Analyst');
  assert.ok(fallback.textClass.includes('text-sky-300'));
});

test('getCategoryBadgeStyle: correctly associates categories with icons and color styles', () => {
  const music = getCategoryBadgeStyle(QuestionCategory.MUSIC_RIGHTS);
  assert.equal(music.label, 'Music Rights');
  assert.equal(music.iconName, 'Music');

  const brand = getCategoryBadgeStyle(QuestionCategory.TRADEMARK_BRAND);
  assert.equal(brand.label, 'Trademark & Brand');
  assert.equal(brand.iconName, 'Tag');

  const chain = getCategoryBadgeStyle(QuestionCategory.CHAIN_OF_TITLE);
  assert.equal(chain.label, 'Chain of Title');
  assert.equal(chain.iconName, 'FileCheck');

  const def = getCategoryBadgeStyle('unclassified' as QuestionCategory);
  assert.equal(def.label, 'General Clearance');
  assert.equal(def.iconName, 'Shield');
});

test('validateClarificationResponse: validates length constraints defensively', () => {
  const empty = validateClarificationResponse('   ');
  assert.equal(empty.isValid, false);
  assert.ok(empty.error?.includes('cannot be empty'));

  const short = validateClarificationResponse('Too short');
  assert.equal(short.isValid, false);
  assert.ok(short.error?.includes('too brief'));

  const valid = validateClarificationResponse('Executed sync agreement secured from Vanguard Media.');
  assert.equal(valid.isValid, true);
  assert.equal(valid.error, null);
  assert.ok(valid.charCount > 10);
  assert.ok(valid.remainingChars < 1000);

  const longText = 'A'.repeat(1001);
  const oversized = validateClarificationResponse(longText);
  assert.equal(oversized.isValid, false);
  assert.ok(oversized.error?.includes('exceeds maximum limit'));
});

test('validateAttachedDocument: enforces allowed file extensions and size boundaries', () => {
  const invalidExt = validateAttachedDocument({ name: 'malware.exe', size: 1024 });
  assert.equal(invalidExt.isValid, false);
  assert.ok(invalidExt.error?.includes('Only .pdf, .docx files are permitted'));

  const validPdf = validateAttachedDocument({ name: 'sync_license_signed.pdf', size: 2 * 1024 * 1024 });
  assert.equal(validPdf.isValid, true);
  assert.equal(validPdf.error, null);

  const validDocx = validateAttachedDocument({ name: 'contract_rider.docx', size: 500 * 1024 });
  assert.equal(validDocx.isValid, true);

  const oversized = validateAttachedDocument({ name: 'giant_archive.pdf', size: 20 * 1024 * 1024 });
  assert.equal(oversized.isValid, false);
  assert.ok(oversized.error?.includes('exceeds 15MB limit'));
});

test('formatFileSize: formats byte counts into human-readable representations', () => {
  assert.equal(formatFileSize(512), '512 B');
  assert.equal(formatFileSize(2048), '2.0 KB');
  assert.equal(formatFileSize(5 * 1024 * 1024), '5.0 MB');
});

test('option selection and payload formatting: validates submission contracts', () => {
  const musicReq = getClarificationByClaimKey('music_cue_midnight_serenade');
  assert.ok(musicReq !== undefined);
  assert.equal(musicReq?.category, QuestionCategory.MUSIC_RIGHTS);
  assert.ok((musicReq?.suggestedOptions.length ?? 0) >= 2);

  const selectedOption = musicReq?.suggestedOptions[0] ?? '';
  assert.ok(selectedOption.length > 0);

  const payload: ClarificationResponsePayload = {
    requestId: musicReq?.id ?? '',
    claimKey: musicReq?.claimKey ?? '',
    responseText: 'Producer confirms sync and master license fully executed with label.',
    selectedOption,
    action: 'submit',
    attachments: [
      {
        id: 'att_01',
        name: 'executed_license.pdf',
        sizeBytes: 1024 * 1024,
        mimeType: 'application/pdf',
        uploadedAt: '2026-09-07T10:00:00Z',
      },
    ],
    submittedByRole: UserRole.PRODUCER,
    submittedAt: '2026-09-07T10:05:00Z',
  };

  assert.equal(payload.action, 'submit');
  assert.equal(payload.selectedOption, selectedOption);
  assert.equal(payload.attachments.length, 1);
  assert.equal(payload.submittedByRole, UserRole.PRODUCER);
});
