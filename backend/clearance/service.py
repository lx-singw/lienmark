"""Revision, snapshot and reviewer authority invariants shared by API and worker."""
import copy
import re
import uuid

from fastapi import HTTPException

from .models import Use, digest, now
from .store import Conflict


def scope(ctx, production_id, reviewer=False):
    if not ctx.user_id or ctx.auth_method not in ("session_cookie", "jwt", "api_key"):
        raise HTTPException(401, "A verified session is required.")
    roles = ("REVIEWER", "ADMIN") if reviewer else ("PRODUCER", "REVIEWER", "ADMIN")
    if str(ctx.production_roles.get(production_id, "")).upper() not in roles:
        raise HTTPException(403, "This action requires authority assigned to this production.")
    org = ctx.organization_id
    if not all(re.fullmatch(r"[A-Za-z0-9_-]{1,128}", v) for v in (org, production_id)):
        raise HTTPException(422, "Invalid production scope.")
    return f"organizations/{org}/productions/{production_id}"


def current(store, root):
    head = store.get(f"{root}/live_control/head") or {}
    snapshot = store.get(head["snapshot_path"]) if head.get("snapshot_path") else None
    job = store.get(head["pending_job"]) if head.get("pending_job") else None
    last = store.get(head["last_job"]) if head.get("last_job") else None
    from .automation import overview
    return {"snapshot": snapshot, "pending_audit": public_job(job) if job else None,
            "latest_audit": public_job(last) if last else None, "automation": overview(store, root),
            "claims": snapshot["claims"] if snapshot else [], "events": snapshot["events"] if snapshot else []}


def public_job(job):
    return {**{k: job.get(k) for k in ("audit_id", "revision_id", "status", "outcome", "status_url", "error", "reserved_usd", "tasks", "trigger", "created_at", "completed_at")},
            "calls": call_traces(job["calls"])}


def call_traces(calls):
    return {key: {**{k: v for k, v in call.items() if k != "result"}, "trace": call.get("result", {}).get("trace")} for key, call in calls.items()}


def submit(store, root, payload, actor, idempotency_key, source_event=None):
    if not idempotency_key or len(idempotency_key) > 200:
        raise HTTPException(422, "Supply an Idempotency-Key of at most 200 characters.")
    body = payload.model_dump(mode="json")
    rev, audit = "rev_" + uuid.uuid4().hex, "audit_" + uuid.uuid4().hex
    path = f"{root}/live_jobs/{audit}"
    idem = f"{root}/live_idempotency/{digest(idempotency_key)}"
    def commit(tx):
        existing = tx.get(idem)
        if existing:
            if existing["payload_hash"] != digest(body):
                raise Conflict("Idempotency key already used for another submission.")
            return public_job(tx.get(existing["job_path"]))
        head = tx.get(f"{root}/live_control/head") or {}
        if head.get("pending_job"):
            raise Conflict("A revision is already being investigated. Wait for its result.")
        if payload.parent_revision_id != head.get("revision_id"):
            raise Conflict("The baseline is missing or is no longer the current revision.")
        parent = tx.get(head["snapshot_path"]) if head.get("snapshot_path") else None
        if parent and parent["snapshot_id"] != payload.expected_parent_snapshot_id:
            raise Conflict("Baseline decisions changed. Refresh before submitting.")
        if parent and not payload.source_text:
            build_claims(body, parent)  # Reject unknown changes before accepting work.
        job = {"audit_id": audit, "revision_id": rev, "status": "QUEUED", "payload": body,
               "actor": actor, "parent_snapshot": head.get("snapshot_path"), "created_at": now(),
               "status_url": f"/api/clearance/productions/{payload.production_id}/audits/{audit}",
               "fence": 0, "lease_until": 0, "calls": {}, "reserved_usd": 0.0, "tasks": [],
               "trigger": {"kind": "manual", "name": "Revision submitted", "actor": actor}}
        if source_event:
            policy_path = f"{root}/live_automation/policy"
            policy = tx.get(policy_path) or {}
            if not policy.get("enabled") or policy.get("allocated_usd", 0) + policy.get("reserved_usd", 0) + payload.max_spend_usd > policy.get("total_allowance_usd", 0) + 1e-9:
                raise Conflict("Automatic research is paused or its allowance is exhausted.")
            event = tx.get(source_event)
            if not event or event["status"] != "QUEUED":
                raise Conflict("Source event is no longer queued.")
            policy["allocated_usd"] = policy.get("allocated_usd", 0) + payload.max_spend_usd
            job.update(source_event=source_event, trigger={"kind": event["kind"], "name": event["name"], "source_uri": event["source_uri"], "detected_at": event["created_at"]})
            tx.put(policy_path, policy)
            tx.put(source_event, {**event, "status": "PROCESSING", "job_path": path})
        tx.put(path, job)
        tx.put(f"{root}/live_revisions/{rev}", {"revision_id": rev, "submitted_at": now(), "actor": actor, "payload": body})
        tx.put(idem, {"payload_hash": digest(body), "job_path": path})
        tx.put(f"{root}/live_control/head", {**head, "pending_job": path, "last_job": path})
        return public_job(job)
    return store.atomic(commit)


