"""Dedicated worker HTTP service for Cloud Run or a local process.

Run with uvicorn backend.clearance.runtime:app --port 8081.
Cloud Run requires instance-based CPU allocation and at least one warm instance
for scheduled checks and queue recovery when no HTTP request is in progress.
"""
import os
import re
import threading
from contextlib import asynccontextmanager
from pathlib import PurePosixPath

from fastapi import FastAPI, HTTPException, Request

from .automation import ingest_file
from .store import get_store
from .worker import serve


@asynccontextmanager
async def lifespan(app):
    stop = threading.Event()
    worker = threading.Thread(target=serve, args=(stop,), name='clearance-worker', daemon=True)
    app.state.worker = worker
    worker.start()
    yield
    stop.set()
    worker.join(timeout=5)


app = FastAPI(title='Lienmark source worker', lifespan=lifespan)


@app.get('/health')
def health():
    alive = bool(getattr(app.state, 'worker', None) and app.state.worker.is_alive())
    if not alive:
        raise HTTPException(503, 'Worker is not running.')
    return {'status': 'running'}


def verify_event_identity(request):
    audience = os.getenv('CLEARANCE_EVENTARC_AUDIENCE')
    identity = os.getenv('CLEARANCE_EVENTARC_SERVICE_ACCOUNT')
    if not audience or not identity:
        raise HTTPException(503, 'Eventarc identity configuration is required.')
    authorization = request.headers.get('Authorization', '')
    if not authorization.startswith('Bearer '):
        raise HTTPException(401, 'A service identity token is required.')
    try:
        from google.auth.transport.requests import Request as AuthRequest
        from google.oauth2.id_token import verify_oauth2_token
        claims = verify_oauth2_token(authorization[7:], AuthRequest(), audience=audience)
        if claims.get('email') != identity or not claims.get('email_verified'):
            raise ValueError('Wrong service identity')
    except Exception:
        raise HTTPException(403, 'Invalid Eventarc service identity.') from None


@app.post('/eventarc')
async def eventarc(request: Request):
    verify_event_identity(request)
    try:
        envelope = await request.json()
    except ValueError:
        raise HTTPException(400, 'Malformed storage event.') from None
    event_type = request.headers.get('ce-type') or envelope.get('type')
    if event_type != 'google.cloud.storage.object.v1.finalized':
        raise HTTPException(400, 'Only finalized storage events are supported.')
    data = envelope.get('data', envelope)
    bucket_name = os.getenv('CLEARANCE_WATCH_BUCKET')
    if not bucket_name or data.get('bucket') != bucket_name:
        raise HTTPException(403, 'The bucket is not connected to this worker.')
    name = str(data.get('name', ''))
    match = re.fullmatch(r'(organizations/[A-Za-z0-9_-]{1,128}/productions/[A-Za-z0-9_-]{1,128})/(locked|agreements)/(.+)', name)
    if not match or '..' in PurePosixPath(name).parts:
        raise HTTPException(422, 'The object is outside a watched production folder.')
    root, folder, _ = match.groups()
    store = get_store()
    if not store.get(root + '/live_automation/policy'):
        raise HTTPException(403, 'The production has no authorized processing policy.')
    try:
        generation = int(data['generation'])
        from google.cloud import storage
        blob = storage.Client().bucket(bucket_name).blob(name, generation=generation)
        blob.reload()
        if (blob.size or 0) > 4_000_000:
            raise HTTPException(413, 'The document exceeds 4 MB.')
        ingest_file(store, root, 'revision' if folder == 'locked' else 'agreement', PurePosixPath(name).name,
            f'gs://{bucket_name}/{name}', lambda: blob.download_as_bytes(if_generation_match=generation),
            str(generation), PurePosixPath(name).parent.name)
    except HTTPException:
        raise
    except (ValueError, KeyError):
        raise HTTPException(422, 'A valid storage object generation is required.') from None
    except Exception:
        raise HTTPException(503, 'The storage event could not be durably recorded; retry delivery.') from None
    return {'status': 'recorded'}
