/**
 * frontend/tests/dedup.test.ts
 *
 * Automated unit test suite for frontend deduplication utilities and format badge mappings.
 * Sprint 2.2: Content Digesting, Deduplication & Rename Invariance.
 * Enforces file <= 250 lines and function <= 40 lines strictly.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatCacheHitSavings,
  getFormatBadgeStyle,
} from '../app/components/dedup/dedup_utils';

test('formatCacheHitSavings: formats exact zero spend and claim counts', () => {
  const output = formatCacheHitSavings(0, 14, 42);
  assert.equal(
    output,
    'Incurred $0.00 API spend; loaded 14 existing claims in 42ms.'
  );

  const zeroClaims = formatCacheHitSavings(0, 0, 15);
  assert.equal(
    zeroClaims,
    'Incurred $0.00 API spend; loaded 0 existing claims in 15ms.'
  );
});

test('formatCacheHitSavings: handles singular vs plural claim noun forms', () => {
  const singular = formatCacheHitSavings(0, 1, 38);
  assert.equal(
    singular,
    'Incurred $0.00 API spend; loaded 1 existing claim in 38ms.'
  );

  const plural = formatCacheHitSavings(0, 2, 50);
  assert.equal(
    plural,
    'Incurred $0.00 API spend; loaded 2 existing claims in 50ms.'
  );
});

test('formatCacheHitSavings: formats non-zero financial savings and rounding', () => {
  const nonZero = formatCacheHitSavings(12.5, 45, 99.4);
  assert.equal(
    nonZero,
    'Incurred $12.50 API spend; loaded 45 existing claims in 99ms.'
  );

  const fractionalClaims = formatCacheHitSavings(3.999, 10.8, 12.3);
  assert.equal(
    fractionalClaims,
    'Incurred $4.00 API spend; loaded 10 existing claims in 12ms.'
  );
});

test('formatCacheHitSavings: defensive handling of negative and NaN parameters', () => {
  const negative = formatCacheHitSavings(-5, -2, -10);
  assert.equal(
    negative,
    'Incurred $0.00 API spend; loaded 0 existing claims in 0ms.'
  );

  const nanValues = formatCacheHitSavings(Number.NaN, Number.NaN, Number.NaN);
  assert.equal(
    nanValues,
    'Incurred $0.00 API spend; loaded 0 existing claims in 0ms.'
  );
});

test('getFormatBadgeStyle: validates PDF badge styling and labels', () => {
  const pdfStyle = getFormatBadgeStyle('pdf');
  assert.equal(pdfStyle.label, 'PDF');
  assert.equal(pdfStyle.iconName, 'FileText');
  assert.equal(pdfStyle.bg, 'bg-rose-950/60');
  assert.equal(pdfStyle.text, 'text-rose-300');
  assert.equal(pdfStyle.border, 'border-rose-500/40');
});

test('getFormatBadgeStyle: validates Final Draft FDX badge styling and labels', () => {
  const fdxStyle = getFormatBadgeStyle('fdx');
  assert.equal(fdxStyle.label, 'FINAL DRAFT (FDX)');
  assert.equal(fdxStyle.iconName, 'FileCode');
  assert.equal(fdxStyle.bg, 'bg-sky-950/60');
  assert.equal(fdxStyle.text, 'text-sky-300');
  assert.equal(fdxStyle.border, 'border-sky-500/40');
});

test('getFormatBadgeStyle: validates Fountain badge styling and labels', () => {
  const fountainStyle = getFormatBadgeStyle('fountain');
  assert.equal(fountainStyle.label, 'FOUNTAIN');
  assert.equal(fountainStyle.iconName, 'PenTool');
  assert.equal(fountainStyle.bg, 'bg-emerald-950/60');
  assert.equal(fountainStyle.text, 'text-emerald-300');
  assert.equal(fountainStyle.border, 'border-emerald-500/40');
});

test('getFormatBadgeStyle: validates CMX 3600 EDL badge styling and labels', () => {
  const edlStyle = getFormatBadgeStyle('edl');
  assert.equal(edlStyle.label, 'CMX 3600 EDL');
  assert.equal(edlStyle.iconName, 'Film');
  assert.equal(edlStyle.bg, 'bg-amber-950/60');
  assert.equal(edlStyle.text, 'text-amber-300');
  assert.equal(edlStyle.border, 'border-amber-500/40');
});

test('getFormatBadgeStyle: handles case-insensitivity, trim, and fallback defaults', () => {
  const upperCase = getFormatBadgeStyle('  PDF  ');
  assert.equal(upperCase.label, 'PDF');

  const mixedCase = getFormatBadgeStyle('Fountain');
  assert.equal(mixedCase.label, 'FOUNTAIN');

  const unknown = getFormatBadgeStyle('unknown_format');
  assert.equal(unknown.label, 'UNKNOWN FORMAT');
  assert.equal(unknown.iconName, 'FileQuestion');
  assert.equal(unknown.bg, 'bg-zinc-800/80');

  const empty = getFormatBadgeStyle('');
  assert.equal(empty.label, 'UNKNOWN FORMAT');
});
