"""
Lienmark Multi-Tenant Session & Firestore Isolation Test Suite
Sprint 6B Component 1: Multi-Tenant Session & Firestore Isolation Tests.
Verifies:
1. Concurrent Visitor Isolation (Session A mutations do not leak into Session B; Session B reset does not affect Session A).
2. In-Flight Commit Invalidation (superseded run commits rejected with HTTP 409 / StaleRunCommitError; active run uncorrupted).
3. Environment-Wide Reset Security Gate (HTTP 403 in ENVIRONMENT=demo unless presenter token sarah_jenkins_token_2026 provided).
4. Independent Cryptographic SHA-256 Hash Chaining per Run.
5. Persistent Environment Usage Counters surviving session & environment resets.
Authored strictly under Google AntiGravity for Agentic Cinema compliance.
"""

import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app, counsel_checkpoint_manager
from backend.storage.firestore_client import StaleRunCommitError
from backend.domain.models import ReviewAction, DecisionState, DecisionStatus

client = TestClient(app)


class TestConcurrentVisitorIsolation:
    """
    Verifies that multiple concurrent visitors operate in completely isolated
    session and run spaces. Mutations, resets, and queue transitions in one session
    never leak or affect another session.
    """

    def test_two_concurrent_sessions_full_lifecycle(self):
        sess_a = "sess_evaluator_alpha"
        sess_b = "sess_evaluator_beta"

        # 1. Seed Session A into drifted state (10 carried, 2 stale)
        res_a_seed = client.post(
            "/api/demo/seed?mode=drifted",
            headers={"X-Session-ID": sess_a},
        )
        assert res_a_seed.status_code == 200
        state_a = res_a_seed.json()
        assert state_a["mode"] == "drifted"
        assert state_a["approved_claims"] == 10
        assert state_a["stale_count"] == 2

        # Verify Session A queue has 2 items (Item 11 poster, Item 12 music cue)
        q_a = client.get("/api/review/queue", headers={"X-Session-ID": sess_a}).json()
        assert q_a["total_stale_count"] == 2
        keys_a = [item["stable_lineage_key"] for item in q_a["items"]]
        assert "poster_noir_detective_magazine" in keys_a
        assert "music_cue_midnight_serenade" in keys_a

        # 2. Session B initializes clean baseline (12 approvals)
        res_b_state = client.get("/api/demo/state", headers={"X-Session-ID": sess_b})
        assert res_b_state.status_code == 200
        state_b = res_b_state.json()
        assert state_b["approved_claims"] == 12
        assert state_b["stale_count"] == 0

        # Session B queue should be a clean pristine review queue (2 stale items awaiting review, 0 resolved)
        q_b = client.get("/api/review/queue", headers={"X-Session-ID": sess_b}).json()
        assert q_b["total_stale_count"] == 2
        assert len(q_b["items"]) == 2
        for item in q_b["items"]:
            assert item["current_state"].lower() == "stale"
            assert item["stable_lineage_key"] in ("poster_noir_detective_magazine", "music_cue_midnight_serenade")

        # 3. Session A performs counsel review actions:
        # Re-attest Item 11 (poster) with legal rationale
        res_a_act1 = client.post(
            "/api/review/action",
            headers={"X-Session-ID": sess_a},
            json={
                "stable_lineage_key": "poster_noir_detective_magazine",
                "action": "re_attest",
                "counsel_rationale": "Artwork confirmed in public domain via LOC registration records; cleared for V8.",
                "reviewer_name": "Sarah Jenkins, Esq.",
            },
        )
        assert res_a_act1.status_code == 200
        act1_data = res_a_act1.json()
        assert act1_data["status"] == "success"
        assert act1_data["action"] == "re_attest"
        assert act1_data["new_status"].lower() == "approved"
        assert act1_data["new_state"].lower() == "re_attested"

        # Designate Item 12 (music cue) as exception
        res_a_act2 = client.post(
            "/api/review/action",
            headers={"X-Session-ID": sess_a},
            json={
                "stable_lineage_key": "music_cue_midnight_serenade",
                "action": "exception",
                "counsel_rationale": "Active ownership conflict identified; flagged as unresolved underwriter exception.",
                "reviewer_name": "Sarah Jenkins, Esq.",
            },
        )
        assert res_a_act2.status_code == 200
        act2_data = res_a_act2.json()
        assert act2_data["status"] == "success"
        assert act2_data["action"] == "exception"
        assert act2_data["new_status"].lower() == "rejected"
        assert act2_data["new_state"].lower() == "exception"

        # Verify Session A audit trail has 2 events and ledger is valid
        audit_a = client.get("/api/review/audit-trail", headers={"X-Session-ID": sess_a}).json()
        assert audit_a["total_events"] == 2
        assert audit_a["is_ledger_tamper_free"] is True
        assert audit_a["chain_head_hash"] != "0" * 64

        # Verify Session A queue has both items transitioned to counsel resolved states
        q_a_resolved = client.get("/api/review/queue", headers={"X-Session-ID": sess_a}).json()
        assert q_a_resolved["total_count"] == 2
        states_a = {it["stable_lineage_key"]: it["current_state"].lower() for it in q_a_resolved["items"]}
        assert states_a["poster_noir_detective_magazine"] == "re_attested"
        assert states_a["music_cue_midnight_serenade"] == "exception"

        # Verify Session A demo state reflects 0 stale claims and 11 approved
        state_a_mid = client.get("/api/demo/state", headers={"X-Session-ID": sess_a}).json()
        assert state_a_mid["stale_count"] == 0
        assert state_a_mid["approved_claims"] == 11
        assert state_a_mid["re_attested_count"] == 1
        assert state_a_mid["exception_count"] == 1

        # Verify Session A exceptions schedule has 10 carried, 1 re-attested, 1 exception
        sched_a = client.get("/api/reports/exceptions", headers={"X-Session-ID": sess_a}).json()
        assert sched_a["total_claims"] == 12
        assert sched_a["carried_forward_count"] == 10
        assert sched_a["re_attested_count"] == 1
        assert sched_a["unresolved_exception_count"] == 1

        # 4. Session B resets to clean baseline
        res_b_reset = client.post("/api/demo/reset", headers={"X-Session-ID": sess_b})
        assert res_b_reset.status_code == 200
        assert res_b_reset.json()["status"] == "RESET_SUCCESS"

        # Session B audit trail remains 0
        audit_b = client.get("/api/review/audit-trail", headers={"X-Session-ID": sess_b}).json()
        assert audit_b["total_events"] == 0

        # Session B state remains 12 baseline approvals
        state_b_after = client.get("/api/demo/state", headers={"X-Session-ID": sess_b}).json()
        assert state_b_after["approved_claims"] == 12
        # Session B queue remains clean pristine (2 stale items awaiting review)
        q_b_after = client.get("/api/review/queue", headers={"X-Session-ID": sess_b}).json()
        assert q_b_after["total_stale_count"] == 2
        for item in q_b_after["items"]:
            assert item["current_state"].lower() == "stale"

        # 5. Verify Session A is COMPLETELY unaffected by Session B's actions and reset:
        state_a_after = client.get("/api/demo/state", headers={"X-Session-ID": sess_a}).json()
        assert state_a_after["total_claims"] == 12
        assert state_a_after["approved_claims"] == 11  # 10 carried + 1 re-attested
        assert state_a_after["re_attested_count"] == 1
        assert state_a_after["exception_count"] == 1

        # Session A review queue remains resolved
        q_a_after = client.get("/api/review/queue", headers={"X-Session-ID": sess_a}).json()
        assert q_a_after["total_count"] == 2
        states_a_after = {it["stable_lineage_key"]: it["current_state"].lower() for it in q_a_after["items"]}
        assert states_a_after["poster_noir_detective_magazine"] == "re_attested"
        assert states_a_after["music_cue_midnight_serenade"] == "exception"

        audit_a_after = client.get("/api/review/audit-trail", headers={"X-Session-ID": sess_a}).json()
        assert audit_a_after["total_events"] == 2
        assert audit_a_after["is_ledger_tamper_free"] is True
        assert audit_a_after["chain_head_hash"] == audit_a["chain_head_hash"]

        sched_a_after = client.get("/api/reports/exceptions", headers={"X-Session-ID": sess_a}).json()
        assert sched_a_after["total_claims"] == 12
        assert sched_a_after["carried_forward_count"] == 10
        assert sched_a_after["re_attested_count"] == 1
        assert sched_a_after["unresolved_exception_count"] == 1


