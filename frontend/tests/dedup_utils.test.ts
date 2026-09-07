/**
 * dedup_utils.test.ts
 * Unit test suite for deduplication utilities, format badge styling, and barrel exports.
 * Sprint 2.2: Content Digesting, Deduplication & Rename Invariance.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatCacheHitSavings,
  getFormatBadgeStyle,
  DedupNotificationBanner,
  DocumentFormatBadge,
} from '../app/components/dedup';

test('formatCacheHitSavings formats exact sprint specification output', () => {
  const message = formatCacheHitSavings(0, 14, 42);
  assert.equal(
    message,
    'Incurred $0.00 API spend; loaded 14 existing claims in 42ms.'
  );
});

test('formatCacheHitSavings handles singular and plural claim grammar', () => {
  const singular = formatCacheHitSavings(0, 1, 35);
  assert.equal(
    singular,
    'Incurred $0.00 API spend; loaded 1 existing claim in 35ms.'
  );

  const plural = formatCacheHitSavings(0, 5, 20);
  assert.equal(
    plural,
    'Incurred $0.00 API spend; loaded 5 existing claims in 20ms.'
  );

  const zeroClaims = formatCacheHitSavings(0, 0, 12);
  assert.equal(
    zeroClaims,
    'Incurred $0.00 API spend; loaded 0 existing claims in 12ms.'
  );
});

test('formatCacheHitSavings formats non-zero spend and latency', () => {
  const formatted = formatCacheHitSavings(1.5, 30, 85);
  assert.equal(
    formatted,
    'Incurred $1.50 API spend; loaded 30 existing claims in 85ms.'
  );
});

test('formatCacheHitSavings defends against negative and NaN inputs', () => {
  const negativeGuarded = formatCacheHitSavings(-10, -5, -40);
  assert.equal(
    negativeGuarded,
    'Incurred $0.00 API spend; loaded 0 existing claims in 0ms.'
  );

  const nanGuarded = formatCacheHitSavings(Number.NaN, Number.NaN, Number.NaN);
  assert.equal(
    nanGuarded,
    'Incurred $0.00 API spend; loaded 0 existing claims in 0ms.'
  );
});

test('getFormatBadgeStyle maps all supported screenplay formats correctly', () => {
  const pdfStyle = getFormatBadgeStyle('pdf');
  assert.equal(pdfStyle.label, 'PDF');
  assert.equal(pdfStyle.iconName, 'FileText');
  assert.match(pdfStyle.bg, /rose/);

  const fdxStyle = getFormatBadgeStyle('fdx');
  assert.equal(fdxStyle.label, 'FINAL DRAFT (FDX)');
  assert.equal(fdxStyle.iconName, 'FileCode');
  assert.match(fdxStyle.bg, /sky/);

  const fountainStyle = getFormatBadgeStyle('fountain');
  assert.equal(fountainStyle.label, 'FOUNTAIN');
  assert.equal(fountainStyle.iconName, 'PenTool');
  assert.match(fountainStyle.bg, /emerald/);

  const edlStyle = getFormatBadgeStyle('edl');
  assert.equal(edlStyle.label, 'CMX 3600 EDL');
  assert.equal(edlStyle.iconName, 'Film');
  assert.match(edlStyle.bg, /amber/);

  const plaintextStyle = getFormatBadgeStyle('plaintext');
  assert.equal(plaintextStyle.label, 'PLAIN TEXT');
  assert.equal(plaintextStyle.iconName, 'AlignLeft');
  assert.match(plaintextStyle.bg, /slate/);

  const txtStyle = getFormatBadgeStyle('txt');
  assert.equal(txtStyle.label, 'PLAIN TEXT');
  assert.equal(txtStyle.iconName, 'AlignLeft');
});

test('getFormatBadgeStyle handles case variations, whitespace, and unknown fallbacks', () => {
  const upperPdf = getFormatBadgeStyle('  PDF  ');
  assert.equal(upperPdf.label, 'PDF');

  const mixedFdx = getFormatBadgeStyle('Fdx');
  assert.equal(mixedFdx.label, 'FINAL DRAFT (FDX)');

  const unknownStyle = getFormatBadgeStyle('unsupported_binary');
  assert.equal(unknownStyle.label, 'UNKNOWN FORMAT');
  assert.equal(unknownStyle.iconName, 'FileQuestion');
  assert.match(unknownStyle.bg, /zinc/);

  const emptyStyle = getFormatBadgeStyle('');
  assert.equal(emptyStyle.label, 'UNKNOWN FORMAT');
  assert.equal(emptyStyle.iconName, 'FileQuestion');
});

test('Barrel export provides React component functions', () => {
  assert.equal(typeof DedupNotificationBanner, 'function');
  assert.equal(typeof DocumentFormatBadge, 'function');
});