def build_claims(body, parent, extracted=None):
    prior = {c["stable_lineage_key"]: c for c in (parent or {}).get("claims", []) if c["state"] != "removed"}
    uses = {k: copy.deepcopy(c["use"]) for k, c in prior.items()}
    if not parent or extracted is not None:
        entries = extracted if extracted is not None else body["initial_uses"]
        uses = {}
        for value in entries:
            if value["stable_lineage_key"] in uses:
                raise Conflict("Duplicate occurrence identifiers.")
            uses[value["stable_lineage_key"]] = Use.model_validate(value).model_dump()
    changed_keys = [c["stable_lineage_key"] for c in body["revised_uses"]]
    added_keys = [c["stable_lineage_key"] for c in body["added_uses"]]
    if len(set(changed_keys + added_keys + body["removed_use_keys"])) != len(changed_keys + added_keys + body["removed_use_keys"]):
        raise Conflict("An occurrence may be changed, added or removed only once.")
    for change in body["revised_uses"]:
        key = change["stable_lineage_key"]
        if key not in uses:
            raise Conflict("Changed occurrence is absent from the baseline.")
        uses[key] = Use.model_validate({**uses[key], **{k: v for k, v in change.items() if v is not None}}).model_dump()
    for use in body["added_uses"]:
        if use["stable_lineage_key"] in uses:
            raise Conflict("Added occurrence already exists.")
        uses[use["stable_lineage_key"]] = use
    for key in body["removed_use_keys"]:
        if key not in uses:
            raise Conflict("Removed occurrence is absent from the baseline.")
        del uses[key]
    if len(uses) > 20 or not uses:
        raise Conflict("A revision must contain between one and twenty occurrences.")
    for key, use in uses.items():
        if key in use["dependency_keys"] or set(use["dependency_keys"]) - (uses.keys() | prior.keys()):
            raise Conflict("Dependencies must name other recorded occurrences.")
    visited, visiting = set(), set()
    def visit(key):
        if key in visiting:
            raise Conflict("Dependency cycle detected. Clarify the work and rights relationships before investigation.")
        if key in visited or key not in uses:
            return
        visiting.add(key)
        for dependency in uses[key]["dependency_keys"]:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)
    for key in uses:
        visit(key)
    if set(body["revalidate_keys"]) - uses.keys():
        raise Conflict("Evidence revalidation must target a recorded occurrence.")
    changed = {k for k, u in uses.items() if k not in prior or digest(u) != digest(prior[k]["use"])} | (prior.keys() - uses.keys()) | set(body["revalidate_keys"])
    affected = downstream(uses, changed | {k for k, c in prior.items() if c["state"] not in ("carried_forward", "re_attested")})
    claims = []
    for key, use in uses.items():
        old = prior.get(key)
        preserved = bool(old and key not in affected)
        labels = {"description": "Creative asset", "asset_type": "Asset type", "scene_or_timecode": "Scene or timecode",
            "duration_or_prominence": "Duration or prominence", "context": "Creative context", "intended_territory": "Territory",
            "intended_media": "Media", "dependency_keys": "Recorded dependencies"}
        changes = [{"field": label, "before": old["use"].get(field), "after": use.get(field)} for field, label in labels.items()
                   if old and old["use"].get(field) != use.get(field)]
        dependent_on = [uses.get(dep, prior.get(dep, {}).get("use", {})).get("description", dep)
                        for dep in use["dependency_keys"] if dep in affected]
        basis = "Prior reviewer decision retained; the use and its dependencies are unchanged." if preserved else (
            "A new creative occurrence requires review." if not old else
            "Recorded creative facts changed." if changes else
            "Affected dependency: " + "; ".join(dependent_on) if dependent_on else
            "New evidence or a review directive requires revalidation." if key in body["revalidate_keys"] else
            "The prior occurrence has no current approval to carry forward.")
        claims.append({"claim_id": "claim_" + digest(key)[:24], "stable_lineage_key": key, "use": use,
            "description": use["description"], "asset_type": use["asset_type"], "scene": use["scene_or_timecode"],
            "prominence": use["duration_or_prominence"], "before": old["prominence"] if old else "No prior occurrence",
            "state": "carried_forward" if preserved else ("stale" if old else "new"),
            "reason_code": "Unchanged use and dependencies; prior reviewer decision retained." if preserved else "Use, dependency or unresolved decision requires investigation.",
            "decision": copy.deepcopy(old.get("decision")) if preserved else None,
            "evidence_citations": copy.deepcopy(old.get("evidence_citations", [])) if preserved else [],
            "investigation": copy.deepcopy(old.get("investigation")) if preserved else None,
            "directive": (old.get("decision") or {}).get("rationale") if old and old["state"] == "exception" else None})
        claims[-1].update(change_summary=changes, change_basis=basis, affected_dependencies=dependent_on,
                         baseline_snapshot_id=(parent or {}).get("snapshot_id"))
    for key in prior.keys() - uses.keys():
        claims.append({**copy.deepcopy(prior[key]), "state": "removed", "decision": None, "reason_code": "Occurrence removed from this revision."})
    return claims