class TestInFlightCommitInvalidation:
    """
    Verifies that when a visitor resets a session or starts a fresh run,
    any in-flight review actions targeting the old/superseded run_id are rejected
    with HTTP 409 Conflict / StaleRunCommitError without corrupting the active run.
    """

    def test_stale_run_commit_rejected_with_http_409(self):
        sess_id = "sess_evaluator_concurrency_race"

        # 1. Seed session to drifted state and capture the active run_id
        seed_res = client.post("/api/demo/seed?mode=drifted", headers={"X-Session-ID": sess_id})
        assert seed_res.status_code == 200
        run_1_id = seed_res.json()["run_id"]
        assert run_1_id.startswith("run_")

        # 2. Simulate concurrent reset (e.g. user clicks reset in another tab or retry)
        reset_res = client.post("/api/demo/reset", headers={"X-Session-ID": sess_id})
        assert reset_res.status_code == 200
        run_2_id = reset_res.json()["run_id"]
        assert run_2_id.startswith("run_")
        assert run_2_id != run_1_id, "Reset must create a new active run"

        # 3. In-flight action arrives with the superseded run_1_id
        stale_action_res = client.post(
            "/api/review/action",
            headers={"X-Session-ID": sess_id, "X-Run-ID": run_1_id},
            json={
                "stable_lineage_key": "poster_noir_detective_magazine",
                "action": "re_attest",
                "counsel_rationale": "Valid legal rationale but targeting superseded run",
                "reviewer_name": "Sarah Jenkins, Esq.",
                "run_id": run_1_id,
            },
        )
        assert stale_action_res.status_code == 409
        detail = stale_action_res.json()["detail"]
        assert "In-flight commit invalidation" in detail
        assert run_1_id in detail

        # 4. Verify directly with Python API that StaleRunCommitError is raised
        with pytest.raises(StaleRunCommitError) as exc_info:
            counsel_checkpoint_manager.record_counsel_action(
                session_id=sess_id,
                run_id=run_1_id,
                action=ReviewAction.RE_ATTEST,
                lineage_key="poster_noir_detective_magazine",
                rationale="Should fail because run_1 is stale",
            )
        assert "In-flight commit invalidation" in str(exc_info.value)

        # 5. Verify the new active run (run_2) is completely uncorrupted
        active_state = client.get("/api/demo/state", headers={"X-Session-ID": sess_id}).json()
        assert active_state["run_id"] == run_2_id
        assert active_state["approved_claims"] == 12  # Baseline preserved
        assert active_state["audit_events_count"] == 0  # No events recorded into run_2

        # 6. Verify committing to the active run (run_2) succeeds
        valid_action_res = client.post(
            "/api/review/action",
            headers={"X-Session-ID": sess_id, "X-Run-ID": run_2_id},
            json={
                "stable_lineage_key": "poster_noir_detective_magazine",
                "action": "re_attest",
                "counsel_rationale": "Valid commit to active run_2",
                "reviewer_name": "Sarah Jenkins, Esq.",
                "run_id": run_2_id,
            },
        )
        assert valid_action_res.status_code == 200
        assert valid_action_res.json()["status"] == "success"


