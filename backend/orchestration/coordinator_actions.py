"""
backend/orchestration/coordinator_actions.py

Modular execution handlers for EvidenceDrivenCoordinator 8-action matrix.
Enforces shared query limits (max 5), circuit breaker checks, 429 backoff,
provider outage evidence preservation, and Milestone B budget reservations.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.domain.models import (
    ApprovalOrigin,
    AtomicRightsClaim,
    CensusDisposition,
    EvidenceStance,
    PublicEvidenceSnapshot,
    WorkflowReason,
)
from backend.orchestration.milestone_b_reservation import PaidActionType

logger = logging.getLogger("lienmark.orchestration.coordinator_actions")


async def execute_act_01_agreements(coordinator: Any, norm: AtomicRightsClaim, action: Any) -> Dict[str, Any]:
    """ACT_01: Evaluates private agreements in contract vault against claim."""
    coordinator.budget.consume(calls=1, dollars=0.01)
    cid = norm.claim_id
    ctx = coordinator.claim_contexts.setdefault(cid, {})
    t_key = (norm.occurrence_lineage_id or cid).lower()
    s_key = (norm.rights_subject or "").lower()

    matching = [
        c for c in coordinator.contracts
        if t_key in f"{getattr(c, 'agreement_id', '')} {getattr(c, 'stable_lineage_key', '')} {getattr(c, 'title', '')}".lower()
        or (s_key and s_key in f"{getattr(c, 'title', '')} {getattr(c, 'scope', '')}".lower())
    ]
    ctx["private_agreements_evaluated"] = True
    m_ids = [getattr(c, "agreement_id", str(i)) for i, c in enumerate(matching)]
    if matching:
        primary = matching[0]
        norm.licensor_grant_confirmed = True
        norm.licensed_media = getattr(primary, "permitted_media", ["theatrical", "svod"])
        norm.licensed_territory = getattr(primary, "territories", ["worldwide"])
        norm.licensed_term = getattr(primary, "term", "perpetual")
        ctx["contract_shield_applied"], ctx["matching_contracts"] = True, m_ids
    else:
        ctx["contract_shield_applied"], ctx["missing_crucial_scope"] = False, True
        ctx["scope_field_missing"] = "executed_license"

    coordinator._record_action(cid, action, {"matching_count": len(matching)})
    return {"status": "SUCCESS", "action": getattr(action, "value", str(action)), "matching_contracts": m_ids}


def _handle_act_02_success(coordinator: Any, norm: AtomicRightsClaim, snap: Any, mb_res: Any, cid: str, ctx: Dict[str, Any]) -> None:
    """Handles snapshot persistence, circuit success, and Milestone B settlement."""
    ctx["public_search_performed"], ctx["public_evidence"], ctx["preliminary_evidence"] = True, snap, snap
    if snap.snapshot_id not in norm.evidence_ids: norm.evidence_ids.append(snap.snapshot_id)
    coordinator.circuit_breaker.record_success()
    coordinator.limits_governor.add_partial_finding(snap.model_dump())
    coordinator.milestone_b.checkpoint_before_advancing(coordinator.run_id, "prod_default", cid, "ACT_02", [snap.model_dump()])
    coordinator.milestone_b.settle_for_action(mb_res.reservation_id, actual_usage={"mode": "basic"})


def _build_snapshot(tool_out: Dict[str, Any], norm: AtomicRightsClaim, l_key: str, query: str) -> PublicEvidenceSnapshot:
    st_val = tool_out.get("stance", "supporting").lower()
    ev_stance = next((s for s in EvidenceStance if s.value == st_val), EvidenceStance.SUPPORTING)
    return PublicEvidenceSnapshot(
        snapshot_id=tool_out.get("snapshot_id", f"snap_{l_key}"), use_id=norm.occurrence_id,
        stable_lineage_key=l_key, query=query, source_title=tool_out.get("source_title", ""),
        source_url=tool_out.get("source_url", ""), excerpt=tool_out.get("excerpt", ""),
        stance=ev_stance, provider="Parallel", provider_call_id=tool_out.get("provider_call_id"),
        http_status=tool_out.get("http_status", 200),
    )


async def execute_act_02_search(
    coordinator: Any, norm: AtomicRightsClaim, action: Any,
    custom_query: Optional[str] = None, http_status_override: Optional[int] = None,
) -> Dict[str, Any]:
    """ACT_02: Executes public search under shared limits, breaker check, and Milestone B reservation."""
    from backend.orchestration.adk_pipeline import revalidate_evidence_tool
    coordinator.budget.consume(calls=1, dollars=0.04)
    cid, l_key = norm.claim_id, norm.occurrence_lineage_id or norm.claim_id
    ctx = coordinator.claim_contexts.setdefault(cid, {})
    query = custom_query or f"{norm.rights_subject} copyright registry public domain"

    coordinator.circuit_breaker.check_breaker()
    coordinator.limits_governor.record_query(query=query, entity_name=norm.rights_subject)
    mb_res = coordinator.milestone_b.reserve_for_action(
        run_id=coordinator.run_id, production_id="prod_default",
        action_type=PaidActionType.PAID_SEARCH, action_id=f"act_02_{cid}",
    )
    if http_status_override in (504, 502, 503, 408):
        ctx["last_search_status"], ctx["provider_offline"] = http_status_override, True
        coordinator.circuit_breaker.handle_provider_outage("ACT_02", list(norm.evidence_ids), norm)
        coordinator.milestone_b.recover_on_failure(mb_res.reservation_id, "provider_offline")
        coordinator._record_action(cid, action, {"status": "PROVIDER_OFFLINE", "http_status": http_status_override})
        return {"status": "PROVIDER_OFFLINE", "http_status": http_status_override}

    tool_out = await revalidate_evidence_tool(query=query, asset_key=l_key, parallel_service=coordinator.parallel)
    snap = _build_snapshot(tool_out, norm, l_key, query)
    if snap.http_status in (504, 502, 503, 408):
        ctx["last_search_status"], ctx["provider_offline"] = snap.http_status, True
        coordinator.circuit_breaker.handle_provider_outage("ACT_02", list(norm.evidence_ids), norm)
        coordinator.milestone_b.recover_on_failure(mb_res.reservation_id, "provider_offline")
    else:
        _handle_act_02_success(coordinator, norm, snap, mb_res, cid, ctx)

    coordinator._record_action(cid, action, {"query": query, "stance": snap.stance.value})
    return {"status": "SUCCESS", "action": getattr(action, "value", str(action)), "snapshot": snap.model_dump()}



async def execute_act_03_inspect(coordinator: Any, norm: AtomicRightsClaim, action: Any) -> Dict[str, Any]:
    """ACT_03: Inspects specific URLs with separate inspection budget and checkpointing."""
    from backend.services.parallel_extract import ParallelExtractService
    coordinator.budget.consume(calls=1, dollars=0.02)
    cid = norm.claim_id
    ctx = coordinator.claim_contexts.setdefault(cid, {})
    urls = ctx.get("urls_to_inspect", [])
    if not urls:
        coordinator._record_action(cid, action, {"extracted_count": 0})
        return {"status": "FAILURE", "action": getattr(action, "value", str(action)), "claim_id": cid, "extracted_sources": []}

    coordinator.limits_governor.record_inspection(urls[0])
    mb_res = coordinator.milestone_b.reserve_for_action(
        run_id=coordinator.run_id, production_id="prod_default",
        action_type=PaidActionType.EXTRACTION, action_id=f"act_03_{cid}",
    )
    ext_svc = ParallelExtractService(use_fallback=coordinator.use_fallback)
    results = await ext_svc.extract(urls)
    extracted = [r.model_dump() for r in results]
    if not extracted:
        coordinator.milestone_b.recover_on_failure(mb_res.reservation_id, "empty_extraction")
        coordinator._record_action(cid, action, {"details": "Extraction failed or yielded no results", "extracted_count": 0})
        return {"status": "FAILURE", "action": getattr(action, "value", str(action)), "claim_id": cid, "extracted_sources": []}

    ctx["source_inspected"], ctx["source_inspection_performed"], ctx["extracted_sources"] = True, True, extracted
    coordinator.milestone_b.checkpoint_before_advancing(coordinator.run_id, "prod_default", cid, "ACT_03", extracted)
    coordinator.milestone_b.settle_for_action(mb_res.reservation_id, actual_usage={"mode": "basic"})
    coordinator._record_action(cid, action, {"details": "Source inspected", "extracted_count": len(extracted)})
    return {"status": "SUCCESS", "action": getattr(action, "value", str(action)), "claim_id": cid, "extracted_sources": extracted}


async def execute_act_05_adversarial(
    coordinator: Any, norm: AtomicRightsClaim, action: Any, custom_query: Optional[str] = None,
) -> Dict[str, Any]:
    """ACT_05: Performs adversarial probe under shared query limit and Milestone B reservation."""
    from backend.orchestration.adk_pipeline import revalidate_evidence_tool
    coordinator.budget.consume(calls=1, dollars=0.04)
    cid, l_key = norm.claim_id, norm.occurrence_lineage_id or norm.claim_id
    ctx = coordinator.claim_contexts.setdefault(cid, {})
    query = custom_query or f"{norm.rights_subject} copyright dispute renewal contested ownership"

    coordinator.circuit_breaker.check_breaker()
    coordinator.limits_governor.record_query(query=query, entity_name=norm.rights_subject)
    mb_res = coordinator.milestone_b.reserve_for_action(
        run_id=coordinator.run_id, production_id="prod_default",
        action_type=PaidActionType.PAID_SEARCH, action_id=f"act_05_{cid}",
    )
    tool_out = await revalidate_evidence_tool(query=query, asset_key=l_key, objective="adversarial_disconfirmation", parallel_service=coordinator.parallel)
    ctx["adversarial_disconfirmation_performed"], ctx["adversarial_evidence"] = True, tool_out
    if tool_out.get("snapshot_id"): norm.evidence_ids.append(tool_out["snapshot_id"])

    tool_stance = (tool_out.get("stance") or "").strip().upper()
    if tool_stance == "CONTRADICTORY":
        ctx["has_adverse_evidence"] = True
        norm.workflow_reason, norm.disposition = WorkflowReason.EVIDENCE_CHANGE, CensusDisposition.NEEDS_REVIEW

    coordinator.circuit_breaker.record_success()
    coordinator.milestone_b.checkpoint_before_advancing(coordinator.run_id, "prod_default", cid, "ACT_05", [tool_out])
    coordinator.milestone_b.settle_for_action(mb_res.reservation_id, actual_usage={"mode": "basic"})
    coordinator._record_action(cid, action, {"query": query, "adversarial_output": tool_out, "stance": tool_stance})
    return {"status": "SUCCESS", "action": getattr(action, "value", str(action)), "tool_output": tool_out}


async def execute_act_07_briefing(coordinator: Any, norm: AtomicRightsClaim, action: Any) -> Dict[str, Any]:
    """ACT_07: Generates counsel review brief with Milestone B token reservation and checkpoint."""
    coordinator.budget.consume(tokens=500, dollars=0.02)
    cid = norm.claim_id
    ctx = coordinator.claim_contexts.setdefault(cid, {})
    mb_res = coordinator.milestone_b.reserve_for_action(
        run_id=coordinator.run_id, production_id="prod_default",
        action_type=PaidActionType.BRIEFING_CALL, action_id=f"act_07_{cid}",
        model_or_mode="gemini-1.5-pro",
    )
    adv_ev, pub_ev = ctx.get("adversarial_evidence"), ctx.get("public_evidence")
    adv_stance = (adv_ev.get("stance") if isinstance(adv_ev, dict) else getattr(adv_ev, "stance", "")) or ""
    adv_stance = (adv_stance.value if hasattr(adv_stance, "value") else str(adv_stance)).upper()
    target_stance = "CONTRADICTORY" if adv_stance == "CONTRADICTORY" else (adv_stance or "SUPPORTING")
    ev = adv_ev if adv_stance == "CONTRADICTORY" else (adv_ev or pub_ev)
    excerpt = ev.get("excerpt", "") if isinstance(ev, dict) else getattr(ev, "excerpt", "")
    src_title = ev.get("source_title", "") if isinstance(ev, dict) else getattr(ev, "source_title", "")
    src_url = ev.get("source_url", "") if isinstance(ev, dict) else getattr(ev, "source_url", "")

    briefing = await coordinator.gemini.synthesize_counsel_briefing(
        asset_name=norm.rights_subject,
        reason_code=norm.workflow_reason.value if hasattr(norm.workflow_reason, "value") else str(norm.workflow_reason),
        evidence_excerpt=excerpt or "Clearance validated via public registry and contract vault.",
        source_title=src_title or "Clearance Register", source_url=src_url or "https://copyright.gov",
        evidence_stance=target_stance, claim_id=norm.occurrence_lineage_id or cid, evidence=ev,
    )
    norm.disposition, norm.approval_origin = CensusDisposition.NEEDS_REVIEW, ApprovalOrigin.NONE
    coordinator.claim_states[cid], ctx["counsel_briefing"] = "ready_for_review", briefing.model_dump()
    coordinator.milestone_b.checkpoint_before_advancing(coordinator.run_id, "prod_default", cid, "ACT_07", [briefing.model_dump()])
    coordinator.milestone_b.settle_for_action(mb_res.reservation_id, actual_usage={"model": "gemini-1.5-pro", "tokens_prompt": 500, "tokens_completion": 250})
    coordinator._record_action(cid, action, {"briefing_prepared": True, "stance": target_stance})
    return {"status": "SUCCESS", "action": getattr(action, "value", str(action)), "briefing": briefing.model_dump()}


async def execute_action_step(
    coordinator: Any, action: Any, claim: Any,
    custom_query: Optional[str] = None, http_status_override: Optional[int] = None,
) -> Dict[str, Any]:
    """Main entrypoint routing each CoordinatorAction to its dedicated execution function."""
    norm = coordinator._resolve_claim(claim)
    cid, code = norm.claim_id, getattr(action, "value", str(action))
    if "ACT_01" in code: return await execute_act_01_agreements(coordinator, norm, action)
    if "ACT_02" in code: return await execute_act_02_search(coordinator, norm, action, custom_query, http_status_override)
    if "ACT_03" in code: return await execute_act_03_inspect(coordinator, norm, action)
    if "ACT_04" in code:
        ch = coordinator.split_claim(norm)
        return {"status": "SUCCESS", "action": code, "children": [c.model_dump() for c in ch]}
    if "ACT_05" in code: return await execute_act_05_adversarial(coordinator, norm, action, custom_query)
    if "ACT_06" in code:
        q_text = custom_query or f"Clarification requested for license/scope on {norm.rights_subject}"
        missing = coordinator.claim_contexts.setdefault(cid, {}).get("scope_field_missing", "licensed_scope")
        clrf = coordinator.suspend_claim(claim=norm, question_text=q_text, scope_field_missing=missing)
        return {"status": "SUSPENDED", "action": code, "clarification_request": clrf.model_dump()}
    if "ACT_07" in code: return await execute_act_07_briefing(coordinator, norm, action)
    if "ACT_08" in code:
        norm.disposition, coordinator.claim_states[cid] = CensusDisposition.NEEDS_REVIEW, "unresolved_exception"
        coordinator._record_action(cid, action, {"reason": norm.workflow_reason})
        return {"status": "STOPPED", "action": code, "claim_id": cid, "reason": norm.workflow_reason}
    raise ValueError(f"Unknown coordinator action: {action}")
