"""Real ADK execution and process recovery; only provider HTTP is substituted."""
import json
import os

import pytest

from tests.test_clearance_workflow import harness, ROOT, BASE, use, intake
from backend.clearance.models import RevisionInput, digest
from backend.clearance.service import submit
from backend.clearance.store import SQLiteStore
from backend.clearance.worker import Worker


def test_local_session_expiry_and_revocation_survive_restart(tmp_path):
    import time
    from backend.storage.sqlite_session_store import SQLiteSessionStore
    from backend.storage.session_store import SessionRecord
    path = tmp_path / 'sessions.db'
    first = SQLiteSessionStore(path)
    first.create_session(SessionRecord('active', 'operator', 'test@example.invalid', 'Test producer',
        'PRODUCER', 'test_org', 'test_production', time.time() + 60))
    first.create_session(SessionRecord('expired', 'operator', 'test@example.invalid', 'Test producer',
        'PRODUCER', 'test_org', 'test_production', time.time() - 1))
    restarted = SQLiteSessionStore(path)
    assert restarted.get_session('active').production_id == 'test_production'
    assert restarted.get_session('expired') is None
    assert restarted.get_session('missing') is None
    assert restarted.revoke_session('active')
    assert SQLiteSessionStore(path).is_revoked('active')


def test_adk_events_correlate_with_calls_and_scoped_export(harness):
    store, worker, _, client = harness
    producer = client()
    snapshot = intake(producer, worker)
    job = store.get(ROOT + '/live_jobs/' + snapshot['audit_id'])
    for key, call in job['calls'].items():
        trace = call['result']['trace']
        assert trace['correlation']['audit_id'] == job['audit_id']
        assert trace['correlation']['call_id'] == key
        assert trace['orchestration']['framework'] == 'Google ADK'
        assert trace['orchestration']['events']
        assert all(e['invocation_id'] and e['event_id'] for e in trace['orchestration']['events'])
        if key.endswith(':search'):
            assert any(e['tool_calls'] == ['parallel_search'] for e in trace['orchestration']['events'])
            assert any(e['tool_responses'] == ['parallel_search'] for e in trace['orchestration']['events'])
    path = BASE + f"/revisions/{snapshot['revision_id']}/snapshots/{snapshot['snapshot_id']}/execution-record"
    response = producer.get(path)
    assert response.status_code == 200
    body = response.json()
    sha = body.pop('record_sha256')
    assert digest(body) == sha
    assert body['snapshot'] == snapshot
    assert body['execution']['audit_id'] == job['audit_id']
    assert client(production='other').get(path).status_code == 403
    assert producer.get(path.replace(snapshot['snapshot_id'], 'snapshot_unknown')).status_code == 404


@pytest.mark.skipif(not hasattr(os, 'fork'), reason='Process-kill recovery proof runs on Linux worker platform')
def test_process_exit_after_completed_call_reuses_result_and_fences_old_worker(harness):
    store, worker, _, _ = harness
    job = submit(store, ROOT, RevisionInput(production_id='production_acceptance', initial_uses=[use('a')]), 'test-operator', 'process-exit')
    path = ROOT + '/live_jobs/' + job['audit_id']
    class InterruptedWorker(Worker):
        def call(self, path, fence, key, reservation, callback):
            result = super().call(path, fence, key, reservation, callback)
            if key.endswith(':plan'):
                os._exit(23)  # Abrupt process death, no Python cleanup or graceful job completion.
            return result
    pid = os.fork()
    if pid == 0:
        InterruptedWorker(SQLiteStore(store.path), worker.providers).run(path)
        os._exit(24)
    _, status = os.waitpid(pid, 0)
    assert os.waitstatus_to_exitcode(status) == 23
    interrupted = store.get(path)
    first_key = next(iter(interrupted['calls']))
    first_result = interrupted['calls'][first_key]
    assert first_result['status'] == 'COMPLETED'
    def expire(tx):
        record = tx.get(path)
        record['lease_until'] = 0
        tx.put(path, record)
    store.atomic(expire)  # Controlled expiry avoids waiting the full lease duration.
    Worker(SQLiteStore(store.path), worker.providers).run(path)
    finished = store.get(path)
    assert finished['status'] == 'COMPLETED'
    assert finished['calls'][first_key] == first_result
    assert len(finished['calls']) == 4
    assert finished['recoveries'][0]['completed_calls_reused'] == 1
    assert finished['fence'] == interrupted['fence'] + 1
    from backend.clearance.store import Conflict
    with pytest.raises(Conflict):
        worker.update(path, interrupted['fence'], lambda j: j.update(error='stale writer'))
