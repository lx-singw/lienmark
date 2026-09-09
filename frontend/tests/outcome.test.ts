import test from 'node:test';
import assert from 'node:assert/strict';
import { productionOutcome } from '../app/components/workspace/outcome';

test('an empty production never presents an all-clear outcome', () => {
  const result = productionOutcome(null, {}, {});
  assert.equal(result.next[1], '/revisions');
  assert.equal(result.approved, 0);
  assert.doesNotMatch(result.title, /approved/);
});
test('preservation requires an actual sign-off and excludes removed occurrences', () => {
  const result = productionOutcome({ claims: [
    { state: 'carried_forward', decision: { action: 'sign_off' } },
    { state: 'carried_forward' },
    { state: 'removed', decision: { action: 'sign_off' } },
    { state: 'stale', change_summary: [{ field: 'duration' }] },
  ], comparison: { baseline_snapshot_id: 'baseline' } }, {}, {});
  assert.equal(result.preserved, 1);
  assert.equal(result.total, 3);
  assert.equal(result.blockers, 2);
  assert.equal(result.changed, 1);
});
test('active work takes priority over the prior approved snapshot', () => {
  const result = productionOutcome({ claims: [{ state: 're_attested', decision: { action: 'sign_off' } }] }, { status: 'PROCESSING' }, {});
  assert.equal(result.active, true);
  assert.equal(result.next[1], '/investigations');
});
test('missing information and failed research lead to distinct actions', () => {
  const snapshot = { claims: [{ state: 'stale' }] };
  const automation = { clarifications: [{ status: 'PENDING' }, { status: 'SUPERSEDED' }] };
  assert.equal(productionOutcome(snapshot, {}, automation).next[1], '/inbox');
  assert.equal(productionOutcome(snapshot, { status: 'FAILED' }, automation).next[1], '/investigations');
});
test('an agreement resumption is described as evidence work rather than zero creative changes', () => {
  const result = productionOutcome({ claims: [], comparison: { baseline_snapshot_id: 'before' } }, { trigger: { kind: 'agreement' } }, {});
  assert.equal(result.changeDescription, 'Supporting document reassessed');
});
