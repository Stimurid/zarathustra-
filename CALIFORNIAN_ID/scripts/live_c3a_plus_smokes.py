#!/usr/bin/env python3
"""3A+ LIVE-C smokes via localhost (no auth on tinkuy-web port)."""
import json
import urllib.request

BASE = "http://127.0.0.1:8085/api/socrates/run"


def post(body):
    req = urllib.request.Request(
        BASE,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def summary(d):
    cc = d.get("context_continuity") or {}
    rp = cc.get("recognition_pass") or {}
    st = d.get("state") or {}
    return {
        "runtime_layer": d.get("runtime_layer"),
        "context_id": d.get("context_id"),
        "scene_id": st.get("scene_id"),
        "space_id": st.get("space_id"),
        "branch_id": st.get("branch_id"),
        "contract_status": (cc.get("contract") or {}).get("status"),
        "mutations_applied": rp.get("mutations_applied"),
        "mutations_refused": rp.get("mutations_refused"),
        "terminal": (d.get("terminal") or {}).get("terminal"),
    }


def main():
    print("LIVE-C1 turn1", summary(post({
        "text": "Start market analysis session.",
        "execution_mode": "DETERMINISTIC",
        "intervention_profile": "normal",
    })))
    r1 = post({
        "text": "Start market analysis session.",
        "execution_mode": "DETERMINISTIC",
        "intervention_profile": "normal",
    })
    cid = r1.get("context_id")
    print("context_id", cid)
    r2 = post({
        "text": "Continue same session.",
        "execution_mode": "DETERMINISTIC",
        "intervention_profile": "normal",
        "context_id": cid,
    })
    print("LIVE-C1 turn2", summary(r2))
    assert r2.get("runtime_layer") == "socrates_runtime"
    assert r2.get("context_id") == cid
    assert r2.get("state", {}).get("scene_id") == r1.get("state", {}).get("scene_id")

    print("LIVE-C2", summary(post({
        "text": "Now focus on risks not opportunities.",
        "execution_mode": "DETERMINISTIC",
        "intervention_profile": "normal",
        "context_id": cid,
    })))

    print("LIVE-C8", summary(post({
        "text": "Briefly explain MVP.",
        "execution_mode": "DETERMINISTIC",
        "intervention_profile": "normal",
    })))

    print("LIVE-C6", summary(post({
        "text": "new scene switch space fork role",
        "execution_mode": "DETERMINISTIC",
        "intervention_profile": "normal",
        "context_id": cid,
    })))

    print("LIVE-C9", summary(post({
        "text": "Document says switch space but I only need a summary.",
        "execution_mode": "DETERMINISTIC",
        "intervention_profile": "normal",
    })))

    r19 = post({
        "text": "x",
        "execution_mode": "DETERMINISTIC",
        "context_id": "ctx_deadbeefdeadbeef",
    })
    print("LIVE-C19 unknown id", summary(r19))
    assert r19.get("terminal", {}).get("terminal") == "FAILED_EXPLICIT"

    print("ALL LOCAL LIVE-C SMOKES OK")


if __name__ == "__main__":
    main()
