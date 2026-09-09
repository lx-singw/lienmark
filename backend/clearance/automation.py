"""Durable, production-scoped source inbox and automatic dispatch.

No browser process owns this loop. Queue records survive process termination.
An allowance is reserved transactionally before an automatic job is accepted.
"""
import os
import time
from pathlib import Path

from .models import SourceInput, RevisionInput, digest, now
from .store import Conflict


def records(store, root, collection):
    return store.collection(collection, root=root)


def overview(store, root):
    policy = store.get(f"{root}/live_automation/policy") or {"enabled": False}
    events = sorted(records(store, root, "live_sources"), key=lambda v: v[1]["created_at"], reverse=True)[:30]
    questions = records(store, root, "live_clarifications")
    heartbeat = store.get('system/runtime/clearance/worker') or {}
    return {"policy": policy, "worker_available": time.time() - heartbeat.get("timestamp", 0) < 90,
        "worker_seen_at": heartbeat.get("seen_at"),
        "sources": [{k: v for k, v in d.items() if k not in ("text", "claim_keys")} for _, d in events],
        "clarifications": [d for _, d in questions if d["status"] != "SUPERSEDED"],
        "folder": f"{root}/locked/", "agreement_folder": f"{root}/agreements/",
        "storage_configured": bool(os.getenv("CLEARANCE_WATCH_ROOT") or os.getenv("CLEARANCE_WATCH_BUCKET"))}


def save_policy(store, root, payload, actor):
    def commit(tx):
        path = f"{root}/live_automation/policy"
        old = tx.get(path) or {}
        reserved, allocated = old.get("reserved_usd", 0), old.get("allocated_usd", 0)
        if payload.total_allowance_usd < reserved + allocated:
            raise Conflict("The allowance cannot be lower than existing reservations.")
        policy = {**old, **payload.model_dump(), "reserved_usd": reserved, "allocated_usd": allocated,
                  "authorized_by": actor, "updated_at": now()}
        tx.put(path, policy)
        return policy
    return store.atomic(commit)


def record_event(tx, root, source, actor, identity=None):
    data = source.model_dump()
    key = digest(identity or {"kind": source.kind, "text": source.text, "clarification": source.clarification_id, "keys": source.claim_keys})
    path = f"{root}/live_sources/{key}"
    old = tx.get(path)
    if old:
        return {"event_id": key, "status": old["status"], "duplicate": True}
    event = {**data, "event_id": key, "actor": actor, "created_at": now(), "status": "QUEUED",
             "content_sha256": digest(source.text)}
    tx.put(path, event)
    return {"event_id": key, "status": "QUEUED", "duplicate": False}


def ingest(store, root, source, actor, identity=None):
    if source.kind in ("revision", "agreement") and len(source.text.strip()) < 20:
        raise Conflict("The document has too little readable text. Supply a text PDF, screenplay, cue sheet or agreement.")
    return store.atomic(lambda tx: record_event(tx, root, source, actor, identity))


def settle(tx, root, job, status, reason=None):
    if not job.get("source_event"):
        return
    path = f"{root}/live_automation/policy"
    policy = tx.get(path)
    event = tx.get(job["source_event"])
    if not event or event["status"] != "PROCESSING":
        return
    policy["allocated_usd"] = max(0, policy.get("allocated_usd", 0) - job["payload"]["max_spend_usd"])
    policy["reserved_usd"] = policy.get("reserved_usd", 0) + job["reserved_usd"]
    tx.put(path, policy)
    tx.put(job["source_event"], {**event, "status": status, "reason": reason, "completed_at": now()})


def dispatch(store):
    from .service import submit
    for event_path, event in sorted(store.collection("live_sources", statuses=["QUEUED"]), key=lambda v: v[1]["created_at"]):
        if event["status"] != "QUEUED":
            continue
        root = event_path.rsplit('/live_sources/', 1)[0]
        policy = store.get(f"{root}/live_automation/policy") or {}
        if not policy.get("enabled"):
            continue
        head = store.get(f"{root}/live_control/head") or {}
        if head.get("pending_job"):
            continue
        snapshot = store.get(head["snapshot_path"]) if head.get("snapshot_path") else None
        if event["kind"] != "revision" and not snapshot:
            continue
        body = {"production_id": root.rsplit('/', 1)[1], "max_spend_usd": policy["per_run_usd"], "agentic": True}
        if snapshot:
            body.update(parent_revision_id=snapshot["revision_id"], expected_parent_snapshot_id=snapshot["snapshot_id"])
        if event["kind"] == "revision":
            body["source_text"] = event["text"]
        else:
            valid = {c["stable_lineage_key"] for c in snapshot["claims"] if c["state"] != "removed"}
            body["revalidate_keys"] = [k for k in event["claim_keys"] if k in valid]
        try:
            submit(store, root, RevisionInput(**body), "automation:" + policy["authorized_by"], event["event_id"], event_path)
        except Conflict as exc:
            def explain(tx):
                latest = tx.get(event_path)
                if latest and latest["status"] == "QUEUED":
                    tx.put(event_path, {**latest, "reason": str(exc)})
            store.atomic(explain)
            continue  # Remains durable; another worker or a policy change can unblock it.


