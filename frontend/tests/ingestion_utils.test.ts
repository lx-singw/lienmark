/**
 * Ingestion Utilities Test Suite
 * Validates GCS path regex, canonical path verification, file size formatting, and status badge styling.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  LOCKED_FOLDER_REGEX,
  validateGcsTargetPath,
  formatFileSize,
  getStatusBadgeStyle,
  buildGcsUri,
  MAX_FILE_SIZE_BYTES,
  DEFAULT_INTAKE_BUCKET,
} from '../app/components/ingestion/ingestion_utils';

test('LOCKED_FOLDER_REGEX matches strictly canonical locked milestone paths', () => {
  const validPath =
    'organizations/studio-alpha/productions/prod-001/locked/Shadows_Broadway_v8.pdf';
  assert.equal(LOCKED_FOLDER_REGEX.test(validPath), true);

  const match = LOCKED_FOLDER_REGEX.exec(validPath);
  assert.ok(match);
  assert.equal(match[1], 'studio-alpha');
  assert.equal(match[2], 'prod-001');
  assert.equal(match[3], 'Shadows_Broadway_v8.pdf');

  // Negative tests
  assert.equal(
    LOCKED_FOLDER_REGEX.test(
      'organizations/studio-alpha/productions/prod-001/drafts/Shadows_Broadway_v8.pdf'
    ),
    false
  );
  assert.equal(
    LOCKED_FOLDER_REGEX.test(
      'organizations/studio-alpha/productions/prod-001/locked/script.docx'
    ),
    false
  );
  assert.equal(
    LOCKED_FOLDER_REGEX.test(
      'organizations/studio@alpha/productions/prod-001/locked/script.pdf'
    ),
    false
  );
});

test('validateGcsTargetPath parses relative, leading-slash, and gs:// paths', () => {
  // Canonical relative path
  const res1 = validateGcsTargetPath(
    'organizations/org-warner/productions/prod-matrix/locked/script_final.pdf'
  );
  assert.equal(res1.isValid, true);
  assert.equal(res1.orgId, 'org-warner');
  assert.equal(res1.prodId, 'prod-matrix');
  assert.equal(res1.filename, 'script_final.pdf');

  // Path with leading slash
  const res2 = validateGcsTargetPath(
    '/organizations/org-warner/productions/prod-matrix/locked/script_final.pdf'
  );
  assert.equal(res2.isValid, true);
  assert.equal(res2.orgId, 'org-warner');

  // Full gs:// URI scheme
  const res3 = validateGcsTargetPath(
    'gs://lienmark-intake-vault/organizations/org-paramount/productions/prod-topgun/locked/draft_locked.pdf'
  );
  assert.equal(res3.isValid, true);
  assert.equal(res3.orgId, 'org-paramount');
  assert.equal(res3.prodId, 'prod-topgun');
  assert.equal(res3.filename, 'draft_locked.pdf');
});

test('validateGcsTargetPath returns specific diagnostic errors for invalid inputs', () => {
  // Empty
  assert.equal(validateGcsTargetPath('').isValid, false);
  assert.match(validateGcsTargetPath('').error ?? '', /cannot be empty/i);

  // Non-PDF
  const nonPdf = validateGcsTargetPath(
    'organizations/org-1/productions/prod-1/locked/draft.docx'
  );
  assert.equal(nonPdf.isValid, false);
  assert.match(nonPdf.error ?? '', /Only PDF/i);

  // Wrong directory (not /locked/)
  const wrongFolder = validateGcsTargetPath(
    'organizations/org-1/productions/prod-1/temp/draft.pdf'
  );
  assert.equal(wrongFolder.isValid, false);
  assert.match(wrongFolder.error ?? '', /\/locked\//i);

  // Missing org segment
  const missingOrg = validateGcsTargetPath(
    'studios/org-1/productions/prod-1/locked/draft.pdf'
  );
  assert.equal(missingOrg.isValid, false);
  assert.match(missingOrg.error ?? '', /organizations/i);
});

test('formatFileSize converts byte counts into human-readable strings', () => {
  assert.equal(formatFileSize(0), '0 B');
  assert.equal(formatFileSize(-100), '0 B');
  assert.equal(formatFileSize(500), '500 B');
  assert.equal(formatFileSize(1024), '1 KB');
  assert.equal(formatFileSize(520 * 1024), '520 KB');
  assert.equal(formatFileSize(1.4 * 1024 * 1024), '1.4 MB');
  assert.equal(formatFileSize(MAX_FILE_SIZE_BYTES), '50 MB');
  assert.equal(formatFileSize(1024 * 1024 * 1024), '1.00 GB');
});

test('getStatusBadgeStyle maps known and unknown ingestion statuses correctly', () => {
  const queued = getStatusBadgeStyle('QUEUED');
  assert.equal(queued.label, 'QUEUED');
  assert.match(queued.bg, /amber/);

  const processing = getStatusBadgeStyle('processing');
  assert.equal(processing.label, 'PROCESSING');
  assert.match(processing.bg, /sky/);

  const completed = getStatusBadgeStyle('COMPLETED');
  assert.equal(completed.label, 'COMPLETED');
  assert.match(completed.bg, /emerald/);

  const rejected = getStatusBadgeStyle('REJECTED_OUT_OF_SCOPE');
  assert.equal(rejected.label, 'REJECTED_OUT_OF_SCOPE');
  assert.match(rejected.bg, /rose/);

  const fallback = getStatusBadgeStyle('CUSTOM_STAGE');
  assert.equal(fallback.label, 'CUSTOM_STAGE');
  assert.match(fallback.bg, /slate/);
});

test('buildGcsUri constructs standardized target URIs', () => {
  const uri = buildGcsUri(
    DEFAULT_INTAKE_BUCKET,
    'studio-alpha',
    'prod-001',
    'script_locked.pdf'
  );
  assert.equal(
    uri,
    'gs://lienmark-intake-storage/organizations/studio-alpha/productions/prod-001/locked/script_locked.pdf'
  );

  // Fallback defaults when values are empty/whitespace
  const fallbackUri = buildGcsUri('', '', '', '');
  assert.equal(
    fallbackUri,
    'gs://lienmark-intake-storage/organizations/{orgId}/productions/{prodId}/locked/{filename}.pdf'
  );
});

test('getStatusBadgeStyle handles FAILED and EVALUATING statuses', () => {
  const failed = getStatusBadgeStyle('FAILED');
  assert.equal(failed.label, 'FAILED');
  assert.match(failed.bg, /rose/);

  const evaluating = getStatusBadgeStyle('EVALUATING');
  assert.equal(evaluating.label, 'PROCESSING');
  assert.match(evaluating.bg, /sky/);
});

