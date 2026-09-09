"""Opt-in live intake check against real providers, isolated from production data.

Run with --source-file PATH. Credentials come from the existing environment/.env.
Produces a local unresolved draft snapshot; never records a reviewer approval.
"""
import argparse
import json
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(".data/live-verification.json"))
    args = parser.parse_args()
    load_dotenv()
    os.environ["CLEARANCE_LIVE_ENABLED"] = "true"
    from backend.clearance.models import RevisionInput
    from backend.clearance.service import submit, current
    from backend.clearance.store import SQLiteStore
    from backend.clearance.worker import Worker
    root = "organizations/local_verification/productions/live_verification"
    payload = RevisionInput(production_id="live_verification", source_text=args.source_file.read_text(), max_spend_usd=.25)
    with tempfile.TemporaryDirectory(prefix="lienmark-live-") as directory:
        store = SQLiteStore(Path(directory) / "verification.db")
        job = submit(store, root, payload, "local-verification-producer", "verification")
        Worker(store).run(root + "/live_jobs/" + job["audit_id"])
        result = current(store, root)
        dispatch = store.get(root + "/live_jobs/" + job["audit_id"])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"workspace": result, "dispatch": dispatch}, indent=2))
        snapshot = result.get("snapshot") or {}
        calls = dispatch["calls"]
        print(json.dumps({"status": dispatch["status"], "error": dispatch.get("error"), "claims": len(snapshot.get("claims", [])),
            "completed_provider_calls": sum(c["status"] == "COMPLETED" for c in calls.values()),
            "reserved_usd": dispatch["reserved_usd"], "output": str(args.output)}))
        if not snapshot.get("claims") or any(not c.get("investigation") or c.get("investigation_error") for c in snapshot["claims"]):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
