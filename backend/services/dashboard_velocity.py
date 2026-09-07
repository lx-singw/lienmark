"""
backend/services/dashboard_velocity.py

Mathematical computation of clearance velocity, stale aging, and burn rates.
Sprint 6.1: Command Center Core.
Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.api.routes.dashboard_schemas import (
    BlockerVelocityMetric,
    ProductionVelocityStats,
    ResolutionTimeMetric,
    StaleClaimAgingMetric,
)


def parse_iso_ts(val: Optional[str], default: datetime) -> datetime:
    """Parses ISO timestamp string into timezone-aware UTC datetime."""
    if not val:
        return default
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return default


def compute_resolution_metric(
    events: List[Dict[str, Any]], cutoff: datetime
) -> ResolutionTimeMetric:
    """Calculates median and P90 resolution latency from paired audit events."""
    durations: List[float] = []
    starts: Dict[str, datetime] = {}
    for ev in sorted(events, key=lambda x: str(x.get("timestamp_utc") or x.get("timestamp", ""))):
        ts = parse_iso_ts(ev.get("timestamp_utc") or ev.get("event_timestamp") or ev.get("timestamp"), cutoff)
        act = str(ev.get("action_type") or ev.get("action", "")).upper()
        cid = ev.get("claim_id") or ev.get("payload", {}).get("claim_id", "")
        if not cid:
            continue
        if "INVALIDATED" in act or "DISPATCHED" in act:
            starts[cid] = ts
        elif cid in starts and any(k in act for k in ("SIGNED_OFF", "RE_ATTESTED", "RESOLVED")):
            diff = max(0.0, round((ts - starts.pop(cid)).total_seconds() / 3600.0, 2))
            if ts >= cutoff:
                durations.append(diff)

    if not durations:
        return ResolutionTimeMetric(median_hours=0.0, p90_hours=0.0, min_hours=0.0, max_hours=0.0, sample_count=0)
    durations.sort()
    p90_idx = int(len(durations) * 0.9)
    return ResolutionTimeMetric(
        median_hours=round(float(statistics.median(durations)), 2),
        p90_hours=round(durations[min(p90_idx, len(durations) - 1)], 2),
        min_hours=round(min(durations), 2), max_hours=round(max(durations), 2),
        sample_count=len(durations),
    )


def compute_stale_aging(
    claims: List[Dict[str, Any]], now: datetime
) -> Tuple[StaleClaimAgingMetric, bool]:
    """Calculates stale aging hours and distribution buckets."""
    ages = [
        max(0.0, round((now - parse_iso_ts(c.get("created_at"), now)).total_seconds() / 3600.0, 2))
        for c in claims
    ]
    has_high_sev = len(claims) > 0
    if not ages:
        empty = StaleClaimAgingMetric(avg_stale_hours=0.0, max_stale_hours=0.0, stale_count=0, distribution_under_24h=0, distribution_24_to_72h=0, distribution_over_72h=0)
        return empty, False

    return StaleClaimAgingMetric(
        avg_stale_hours=round(sum(ages) / len(ages), 2), max_stale_hours=round(max(ages), 2),
        stale_count=len(ages), distribution_under_24h=sum(1 for a in ages if a < 24.0),
        distribution_24_to_72h=sum(1 for a in ages if 24.0 <= a <= 72.0),
        distribution_over_72h=sum(1 for a in ages if a > 72.0),
    ), has_high_sev


def compute_blocker_velocity(
    events: List[Dict[str, Any]], now: datetime
) -> BlockerVelocityMetric:
    """Calculates 24-hour blocker creation vs resolution burn rate."""
    cutoff_24h = now - timedelta(hours=24)
    new_b, res_b = 0, 0
    for ev in events:
        ts = parse_iso_ts(ev.get("timestamp_utc") or ev.get("event_timestamp") or ev.get("timestamp"), cutoff_24h)
        if ts < cutoff_24h:
            continue
        act = str(ev.get("action_type") or ev.get("action", "")).upper()
        if any(k in act for k in ("INVALIDATED", "DISPATCHED", "REJECT")):
            new_b += 1
        elif any(k in act for k in ("SIGNED_OFF", "RE_ATTESTED", "RESOLVED")):
            res_b += 1

    total = new_b + res_b
    pct = round((res_b / total) * 100.0, 2) if total > 0 else 0.0
    return BlockerVelocityMetric(
        new_blockers_24h=new_b, resolved_blockers_24h=res_b,
        net_burn_rate=round(float(res_b - new_b), 2), resolution_rate_pct=pct,
    )


def calc_production_velocity(
    repo: Any, pid: str, ptitle: str, runs: List[Any], cutoff: datetime, now: datetime
) -> ProductionVelocityStats:
    """Computes velocity stats for an individual production container."""
    audit_events: List[Dict[str, Any]] = []
    unresolved_claims: List[Dict[str, Any]] = []
    for r in runs:
        audit_events.extend(repo.list_audit_events(pid, r.run_id))
        claims = repo.list_claims(pid, r.run_id)
        unresolved_claims.extend([c for c in claims if str(c.get("status", "")).upper() in ("NEEDS_REVIEW", "STALE")])

    res_metric = compute_resolution_metric(audit_events, cutoff)
    stale_metric, has_p0 = compute_stale_aging(unresolved_claims, now)
    burn_metric = compute_blocker_velocity(audit_events, now)

    return ProductionVelocityStats(
        production_id=pid, production_title=ptitle, resolution_time=res_metric,
        stale_aging=stale_metric, blocker_velocity=burn_metric,
        has_active_high_severity_blockers=has_p0, unresolved_blocker_count=len(unresolved_claims),
    )


def aggregate_velocity_stats(
    stats_list: List[ProductionVelocityStats]
) -> ProductionVelocityStats:
    """Rolls up per-production velocity statistics into tenant-wide aggregate."""
    tot_unresolved = sum(s.unresolved_blocker_count for s in stats_list)
    any_p0 = any(s.has_active_high_severity_blockers for s in stats_list)
    new_24 = sum(s.blocker_velocity.new_blockers_24h for s in stats_list)
    res_24 = sum(s.blocker_velocity.resolved_blockers_24h for s in stats_list)
    burn_pct = round((res_24 / (new_24 + res_24)) * 100.0, 2) if (new_24 + res_24) > 0 else 0.0

    all_samples = sum(s.resolution_time.sample_count for s in stats_list)
    avg_med = (
        round(sum(s.resolution_time.median_hours * s.resolution_time.sample_count for s in stats_list) / all_samples, 2)
        if all_samples > 0 else 0.0
    )
    tot_u24 = sum(s.stale_aging.distribution_under_24h for s in stats_list)
    tot_24_72 = sum(s.stale_aging.distribution_24_to_72h for s in stats_list)
    tot_o72 = sum(s.stale_aging.distribution_over_72h for s in stats_list)
    max_st = max((s.stale_aging.max_stale_hours for s in stats_list), default=0.0)
    avg_st = (
        round(sum(s.stale_aging.avg_stale_hours * s.stale_aging.stale_count for s in stats_list) / tot_unresolved, 2)
        if tot_unresolved > 0 else 0.0
    )
    return ProductionVelocityStats(
        production_id="aggregate", production_title="Tenant Organization Aggregate",
        resolution_time=ResolutionTimeMetric(median_hours=avg_med, p90_hours=avg_med, min_hours=0.0, max_hours=0.0, sample_count=all_samples),
        stale_aging=StaleClaimAgingMetric(avg_stale_hours=avg_st, max_stale_hours=max_st, stale_count=tot_unresolved, distribution_under_24h=tot_u24, distribution_24_to_72h=tot_24_72, distribution_over_72h=tot_o72),
        blocker_velocity=BlockerVelocityMetric(new_blockers_24h=new_24, resolved_blockers_24h=res_24, net_burn_rate=float(res_24 - new_24), resolution_rate_pct=burn_pct),
        has_active_high_severity_blockers=any_p0, unresolved_blocker_count=tot_unresolved,
    )
