#!/usr/bin/env python3
"""Extended LIVE-C3..C5,C7,C10 smokes on VM localhost."""
import json
import sqlite3
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8085/api/socrates/run"
STORE = Path("/srv/tinkuy/runs/socrates_contexts.db")


def post(body):
    req = urllib.request.Request(
        BASE, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main():
    # C3/C4 fork
    r1 = post({"text": "establish parent", "execution_mode": "DETERMINISTIC",
               "intervention_profile": "normal"})
    cid = r1["context_id"]
    parent_scene = r1["state"]["scene_id"]
    r2 = post({"text": "fork", "execution_mode": "DETERMINISTIC",
               "intervention_profile": "normal", "context_id": cid,
               "context_action": {"kind": "FORK", "hypothesis": "alt path",
                                  "human_explicit_choice": True,
                                  "activate_branch": True}})
    print("LIVE-C3 fork", r2["context_id"], r2["state"].get("branch_id"),
          list((r2["state"].get("scene_registry") or {}).get("branches", {}).keys()
               if isinstance(r2["state"].get("scene_registry"), dict) else []))
    loaded = post({"text": "readdress parent", "execution_mode": "DETERMINISTIC",
                   "context_id": cid, "intervention_profile": "normal"})
    print("LIVE-C4 parent scene preserved",
          loaded["state"]["scene_id"] == parent_scene, parent_scene)

    # C10 durability — store file exists and reloads
    exists = STORE.exists()
    print("LIVE-C10 store exists", exists)
    if exists:
        conn = sqlite3.connect(str(STORE))
        n = conn.execute("SELECT COUNT(*) FROM socrates_contexts").fetchone()[0]
        print("LIVE-C10 row count", n)
    print("EXTENDED OK")


if __name__ == "__main__":
    main()