def schedule_evidence(store, clock=None):
    clock = clock or time.time()
    for path, policy in store.collection("live_automation"):
        if not policy.get("enabled") or not policy.get("watch_evidence"):
            continue
        root = path.rsplit('/live_automation/', 1)[0]
        head = store.get(f"{root}/live_control/head") or {}
        snapshot = store.get(head["snapshot_path"]) if head.get("snapshot_path") else None
        if not snapshot:
            continue
        slot = int(clock // (policy["evidence_interval_hours"] * 3600))
        for claim in snapshot["claims"]:
            if claim["state"] not in ("carried_forward", "re_attested") or not claim["evidence_citations"]:
                continue
            source = SourceInput(kind="evidence", name="Scheduled evidence check: " + claim["description"][:150],
                claim_keys=[claim["stable_lineage_key"]])
            ingest(store, root, source, "evidence-monitor", f"evidence:{slot}:{claim['claim_id']}")


def decode_document(name, raw):
    if len(raw) > 4_000_000:
        raise Conflict("Documents must be smaller than 4 MB.")
    suffix = Path(name).suffix.lower()
    if suffix == '.pdf':
        import io
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(raw))
            if len(reader.pages) > 60:
                raise Conflict("This workspace supports up to 60 PDF pages per document.")
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        except Conflict:
            raise
        except Exception:
            raise Conflict("The PDF could not be read. Supply a text PDF or plain text export.") from None
    elif suffix in ('.txt', '.fountain', '.json', '.md', '.fdx'):
        try:
            text = raw.decode('utf-8-sig')
            if suffix == '.fdx':
                import defusedxml.ElementTree as ET
                text = '\n'.join(ET.fromstring(text).itertext())
        except Exception:
            raise Conflict("The document is not a supported UTF-8 text export.") from None
    else:
        raise Conflict("Use PDF, TXT, Fountain, FDX, Markdown or a structured JSON cut.")
    if not 20 <= len(text.strip()) <= 24000:
        raise Conflict("Readable document text must contain 20–24,000 characters. Scanned PDFs need OCR before upload.")
    return text.strip()


def poll_folders(store):
    """Restricted server-configured roots only; no client-supplied filesystem paths."""
    local_root = os.getenv("CLEARANCE_WATCH_ROOT")
    bucket_name = os.getenv("CLEARANCE_WATCH_BUCKET")
    if not local_root and not bucket_name:
        return
    for path, policy in store.collection("live_automation"):
        if not policy.get("enabled"):
            continue
        root = path.rsplit('/live_automation/', 1)[0]
        if local_root:
            base = Path(local_root).resolve()
            for kind, folder in (("revision", "locked"), ("agreement", "agreements")):
                directory = (base / root / folder).resolve()
                if directory != base / root / folder or not directory.is_relative_to(base) or not directory.exists():
                    continue
                for file in directory.rglob('*'):
                    if not file.is_file() or not file.resolve().is_relative_to(directory) or file.name.startswith('.'):
                        continue
                    if file.stat().st_size <= 4_000_000:
                        ingest_file(store, root, kind, file.name, file.as_uri(), lambda f=file: f.read_bytes(), str(file.stat().st_mtime_ns), file.parent.name)
        if bucket_name:
            from google.cloud import storage
            bucket = storage.Client().bucket(bucket_name)
            for kind, folder in (("revision", "locked"), ("agreement", "agreements")):
                for blob in bucket.list_blobs(prefix=f'{root}/{folder}/'):
                    if blob.name.endswith('/'):
                        continue
                    if (blob.size or 0) > 4_000_000:
                        continue
                    ingest_file(store, root, kind, Path(blob.name).name, f'gs://{bucket_name}/{blob.name}',
                        lambda b=blob: b.download_as_bytes(if_generation_match=b.generation), str(blob.generation), Path(blob.name).parent.name)


def ingest_file(store, root, kind, name, uri, read, generation, parent):
    marker = f"{root}/live_files/{digest([uri, generation])}"
    if store.get(marker):
        return
    try:
        text = decode_document(name, read())
        import re
        question = parent if re.fullmatch(r'clarification_[a-f0-9]{24}', parent) else None
        source = SourceInput(kind=kind, name=name[:200], text=text, source_uri=uri, clarification_id=question)
        def commit(tx):
            result = record_event(tx, root, source, "storage-watcher")
            tx.put(marker, {"observed_at": now(), **result})
        store.atomic(commit)
    except Conflict as exc:
        def fail(tx):
            tx.put(marker, {"observed_at": now(), "error": str(exc)})
            tx.put(f"{root}/live_sources/{digest([uri, generation])}", {"event_id": digest([uri, generation]),
                "kind": kind, "name": name[:200], "source_uri": uri, "created_at": now(), "status": "FAILED", "reason": str(exc)})
        store.atomic(fail)
