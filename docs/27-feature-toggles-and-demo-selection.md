# 27. Feature Toggles & Hackathon Demo Execution Matrix

*This document defines Lienmark's modular feature toggle architecture (`clearance_config.json` & `FeatureTogglePanel.tsx`) and specifies exact execution parameters for the 3-minute hackathon video demo.*

---

## 🎛️ 1. Modular Feature Toggle Architecture

To ensure Lienmark remains lightweight, fast, and adaptable across indie budgets ($1M) and studio blockbusters ($200M+), **all 32 Bounded Autonomy capabilities are modular and opt-in**.

Production legal officers and line producers configure active modules via the **Clearance Intelligence Suite Config** panel (`src/components/FeatureTogglePanel.tsx` / `backend/config/clearance_config.json`).

### Configuration Payload (`clearance_config.json`)
```json
{
  "production_id": "prod_demo_01",
  "active_features": {
    "proactive_file_watcher": true,
    "sha256_script_dedup": true,
    "parallel_search_api": true,
    "parallel_task_api": false,
    "multi_hop_lead_chasing": true,
    "conflict_arbitration": true,
    "fair_use_pre_analyzer": true,
    "attorney_override_modal": true,
    "dual_key_signatures": true,
    "eo_certificate_generator": true,
    "ledger_hash_integrity_auditor": true,

    "visual_ip_detection": false,
    "edl_timeline_conformer": false,
    "sag_aftra_option_tracker": false,
    "genai_provenance_auditor": false,
    "multi_jurisdiction_routing": false,
    "ascap_music_cue_sheet": false,
    "statutory_damages_calculator": false,
    "eo_binder_webhook_api": false
  }
}
```

---

## 🎬 2. The 3-Minute Video Demo Execution Selection (6 Hero Features)

For the **3-minute hackathon submission video**, execution must run in **<15 seconds total pipeline latency** while demonstrating indisputable technical mastery. 

We activate **6 Core Hero Features** on camera, while highlighting the remaining 26 capabilities as available toggle switches in the UI:

