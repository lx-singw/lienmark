"""Atomic durable document storage. Cloud failures never switch to memory."""
import copy
import json
import os
import sqlite3
from functools import lru_cache
from pathlib import Path


class Conflict(Exception):
    pass


class Transaction:
    def __init__(self, read):
        self.read = read
        self.cache = {}
        self.writes = {}

    def get(self, path):
        if path not in self.cache:
            self.cache[path] = self.read(path)
        return copy.deepcopy(self.writes.get(path, self.cache[path]))

    def put(self, path, data):
        if len(json.dumps(data).encode()) > 850000:
            raise ValueError("Record exceeds storage limit")
        self.writes[path] = copy.deepcopy(data)


class SQLiteStore:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=30) as db:
            try:
                db.execute("PRAGMA journal_mode=WAL")
            except sqlite3.OperationalError:
                pass
            db.execute("CREATE TABLE IF NOT EXISTS documents (path TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    def atomic(self, callback):
        with sqlite3.connect(self.path, timeout=30) as db:
            db.execute("BEGIN IMMEDIATE")
            def read(path):
                row = db.execute("SELECT payload FROM documents WHERE path=?", (path,)).fetchone()
                return json.loads(row[0]) if row else None
            tx = Transaction(read)
            result = callback(tx)
            for path, data in tx.writes.items():
                db.execute("INSERT INTO documents VALUES (?,?) ON CONFLICT(path) DO UPDATE SET payload=excluded.payload", (path, json.dumps(data)))
            return result

    def get(self, path):
        return self.atomic(lambda tx: tx.get(path))

    def pending(self):
        with sqlite3.connect(self.path, timeout=30) as db:
            rows = db.execute("SELECT path,payload FROM documents WHERE path LIKE '%/live_jobs/%'").fetchall()
        return [(p, json.loads(d)) for p, d in rows if json.loads(d)["status"] in ("QUEUED", "PROCESSING")]

    def collection(self, name, root=None, statuses=None):
        with sqlite3.connect(self.path, timeout=30) as db:
            rows = db.execute("SELECT path,payload FROM documents WHERE path LIKE ?", (f'{root}/{name}/%' if root else f'%/{name}/%',)).fetchall()
        return [(p, json.loads(d)) for p, d in rows if p.split('/')[-2] == name
                and (not root or p.startswith(f'{root}/{name}/')) and (not statuses or json.loads(d).get('status') in statuses)]


class FirestoreStore:
    def __init__(self):
        from google.cloud import firestore
        self.db = firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID"))

    def atomic(self, callback):
        from google.cloud import firestore
        @firestore.transactional
        def run(native):
            def read(path):
                doc = self.db.document(path).get(transaction=native)
                return doc.to_dict() if doc.exists else None
            tx = Transaction(read)
            result = callback(tx)
            # All reads precede writes, including callback reads after staged puts.
            for path, data in tx.writes.items():
                native.set(self.db.document(path), data)
            return result
        return run(self.db.transaction())

    def get(self, path):
        doc = self.db.document(path).get()
        return doc.to_dict() if doc.exists else None

    def pending(self):
        from google.cloud.firestore_v1.base_query import FieldFilter
        return [(d.reference.path, d.to_dict()) for d in self.db.collection_group("live_jobs").where(filter=FieldFilter("status", "in", ["QUEUED", "PROCESSING"])).stream()]

    def collection(self, name, root=None, statuses=None):
        query = self.db.collection(f'{root}/{name}') if root else self.db.collection_group(name)
        if statuses:
            from google.cloud.firestore_v1.base_query import FieldFilter
            query = query.where(filter=FieldFilter('status', 'in', statuses))
        return [(d.reference.path, d.to_dict()) for d in query.stream()]


@lru_cache
def get_store():
    if os.getenv("K_SERVICE") or os.getenv("FIRESTORE_EMULATOR_HOST") or os.getenv("CLEARANCE_STORE") == "firestore":
        return FirestoreStore()
    return SQLiteStore(os.getenv("CLEARANCE_SQLITE_PATH", ".data/clearance.sqlite3"))
