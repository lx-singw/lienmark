"""Real mounted routes, durable stores and workers; only provider HTTP is replaced."""
import json
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from tests.test_clearance_workflow import harness, use, intake, sign, ROOT, BASE
from backend.clearance.automation import poll_folders, dispatch, ingest, schedule_evidence, decode_document
from backend.clearance.models import SourceInput
from backend.clearance.store import SQLiteStore, Conflict
from backend.clearance.worker import Worker


def enable(client, **changes):
    response = client.put(BASE + '/automation', json={"enabled": True, "per_run_usd": 1,
        "total_allowance_usd": 10, "production_name": "Acceptance production", **changes})
    assert response.status_code == 200, response.text
    return response.json()


def drain(store, worker):
    dispatch(store)
    for path, _ in store.pending():
        worker.run(path)


def agent_transport(worker, *, material=False, ambiguous=False, challenge=False, strategy='public_research'):
    original = worker.providers.client
    calls = []
    def transport(request):
        data = json.loads(request.content)
        calls.append(data)
        if request.url.host == 'api.parallel.ai':
            return httpx.Response(200, json={"search_id": "observed-search", "results": [{
                "url": "https://catalogue.example.test/record", "title": "Publisher catalogue",
                "excerpts": ["Attribution changed to successor publisher." if material else "Publisher catalogue attribution."]}]})
        incoming = json.loads(data['contents'][0]['parts'][0]['text'])
        schema = data['generationConfig']['responseSchema']['properties']
        if 'material' in schema:
            output = {"material": material, "explanation": "A supported ownership change." if material else "Formatting only; no relevant fact changed.",
                "cited_ids": [incoming['evidence'][0]['evidence_id']]}
        elif 'clarification_id' in schema:
            output = {"clarification_id": None if ambiguous else incoming['open_clarifications'][0]['clarification_id'],
                "supports_match": not ambiguous, "explanation": "Work and grant scope match." if not ambiguous else "Insufficient work identification."}
        elif 'objective' in schema:
            output = {"objective": "Verify the attribution and applicable grant", "public_query": incoming['use']['description'] + ' publisher',
                "private_facts_needed": ['Private grant'], "stop_condition": "Supported facts and a specific private information request", "strategy": strategy}
        elif 'uses' in schema:
            output = {"uses": [use('a'), use('b')]}
        else:
            private = any(e['provider'] == 'Production document' for e in incoming['evidence'])
            ids = [e['evidence_id'] for e in incoming['evidence']]
            if 'verdict' in schema:
                repeat = challenge and len([c for c in calls if 'search_queries' in c]) == 1
                output = {"verdict": "research" if repeat else "supported" if private else "needs_information",
                    "explanation": "The first source is inadequate; check the publisher directly." if repeat else "Evidence checked against the supplied grant.",
                    "cited_ids": ids, "missing_facts": [] if private else ['Private grant'],
                    "next_query": "Public work a official successor catalogue" if repeat else None}
            else:
                output = {"summary": "Attribution and supplied document considered.", "cited_ids": ids,
                    "missing_facts": [] if private else ['Private grant'], "next_query": None}
        return httpx.Response(200, json={"responseId": "observed-model", "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(output)}]}}]})
    worker.providers.client = httpx.Client(transport=httpx.MockTransport(transport))
    return calls


def test_folder_revision_handoffs_selective_preservation_and_rename_dedup(harness, tmp_path, monkeypatch):
    store, worker, _, client = harness
    producer, reviewer = client(), client('REVIEWER')
    enable(producer)
    monkeypatch.setenv('CLEARANCE_WATCH_ROOT', str(tmp_path / 'watch'))
    folder = tmp_path / 'watch' / ROOT / 'locked'
    folder.mkdir(parents=True)
    cut = {'uses': [use('a'), use('b')]}
    (folder / 'cut-seven.json').write_text(json.dumps(cut))
    poll_folders(store)
    drain(store, worker)  # No browser, route invocation or click starts the worker.
    baseline = producer.get(BASE).json()['snapshot']
    for i in range(2):
        response = sign(reviewer, baseline, i)
        assert response.status_code == 200, response.text
        baseline = response.json()
    cut['uses'][0]['duration_or_prominence'] = '14 seconds foreground'
    (folder / 'cut-eight.json').write_text(json.dumps(cut))
    poll_folders(SQLiteStore(store.path))
    drain(store, Worker(SQLiteStore(store.path), worker.providers))
    state = producer.get(BASE).json()
    snapshot = state['snapshot']
    assert [c['state'] for c in snapshot['claims']] == ['stale', 'carried_forward']
    assert snapshot['claims'][1]['decision'] == baseline['claims'][1]['decision']
    assert snapshot['claims'][0]['decision'] is None
    assert snapshot['comparison']['approvals_before'] == 2
    assert snapshot['comparison']['blockers_after'] == 1
    assert snapshot['comparison']['blockers_before'] == 0
    assert {t['agent'] for t in snapshot['tasks']} >= {'Document intake', 'Change coordinator', 'Investigation planner', 'Rights researcher', 'Evidence reviewer', 'Delivery coordinator'}
    assert all('claim_' not in key or key.startswith(snapshot['claims'][0]['claim_id']) for key in snapshot['telemetry']['calls'])
    (folder / 'renamed-cut.json').write_text(json.dumps(cut))
    poll_folders(store)
    drain(store, worker)
    assert producer.get(BASE).json()['snapshot']['snapshot_id'] == snapshot['snapshot_id']
    assert store.get(ROOT + '/live_automation/policy')['allocated_usd'] == 0


def test_matching_agreement_resumes_only_target_and_never_signs_off(harness):
    store, worker, _, client = harness
    producer = client()
    snapshot = intake(producer, worker)
    enable(producer)
    calls = agent_transport(worker)
    question = producer.get(BASE).json()['automation']['clarifications'][0]
    response = producer.post(BASE + '/documents?name=grant.txt&kind=agreement',
        content=b'Agreement for Public work a: grant for the stated production scope.', headers={'Content-Type': 'text/plain'})
    assert response.status_code == 202
    drain(store, worker)
    updated = producer.get(BASE).json()['snapshot']
    assert updated['claims'][0]['investigation']['missing_facts'] == []
    assert updated['claims'][0]['decision'] is None
    assert updated['claims'][1] == snapshot['claims'][1]
    assert updated['comparison']['missing_facts_resolved'] == 1
    assert sum('search_queries' in c for c in calls) == 1
    assert any(t['agent'] == 'Agreement matcher' for t in updated['tasks'])
    evidence = next(e for e in updated['claims'][0]['evidence_citations'] if e['provider'] == 'Production document')
    assert producer.get(evidence['url']).status_code == 200
    assert client(production='other').get(evidence['url']).status_code == 403


def test_ambiguous_agreement_retained_and_explicit_assignment_resumes(harness):
    store, worker, _, client = harness
    producer = client()
    original = intake(producer, worker)
    enable(producer)
    agent_transport(worker, ambiguous=True)
    event = ingest(store, ROOT, SourceInput(kind='agreement', name='ambiguous.txt', text='An agreement with an ambiguous unnamed work and an unclear production scope.'), 'test')
    drain(store, worker)
    assert producer.get(BASE).json()['snapshot']['snapshot_id'] == original['snapshot_id']
    assert store.get(ROOT + '/live_sources/' + event['event_id'])['status'] == 'WAITING_FOR_MATCH'
    question = producer.get(BASE).json()['automation']['clarifications'][0]
    assigned = producer.post(BASE + '/documents/' + event['event_id'] + '/assign', params={'clarification_id': question['clarification_id']})
    assert assigned.status_code == 202, assigned.text
    drain(store, worker)
    assert producer.get(BASE).json()['snapshot']['claims'][0]['investigation']['missing_facts'] == []


@pytest.mark.parametrize('material', [False, True])
def test_external_evidence_requires_material_attributable_change(harness, material):
    store, worker, _, client = harness
    producer, reviewer = client(), client('REVIEWER')
    baseline = intake(producer, worker, [use('a')])
    baseline = sign(reviewer, baseline).json()
    enable(producer, watch_evidence=True)
    calls = agent_transport(worker, material=material)
    schedule_evidence(store, time.time())
    drain(store, worker)
    updated = producer.get(BASE).json()['snapshot']
    assert updated['claims'][0]['state'] == ('stale' if material else 're_attested')
    if not material:
        assert updated['snapshot_id'] == baseline['snapshot_id']
        assert updated['claims'][0]['decision'] == baseline['claims'][0]['decision']
    else:
        assert updated['claims'][0]['decision'] is None
    assert sum('search_queries' in c for c in calls) == (2 if material else 1)
    before = len(calls)
    schedule_evidence(store, time.time())
    drain(store, worker)
    assert len(calls) == before


def test_evidence_reviewer_handoff_changes_the_next_query(harness):
    _, worker, _, client = harness
    calls = agent_transport(worker, challenge=True)
    result = intake(client(), worker, [use('a')])
    searches = [c['search_queries'][0] for c in calls if 'search_queries' in c]
    assert searches == ['Public work a publisher', 'Public work a official successor catalogue']
    researchers = [t for t in result['tasks'] if t['agent'] == 'Rights researcher']
    assert researchers[1]['handoff_from'] == 'Evidence reviewer'


def test_policy_pause_exhaustion_and_concurrent_dispatch_never_overspend(harness):
    store, worker, calls, client = harness
    producer = client()
    enable(producer, total_allowance_usd=1)
    source = SourceInput(kind='revision', name='a.json', text=json.dumps({'uses': [use('a')]}))
    event = ingest(store, ROOT, source, 'test')
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: dispatch(SQLiteStore(store.path)), range(2)))
    assert len(store.pending()) == 1
    assert store.get(ROOT + '/live_automation/policy')['allocated_usd'] == 1
    drain(store, worker)
    calls.clear()
    next_event = ingest(store, ROOT, SourceInput(kind='revision', name='b.json', text=json.dumps({'uses': [use('b')]})), 'test')
    dispatch(store)
    assert not store.pending()  # Remaining allowance cannot reserve a full new run.
    assert calls == []
    enable(producer, enabled=False, total_allowance_usd=10)
    dispatch(store)
    assert not store.pending()
    enable(producer)
    drain(store, worker)
    assert store.get(ROOT + '/live_sources/' + next_event['event_id'])['status'] == 'COMPLETED'


