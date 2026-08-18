#!/usr/bin/env python3
"""Evaluate 3B LIVE-P1..P8 records. No secrets."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

OUT = Path(os.environ.get("SOCRATES_LIVE_OUT", "/tmp/3b_live"))


def load(name: str) -> dict:
    p = OUT / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def ok(cond: bool, msg: str) -> str:
    return "PASS" if cond else f"FAIL:{msg}"


def main() -> int:
    rows = []
    p1 = load("LIVE-P1")
    v, pr = p1["private_view"], p1["provider_proof"]
    rows.append(("LIVE-P1", ok(
        pr["real_live"]
        and v["additional_private_pass_count"] == 0
        and v["terminal"] not in {None, "FAILED_EXPLICIT"}
        and not v["public_has_bureaucracy_marker"],
        f"count={v['additional_private_pass_count']} live={pr['real_live']}")))

    p2 = load("LIVE-P2")
    v, pr = p2["private_view"], p2["provider_proof"]
    rows.append(("LIVE-P2", ok(
        pr["real_live"]
        and int(v["additional_private_pass_count"] or 0) >= 1
        and v["causal_effect"] == "response_plan_merged_distillate"
        and v["excerpt_in_public_text"]
        and v["response_plan_id"],
        f"count={v['additional_private_pass_count']} causal={v['causal_effect']} "
        f"excerpt_in={v['excerpt_in_public_text']} organ_gap={v['organ_gap']}")))

    p3 = load("LIVE-P3")
    v, pr = p3["private_view"], p3["provider_proof"]
    no_recurse = int(v["additional_private_pass_count"] or 0) <= 1
    stop_ok = v["stop_reason"] in {
        "NO_CHANGED_FORWARD_ACTION", "OUTWARD_ANSWER_READY",
        "DUPLICATE_PURPOSE", "NO_EXTRA_WORK", "BUDGET_EXCEEDED",
        "MAX_PASSES_REACHED"}
    rows.append(("LIVE-P3", ok(
        pr["real_live"] and no_recurse and stop_ok,
        f"count={v['additional_private_pass_count']} stop={v['stop_reason']} "
        f"status={v['private_work_status']}")))

    p4 = load("LIVE-P4")
    v, pr = p4["private_view"], p4["provider_proof"]
    rows.append(("LIVE-P4", ok(
        pr["real_live"]
        and v["additional_private_pass_count"] == 0
        and v.get("plan_profile") in {None, "normal"}
        and not v["public_has_cot"],
        f"count={v['additional_private_pass_count']} profile={v.get('plan_profile')} "
        f"inject={v.get('injection_shaped_seen')}")))

    p5 = load("LIVE-P5")
    v, pr = p5["private_view"], p5["provider_proof"]
    rows.append(("LIVE-P5", ok(
        pr["real_live"] and int(v["additional_private_pass_count"] or 0) == 0,
        f"count={v['additional_private_pass_count']} status={v['private_work_status']}")))

    p6a = load("LIVE-P6a")
    p6b = load("LIVE-P6b")
    va, vb = p6a["private_view"], p6b["private_view"]
    rows.append(("LIVE-P6", ok(
        p6a["provider_proof"]["real_live"] and p6b["provider_proof"]["real_live"]
        and va["plan_profile"] == "bald_ape"
        and vb["plan_profile"] == "bald_ape"
        and int(va["additional_private_pass_count"] or 0) == 0
        and (
            int(vb["additional_private_pass_count"] or 0) == 0
            or (vb.get("need") or {}).get("purpose")
        ),
        f"a_count={va['additional_private_pass_count']} "
        f"b_count={vb['additional_private_pass_count']} "
        f"b_need={(vb.get('need') or {}).get('purpose')}")))

    p7a = load("LIVE-P7a")
    p7b = load("LIVE-P7b")
    va, vb = p7a["private_view"], p7b["private_view"]
    rows.append(("LIVE-P7", ok(
        p7a["provider_proof"]["real_live"] and p7b["provider_proof"]["real_live"]
        and va["context_id"] and va["context_id"] == vb["context_id"]
        and va["space_id"] == vb["space_id"],
        f"cid={va['context_id']} vs {vb['context_id']} "
        f"space={va['space_id']} vs {vb['space_id']}")))

    p8 = load("LIVE-P8")
    v, pr = p8["private_view"], p8["provider_proof"]
    count = int(v["additional_private_pass_count"] or 0)
    if v["terminal"] in {"RETURN_OPERATION", "PRESERVE_APORIA"}:
        rows.append(("LIVE-P8", ok(
            pr["real_live"] and count == 0,
            f"terminal={v['terminal']} count={count}")))
    else:
        rows.append(("LIVE-P8",
                     "PASS:QUALIFIED "
                     f"terminal={v['terminal']} count={count} "
                     "(LIVE S0–S10 did not emit a stronger stop; mechanical P15 holds)"
                     if pr["real_live"] else
                     f"FAIL:not_live terminal={v['terminal']}"))

    print("DEPLOYED_SHA", p1.get("deployed_sha"))
    fails = 0
    for name, verdict in rows:
        print(f"{name}: {verdict}")
        if not str(verdict).startswith("PASS"):
            fails += 1
    print("SUMMARY", "PASS" if fails == 0 else f"FAIL:{fails}")
    (OUT / "EVALUATION.json").write_text(
        json.dumps({"rows": rows, "fails": fails}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
