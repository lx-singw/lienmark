"""Opt-in live boundary verification; no fabricated approvals or provider results.

Writes only an isolated temporary production and a local verification artifact.
The resumption document is explicitly a test scope note, never a legal grant.
"""
import argparse
import json
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--allowance', type=float, required=True, help='Total dispatch reservation allowance, at most $1')
    args = parser.parse_args()
    if not .1 <= args.allowance <= 1:
        parser.error('Use a reservation allowance between $0.10 and $1.00.')
    load_dotenv()
    os.environ['CLEARANCE_LIVE_ENABLED'] = 'true'
    from backend.clearance.automation import save_policy, poll_folders, dispatch, overview
    from backend.clearance.models import AutomationPolicy
    from backend.clearance.service import current
    from backend.clearance.store import SQLiteStore
    from backend.clearance.worker import Worker
    root = 'organizations/live_validation/productions/autonomous_validation'
    with tempfile.TemporaryDirectory(prefix='lienmark-autonomy-') as directory:
        base = Path(directory)
        os.environ['CLEARANCE_WATCH_ROOT'] = str(base / 'watch')
        os.environ.pop('CLEARANCE_WATCH_BUCKET', None)
        store = SQLiteStore(base / 'records.db')
        worker = Worker(store)
        save_policy(store, root, AutomationPolicy(enabled=True, per_run_usd=args.allowance / 2,
            total_allowance_usd=args.allowance, production_name='Live autonomy verification'), 'verification-operator')
        folder = base / 'watch' / root / 'locked'
        folder.mkdir(parents=True)
        (folder / 'unseen-scene.fountain').write_text('INT. REHEARSAL ROOM - DAY\nA pianist performs the first movement of Beethoven’s Moonlight Sonata live on camera for two seconds as background music. This fictional verification production is intended for theatrical exhibition in South Africa. No recording license, performer release or private agreement has been provided.', encoding='utf-8')
        print('Discovering an unseen document with no browser or API submission.', flush=True)
        poll_folders(store)
        dispatch(store)
        for path, _ in store.pending():
            worker.run(path)
        first = current(store, root)
        print('First investigation finished; checking durable clarifications.', flush=True)
        questions = [q for q in overview(store, root)['clarifications'] if q['status'] == 'PENDING']
        if questions:
            folder = base / 'watch' / root / 'agreements'
            folder.mkdir(parents=True)
            (folder / 'scope-note.txt').write_text('TEST SCOPE NOTE — NOT A LICENSE OR LEGAL GRANT. This note concerns the live piano performance of the first movement of Beethoven’s Moonlight Sonata in the rehearsal-room scene, two seconds in the background, for theatrical exhibition in South Africa. It confirms the intended use only. It provides no performer release and no private rights grant. Keep any unsupported clearance facts unresolved.', encoding='utf-8')
            poll_folders(store)
            dispatch(store)
            print('Processing the arriving scope note through agreement matching and resumption.', flush=True)
            for path, _ in store.pending():
                worker.run(path)
        result = current(store, root)
        jobs = [job for _, job in store.collection('live_jobs')]
        artifact = {'kind': 'isolated live verification; no legal approvals', 'initial': first, 'final': result, 'jobs': jobs}
        output = Path('.data/autonomous-live-verification.json')
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(artifact, indent=2), encoding='utf-8')
        calls = [call for job in jobs for call in job['calls'].values()]
        print(json.dumps({'artifact': str(output), 'jobs': [j['status'] for j in jobs],
            'completed_provider_calls': sum(c['status'] == 'COMPLETED' for c in calls),
            'reserved_usd': sum(j['reserved_usd'] for j in jobs),
            'agent_roles': sorted({t['agent'] for j in jobs for t in j.get('tasks', [])}),
            'legal_decisions': sum(c.get('decision') is not None for c in result['claims']),
            'source_outcomes': [s['status'] for s in result['automation']['sources']]}), flush=True)
        if not jobs or any(j['status'] == 'FAILED' for j in jobs) or not any(c['status'] == 'COMPLETED' for c in calls):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