def test_directive_automatically_reinvestigates_transitive_dependents(harness):
    store, worker, _, client = harness
    producer, reviewer = client(), client('REVIEWER')
    baseline = intake(producer, worker, [use('a'), use('b', ['a']), use('independent')])
    for i in range(3):
        baseline = sign(reviewer, baseline, i).json()
    enable(producer)
    response = sign(reviewer, baseline, 0, 'reject')
    assert response.status_code == 200
    drain(store, worker)
    current = producer.get(BASE).json()['snapshot']
    assert [c['state'] for c in current['claims']] == ['stale', 'stale', 'carried_forward']
    assert current['claims'][2]['decision'] == baseline['claims'][2]['decision']
    assert current['trigger']['kind'] == 'directive'


def test_document_authority_limits_and_malformed_pdf(harness):
    _, _, _, client = harness
    assert client(production='other').put(BASE + '/automation', json={'enabled': True}).status_code == 403
    assert client().post(BASE + '/documents?name=bad.pdf', content=b'not a PDF').status_code == 409
    with pytest.raises(Conflict):
        decode_document('bad.txt', b'a' * 4_000_001)


def test_completed_plan_survives_crash_without_repeating_model_call(harness):
    store, worker, calls, client = harness
    job = client().post('/api/clearance/revisions', json={'production_id': 'production_acceptance', 'initial_uses': [use('a')]},
        headers={'Idempotency-Key': 'mid-plan-crash'}).json()
    path = ROOT + '/live_jobs/' + job['audit_id']
    original_review = worker.providers.review
    def crash(*args):
        raise KeyboardInterrupt('Simulated worker termination')
    worker.providers.review = crash
    with pytest.raises(KeyboardInterrupt):
        worker.run(path)
    plan_calls = len([c for _, c in calls if 'objective' in c.get('generationConfig', {}).get('responseSchema', {}).get('properties', {})])
    assert plan_calls == 1
    store.atomic(lambda tx: tx.put(path, {**tx.get(path), 'lease_until': 0}))
    worker.providers.review = original_review
    Worker(SQLiteStore(store.path), worker.providers).run(path)
    assert len([c for _, c in calls if 'objective' in c.get('generationConfig', {}).get('responseSchema', {}).get('properties', {})]) == 1
    snapshot = client().get(BASE).json()['snapshot']
    assert snapshot['claims'][0]['decision'] is None
    assert 'uncertain' in snapshot['claims'][0]['investigation_error']


