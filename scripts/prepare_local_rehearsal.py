"""Prepare a separate local production and private invitations; never approve claims."""
import argparse
import hashlib
import os
import re
import secrets
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--production', default='last_rehearsal')
    parser.add_argument('--allowance', required=True, type=float)
    parser.add_argument('--start', action='store_true', help='Place the baseline in the watched folder for real automatic research')
    parser.add_argument('--renew-invites', action='store_true', help='Issue replacement private links for an existing local rehearsal without resetting its records or allowance')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', args.production) or not .8 <= args.allowance <= 3:
        parser.error('Use a valid production identifier and a bounded allowance between $0.80 and $3.')
    if os.getenv('K_SERVICE') or os.getenv('CLEARANCE_STORE') == 'firestore':
        parser.error('This preparation command is local only.')
    os.environ.update(USE_LOCAL_STORAGE='true', BUDGET_STORE_MODE='local_disk')
    from backend.clearance.store import SQLiteStore
    from backend.clearance.models import AutomationPolicy
    from backend.clearance.automation import save_policy
    from backend.storage.invite_store import LocalInviteStore
    root = 'organizations/demonstration_studio/productions/' + args.production
    store = SQLiteStore(os.getenv('CLEARANCE_SQLITE_PATH', '.data/clearance.sqlite3'))
    existing = store.get(root + '/live_automation/policy')
    if existing and not args.renew_invites:
        parser.error('That rehearsal already exists. Choose a new identifier; existing work is never reset.')
    if args.renew_invites and (not existing or args.start):
        parser.error('Renewal requires an existing rehearsal and cannot start another baseline.')
    if not existing:
        save_policy(store, root, AutomationPolicy(enabled=True, per_run_usd=.8,
            total_allowance_usd=args.allowance, production_name='The Last Rehearsal — demonstration'), 'local-production-owner')
    folder = Path(os.getenv('CLEARANCE_WATCH_ROOT', '.data/watch')) / root / 'locked'
    folder.mkdir(parents=True, exist_ok=True)
    invites = LocalInviteStore()
    links = []
    for role in ('producer', 'reviewer'):
        token = secrets.token_urlsafe(32)
        invites.create_invite(hashlib.sha256(token.encode()).hexdigest(), role, 'demonstration_studio', args.production,
            max_uses=1, expires_in=86400)
        links.append(f'- {role.capitalize()}: http://localhost:3100/?invite={token}')
    output = Path('.data') / (args.production + '-private-access.md')
    output.write_text('# Private local rehearsal access\n\nSingle-use invitations, valid for 24 hours. Use separate browser profiles. Do not publish.\n\n' + '\n'.join(links) + '\n\nThe reviewer role is scoped only to this fictional production. No decision is pre-recorded.\n')
    output.chmod(0o600)
    if args.start:
        packet = Path(__file__).resolve().parents[1] / 'demo/live-clearance/baseline.json'
        (folder / 'baseline.json').write_bytes(packet.read_bytes())
    print(f'Prepared {root}. Private invitations: {output}. Watched folder: {folder}. No reviewer decisions recorded.')


if __name__ == '__main__':
    main()
