/**
 * Ingestion Module Test Suite
 * Automated tests for GCS target path validation, file size formatting, and status badge styles.
 * Authored strictly under Google AntiGravity architectural guidelines.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  validateGcsTargetPath,
  formatFileSize,
  getStatusBadgeStyle,
} from '../app/components/ingestion/ingestion_utils';

test('validateGcsTargetPath: accepts compliant canonical locked milestone paths', () => {
  const canonical = 'organizations/org_warner/productions/prod_batman/locked/screenplay_v8.pdf';
  const result = validateGcsTargetPath(canonical);
  assert.equal(result.isValid, true);
  assert.equal(result.orgId, 'org_warner');
  assert.equal(result.prodId, 'prod_batman');
  assert.equal(result.filename, 'screenplay_v8.pdf');
  assert.equal(result.error, undefined);

  // Leading slash and gs:// scheme normalization
  const withLeadingSlash = validateGcsTargetPath(`/${canonical}`);
  assert.equal(withLeadingSlash.isValid, true);
  assert.equal(withLeadingSlash.orgId, 'org_warner');

  const withGsUri = validateGcsTargetPath(`gs://intake-bucket/${canonical}`);
  assert.equal(withGsUri.isValid, true);
  assert.equal(withGsUri.orgId, 'org_warner');
});

test('validateGcsTargetPath: rejects non-locked subdirectories (sandbox, drafts, temp)', () => {
  const base = 'organizations/org_disney/productions/prod_lion';

  const sandbox = validateGcsTargetPath(`${base}/sandbox/screenplay.pdf`);
  assert.equal(sandbox.isValid, false);
  assert.match(sandbox.error ?? '', /\/locked\//i);

  const drafts = validateGcsTargetPath(`${base}/drafts/screenplay.pdf`);
  assert.equal(drafts.isValid, false);
  assert.match(drafts.error ?? '', /\/locked\//i);

  const temp = validateGcsTargetPath(`${base}/temp/screenplay.pdf`);
  assert.equal(temp.isValid, false);
  assert.match(temp.error ?? '', /\/locked\//i);
});

test('validateGcsTargetPath: rejects non-PDF file extensions', () => {
  const base = 'organizations/org_paramount/productions/prod_trek/locked';

  const docx = validateGcsTargetPath(`${base}/screenplay.docx`);
  assert.equal(docx.isValid, false);
  assert.match(docx.error ?? '', /Only PDF documents/i);

  const txt = validateGcsTargetPath(`${base}/screenplay.txt`);
  assert.equal(txt.isValid, false);
  assert.match(txt.error ?? '', /Only PDF documents/i);

  const fdx = validateGcsTargetPath(`${base}/screenplay.fdx`);
  assert.equal(fdx.isValid, false);
  assert.match(fdx.error ?? '', /Only PDF documents/i);
});

test('validateGcsTargetPath: rejects directory traversal attacks', () => {
  const traversal1 = validateGcsTargetPath(
    'organizations/org_sony/productions/prod_spider/locked/../../etc/passwd'
  );
  assert.equal(traversal1.isValid, false);

  const traversal2 = validateGcsTargetPath(
    'organizations/org_sony/productions/../etc/passwd.pdf'
  );
  assert.equal(traversal2.isValid, false);

  const traversal3 = validateGcsTargetPath(
    'organizations/org_sony/productions/prod_spider/locked/../../../sensitive.pdf'
  );
  assert.equal(traversal3.isValid, false);
});

test('validateGcsTargetPath: rejects empty or invalid missing paths', () => {
  const empty = validateGcsTargetPath('');
  assert.equal(empty.isValid, false);
  assert.match(empty.error ?? '', /cannot be empty/i);

  const whitespace = validateGcsTargetPath('   ');
  assert.equal(whitespace.isValid, false);
  assert.match(whitespace.error ?? '', /cannot be empty/i);
});

test('formatFileSize: formats zero and negative bytes correctly', () => {
  assert.equal(formatFileSize(0), '0 B');
  assert.equal(formatFileSize(-1), '0 B');
  assert.equal(formatFileSize(-1048576), '0 B');
  assert.equal(formatFileSize(NaN), '0 B');
});

test('formatFileSize: formats sub-kilobyte byte counts', () => {
  assert.equal(formatFileSize(1), '1 B');
  assert.equal(formatFileSize(512), '512 B');
  assert.equal(formatFileSize(1023), '1023 B');
});

test('formatFileSize: formats KB, MB, and GB ranges with proper precision', () => {
  // Kilobytes
  assert.equal(formatFileSize(1024), '1 KB');
  assert.equal(formatFileSize(520 * 1024), '520 KB');
  assert.equal(formatFileSize(1536), '1.5 KB');

  // Megabytes
  assert.equal(formatFileSize(1024 * 1024), '1 MB');
  assert.equal(formatFileSize(1.4 * 1024 * 1024), '1.4 MB');
  assert.equal(formatFileSize(50 * 1024 * 1024), '50 MB');

  // Gigabytes
  assert.equal(formatFileSize(1024 * 1024 * 1024), '1.00 GB');
  assert.equal(formatFileSize(2.5 * 1024 * 1024 * 1024), '2.50 GB');
});

test('getStatusBadgeStyle: returns expected styling for known statuses', () => {
  const queued = getStatusBadgeStyle('QUEUED');
  assert.equal(queued.label, 'QUEUED');
  assert.match(queued.bg, /amber/);
  assert.match(queued.text, /amber/);

  const processing = getStatusBadgeStyle('PROCESSING');
  assert.equal(processing.label, 'PROCESSING');
  assert.match(processing.bg, /sky/);

  const completed = getStatusBadgeStyle('COMPLETED');
  assert.equal(completed.label, 'COMPLETED');
  assert.match(completed.bg, /emerald/);

  const rejected = getStatusBadgeStyle('REJECTED_OUT_OF_SCOPE');
  assert.equal(rejected.label, 'REJECTED_OUT_OF_SCOPE');
  assert.match(rejected.bg, /rose/);

  const failed = getStatusBadgeStyle('FAILED');
  assert.equal(failed.label, 'FAILED');
  assert.match(failed.bg, /rose/);
});

test('getStatusBadgeStyle: handles case-insensitivity and fallback for unknown status', () => {
  const lowerProcessing = getStatusBadgeStyle('processing');
  assert.equal(lowerProcessing.label, 'PROCESSING');
  assert.match(lowerProcessing.bg, /sky/);

  const unknown = getStatusBadgeStyle('CUSTOM_UNRECOGNIZED_STATUS');
  assert.equal(unknown.label, 'CUSTOM_UNRECOGNIZED_STATUS');
  assert.match(unknown.bg, /slate/);

  const emptyStatus = getStatusBadgeStyle('');
  assert.equal(emptyStatus.label, 'UNKNOWN');
  assert.match(emptyStatus.bg, /slate/);
});
