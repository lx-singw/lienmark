/**
 * Frontend Truthfulness & Fail-Closed Test Suite
 * Validates fail-closed API client behavior, Server Action error envelopes,
 * ConnectionState lifecycle invariants, and truthful error propagation.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { ConnectionState } from '../lib/types';
import { LienmarkApiClient, ApiNetworkError } from '../lib/api_client';
import {
  fetchClearanceStateAction,
  evaluateClearanceDeltaAction,
  fetchReviewQueueAction,
  fetchAuditTrailAction,
} from '../app/actions';

test('ConnectionState: exposes canonical fail-closed connection lifecycle states', () => {
  assert.equal(ConnectionState.LOADING, 'loading');
  assert.equal(ConnectionState.CONNECTED, 'connected');
  assert.equal(ConnectionState.EMPTY, 'empty');
  assert.equal(ConnectionState.UNAVAILABLE, 'unavailable');
  assert.equal(ConnectionState.STALE, 'stale');

  const validStates: ConnectionState[] = [
    'loading',
    'connected',
    'empty',
    'unavailable',
    'stale',
  ];
  assert.equal(validStates.length, 5);
});

test('apiClient: DEFAULT_CONFIG enforces enableFallback: false (fail-closed default)', () => {
  const client = new LienmarkApiClient();
  assert.equal(client.enableFallback, false);
});

test('apiClient: getHealth throws genuine network error when backend is offline without fallback', async () => {
  const offlineClient = new LienmarkApiClient({
    baseUrl: 'http://127.0.0.1:59999',
    defaultTimeoutMs: 1000,
    enableFallback: false,
  });

  await assert.rejects(
    async () => {
      await offlineClient.getHealth();
    },
    (err: unknown) => {
      assert.ok(err instanceof ApiNetworkError || err instanceof Error);
      return true;
    }
  );
});

test('apiClient: getFixtures throws genuine network error when backend is offline without fallback', async () => {
  const offlineClient = new LienmarkApiClient({
    baseUrl: 'http://127.0.0.1:59999',
    defaultTimeoutMs: 1000,
    enableFallback: false,
  });

  await assert.rejects(
    async () => {
      await offlineClient.getFixtures();
    },
    (err: unknown) => {
      assert.ok(err instanceof ApiNetworkError || err instanceof Error);
      return true;
    }
  );
});

test('apiClient: runDriftAnalysis throws genuine error when backend is unreachable', async () => {
  const offlineClient = new LienmarkApiClient({
    baseUrl: 'http://127.0.0.1:59999',
    defaultTimeoutMs: 1000,
    enableFallback: false,
  });

  await assert.rejects(
    async () => {
      await offlineClient.runDriftAnalysis('v8');
    },
    (err: unknown) => {
      assert.ok(err instanceof ApiNetworkError || err instanceof Error);
      return true;
    }
  );
});

test('apiClient: getExceptionsSchedule throws genuine error when backend is unreachable', async () => {
  const offlineClient = new LienmarkApiClient({
    baseUrl: 'http://127.0.0.1:59999',
    defaultTimeoutMs: 1000,
    enableFallback: false,
  });

  await assert.rejects(
    async () => {
      await offlineClient.getExceptionsSchedule();
    },
    (err: unknown) => {
      assert.ok(err instanceof ApiNetworkError || err instanceof Error);
      return true;
    }
  );
});

test('apiClient: getReviewQueue throws genuine error without returning golden fallback queue', async () => {
  const offlineClient = new LienmarkApiClient({
    baseUrl: 'http://127.0.0.1:59999',
    defaultTimeoutMs: 1000,
    enableFallback: false,
  });

  await assert.rejects(
    async () => {
      await offlineClient.getReviewQueue();
    },
    (err: unknown) => {
      assert.ok(err instanceof ApiNetworkError || err instanceof Error);
      return true;
    }
  );
});

test('apiClient: getAuditTrail throws genuine error without returning golden fallback trail', async () => {
  const offlineClient = new LienmarkApiClient({
    baseUrl: 'http://127.0.0.1:59999',
    defaultTimeoutMs: 1000,
    enableFallback: false,
  });

  await assert.rejects(
    async () => {
      await offlineClient.getAuditTrail();
    },
    (err: unknown) => {
      assert.ok(err instanceof ApiNetworkError || err instanceof Error);
      return true;
    }
  );
});

test('actions: fetchClearanceStateAction returns success: false on failure without masking disconnection', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => { throw new TypeError('Controlled offline transport'); });
  const res = await fetchClearanceStateAction();
  assert.equal(res.success, false);
  assert.ok(typeof res.error === 'string' && res.error.length > 0);
  assert.equal(res.data, undefined);
});

test('actions: evaluateClearanceDeltaAction returns success: false on failure', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => { throw new TypeError('Controlled offline transport'); });
  const res = await evaluateClearanceDeltaAction('v8');
  assert.equal(res.success, false);
  assert.ok(typeof res.error === 'string' && res.error.length > 0);
  assert.equal(res.data, undefined);
});

test('actions: fetchReviewQueueAction returns success: false without synthesizing mock data arrays', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => { throw new TypeError('Controlled offline transport'); });
  const res = await fetchReviewQueueAction();
  assert.equal(res.success, false);
  assert.ok(typeof res.error === 'string' && res.error.length > 0);
  assert.equal(res.data, undefined);
});

test('actions: fetchAuditTrailAction returns success: false without synthesizing mock data arrays', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => { throw new TypeError('Controlled offline transport'); });
  const res = await fetchAuditTrailAction();
  assert.equal(res.success, false);
  assert.ok(typeof res.error === 'string' && res.error.length > 0);
  assert.equal(res.data, undefined);
});
