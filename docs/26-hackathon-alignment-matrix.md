# 26. Hackathon Alignment & Compliance Matrix

*This document serves as the primary evaluation guide for judges of **Agentic Cinema: The Blockbuster Hackathon**. It maps every binding rule, partner requirement, and judging criterion directly to Lienmark's code files, data schemas, and 60-second CLI verification commands.*

---

## 🎯 1. Binding Hackathon Requirements Mapping

| Rule / Requirement | Hackathon Citation | Lienmark Code Implementation | Verification CLI Command |
|---|---|---|---|
| **Live Parallel Search API Usage** | `01-hackathon-scope.md` §4 | [`backend/agents/research/parallel_client.py`](file:///z:/home/lx_singw/projects/lienmark/backend/agents/research/parallel_client.py)<br>[`backend/agents/research/multi_tool_router.py`](file:///z:/home/lx_singw/projects/lienmark/backend/agents/research/multi_tool_router.py) | `python scripts/verify_integrations.py` |
| **Google Cloud Agent Builder Orchestration** | `01-hackathon-scope.md` §2 | [`backend/orchestration/agent_builder_config.py`](file:///z:/home/lx_singw/projects/lienmark/backend/orchestration/agent_builder_config.py)<br>[`backend/orchestration/pipeline.py`](file:///z:/home/lx_singw/projects/lienmark/backend/orchestration/pipeline.py) | `python scripts/verify_integrations.py` |
| **Media & Entertainment Workflow** | `01-hackathon-scope.md` §2 | Title Insurance Rights Clearance ($51.4M TAM)<br>[`docs/04-prd.md`](file:///z:/home/lx_singw/projects/lienmark/docs/04-prd.md) §1 | N/A (Domain Specific) |
| **3-Minute Hard Limit Video** | `01-hackathon-scope.md` §6 | [`docs/05-pitch-deck.md`](file:///z:/home/lx_singw/projects/lienmark/docs/05-pitch-deck.md)<br>[`demo/demo_script.md`](file:///z:/home/lx_singw/projects/lienmark/demo/demo_script.md) | Video URL in Devpost |

---

## 🏆 2. Devpost Judging Criteria Alignment

### 2.1 Technological Implementation (40% Weight)
* **Agentic Autonomy**: 32 documented Bounded Autonomy capabilities (`04-prd.md` §5).
* **Enterprise Feature Toggle & Presets**: 1-click profiles (`preset_profiles.json`), API spend budget governor (`execution_budget_governor.py`), safety guard (`feature_dependency_guard.py`), and studio policy inheritance (`studio_policy_engine.py`).
* **Attorney Ethics Pre-Screening**: Counsel conflict-of-interest verifier (`ethics_pre_screening.py`) under ABA rules.
* **RFC 3161 Timestamping Anchor**: Trusted TSA / L2 blockchain timestamp anchor service (`anchor_service.py`) for FRE 902(13) court evidence.
* **Statutory Damages Calculator**: 17 U.S.C. § 504(c) worst-case lawsuit exposure calculator (`statutory_damages_calc.py`).
* **Attorney Defense Memorandum Exporter**: Instant litigation defense PDF brief exporter (`legal_brief_exporter.py`).
* **Pure Python Statutory Legal Rule Engine**: Zero-LLM statutory Fair Use matrix evaluator (`statutory_rule_engine.py`) eliminating legal hallucinations.
* **Dual-Key Cryptographic Signatures**: RSA-256 dual-signature engine (`dual_key_signer.py`) for attorney sign-off verification.
* **Attorney Rejection & Re-Investigation Loop**: Bidirectional feedback loop (`attorney_rejection_router.py`) routing attorney rejections back to Research.
* **ISO 27001 Legal Audit Manifest Exporter**: Standardized legal compliance manifest generator (`legal_audit_exporter.py`).
* **Research Plan Synthesis DAG**: Upfront reasoning DAG plan generator (`research_planner.py`).
* **Claim Dependency Resolver**: Prerequisite claim ordering & parent-child dependency tree resolver (`claim_dependency_resolver.py`).
* **Dynamic Tool Synthesis**: Prompt instruction self-adaptation & custom schema generator (`tool_synthesizer.py`).
* **Multi-Agent Peer Deliberation**: 3-persona consensus voting engine (`peer_deliberation.py`).
* **Autonomous Self-Correction Feedback Loop**: Internal reflection pass (`self_correction_loop.py`) reformulating search strategies on low eval scores.
* **Inter-Agent Negotiation Protocol**: Peer negotiation between Risk Scoring and Research Agents (`agent_negotiator.py`) to resolve conflicting evidence.
* **Autonomous Circuit Breaker & Fallback**: Circuit breaker (`circuit_breaker.py`) switching to public mirrors on 5xx errors.
* **Sub-Goal Verification Planner**: Hierarchical goal decomposition (`subgoal_planner.py`) into sync, master, and sample sub-goals.
* **Multimodal Visual IP & Logo Detector**: Uses Gemini 3.6 Multimodal Vision to detect background brand logos and extract frame timecodes & bounding boxes (`visual_ip_detector.py`).
* **FCP XML / DaVinci EDL Timeline Conformer**: Parses professional Hollywood edit decision lists (`timeline_conformer.py`) linking claims directly to video frames.
* **Decoupled Background Poller**: [`backend/agents/discovery/poller.py`](file:///z:/home/lx_singw/projects/lienmark/backend/agents/discovery/poller.py) runs autonomously, detecting file drops and monitoring aging claims.
* **Persistent Agent State & Heartbeat**: [`backend/agents/discovery/heartbeat.py`](file:///z:/home/lx_singw/projects/lienmark/backend/agents/discovery/heartbeat.py) emits liveness signals; state is checkpointed to `agent_state_store` in Firestore (`06-data-schema.md`).
* **Error Resilience & Throttling**: `asyncio.Semaphore(10)` rate governor in [`backend/agents/research/parallel_client.py`](file:///z:/home/lx_singw/projects/lienmark/backend/agents/research/parallel_client.py); single-retry backoff; graceful failure routing (`call_status: failed`).
* **Prompt Injection Defense**: [`backend/agents/intake/self_reflection.py`](file:///z:/home/lx_singw/projects/lienmark/backend/agents/intake/self_reflection.py) traps embedded `[SYSTEM OVERRIDE]` instructions using [`demo/sample_script_adversarial.pdf`](file:///z:/home/lx_singw/projects/lienmark/demo/sample_script_adversarial.pdf).

### 2.2 Design & User Experience (30% Weight)
* **Human-in-the-Loop (HITL) Clearance Intelligence**: Framing output as *Clearance Intelligence & Verification Audit* rather than definitive legal opinion (`04-prd.md` §5.5).
* **Attorney Sign-Off Workflows**: `ClarifyingQuestionModal.tsx` and `AttorneyOverrideModal.tsx` pre-populate legal citations (`suggested_legal_citation`) and Fair Use defenses (`suggested_fair_use_defense`), writing immutable overrides (`action_type: attorney_override`) with dual-key RSA-256 signatures to Firestore.
* **Urgency-Routed Proactive Toast Alerts**: [`ToastContainer.tsx`](file:///z:/home/lx_singw/projects/lienmark/frontend/app/components/ToastContainer.tsx) surfaces immediate alerts for urgent disputes while batching routine claims.

### 2.3 Potential Impact & Market Feasibility (30% Weight)
* **Title Insurance Thesis**: Independent clearance verification layer sitting between studios, E&O insurers, and completion bond companies (`docs/17-moat-mechanics.md`).
* **Underwriting Partner API Webhook Integrator**: Exposes `POST /api/v1/underwriting/bind-policy` (`eo_binder_api.py`) allowing Chubb/Hiscox to programmatically pull certificates and bind policies.
* **Post-Production Wrap Delivery Checklist**: Generates wrap clearance summaries (`wrap_checklist.py`) verifying 100% claim clearance before distributors (A24, Netflix) release funds.
* **Official E&O Title Clearance Certificate Generator**: Generates Form E&O-2026 PDF audit certificates with cryptographic hash stamps required by insurers (`backend/agents/report/chain_of_title_cert.py`).
* **Standardized ASCAP/BMI Music Cue Sheet Exporter**: Exports industry-standard cue sheets (`cue_sheet_exporter.py`) with PRO work codes, saving 20+ hours of post-production legal paperwork.
* **SAG-AFTRA Guild Residuals & Expiration Tracker**: Tracks actor likeness/voice option expiration dates (`union_rights_tracker.py`), alerting legal 60 days before distribution rights expire.
* **Completion Bond Underwriting Contingency Risk Score**: Computes `bond_compliance_score` (%) to ensure uncleared IP risk never triggers a bond stop-order on film budget drawdowns (`bond_underwriting_risk.py`).
* **Unit Economics**: Replaces $250–$700/hr manual entertainment counsel with sub-5-second, $0.15/claim automated research.
* **Clearance Velocity & Risk Regression Tracking**: Computes `clearance_velocity_score` and `risk_trend` across script revisions (Draft 1 -> Draft 3).

---

## ⚡ 3. Quick Verification Commands

Judges can verify all technical claims in under 60 seconds using these self-contained scripts:

```bash
# 1. Verify Parallel API live connectivity, Agent Builder config, and Firestore write security rules (<5s)
python scripts/verify_integrations.py

# 2. Audit SHA-256 cryptographic hash-chain ledger integrity (<5s)
python scripts/verify_ledger_integrity.py

# 3. Run complete end-to-end benchmark test suite
pytest tests/test_e2e_pipeline.py
```