| Hero Feature | Component / File | What Judge Sees on Camera |
|---|---|---|
| **1. Proactive File Drop Watcher** | [`backend/agents/discovery/poller.py`](file:///z:/home/lx_singw/projects/lienmark/backend/agents/discovery/poller.py) | Dragging `sample_script_adversarial.pdf` into `poller_watch_dir/` triggers automated agent intake **without pressing a UI button**. |
| **2. SHA-256 Script Deduplication** | [`backend/agents/intake/script_hasher.py`](file:///z:/home/lx_singw/projects/lienmark/backend/agents/intake/script_hasher.py) | Dropping a duplicate script returns instantaneous cached ledger results (<0.1s) with zero Parallel search API token waste. |
| **3. Live Parallel Search Verification** | [`backend/agents/research/parallel_client.py`](file:///z:/home/lx_singw/projects/lienmark/backend/agents/research/parallel_client.py) | Real-time Parallel Search API queries verifying music rights and public domain records. |
| **4. Multi-Source Conflict Arbitration** | [`backend/agents/risk_scoring/conflict_arbitration.py`](file:///z:/home/lx_singw/projects/lienmark/backend/agents/risk_scoring/conflict_arbitration.py) | **Demo Centerpiece**: Apollo 11 audio clip contradiction (Public Domain NASA vs. Private Master Rights), pre-populating Fair Use defense tags. |
| **5. HITL Attorney Override Sign-off** | `AttorneyOverrideModal.tsx` & [`dual_key_signer.py`](file:///z:/home/lx_singw/projects/lienmark/backend/agents/ledger/dual_key_signer.py) | Human attorney reviews conflict, accepts pre-populated legal citation (17 U.S.C. § 107), applies RSA-256 digital signature, and clears claim in 15 seconds. |
| **6. E&O Title Certificate & Ledger Audit** | [`chain_of_title_cert.py`](file:///z:/home/lx_singw/projects/lienmark/backend/agents/report/chain_of_title_cert.py) & [`verify_ledger_integrity.py`](file:///z:/home/lx_singw/projects/lienmark/scripts/verify_ledger_integrity.py) | One-click export of **Form E&O-2026 Title Clearance Certificate PDF** and 5-second CLI verification of SHA-256 hash-chain ledger integrity. |

---

## 🎚️ 3. Full Feature Toggle Matrix (32 Capabilities)

| # | Capability Name | Default Mode in Production | Active in 3-Min Demo? |
|---|---|---|---|
| 1 | Proactive Watcher (`poller.py`) | Enabled | ✅ **Active** |
| 2 | SHA-256 Script Deduplication (`script_hasher.py`) | Enabled | ✅ **Active** |
| 3 | Live Parallel Search API (`parallel_client.py`) | Enabled | ✅ **Active** |
| 4 | Multi-Source Conflict Arbitration (`conflict_arbitration.py`) | Enabled | ✅ **Active** |
| 5 | Fair Use Pre-Analyzer (`fair_use_analyzer.py`) | Enabled | ✅ **Active** |
| 6 | HITL Attorney Override Modal (`AttorneyOverrideModal.tsx`) | Enabled | ✅ **Active** |
| 7 | Dual-Key RSA-256 Attorney Signer (`dual_key_signer.py`) | Enabled | ✅ **Active** |
| 8 | Form E&O-2026 Certificate Generator (`chain_of_title_cert.py`) | Enabled | ✅ **Active** |
| 9 | Cryptographic Ledger Hash Auditor (`verify_ledger_integrity.py`) | Enabled | ✅ **Active** |
| 10 | Prompt Injection Self-Reflection (`self_reflection.py`) | Enabled | ✅ **Active** |
| 11 | Multimodal Visual IP & Logo Detector (`visual_ip_detector.py`) | Optional (UI Toggle) | ⚙️ Optional |
| 12 | FCP XML / DaVinci EDL Conformer (`timeline_conformer.py`) | Optional (UI Toggle) | ⚙️ Optional |
| 13 | SAG-AFTRA Residuals & Option Tracker (`union_rights_tracker.py`) | Optional (UI Toggle) | ⚙️ Optional |
| 14 | GenAI Provenance & Opt-Out Auditor (`genai_provenance.py`) | Optional (UI Toggle) | ⚙️ Optional |
| 15 | Multi-Jurisdiction Territory Routing (`territory_codes`) | Optional (UI Toggle) | ⚙️ Optional |
| 16 | ASCAP / BMI Music Cue Sheet Exporter (`cue_sheet_exporter.py`) | Optional (UI Toggle) | ⚙️ Optional |
| 17 | Statutory Damages Calculator (`statutory_damages_calc.py`) | Optional (UI Toggle) | ⚙️ Optional |
| 18 | E&O Binder Webhook API (`eo_binder_api.py`) | Optional (UI Toggle) | ⚙️ Optional |
| 19 | Post-Production Wrap Delivery Checklist (`wrap_checklist.py`) | Optional (UI Toggle) | ⚙️ Optional |
| 20 | Inverse Domain Steering (`-wiki -lyrics -youtube`) | Optional (UI Toggle) | ⚙️ Optional |
| 21 | Source Authority Weighting (`corroboration_factor`) | Optional (UI Toggle) | ⚙️ Optional |
| 22 | Scene-Proximity Clustering (`co_occurring_claim_ids`) | Optional (UI Toggle) | ⚙️ Optional |
| 23 | Strategy Switching (WHOIS / SEC Filings) | Optional (UI Toggle) | ⚙️ Optional |
| 24 | Automated Script Delta-Diffing (`is_delta_modified`) | Optional (UI Toggle) | ⚙️ Optional |
| 25 | Attorney Legal Citation Engine (`suggested_legal_citation`) | Optional (UI Toggle) | ⚙️ Optional |
| 26 | Web Archive Fallback Safeguard (`cached_snapshot_url`) | Optional (UI Toggle) | ⚙️ Optional |
| 27 | Risk-Trend Regression Tracking (`clearance_velocity_score`) | Optional (UI Toggle) | ⚙️ Optional |
| 28 | Autonomous Dispute Auto-Escalation (`escalation_level: 2`) | Optional (UI Toggle) | ⚙️ Optional |
| 29 | Licensing Cost Floor & Budget Calculator (`cost_estimator.py`) | Optional (UI Toggle) | ⚙️ Optional |
| 30 | Multi-Agent Consensus Verification Protocol (`consensus_verifier.py`) | Optional (UI Toggle) | ⚙️ Optional |
| 31 | Self-Correction Reflection Loop (`self_correction_loop.py`) | Optional (UI Toggle) | ⚙️ Optional |
| 32 | Inter-Agent Negotiation Protocol (`agent_negotiator.py`) | Optional (UI Toggle) | ⚙️ Optional |
