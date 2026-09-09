"""Optional persistent sessions for a local, single-host preview."""
import json
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path

from .session_store import SessionRecord, SessionStoreInterface


class SQLiteSessionStore(SessionStoreInterface):
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        Path(path).chmod(0o600)

    def create_session(self, record):
        with sqlite3.connect(self.path) as connection:
            connection.execute('INSERT INTO sessions VALUES (?, ?)', (record.session_id, json.dumps(asdict(record))))
        return True

    def get_session(self, session_id):
        with sqlite3.connect(self.path) as connection:
            row = connection.execute('SELECT data FROM sessions WHERE id=?', (session_id,)).fetchone()
        if not row:
            return None
        record = SessionRecord(**json.loads(row[0]))
        return None if record.revoked or record.expires_at <= time.time() else record

    def revoke_session(self, session_id):
        with sqlite3.connect(self.path) as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT data FROM sessions WHERE id=?', (session_id,)).fetchone()
            if not row:
                return False
            data = json.loads(row[0])
            data['revoked'] = True
            connection.execute('UPDATE sessions SET data=? WHERE id=?', (json.dumps(data), session_id))
        return True

    def is_revoked(self, session_id):
        return self.get_session(session_id) is None
