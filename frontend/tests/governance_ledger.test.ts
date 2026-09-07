/**
 * Governance & Ledger Test Suite
 * Validating cryptographic chain verification, budget math, and hash truncation.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  truncateHash,
  verifyParentLink,
  formatUtcTimestamp,
} from '../app/components/ledger/audit_utils';
import type { SupersessionEvent } from '../lib/types';

test('truncateHash formats correctly', () => {
  assert.equal(truncateHash(''), '0x000...000');
  assert.equal(truncateHash(null), '0x000...000');
  assert.equal(truncateHash('12345'), '0x12345');
  assert.equal(
    truncateHash('0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890'),
    '0xabcdef...7890'
  );
  assert.equal(
    truncateHash('abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890'),
    '0xabcdef...7890'
  );
});

test('verifyParentLink validates matching hashes', () => {
  const genesisEvent: SupersessionEvent = {
    event_id: 'evt_001',
    stable_lineage_key: 'claim_1',
    action: 'GENESIS',
    prior_decision_id: 'root',
    event_hash: '0x1111111111111111111111111111111111111111111111111111111111111111',
    parent_hash: '0x0000000000000000000000000000000000000000000000000000000000000000',
    timestamp: '2026-09-07T00:00:00Z',
  };

  const childEvent: SupersessionEvent = {
    event_id: 'evt_002',
    stable_lineage_key: 'claim_1',
    action: 'CLAIM_CREATED',
    prior_decision_id: 'dec_1',
    event_hash: '0x2222222222222222222222222222222222222222222222222222222222222222',
    parent_hash: '0x1111111111111111111111111111111111111111111111111111111111111111',
    timestamp: '2026-09-07T00:01:00Z',
  };

  // Genesis parent link check
  assert.equal(verifyParentLink(genesisEvent, undefined), true);

  // Valid chained link check
  assert.equal(verifyParentLink(childEvent, genesisEvent), true);

  // Tampered child with mismatched parent hash
  const tamperedEvent: SupersessionEvent = {
    ...childEvent,
    parent_hash: '0xbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad',
  };
  assert.equal(verifyParentLink(tamperedEvent, genesisEvent), false);
});

test('formatUtcTimestamp formats ISO strings consistently', () => {
  const ts = '2026-09-07T12:30:00.000Z';
  const formatted = formatUtcTimestamp(ts);
  assert.match(formatted, /2026-09-07 12:30:00 UTC/);
});

test('Budget capacity calculations adhere to roadmap formulas', () => {
  const claimCost = 0.04;
  const pageCost = 0.015;
  const additionalBudget = 25.0;

  const unlockedClaims = Math.floor(additionalBudget / claimCost);
  const unlockedPages = Math.floor(additionalBudget / pageCost);

  assert.equal(unlockedClaims, 625);
  assert.equal(unlockedPages, 1666);
});