class TestEnvironmentResetRestriction:
    """
    Verifies that in Judge Demo mode (ENVIRONMENT=demo):
    1. Unauthenticated environment-wide resets return HTTP 403 Forbidden.
    2. Authorized presenter credentials (sarah_jenkins_token_2026) succeed.
    3. Unauthenticated requests to seed 'resolved' state return HTTP 403 Forbidden.
    4. Evaluator session-scoped resets always succeed without credentials.
    """

    def test_demo_environment_wide_reset_restrictions(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "demo")

        # 1. Unauthenticated environment-wide reset via query param returns HTTP 403
        res_unauth_query = client.post("/api/demo/reset?scope=environment")
        assert res_unauth_query.status_code == 403
        assert "Environment-wide reset forbidden in demo environment" in res_unauth_query.json()["detail"]

        # 2. Unauthenticated environment-wide reset via body returns HTTP 403
        res_unauth_body = client.post("/api/demo/reset", json={"scope": "global"})
        assert res_unauth_body.status_code == 403
        assert "Environment-wide reset forbidden in demo environment" in res_unauth_body.json()["detail"]

        # 3. Unauthenticated seeding of 'resolved' state returns HTTP 403 in demo mode
        res_unauth_seed = client.post(
            "/api/demo/seed?mode=resolved",
            headers={"X-Session-ID": "sess_judge_demo"},
        )
        assert res_unauth_seed.status_code == 403
        assert "requires presenter authorization token" in res_unauth_seed.json()["detail"]

        # 4. Authorized presenter token allows environment-wide reset via Bearer Authorization
        res_auth_bearer = client.post(
            "/api/demo/reset?scope=environment",
            headers={"Authorization": "Bearer sarah_jenkins_token_2026"},
        )
        assert res_auth_bearer.status_code == 200
        assert res_auth_bearer.json()["status"] == "RESET_SUCCESS"

        # 5. Authorized presenter token allows seeding 'resolved' via X-Counsel-Token
        res_auth_seed = client.post(
            "/api/demo/seed?mode=resolved",
            headers={
                "X-Session-ID": "sess_presenter_showcase",
                "X-Counsel-Token": "sarah_jenkins_token_2026",
            },
        )
        assert res_auth_seed.status_code == 200
        assert res_auth_seed.json()["status"] == "SEED_SUCCESS"

        # 6. Individual evaluator session reset is allowed without presenter token
        res_evaluator_reset = client.post(
            "/api/demo/reset",
            headers={"X-Session-ID": "sess_individual_evaluator"},
        )
        assert res_evaluator_reset.status_code == 200
        assert res_evaluator_reset.json()["status"] == "RESET_SUCCESS"


