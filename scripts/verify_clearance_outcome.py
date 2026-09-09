"""Live provider integration with explicitly simulated reviewer decisions.

Never writes test approvals into an existing production. Uses the real mounted
application, scoped sessions, temporary persistence and canonical worker.
"""
import argparse
import json
import os
import tempfile
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allowance', required=True, type=float)
    args = parser.parse_args()
    if not 1 <= args.allowance <= 3:
        parser.error('Choose a total reservation allowance from $1 to $3.')
    load_dotenv()
    os.environ.update(CLEARANCE_LIVE_ENABLED='true', USE_LOCAL_STORAGE='true', BUDGET_STORE_MODE='local_disk')
    os.environ.pop('CLEARANCE_WATCH_BUCKET', None)
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.api.routes.auth_routes import sign_session_id
    from backend.storage.session_store import SessionRecord, get_session_store
    from backend.clearance.automation import save_policy, poll_folders, dispatch
    from backend.clearance.models import AutomationPolicy
    from backend.clearance.store import SQLiteStore, get_store
    from backend.clearance.worker import Worker
    production = 'outcome_' + uuid.uuid4().hex[:12]
    root = 'organizations/automated_rehearsal/productions/' + production
    endpoint = '/api/clearance/productions/' + production
    packet = Path(__file__).resolve().parents[1] / 'demo/live-clearance'
    with tempfile.TemporaryDirectory(prefix='lienmark-outcome-') as temp:
        directory = Path(temp)
        store = SQLiteStore(directory / 'records.db')
        app.dependency_overrides[get_store] = lambda: store
        os.environ['CLEARANCE_WATCH_ROOT'] = str(directory / 'watch')
        worker = Worker(store)
        save_policy(store, root, AutomationPolicy(enabled=True, per_run_usd=min(.8, args.allowance / 2),
            total_allowance_usd=args.allowance, production_name='AUTOMATED REHEARSAL — simulated reviewer'), 'integration-test')
        def client(role):
            sid = 'rehearsal_' + uuid.uuid4().hex
            get_session_store().create_session(SessionRecord(sid, 'automated-test-' + role, 'test@example.invalid',
                'Automated test ' + role, role, 'automated_rehearsal', production, time.time() + 600))
            result = TestClient(app)
            result.cookies.set('lienmark_session', sign_session_id(sid))
            result.headers['X-CSRF-Token'] = sid
            return result
        producer, reviewer = client('PRODUCER'), client('REVIEWER')
        output = Path('.data/outcome-verification')
        output.mkdir(parents=True, exist_ok=True)
        def workspace():
            response = producer.get(endpoint)
            response.raise_for_status()
            return response.json()
        def process():
            poll_folders(store)
            dispatch(store)
            for path, _ in store.pending():
                worker.run(path)
            state = workspace()
            (output / 'latest-attempt.json').write_text(json.dumps({'kind': 'Live providers; automated test reviewer',
                'workspace': state, 'jobs': [job for _, job in store.collection('live_jobs', root=root)]}, indent=2))
            if state['pending_audit'] or not state['snapshot']:
                raise RuntimeError('No completed snapshot; inspect the allowance and provider results.')
            return state['snapshot']
        def simulated_review(snapshot, key):
            claim = next(c for c in snapshot['claims'] if c['stable_lineage_key'] == key)
            response = reviewer.post(endpoint + '/claims/' + claim['claim_id'] + '/decision', json={
                'action': 'sign_off', 'revision_id': snapshot['revision_id'], 'expected_snapshot_id': snapshot['snapshot_id'],
                'evidence_ids': [e['evidence_id'] for e in claim['evidence_citations']],
                'rationale': 'AUTOMATED INTEGRATION TEST: simulated reviewer decision for a fictional scenario. This is not a human review, legal opinion or rights grant.'})
            response.raise_for_status()
            return response.json()
        folder = directory / 'watch' / root / 'locked'
        folder.mkdir(parents=True)
        (folder / 'baseline.json').write_bytes((packet / 'baseline.json').read_bytes())
        print('Running real research on three initial occurrences.', flush=True)
        initial = process()
        reviewed = initial
        for claim in initial['claims']:
            reviewed = simulated_review(reviewed, claim['stable_lineage_key'])
        (folder / 'revision.json').write_bytes((packet / 'revision.json').read_bytes())
        print('Detecting the changed cut; comparing against explicitly simulated baseline review.', flush=True)
        revision = process()
        assert sum(c['state'] == 'carried_forward' for c in revision['claims']) == 2
        questions = workspace()['automation']['clarifications']
        question = next((q for q in questions if q['status'] == 'PENDING' and q['claim_key'] == 'rehearsal_piano'), None)
        if not question:
            raise RuntimeError('The live run did not produce a piano clarification. Retain the actual result; do not manufacture the branch.')
        agreement_folder = directory / 'watch' / root / 'agreements' / question['clarification_id']
        agreement_folder.mkdir(parents=True)
        (agreement_folder / 'performance-scope.txt').write_bytes((packet / 'performance-scope.txt').read_bytes())
        print('Resuming the specific question from the arriving fictional scope note.', flush=True)
        resumed = process()
        final = simulated_review(resumed, 'rehearsal_piano')
        assert sum(c['state'] not in ('carried_forward', 're_attested', 'removed') for c in final['claims']) == 1
        (folder / 'renamed-revision.json').write_bytes((packet / 'revision.json').read_bytes())
        jobs_before = len(store.collection('live_jobs', root=root))
        unchanged = process()
        assert unchanged['snapshot_id'] == final['snapshot_id']
        assert len(store.collection('live_jobs', root=root)) == jobs_before
        base = endpoint + f"/revisions/{final['revision_id']}/snapshots/{final['snapshot_id']}"
        for route, filename in [('pdf', 'automated-rehearsal.pdf'), ('execution-record', 'execution-record.json')]:
            response = producer.get(base + '/' + route)
            response.raise_for_status()
            (output / filename).write_bytes(response.content)
        jobs = [job for _, job in store.collection('live_jobs', root=root)]
        report = {'verification_kind': 'Real provider calls; simulated reviewer actions; no human or legal approval',
            'initial': initial, 'reviewed_baseline': reviewed, 'revision': revision, 'resumed': resumed, 'final': final,
            'jobs': jobs, 'duplicate_created_job': False,
            'completed_provider_calls': sum(c['status'] == 'COMPLETED' for j in jobs for c in j['calls'].values()),
            'reserved_usd': sum(j['reserved_usd'] for j in jobs)}
        (output / 'result.json').write_text(json.dumps(report, indent=2))
        print(json.dumps({'artifact_directory': str(output), 'baseline_approvals_simulated': 3,
            'approvals_preserved': 2, 'revision_unresolved': 2, 'final_unresolved': 1,
            'completed_provider_calls': report['completed_provider_calls'], 'reserved_usd': report['reserved_usd'],
            'duplicate_created_job': False, 'human_review_performed': False}), flush=True)


if __name__ == '__main__':
    main()