def downstream(uses, affected):
    affected = set(affected)
    while True:
        expanded = affected | {k for k, u in uses.items() if affected.intersection(u["dependency_keys"])}
        if expanded == affected:
            return expanded
        affected = expanded


def seal(snapshot):
    snapshot["decisions"] = [{"decision_id": (c.get("decision") or {}).get("decision_id"),
        "stable_lineage_key": c["stable_lineage_key"], "status": c["state"],
        "counsel_rationale": (c.get("decision") or {}).get("rationale", "Awaiting reviewer decision")}
        for c in snapshot["claims"] if c["state"] != "removed"]
    snapshot["content_sha256"] = digest({k: v for k, v in snapshot.items() if k != "content_sha256"})
    return snapshot


def decide(store, root, claim_id, body, actor):
    def commit(tx):
        head = tx.get(f"{root}/live_control/head") or {}
        if head.get("pending_job") or head.get("revision_id") != body.revision_id:
            raise Conflict("The revision is not current or an investigation is pending.")
        snapshot = tx.get(head["snapshot_path"]) if head.get("snapshot_path") else None
        if not snapshot or snapshot["snapshot_id"] != body.expected_snapshot_id:
            raise Conflict("The snapshot changed. Refresh before recording a decision.")
        claim = next((c for c in snapshot["claims"] if c["claim_id"] == claim_id and c["state"] != "removed"), None)
        if not claim:
            raise HTTPException(404, "Claim does not exist in this revision.")
        known = {e["evidence_id"] for e in claim["evidence_citations"]}
        if set(body.evidence_ids) - known or (body.action == "sign_off" and not body.evidence_ids):
            raise HTTPException(422, "Sign-off requires evidence IDs attached to this claim.")
        if body.action == "sign_off" and not (claim.get("investigation") or {}).get("summary"):
            raise Conflict("Complete the investigation before signing off.")
        if body.action == "sign_off":
            dependencies = set(claim["use"]["dependency_keys"])
            approved = {c["stable_lineage_key"] for c in snapshot["claims"] if c["state"] in ("carried_forward", "re_attested")}
            if dependencies - approved:
                raise Conflict("Resolve the claim's dependent approvals before signing off.")
        decision = {"decision_id": "decision_" + uuid.uuid4().hex, "actor_id": actor, "created_at": now(),
                    "revision_id": body.revision_id, "basis_snapshot_id": body.expected_snapshot_id, **body.model_dump()}
        claim["decision"] = decision
        claim["state"] = "re_attested" if body.action == "sign_off" else "exception"
        claim["reason_code"] = body.rationale
        if body.action == "sign_off" and claim.get("clarification_id"):
            question_path = f"{root}/live_clarifications/{claim['clarification_id']}"
            question = tx.get(question_path)
            if question:
                tx.put(question_path, {**question, "status": "RESOLVED_BY_REVIEWER", "resolved_by": actor, "resolved_at": now()})
        if body.action == "reject":
            uses = {c["stable_lineage_key"]: c["use"] for c in snapshot["claims"] if c["state"] != "removed"}
            affected = downstream(uses, {claim["stable_lineage_key"]}) - {claim["stable_lineage_key"]}
            for c in snapshot["claims"]:
                if c["stable_lineage_key"] in affected:
                    c.update(state="stale", decision=None, reason_code="A dependency was rejected; revalidation is required.")
        prior_hash = snapshot["content_sha256"]
        snapshot.update(snapshot_id="snapshot_" + uuid.uuid4().hex, created_at=now(), previous_snapshot_sha256=prior_hash)
        event = {**decision, "event_id": decision["decision_id"], "timestamp": decision["created_at"],
                 "reviewer_name": actor, "stable_lineage_key": claim["stable_lineage_key"], "previous_snapshot_sha256": prior_hash}
        event["event_hash"] = digest(event)
        snapshot["events"] = [*snapshot["events"][-99:], event]
        seal(snapshot)
        path = f"{root}/live_revisions/{body.revision_id}/snapshots/{snapshot['snapshot_id']}"
        tx.put(path, snapshot)
        tx.put(f"{root}/live_control/head", {**head, "snapshot_path": path})
        if body.action == "reject":
            from .automation import record_event
            from .models import SourceInput
            record_event(tx, root, SourceInput(kind="directive", name="Reviewer requested reinvestigation",
                text=body.rationale, claim_keys=[claim["stable_lineage_key"]]), actor, decision["decision_id"])
        return snapshot
    return store.atomic(commit)
