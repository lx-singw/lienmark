# 28. Devpost Master Submission & Track Compliance Manifest

*This document serves as the official Devpost submission leave-behind for **Agentic Cinema: The Blockbuster Hackathon**, verifying track compliance, partner MCP server integration, and judge evaluation instructions.*

---

## 📋 1. Devpost Submission Overview

| Field | Submission Value |
|---|---|
| **Project Title** | **Lienmark** — Agentic Chain-of-Title Insurance & Clearance Intelligence |
| **Tagline** | The title insurance model for entertainment IP: autonomous clearance verification powered by Parallel Search API and Google Cloud Agent Builder. |
| **Track Category** | **Parallel Track** ($15,000 Prize Pool) |
| **Submission Deadline** | September 7, 2026 at 10:00 PM GMT+1 |
| **Primary Platform** | Google Cloud Agent Builder / Gemini Enterprise Agent Platform |
| **Partner Integration** | Parallel Search API & Parallel MCP Server (`https://search.parallel.ai/mcp`) |
| **Open-Source License** | MIT License ([`LICENSE`](file:///z:/home/lx_singw/projects/lienmark/LICENSE)) |
| **Public GitHub Repo** | [https://github.com/lx-singw/lienmark](https://github.com/lx-singw/lienmark) |

---

## 🛠️ 2. Partner MCP Server & SDK Integration Verification

As mandated by hackathon rules, Lienmark natively implements **Parallel's Model Context Protocol (MCP) Server** (`https://search.parallel.ai/mcp`):

1. **Parallel MCP Client (`parallel_mcp_client.py`)**:
   - Implements native JSON-RPC and SSE transport connecting directly to Parallel's official MCP endpoint (`https://search.parallel.ai/mcp`).
   - Supports both `Search MCP` (low-latency open search) and `Task MCP` (authenticated deep research).

2. **Google Cloud Agent Builder MCP Config (`agent_builder_mcp_config.json`)**:
   - Registers Parallel's MCP server endpoint natively within Google Cloud Agent Builder, allowing Gemini Enterprise agents to trigger Parallel search tools via standard MCP tool calls.

```json
{
  "mcp_servers": {
    "parallel_search": {
      "url": "https://search.parallel.ai/mcp",
      "transport": "sse",
      "auth": {
        "type": "bearer",
        "env_var": "PARALLEL_API_KEY"
      }
    }
  }
}
```

---

## ⚖️ 3. Hackathon Judging Criteria Self-Assessment

### 3.1 Technological Implementation (40% Weight)
- **Bounded Autonomy**: 32 documented autonomous capabilities including proactive watching (`poller.py`), strategy switching, self-correction reflection loops, and dual-key RSA signatures.
- **Parallel Integration**: Code-level verification via `python scripts/verify_integrations.py`.

### 3.2 Design & User Experience (30% Weight)
- **HITL Framing**: Framed explicitly as *Clearance Intelligence & Verification Audit*.
- **15-Second Attorney Override**: `AttorneyOverrideModal.tsx` pre-populates legal citations (17 U.S.C. § 107).

### 3.3 Potential Impact & Market Feasibility (30% Weight)
- **$51.4M TAM**: Replaces $250–$700/hr manual legal research with sub-5-second, $0.15/claim automated research.
- **E&O Insurance Binding**: Form E&O-2026 Certificate PDF for insurers (Chubb, Hiscox).

---

## ⚡ 4. 60-Second Judge Verification Instructions

Judges can verify all technical requirements using self-contained CLI scripts:

```bash
# 1. Verify Parallel API & Parallel MCP Server connectivity (<5s)
python scripts/verify_integrations.py

# 2. Audit SHA-256 cryptographic hash-chain ledger integrity (<5s)
python scripts/verify_ledger_integrity.py

# 3. Run complete end-to-end benchmark test suite
pytest tests/test_e2e_pipeline.py
```
