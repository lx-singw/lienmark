"""Read-only smoke check of an already running authenticated workspace.

Does not deploy, upload, initiate research, create sessions or record decisions.
Provide an existing session cookie through LIENMARK_VERIFY_COOKIE, never an argument.
"""
import argparse
import json
import os
from urllib.parse import urlparse

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--production', required=True)
    args = parser.parse_args()
    import re
    parsed = urlparse(args.url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        parser.error('Supply only the application origin, without credentials, path or query.')
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1')):
        parser.error('Use HTTPS, or a local HTTP preview.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', args.production):
        parser.error('Invalid production identifier.')
    cookie = os.getenv('LIENMARK_VERIFY_COOKIE')
    if not cookie:
        parser.error('Supply an existing session cookie in LIENMARK_VERIFY_COOKIE.')
    with httpx.Client(base_url=args.url.rstrip('/'), timeout=25, follow_redirects=False) as client:
        endpoint = '/api/clearance/productions/' + args.production
        anonymous = client.get(endpoint)
        if anonymous.status_code not in (401, 403):
            raise RuntimeError('Anonymous access to production records was not denied.')
        client.cookies.set('lienmark_session', cookie)
        response = client.get(endpoint)
        response.raise_for_status()
        state = response.json()
        if not state.get('snapshot') or state.get('pending_audit'):
            raise RuntimeError('A completed, stable snapshot is required for this verification.')
        snapshot = state['snapshot']
        path = endpoint + f"/revisions/{snapshot['revision_id']}/snapshots/{snapshot['snapshot_id']}"
        record = client.get(path + '/execution-record')
        record.raise_for_status()
        body = record.json()
        from backend.clearance.models import digest
        sha = body.pop('record_sha256')
        if sha != digest(body) or body['snapshot'] != snapshot:
            raise RuntimeError('Execution record integrity or snapshot identity did not match.')
        completed = [c for c in body['execution']['calls'].values() if c['status'] == 'COMPLETED']
        if not completed or any(c.get('trace', {}).get('orchestration', {}).get('framework') != 'Google ADK' for c in completed):
            raise RuntimeError('Completed ADK execution was not proven for this snapshot.')
        pdf = client.get(path + '/pdf')
        pdf.raise_for_status()
        if not pdf.content.startswith(b'%PDF-') or pdf.headers.get('x-snapshot-sha256') != snapshot['content_sha256']:
            raise RuntimeError('PDF integrity or snapshot identity did not match.')
        print(json.dumps({'authenticated_workspace': True, 'anonymous_access_denied': True,
            'adk_calls_proven': len(completed), 'execution_record_integrity': True, 'pdf_snapshot_parity': True,
            'worker_heartbeat': bool(state['automation']['worker_available']),
            'not_tested': ['Eventarc delivery', 'cloud worker restart', 'human legal review', 'managed Agent Engine deployment']}))


if __name__ == '__main__':
    main()
