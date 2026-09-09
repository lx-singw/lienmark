"""Run `python -m backend.clearance.worker` as a persistent worker service."""
import logging
import threading
import time
import uuid
import copy
import json
from contextlib import contextmanager
from datetime import datetime

from .models import now, digest, Use
from .providers import Providers, ProviderError, InvalidResponse, TransientResponse
from .service import build_claims, seal, call_traces
from .store import Conflict, get_store

logger = logging.getLogger(__name__)
LEASE_SECONDS = 180


class Worker:
    def __init__(self, store, providers=None):
        self.store = store
        self.providers = providers or Providers()

    def acquire(self, path):
        def commit(tx):
            job = tx.get(path)
            if not job or job["status"] not in ("QUEUED", "PROCESSING") or job["lease_until"] > time.time():
                return None
            if job["status"] == "PROCESSING":
                job.setdefault("recoveries", []).append({"recovered_at": now(), "previous_fence": job["fence"],
                    "completed_calls_reused": sum(c["status"] == "COMPLETED" for c in job["calls"].values()),
                    "reason": "Previous worker lease expired; completed results retained."})
            job.update(status="PROCESSING", fence=job["fence"] + 1, lease_until=time.time() + LEASE_SECONDS)
            tx.put(path, job)
            return job
        return self.store.atomic(commit)

    def update(self, path, fence, change):
        def commit(tx):
            job = tx.get(path)
            if not job or job["fence"] != fence or job["status"] != "PROCESSING" or job["lease_until"] <= time.time():
                raise Conflict("Worker lease lost; stale writes rejected.")
            change(job)
            job["lease_until"] = time.time() + LEASE_SECONDS
            tx.put(path, job)
            tx.put('system/runtime/clearance/worker', {"timestamp": time.time(), "seen_at": now()})
            return job
        return self.store.atomic(commit)

    def call(self, path, fence, key, reservation, callback):
        old = self.store.get(path)["calls"].get(key)
        if old:
            if old["status"] == "COMPLETED":
                return old["result"]
            if old.get("retryable") and not key.endswith(":retry"):
                return self.retry_call(path, fence, key, reservation, callback)
            if old.get("repairable"):
                raise InvalidResponse(old["error"])
            raise ProviderError("A previous provider call has an uncertain or failed outcome. It will not be charged again automatically.")
        def reserve(job):
            if job["reserved_usd"] + reservation > job["payload"]["max_spend_usd"] + 1e-9:
                raise ProviderError("Investigation reservation budget exhausted.")
            job["reserved_usd"] += reservation
            job["calls"][key] = {"status": "STARTED", "started_at": now(), "reserved_usd": reservation}
        self.update(path, fence, reserve)
        try:
            result = callback()
        except ProviderError as exc:
            self.update(path, fence, lambda j: j["calls"][key].update(status="FAILED", error=str(exc), repairable=isinstance(exc, InvalidResponse), retryable=isinstance(exc, TransientResponse)))
            if isinstance(exc, TransientResponse) and not key.endswith(":retry"):
                return self.retry_call(path, fence, key, reservation, callback)
            raise
        result.setdefault("trace", {})["correlation"] = {"audit_id": path.rsplit("/", 1)[1], "call_id": key, "fence": fence}
        self.update(path, fence, lambda j: j["calls"][key].update(status="COMPLETED", result=result, completed_at=now()))
        return result

    def retry_call(self, path, fence, key, reservation, callback):
        with self.task(path, fence, key + ":retry", "Provider recovery", "Retry one explicit transient provider failure within the remaining allowance", "Provider response") as task:
            time.sleep(1)
            result = self.call(path, fence, key + ":retry", reservation, callback)
            task["outcome"] = "The retry returned a validated result. Both attempts remain recorded."
            return result

    def model_call(self, path, fence, key, callback):
        try:
            return self.call(path, fence, key, .05, callback)
        except InvalidResponse:
            with self.task(path, fence, key + ":repair", "Response validation", "Repair invalid model output using the same attached evidence", "Rights researcher") as task:
                result = self.call(path, fence, key + ":repair", .05, callback)
                task["outcome"] = "A replacement response passed schema and evidence-reference validation."
                return result

    @contextmanager
    def task(self, path, fence, key, agent, objective, handoff=None):
        started = now()
        def begin(job):
            tasks = job.setdefault("tasks", [])
            if not any(t["task_id"] == key for t in tasks):
                tasks.append({"task_id": key, "agent": agent, "objective": objective,
                    "handoff_from": handoff, "status": "WORKING", "started_at": started})
        self.update(path, fence, begin)
        result = {}
        try:
            yield result
        except Exception as exc:
            self.update(path, fence, lambda j: next(t for t in j["tasks"] if t["task_id"] == key).update(
                status="BLOCKED", outcome=str(exc)[:1000], completed_at=now()))
            raise
        else:
            self.update(path, fence, lambda j: next(t for t in j["tasks"] if t["task_id"] == key).update(
                status="COMPLETED", outcome=result.get("outcome", "Task completed"),
                output_sha256=digest(result), completed_at=now()))

    def investigate(self, path, fence, claim):
        existing = self.store.get(path)["calls"]
        if any(k.startswith(claim["claim_id"] + ":") and (c["status"] == "STARTED" or c["status"] == "FAILED" and not c.get("repairable") and not c.get("retryable")) for k, c in existing.items()):
            for key, call in existing.items():
                if key.startswith(claim["claim_id"] + ":") and call["status"] == "COMPLETED":
                    if key.endswith(":search"):
                        claim["evidence_citations"].extend(call["result"]["evidence"])
                    if key.endswith(":assessment"):
                        claim["investigation"] = copy.deepcopy(call["result"]["output"])
            raise ProviderError("A previous provider call has an uncertain or failed outcome. Reconcile it before further research.")
        evidence = copy.deepcopy(claim.get("agreement_evidence", []) + claim.get("prior_evidence", []))
        query = f'{claim["description"]} {claim["asset_type"]} rights ownership'[:300]
        agentic = self.store.get(path)["payload"].get("agentic", True)
        search_required = True
        if agentic:
            with self.task(path, fence, claim["claim_id"] + ":plan", "Investigation planner", claim["description"], "Change coordinator") as task:
                plan = self.call(path, fence, claim["claim_id"] + ":plan", .05, lambda: self.providers.plan(claim["use"], claim.get("directive"), evidence))
                claim["research_plan"] = plan["output"]
                query = plan["output"]["public_query"]
                task["outcome"] = plan["output"]["objective"] + " Stop when: " + plan["output"]["stop_condition"]
                if plan["output"]["strategy"] == "request_information" and plan["output"]["private_facts_needed"] and not claim.get("agreement_evidence"):
                    claim["investigation"] = {"summary": plan["output"]["objective"], "missing_facts": plan["output"]["private_facts_needed"], "cited_ids": [], "next_query": None}
                    claim["reason_code"] = "Investigation paused for the private facts identified by the planner."
                    claim["revalidation_action"] = "; ".join(plan["output"]["private_facts_needed"])
                    return
                search_required = not (plan["output"]["strategy"] == "review_documents" and evidence)
        for round_number in range(3 if agentic else 2):
            prefix = f'{claim["claim_id"]}:{round_number}'
            with self.task(path, fence, prefix + ":research", "Rights researcher", query if search_required else "Assess the arriving document against retained evidence", "Evidence reviewer" if round_number else "Investigation planner") as task:
                if search_required:
                    found = self.call(path, fence, prefix + ":search", .01, lambda: self.providers.search(query))
                    evidence.extend(found["evidence"])
                claim["evidence_citations"] = evidence
                if not evidence:
                    claim["reason_code"] = "Live search returned no attributable evidence. Reviewer investigation is required."
                    task["outcome"] = claim["reason_code"]
                    return
                assessed = self.model_call(path, fence, prefix + ":assessment",
                    lambda: self.providers.assess(claim["use"], evidence, claim.get("directive")))
                task["outcome"] = assessed["output"]["summary"]
            claim["investigation"] = assessed["output"]
            claim["reason_code"] = assessed["output"]["summary"]
            claim["revalidation_action"] = "; ".join(assessed["output"]["missing_facts"]) or "Review the findings and supporting sources."
            next_query = assessed["output"].get("next_query")
            if agentic:
                with self.task(path, fence, prefix + ":review", "Evidence reviewer", "Check source support, contradictions and missing private facts", "Rights researcher") as task:
                    reviewed = self.model_call(path, fence, prefix + ":review", lambda: self.providers.review(claim["use"], evidence, assessed["output"]))
                    output = reviewed["output"]
                    claim["evidence_review"] = output
                    claim["investigation"]["missing_facts"] = output["missing_facts"]
                    claim["revalidation_action"] = "; ".join(output["missing_facts"]) or "Review the supported finding."
                    task["outcome"] = output["explanation"]
                    next_query = output["next_query"] if output["verdict"] == "research" else None
            if not next_query or next_query == query:
                break
            query = next_query
            search_required = True
        if agentic and claim.get("evidence_review", {}).get("verdict") == "research":
            claim["investigation_error"] = "Research limit reached before the evidence reviewer accepted the finding."

    def run(self, path):
        job = self.acquire(path)
        if not job:
            return
        root = path.rsplit("/live_jobs/", 1)[0]
        fence = job["fence"]
        try:
            parent = self.store.get(job["parent_snapshot"]) if job["parent_snapshot"] else None
            source = self.store.get(job["source_event"]) if job.get("source_event") else None
            target_keys = None
            agreement = None
            if source and source["kind"] in ("agreement", "evidence", "directive"):
                target_keys, agreement = self.prepare_source(path, root, fence, source, parent)
                if not target_keys:
                    outcome = "WAITING_FOR_MATCH" if source["kind"] == "agreement" else "INCONCLUSIVE" if self.store.get(path).get("monitor_uncertain") else "NO_CHANGE"
                    self.complete_without_change(path, root, fence, job["parent_snapshot"], outcome)
                    return
            extracted = None
            if job["payload"]["source_text"]:
                with self.task(path, fence, "intake", "Document intake", "Read the new cut and align its occurrences with the baseline", "Source watcher") as task:
                    text = job["payload"]["source_text"]
                    try:
                        document = json.loads(text)
                    except ValueError:
                        document = None
                    if isinstance(document, dict) and "uses" in document:
                        extracted = [Use.model_validate(u).model_dump() for u in document["uses"]]
                    else:
                        result = self.call(path, fence, "intake", .05, lambda: self.providers.extract(text, [c["use"] for c in (parent or {}).get("claims", []) if c["state"] != "removed"]))
                        extracted = result["output"]["uses"]
                    task["outcome"] = f"Identified {len(extracted)} creative occurrences."
            with self.task(path, fence, "scope", "Change coordinator", "Preserve unaffected decisions and assign only affected occurrences", "Document intake" if extracted else "Source watcher") as task:
                body = {**job["payload"]}
                if target_keys:
                    body["revalidate_keys"] = target_keys
                claims = build_claims(body, parent, extracted)
                if target_keys:
                    from .service import downstream
                    target_keys = downstream({c["stable_lineage_key"]: c["use"] for c in claims}, target_keys)
                    prior = {c["stable_lineage_key"]: c for c in parent["claims"]}
                    claims = [c if c["stable_lineage_key"] in target_keys else copy.deepcopy(prior[c["stable_lineage_key"]]) for c in claims]
                    for c in claims:
                        if c["stable_lineage_key"] not in target_keys and c["state"] == "re_attested":
                            c["state"] = "carried_forward"
                task["outcome"] = f"{sum(c['state'] == 'carried_forward' for c in claims)} approvals preserved; affected work assigned to research."
            for claim in claims:
                if claim["state"] in ("carried_forward", "removed") or (target_keys is not None and claim["stable_lineage_key"] not in target_keys):
                    continue
                if agreement:
                    claim["agreement_evidence"] = [agreement]
                    claim["prior_evidence"] = next((c.get("evidence_citations", []) for c in parent["claims"] if c["claim_id"] == claim["claim_id"]), [])
                if source and source["kind"] == "directive":
                    claim["directive"] = source["text"]
                try:
                    self.investigate(path, fence, claim)
                except ProviderError as exc:
                    claim["reason_code"] = str(exc)
                    claim["investigation_error"] = str(exc)
            last_agent = self.store.get(path)["tasks"][-1]["agent"]
            with self.task(path, fence, "delivery", "Delivery coordinator", "Record open questions and prepare the updated Exceptions Schedule", last_agent) as task:
                task["outcome"] = f"{sum(bool((c.get('investigation') or {}).get('missing_facts')) for c in claims)} claims need information; {sum(bool(c.get('investigation_error')) for c in claims)} investigations need attention. Authorized reviewer decisions remain required."
            self.finish(path, root, fence, claims, parent, target_keys)
        except Exception as exc:
            message = str(exc) if isinstance(exc, (ProviderError, Conflict)) else "Investigation failed. Inspect worker logs before retrying."
            logger.error("Revision investigation failed (%s)", type(exc).__name__)
            def fail(tx):
                latest = tx.get(path)
                head = tx.get(f"{root}/live_control/head") or {}
                if latest["fence"] != fence or latest["lease_until"] <= time.time() or latest["status"] != "PROCESSING":
                    return
                tx.put(path, {**latest, "status": "FAILED", "error": message})
                from .automation import settle
                settle(tx, root, latest, "FAILED", message)
                if head.get("pending_job") == path:
                    tx.put(f"{root}/live_control/head", {**head, "pending_job": None})
            self.store.atomic(fail)

    def prepare_source(self, path, root, fence, source, parent):
        from .automation import records
        if source["kind"] == "directive":
            valid = {c["stable_lineage_key"] for c in parent["claims"] if c["state"] != "removed"}
            return [k for k in source["claim_keys"] if k in valid], None
        if source["kind"] == "agreement":
            questions = [d for _, d in records(self.store, root, "live_clarifications") if d["status"] == "PENDING"]
            with self.task(path, fence, "agreement-match", "Agreement matcher", "Identify the exact outstanding question this document addresses", "Source watcher") as task:
                matched = next((q for q in questions if q["clarification_id"] == source.get("clarification_id")), None)
                if not matched and not source.get("clarification_id") and questions:
                    result = self.call(path, fence, "agreement-match", .05, lambda: self.providers.match_agreement(source["text"], questions))
                    if result["output"]["supports_match"]:
                        matched = next((q for q in questions if q["clarification_id"] == result["output"]["clarification_id"]), None)
                if not matched:
                    task["outcome"] = "No unambiguous open question matched. Document retained for assignment."
                    return [], None
                task["outcome"] = "Matched: " + matched["description"] + ". Resuming its dependent investigation."
                evidence = {"evidence_id": "agreement_" + source["event_id"][:24], "title": source["name"],
                    "url": f"/api/clearance/productions/{root.rsplit('/', 1)[1]}/documents/{source['event_id']}",
                    "excerpt": source["text"], "provider": "Production document", "retrieved_at": source["created_at"],
                    "response_sha256": source["content_sha256"]}
                return [matched["claim_key"]], evidence
        changed = []
        for claim in parent["claims"]:
            if claim["stable_lineage_key"] not in source["claim_keys"] or claim["state"] not in ("carried_forward", "re_attested"):
                continue
            with self.task(path, fence, "monitor:" + claim["claim_id"], "Evidence monitor", "Check attributable changes to previously relied-on evidence", "Scheduled source check") as task:
                old = [e for e in claim["evidence_citations"] if e["url"].startswith('https://')]
                if not old:
                    task["outcome"] = "No public evidence is attached to this claim."
                    continue
                urls = {e["url"].rstrip('/') for e in old}
                attributable = []
                for i, query in enumerate(sorted(urls)):
                    found = self.call(path, fence, f"monitor-search:{claim['claim_id']}:{i}", .01, lambda q=query: self.providers.search(q))
                    attributable.extend(e for e in found["evidence"] if e["url"].rstrip('/') == query)
                if urls - {e["url"].rstrip('/') for e in attributable}:
                    self.update(path, fence, lambda j: j.update(monitor_uncertain=True))
                if not attributable:
                    task["outcome"] = "The monitored source was not retrieved. No material change established."
                    continue
                compared = self.call(path, fence, "monitor-review:" + claim["claim_id"], .05, lambda: self.providers.compare_evidence(claim["use"], old, attributable))
                task["outcome"] = compared["output"]["explanation"]
                if compared["output"]["material"]:
                    changed.append(claim["stable_lineage_key"])
        return changed, None

    def complete_without_change(self, path, root, fence, parent_path, status):
        def commit(tx):
            job = tx.get(path)
            head = tx.get(f"{root}/live_control/head")
            if job["fence"] != fence or job["lease_until"] <= time.time() or head.get("pending_job") != path:
                raise Conflict("Stale worker cannot complete a source check.")
            from .automation import settle
            settle(tx, root, job, status)
            tx.put(path, {**job, "status": "COMPLETED", "outcome": status, "snapshot_path": parent_path, "completed_at": now()})
            tx.put(f"{root}/live_control/head", {**head, "pending_job": None, "last_job": path})
        self.store.atomic(commit)

    def finish(self, path, root, fence, claims, parent, target_keys=None):
        from .automation import records
        questions = records(self.store, root, "live_clarifications")
        def commit(tx):
            job = tx.get(path)
            head = tx.get(f"{root}/live_control/head") or {}
            if job["fence"] != fence or job["lease_until"] <= time.time() or head.get("pending_job") != path:
                raise Conflict("Stale worker cannot publish results.")
            from .automation import settle
            for question_path, _ in questions:
                question = tx.get(question_path)
                if question["status"] == "PENDING" and (target_keys is None or question["claim_key"] in target_keys):
                    tx.put(question_path, {**question, "status": "SUPERSEDED"})
            for claim in claims:
                if claim["state"] in ("removed", "carried_forward", "re_attested") or (target_keys is not None and claim["stable_lineage_key"] not in target_keys):
                    continue
                missing = (claim.get("investigation") or {}).get("missing_facts", [])
                if missing:
                    question_id = "clarification_" + digest([job["revision_id"], claim["stable_lineage_key"], missing])[:24]
                    claim["clarification_id"] = question_id
                    tx.put(f"{root}/live_clarifications/{question_id}", {"clarification_id": question_id,
                        "claim_key": claim["stable_lineage_key"], "description": claim["description"], "questions": missing,
                        "revision_id": job["revision_id"], "status": "PENDING", "created_at": now(), "retention": "Pinned while pending"})
            before = (parent or {}).get("claims", [])
            old_claims = {c["stable_lineage_key"]: c for c in before if c["state"] != "removed"}
            comparison = {"baseline_snapshot_id": (parent or {}).get("snapshot_id"),
                "approvals_before": sum(c["state"] in ("carried_forward", "re_attested") for c in before),
                "blockers_before": sum(c["state"] not in ("carried_forward", "re_attested", "removed") for c in before),
                "blockers_after": sum(c["state"] not in ("carried_forward", "re_attested", "removed") for c in claims),
                "missing_facts_resolved": sum(len(set((old_claims.get(c["stable_lineage_key"], {}).get("investigation") or {}).get("missing_facts", [])) - set((c.get("investigation") or {}).get("missing_facts", []))) for c in claims if c["state"] != "removed"),
                "elapsed_seconds": round((datetime.fromisoformat(now()) - datetime.fromisoformat(job["created_at"])).total_seconds(), 2)}
            policy = tx.get(f"{root}/live_automation/policy") or {}
            snapshot = seal({"snapshot_id": "snapshot_" + uuid.uuid4().hex, "revision_id": job["revision_id"],
                "production_name": policy.get("production_name", "Production workspace"),
                "audit_id": job["audit_id"], "created_at": now(), "claims": claims, "events": (parent or {}).get("events", [])[-100:],
                "previous_snapshot_sha256": (parent or {}).get("content_sha256"), "comparison": comparison,
                "tasks": job.get("tasks", []), "trigger": job.get("trigger"),
                "telemetry": {"carried_forward_count": sum(c["state"] == "carried_forward" for c in claims),
                    "reopened_count": sum(c["state"] in ("stale", "new") for c in claims), "total_claims": len(claims),
                    "reserved_spend": job["reserved_usd"], "reconciled_spend": "Not reported by providers",
                    "calls": call_traces(job["calls"])}})
            snapshot_path = f"{root}/live_revisions/{job['revision_id']}/snapshots/{snapshot['snapshot_id']}"
            tx.put(snapshot_path, snapshot)
            outcome = "NEEDS_ATTENTION" if any(c.get("investigation_error") for c in claims) else "WAITING_FOR_INFORMATION" if any(c.get("clarification_id") and c["state"] not in ("removed", "re_attested", "carried_forward") for c in claims) else "READY_FOR_REVIEW"
            tx.put(path, {**job, "status": "COMPLETED", "outcome": outcome, "snapshot_path": snapshot_path, "completed_at": now()})
            tx.put(f"{root}/live_control/head", {"revision_id": job["revision_id"], "snapshot_path": snapshot_path, "pending_job": None, "last_job": path})
            settle(tx, root, job, "NEEDS_ATTENTION" if any(c.get("investigation_error") for c in claims) else "COMPLETED")
        self.store.atomic(commit)


def serve(stop=None):
    stop = stop or threading.Event()
    worker = Worker(get_store())
    next_discovery = 0
    while not stop.is_set():
        from .automation import poll_folders, schedule_evidence, dispatch
        if time.monotonic() >= next_discovery:
            for discover in (poll_folders, schedule_evidence):
                try:
                    discover(worker.store)
                except Exception:
                    logger.exception("Source discovery failed; queued investigations remain runnable")
            next_discovery = time.monotonic() + 10
        try:
            worker.store.atomic(lambda tx: tx.put('system/runtime/clearance/worker', {"timestamp": time.time(), "seen_at": now()}))
            dispatch(worker.store)
            for path, _ in worker.store.pending():
                if stop.is_set():
                    break
                worker.run(path)
        except Exception:
            logger.exception("Durable worker sweep failed; retrying")
        stop.wait(2)


if __name__ == "__main__":
    serve()
