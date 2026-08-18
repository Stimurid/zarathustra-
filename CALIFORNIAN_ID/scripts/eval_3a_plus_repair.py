#!/usr/bin/env python3
"""Evaluate LIVE-R1..R7 repair evidence. No tautologies. No secrets."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_3a_plus_live import (  # type: ignore
    c,
    live_ok,
    load,
    no_fork_mutation,
    no_space_mutation,
    pair_drift_admit,
    pair_l1,
    pair_l5,
    pair_suboperation,
    verdict,
)

# Override OUT for the repair suite when imported after setting env.
import eval_3a_plus_live as _e

OUT = Path("/tmp/3a_plus_repair_live")
_e.OUT = OUT


def main():
    report = {}
    report["LIVE-R1"] = pair_l1(
        "R1_t1.json", "R1_t2.json", "same intent paraphrase")
    report["LIVE-R2"] = pair_suboperation(
        "R2_t1.json", "R2_t2.json", "same scene sub-operation")
    report["LIVE-R3"] = pair_l5(
        "R3_t1.json", "R3_t2.json", "material drift hold")
    report["LIVE-R4"] = pair_drift_admit(
        "R4_t1.json", "R4_t2.json", "material drift admit")

    r5 = load("R5.json")
    r5_status = c(r5).get("contract_status")
    report["LIVE-R5"] = verdict(
        live_ok(r5) and r5_status in {"PROVISIONAL", "CONFIRMED"}
        and c(r5).get("clarification_required") is not True
        and no_fork_mutation(r5) and no_space_mutation(r5),
        "direct assistance",
        live=live_ok(r5), contract=r5_status,
        terminal=c(r5).get("terminal"),
        clarification=c(r5).get("clarification_required"))

    r6 = load("R6.json")
    prop = c(r6).get("question_intent_proposal") or (
        r6 or {}).get("response", {}).get("question_intent_proposal") or {}
    plan = c(r6).get("question_set_plan") or (
        r6 or {}).get("response", {}).get("question_set_plan") or {}
    terminal = c(r6).get("terminal")
    requested = prop.get("requested")
    origin = plan.get("origin")
    n_forks = len(plan.get("forks") or plan.get("selected_questions") or [])
    if terminal == "PRESERVE_APORIA":
        r6_ok = live_ok(r6)
        r6_reason = "preserve_aporia_outranks_overlay"
    else:
        r6_ok = (live_ok(r6) and requested is True
                 and origin == "MODEL_PRODUCED_VALIDATED" and n_forks >= 1)
        r6_reason = "b2qr grounded no-count"
    report["LIVE-R6"] = verdict(
        r6_ok, r6_reason, live=live_ok(r6), requested=requested,
        origin=origin, n_forks=n_forks, terminal=terminal)

    r7 = load("R7.json")
    report["LIVE-R7"] = verdict(
        live_ok(r7) and no_fork_mutation(r7) and no_space_mutation(r7)
        and "fork_admitted" not in " ".join(c(r7).get("mutations_applied") or [])
        and "space_transition" not in " ".join(
            c(r7).get("mutations_applied") or []),
        "source/lexical negative",
        live=live_ok(r7),
        applied=c(r7).get("mutations_applied"),
        terminal=c(r7).get("terminal"))

    counts = {"PASS": 0, "FAIL": 0, "N/A": 0, "OTHER": 0}
    for k, v in report.items():
        r = v.get("result")
        if r in counts:
            counts[r] += 1
        else:
            counts["OTHER"] += 1
    all_pass = counts["FAIL"] == 0 and counts["OTHER"] == 0 and counts["PASS"] > 0
    out = {
        "counts": counts,
        "all_pass": all_pass,
        "cases": report,
        "deterministic_behavioral_claims": 0,
        "note": "LIVE repair evaluator; all_pass is false when any case is FAIL",
    }
    if counts["FAIL"] > 0:
        out["note"] += "; REPORT MUST NOT CLAIM ALL PASS"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "EVALUATION.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"counts": counts, "all_pass": all_pass},
                     ensure_ascii=False, indent=2))
    for k, v in report.items():
        print(f"{k:12} {v.get('result'):6} {v.get('reason')}")


if __name__ == "__main__":
    main()