def test_reformatted_structured_cut_preserves_every_approval_without_model_spend(harness):
    store, worker, calls, client = harness
    producer, reviewer = client(), client('REVIEWER')
    baseline = intake(producer, worker)
    for i in range(2):
        baseline = sign(reviewer, baseline, i).json()
    enable(producer)
    calls.clear()
    ingest(store, ROOT, SourceInput(kind='revision', name='same-cut.json', text=json.dumps({'uses': [c['use'] for c in baseline['claims']]}, indent=4)), 'test')
    drain(store, worker)
    assert calls == []
    current = producer.get(BASE).json()['snapshot']
    assert all(c['state'] == 'carried_forward' for c in current['claims'])
    assert current['telemetry']['reserved_spend'] == 0


def test_document_upload_has_its_own_four_megabyte_transport_limit(harness):
    _, _, _, client = harness
    response = client().post(BASE + '/documents?name=broken.pdf', content=b'%PDF-' + b'x' * 1_100_000,
        headers={'Content-Type': 'application/pdf'})
    assert response.status_code == 409  # Parser rejects it, not the old 1 MB middleware limit.
    response = client().post(BASE + '/documents?name=too-big.pdf', content=b'%PDF-' + b'x' * 4_000_000,
        headers={'Content-Type': 'application/pdf'})
    assert response.status_code == 413


