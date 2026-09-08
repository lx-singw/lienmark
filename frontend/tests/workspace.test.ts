import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeClaim, countClaims, safeUrl } from '../app/components/workspace/model';
import { parseUser, requestJson } from '../app/components/workspace/client';

test('workspace: server roles require both organization and production scope', () => {
  assert.equal(parseUser({ display_name: 'Guest' }), null);
  assert.equal(parseUser({ role: 'Reviewer', tenant_id: 'org' }), null);
  assert.equal(parseUser({ role: 'Producer', tenant_id: 'org', production_id: 'prod' })?.role, 'Producer');
  assert.equal(parseUser({ user: { role: 'Reviewer', tenant_id: 'org', production_id: 'prod' } })?.production_id, 'prod');
});
test('workspace: dashboard response without optional evidence or reason still renders', () => {
  const claim = normalizeClaim({ stable_lineage_key: 'music:18', description: 'Cue', scene: '18', asset_type: 'music', state: 'stale', counsel_action: 'Verify trailer use' });
  assert.equal(claim.status, 'reopened');
  assert.equal(claim.reason, 'Verify trailer use');
  assert.equal(claim.evidence, undefined);
  assert.equal(claim.decisionId, undefined, 'A lineage key must not invent an actionable claim ID.');
  assert.throws(() => normalizeClaim({ description: 'Unidentified record' }));
});
test('workspace: reopened claims are distinct from exceptions and preserved approvals', () => {
  const claims = ['stale', 'exception', 'carried_forward', 're_attested'].map((state, i) => normalizeClaim({ stable_lineage_key: String(i), state }));
  assert.deepEqual(countClaims(claims), { total: 4, reopened: 1, exceptions: 1, preserved: 1, reviewed: 1 });
});
test('workspace: source links reject executable and malformed URLs', () => {
  assert.equal(safeUrl('javascript:alert(1)'), undefined);
  assert.equal(safeUrl('data:text/html,example'), undefined);
  assert.equal(safeUrl('/relative/source'), undefined);
  assert.equal(safeUrl('https://example.org/evidence'), 'https://example.org/evidence');
});
test('workspace: current evidence citation response is attributed without invented content', () => {
  const claim = normalizeClaim({ stable_lineage_key: 'asset', evidence_citations: [{ source_title: 'Original source', source_url: 'https://example.org/source', excerpt: 'Recorded excerpt' }] });
  assert.equal(claim.evidence?.title, 'Original source');
  assert.equal(claim.evidence?.excerpt, 'Recorded excerpt');
  assert.equal(claim.evidence?.retrievedAt, undefined);
});
test('workspace: requests use browser sessions, propagate failure, and do not add a reviewer token', async () => {
  const originalFetch = globalThis.fetch;
  let captured: RequestInit | undefined;
  globalThis.fetch = async (_input, init) => { captured = init; return new Response(JSON.stringify({ detail: 'Access denied' }), { status: 403 }); };
  try {
    await assert.rejects(() => requestJson('/api/revisions/audit', { method: 'POST', body: '{}' }), /Access denied/);
    assert.equal(captured?.credentials, 'same-origin');
    assert.equal(new Headers(captured?.headers).has('Authorization'), false);
    assert.equal(new Headers(captured?.headers).has('X-Counsel-Token'), false);
  } finally { globalThis.fetch = originalFetch; }
});