class TestCryptographicChainingAndPersistentCounters:
    """
    Verifies that:
    1. SHA-256 hash chaining is independent per run.
    2. Persistent usage counters survive session resets and environment resets.
    """

    def test_independent_sha256_hash_chaining_per_run(self):
        sess_1 = "sess_crypto_run_1"
        sess_2 = "sess_crypto_run_2"

        # Reset both sessions to create distinct initial runs
        client.post("/api/demo/reset", headers={"X-Session-ID": sess_1})
        client.post("/api/demo/reset", headers={"X-Session-ID": sess_2})

        # Apply action in sess_1
        client.post(
            "/api/review/action",
            headers={"X-Session-ID": sess_1},
            json={
                "stable_lineage_key": "poster_noir_detective_magazine",
                "action": "re_attest",
                "counsel_rationale": "Independent chain 1 test rationale",
                "reviewer_name": "Sarah Jenkins, Esq.",
            },
        )

        # Apply different action in sess_2
        client.post(
            "/api/review/action",
            headers={"X-Session-ID": sess_2},
            json={
                "stable_lineage_key": "music_cue_midnight_serenade",
                "action": "exception",
                "counsel_rationale": "Independent chain 2 test rationale",
                "reviewer_name": "Sarah Jenkins, Esq.",
            },
        )

        trail_1 = client.get("/api/review/audit-trail", headers={"X-Session-ID": sess_1}).json()
        trail_2 = client.get("/api/review/audit-trail", headers={"X-Session-ID": sess_2}).json()

        assert trail_1["is_ledger_tamper_free"] is True
        assert trail_2["is_ledger_tamper_free"] is True

        # First event in both runs must chain from the genesis parent hash '0' * 64
        assert trail_1["events"][0]["parent_event_hash"] == "0" * 64
        assert trail_2["events"][0]["parent_event_hash"] == "0" * 64

        # Distinct actions must produce distinct event hashes
        assert trail_1["events"][0]["event_hash"] != trail_2["events"][0]["event_hash"]

    def test_persistent_usage_counters_survive_resets(self):
        storage = counsel_checkpoint_manager.storage
        env = "test_metrics_env"

        # Increment usage counter
        c1 = storage.increment_usage_counter(env, "api_calls", 5)
        c2 = storage.increment_usage_counter(env, "tokens_processed", 1250)
        assert c1["api_calls"] >= 5
        assert c2["tokens_processed"] >= 1250

        # Perform a session reset
        counsel_checkpoint_manager.reset_session_run("sess_metrics_check")

        # Counters in usage_counters/{env} MUST survive session resets
        metrics_after_sess_reset = storage.get_usage_counter(env)
        assert metrics_after_sess_reset["api_calls"] >= 5
        assert metrics_after_sess_reset["tokens_processed"] >= 1250

        # Perform an environment reset of runs/sessions
        storage.reset_environment(env)

        # Counters in usage_counters/{env} MUST survive environment resets as well
        metrics_after_env_reset = storage.get_usage_counter(env)
        assert metrics_after_env_reset["api_calls"] >= 5
        assert metrics_after_env_reset["tokens_processed"] >= 1250