def test_eventarc_rejects_missing_identity_and_wrong_bucket(harness, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.clearance import runtime
    client = TestClient(runtime.app)
    monkeypatch.delenv('CLEARANCE_EVENTARC_AUDIENCE', raising=False)
    monkeypatch.delenv('CLEARANCE_EVENTARC_SERVICE_ACCOUNT', raising=False)
    assert client.post('/eventarc', json={}).status_code == 503
    monkeypatch.setenv('CLEARANCE_EVENTARC_AUDIENCE', 'https://worker.example.test')
    monkeypatch.setenv('CLEARANCE_EVENTARC_SERVICE_ACCOUNT', 'events@example.test')
    assert client.post('/eventarc', json={}).status_code == 401
    monkeypatch.setattr(runtime, 'verify_event_identity', lambda request: None)
    monkeypatch.setenv('CLEARANCE_WATCH_BUCKET', 'allowed-bucket')
    response = client.post('/eventarc', json={'bucket': 'wrong-bucket'}, headers={'ce-type': 'google.cloud.storage.object.v1.finalized'})
    assert response.status_code == 403


def test_local_watcher_does_not_follow_a_symlink_outside_its_production(harness, tmp_path, monkeypatch):
    store, worker, calls, client = harness
    enable(client())
    base = tmp_path / 'watch'
    folder = base / ROOT / 'locked'
    folder.mkdir(parents=True)
    outside = tmp_path / 'private.txt'
    outside.write_text('A document outside the authorized production root must never be read.')
    (folder / 'escape.txt').symlink_to(outside)
    monkeypatch.setenv('CLEARANCE_WATCH_ROOT', str(base))
    poll_folders(store)
    assert store.collection('live_sources') == []
    assert calls == []


def test_planner_can_request_private_facts_without_unnecessary_web_search(harness):
    _, worker, _, client = harness
    calls = agent_transport(worker, strategy='request_information')
    result = intake(client(), worker, [use('a')])
    assert not any('search_queries' in c for c in calls)
    assert result['claims'][0]['investigation']['missing_facts'] == ['Private grant']
    assert result['claims'][0]['decision'] is None
    assert client().get(BASE).json()['automation']['clarifications'][0]['status'] == 'PENDING'


def test_document_review_reuses_public_evidence_without_searching_again(harness):
    store, worker, _, client = harness
    producer = client()
    intake(producer, worker, [use('a')])
    enable(producer)
    calls = agent_transport(worker, strategy='review_documents')
    question = producer.get(BASE).json()['automation']['clarifications'][0]
    ingest(store, ROOT, SourceInput(kind='agreement', name='grant.txt', text='Private grant covering Public work a in the stated scope.', clarification_id=question['clarification_id']), 'test')
    drain(store, worker)
    assert not any('search_queries' in c for c in calls)
    assert producer.get(BASE).json()['snapshot']['claims'][0]['investigation']['missing_facts'] == []


def test_invalid_citation_is_repaired_once_and_both_calls_remain_in_the_ledger(harness):
    _, worker, _, client = harness
    base_transport = worker.providers.client
    rejected = []
    def transport(request):
        data = json.loads(request.content)
        schema = data.get('generationConfig', {}).get('responseSchema', {})
        if 'summary' in schema.get('properties', {}) and not rejected:
            rejected.append(True)
            incoming = json.loads(data['contents'][0]['parts'][0]['text'])
            assert schema['properties']['cited_ids']['items']['enum'] == [e['evidence_id'] for e in incoming['evidence']]
            return httpx.Response(200, json={'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps({
                'summary': 'An unsupported assertion', 'cited_ids': ['invented-evidence'], 'missing_facts': [], 'next_query': None})}]}}]})
        return base_transport.send(request)
    worker.providers.client = httpx.Client(transport=httpx.MockTransport(transport))
    result = intake(client(), worker, [use('a')])
    calls = result['telemetry']['calls']
    assert any(c['status'] == 'FAILED' and c.get('repairable') for c in calls.values())
    assert any(k.endswith(':repair') and c['status'] == 'COMPLETED' for k, c in calls.items())
    assert 'investigation_error' not in result['claims'][0]
    assert result['claims'][0]['decision'] is None


