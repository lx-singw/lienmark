/**
 * frontend/tests/intake.test.ts
 *
 * Automated unit test suite for Multimodal Intake Stepper,
 * Category Badges, and Confidentiality Indicators.
 * Sprint 2.3: Multimodal Intake Pipeline.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 * Enforces file <= 250 lines and function <= 40 lines.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  calculateStepperProgress,
  getStepperStepStatus,
  getAssetCategoryBadgeProps,
  getConfidentialityBadgeProps,
  detectDialogueQuotes,
} from '../app/components/intake/intake_utils';

test('calculateStepperProgress: maps all intake lifecycle stages to progress percentages', () => {
  assert.equal(calculateStepperProgress('IDLE'), 0);
  assert.equal(calculateStepperProgress('PARSING'), 25);
  assert.equal(calculateStepperProgress('EXTRACTING_PRIMARY'), 50);
  assert.equal(calculateStepperProgress('SELF_REFLECTION'), 75);
  assert.equal(calculateStepperProgress('BASELINE_COMMITTED'), 100);
  assert.equal(calculateStepperProgress('ERROR'), 0);
});

test('getStepperStepStatus: computes completed, active, and upcoming step states', () => {
  // Current step is 2 (0-indexed, i.e., 3rd step)
  assert.equal(getStepperStepStatus(0, 2), 'completed');
  assert.equal(getStepperStepStatus(1, 2), 'completed');
  assert.equal(getStepperStepStatus(2, 2), 'active');
  assert.equal(getStepperStepStatus(3, 2), 'upcoming');
});

test('getStepperStepStatus: correctly flags error step when error flag is active', () => {
  assert.equal(getStepperStepStatus(1, 1, true), 'error');
  assert.equal(getStepperStepStatus(0, 1, true), 'completed');
  assert.equal(getStepperStepStatus(2, 1, true), 'upcoming');
});

test('getAssetCategoryBadgeProps: styles music cues with high-contrast indigo palette', () => {
  const music = getAssetCategoryBadgeProps('music');
  assert.equal(music.label, 'MUSIC CUE');
  assert.equal(music.iconName, 'Music');
  assert.equal(music.bg, 'bg-indigo-950/80');
  assert.equal(music.text, 'text-indigo-300');
  assert.equal(music.border, 'border-indigo-500/50');

  const musicCue = getAssetCategoryBadgeProps('music_cue');
  assert.equal(musicCue.label, 'MUSIC CUE');
});

test('getAssetCategoryBadgeProps: styles archival footage with high-contrast sky palette', () => {
  const footage = getAssetCategoryBadgeProps('footage');
  assert.equal(footage.label, 'ARCHIVAL FOOTAGE');
  assert.equal(footage.iconName, 'Film');
  assert.equal(footage.bg, 'bg-sky-950/80');
  assert.equal(footage.text, 'text-sky-300');
  assert.equal(footage.border, 'border-sky-500/50');

  const clip = getAssetCategoryBadgeProps('clip');
  assert.equal(clip.label, 'ARCHIVAL FOOTAGE');
});

test('getAssetCategoryBadgeProps: styles trademarks and brands with high-contrast cyan palette', () => {
  const brand = getAssetCategoryBadgeProps('brand');
  assert.equal(brand.label, 'TRADEMARK');
  assert.equal(brand.iconName, 'Tag');
  assert.equal(brand.bg, 'bg-cyan-950/80');
  assert.equal(brand.text, 'text-cyan-300');
  assert.equal(brand.border, 'border-cyan-500/50');

  const trademark = getAssetCategoryBadgeProps('trademark');
  assert.equal(trademark.label, 'TRADEMARK');
});

test('getAssetCategoryBadgeProps: styles artwork, props, and likeness categories', () => {
  const artwork = getAssetCategoryBadgeProps('artwork');
  assert.equal(artwork.label, 'ARTWORK');
  assert.equal(artwork.bg, 'bg-purple-950/80');

  const prop = getAssetCategoryBadgeProps('prop');
  assert.equal(prop.label, 'PROP');
  assert.equal(prop.bg, 'bg-amber-950/80');

  const likeness = getAssetCategoryBadgeProps('likeness');
  assert.equal(likeness.label, 'LIKENESS');
  assert.equal(likeness.bg, 'bg-rose-950/80');
});

test('getAssetCategoryBadgeProps: provides defensive fallback for unknown asset types', () => {
  const unknown = getAssetCategoryBadgeProps('custom_asset');
  assert.equal(unknown.label, 'CUSTOM_ASSET');
  assert.equal(unknown.bg, 'bg-slate-800');

  const empty = getAssetCategoryBadgeProps('');
  assert.equal(empty.label, 'OTHER');
});

test('detectDialogueQuotes: detects quotation marks and spoken dialogue snippets', () => {
  assert.equal(detectDialogueQuotes('Ray says: "Watch that tape"'), true);
  assert.equal(detectDialogueQuotes("She replied: 'Never again'"), true);
  assert.equal(detectDialogueQuotes('A framed vintage poster on the wall'), false);
  assert.equal(detectDialogueQuotes(''), false);
});

test('getConfidentialityBadgeProps: confirms confidential status for descriptions <= 20 words', () => {
  const cleanDesc = "instrumental piece 'Clair de Lune' by Claude Debussy — sync licensing status";
  const badge = getConfidentialityBadgeProps(cleanDesc, 20);

  assert.equal(badge.isConfidential, true);
  assert.equal(badge.label, 'CONFIDENTIAL / ZERO-SPOILER');
  assert.equal(badge.bg, 'bg-emerald-950/80');
  assert.equal(badge.text, 'text-emerald-300');
  assert.equal(badge.border, 'border-emerald-500/50');
  assert.equal(badge.iconName, 'ShieldCheck');
  assert.equal(badge.wordCount <= 20, true);
});

test('getConfidentialityBadgeProps: flags warning for descriptions exceeding target word limit', () => {
  const longDesc = 'Word '.repeat(25) + 'end';
  const badge = getConfidentialityBadgeProps(longDesc, 20);

  assert.equal(badge.isConfidential, false);
  assert.equal(badge.label, 'EXCEEDS 20 WORDS');
  assert.equal(badge.bg, 'bg-amber-950/80');
  assert.equal(badge.text, 'text-amber-300');
  assert.equal(badge.border, 'border-amber-500/50');
  assert.equal(badge.iconName, 'AlertTriangle');
  assert.equal(badge.wordCount > 20, true);
});