def test_transient_provider_failure_recovers_once_with_explicit_reservations(harness):
    _, worker, _, client = harness
    original = worker.providers.client
    failed = []
    def transport(request):
        if not failed:
            failed.append(True)
            return httpx.Response(503)
        return original.send(request)
    worker.providers.client = httpx.Client(transport=httpx.MockTransport(transport))
    result = intake(client(), worker, [use('a')])
    assert 'investigation_error' not in result['claims'][0]
    calls = result['telemetry']['calls']
    assert any(c.get('retryable') and c['status'] == 'FAILED' for c in calls.values())
    assert any(k.endswith(':retry') and c['status'] == 'COMPLETED' for k, c in calls.items())
    assert result['telemetry']['reserved_spend'] == pytest.approx(.21)


def test_watched_folder_cannot_redirect_to_another_production(harness, tmp_path, monkeypatch):
    store, _, _, client = harness
    enable(client())
    base = tmp_path / 'watch'
    production = base / ROOT
    production.mkdir(parents=True)
    another = base / 'other-production'
    another.mkdir()
    (another / 'secret.txt').write_text('This other production is not assigned to the active workspace.')
    (production / 'locked').symlink_to(another, target_is_directory=True)
    monkeypatch.setenv('CLEARANCE_WATCH_ROOT', str(base))
    poll_folders(store)
    assert store.collection('live_sources') == []


def test_dependency_cycles_fail_before_research(harness):
    store, worker, calls, client = harness
    response = client().post('/api/clearance/revisions', json={'production_id': 'production_acceptance',
        'initial_uses': [use('a', ['b']), use('b', ['a'])]}, headers={'Idempotency-Key': 'cycle'})
    assert response.status_code == 202
    worker.run(ROOT + '/live_jobs/' + response.json()['audit_id'])
    job = client().get(response.json()['status_url']).json()
    assert job['status'] == 'FAILED' and 'cycle' in job['error']
    assert calls == []
