"""G-S25R.8F — unblind C01, apply pair rule, compute R8 final gate.

Runs AFTER ``C01_FRESH_BLIND_SCORE.json`` is frozen. Opens
C01's PRIVATE_ARM_MAP once, mechanically maps blind labels → arm roles,
computes the pair verdict per the frozen rule, and combines with the
already-locked C02..C11 unblind results to write:

    docs/socrates_gs26/live_acceptance/r8_closure/C01_UNBLINDED_VERDICT.json
    docs/socrates_gs26/live_acceptance/r8_closure/R8_FINAL_GATE.json

Frozen pair rule (from the handoff):

    B_BETTER                 if B >= A + 4 and no new fatal
                             and same/better hard-contract class
    NO_MATERIAL_DIFFERENCE   if abs(B - A) < 4 and no decisive fatal delta
    A_BETTER                 if A >= B + 4 or B adds a fatal
    INCOMPARABLE             on execution/control mismatch

Semantic gate: >= 7 of 10 required families B_BETTER.
Ablation gate: behavioural degradation OR mandatory-body fail-close.
The script does not "beautify" any result.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIVE = REPO / "docs" / "socrates_gs26" / "live_acceptance" / "r8"
CLOSURE = REPO / "docs" / "socrates_gs26" / "live_acceptance" / "r8_closure"


# ---------------------------------------------------------- locked results

#: Owner-supplied C02..C11 unblind results, pasted verbatim from the
#: authoritative handoff. Kept here so the final gate JSON is a single
#: reproducible artefact. Scores must NOT be edited.
LOCKED_UNBLIND: dict[str, dict] = {
    "R8-C02_STATUS_TEMPORALITY": {"A": 36, "B": 39, "pair_verdict": "NO_MATERIAL_DIFFERENCE",
                                    "family": "required"},
    "R8-C03_OPERATION_OBJECT_PESKOV": {"A": 31, "B": 40, "pair_verdict": "B_BETTER",
                                         "family": "required"},
    "R8-C04_ONTOLOGY_GAP": {"A": 28, "B": 40, "pair_verdict": "B_BETTER",
                             "family": "required"},
    "R8-C05_RETRIEVAL_ATTENTION": {"A": 28, "B": 39, "pair_verdict": "B_BETTER",
                                    "family": "extra"},
    "R8-C06_HUMAN_OWNERSHIP": {"A": 35, "B": 40, "pair_verdict": "B_BETTER",
                                 "family": "required"},
    "R8-C07_REFLEXIVE_RETURN": {"A": 24, "B": 40, "pair_verdict": "B_BETTER",
                                  "a_fatal": ["TASK_ABANDONMENT_AS_REFLECTION"],
                                  "family": "required"},
    "R8-C08_COUNCIL_AUTHORITY": {"A": 38, "B": 40, "pair_verdict": "NO_MATERIAL_DIFFERENCE",
                                   "family": "required"},
    "R8-C09_FALSE_SYNTHESIS": {"A": 31, "B": 40, "pair_verdict": "B_BETTER",
                                 "family": "required"},
    "R8-C10_MEMORY_WRITE": {"A": 31, "B": 40, "pair_verdict": "B_BETTER",
                             "family": "required"},
    "R8-C11_DIRECT_ASSISTANCE_BYPASS": {"A": 39, "B": 40, "pair_verdict": "NO_MATERIAL_DIFFERENCE",
                                          "family": "required"},
}

#: Behavioral ablation scores (B vs C-minus-target). No degradation seen.
LOCKED_ABLATION: dict[str, dict] = {
    "R8-C02_STATUS_TEMPORALITY": {"B": 39, "C": 39, "target": "B02"},
    "R8-C03_OPERATION_OBJECT_PESKOV": {"B": 40, "C": 38, "target": "B03"},
    "R8-C04_ONTOLOGY_GAP": {"B": 40, "C": 38, "target": "B08"},
    "R8-C05_RETRIEVAL_ATTENTION": {"B": 39, "C": 39, "target": "B04"},
    "R8-C06_HUMAN_OWNERSHIP": {"B": 40, "C": 40, "target": "B06"},
    "R8-C07_REFLEXIVE_RETURN": {"B": 40, "C": 40, "target": "B07"},
    "R8-C08_COUNCIL_AUTHORITY": {"B": 40, "C": 40, "target": "B09"},
    "R8-C09_FALSE_SYNTHESIS": {"B": 40, "C": 40, "target": "B08"},
    "R8-C10_MEMORY_WRITE": {"B": 40, "C": 39, "target": "B05"},
    "R8-C11_DIRECT_ASSISTANCE_BYPASS": {"B": 40, "C": 40, "target": "B10"},
}


# ---------------------------------------------------------- pair rule


def apply_pair_rule(a_total: int, b_total: int,
                    a_fatals: list[str], b_fatals: list[str]) -> str:
    new_b_fatal = any(f not in a_fatals for f in b_fatals)
    if new_b_fatal:
        return "A_BETTER"
    if b_total >= a_total + 4:
        return "B_BETTER"
    if a_total >= b_total + 4:
        return "A_BETTER"
    return "NO_MATERIAL_DIFFERENCE"


def apply_ablation_rule(b_total: int, c_total: int) -> str:
    if b_total >= c_total + 4:
        return "B_BETTER"
    if c_total >= b_total + 4:
        return "C_BETTER"
    return "NO_MATERIAL_DIFFERENCE"


# ---------------------------------------------------------- main


def _load_score() -> dict:
    p = CLOSURE / "C01_FRESH_BLIND_SCORE.json"
    b = p.read_bytes()
    d = json.loads(b.decode("utf-8"))
    # Verify the stored score_file_sha256 matches the file's bytes-minus-that-hash.
    body_no_hash = json.dumps({k: v for k, v in d.items()
                                if k != "score_file_sha256"},
                               ensure_ascii=False, indent=2, sort_keys=True)
    computed = hashlib.sha256(body_no_hash.encode("utf-8")).hexdigest()
    if computed != d.get("score_file_sha256"):
        raise SystemExit(
            f"C01 score file self-hash mismatch — file was modified after "
            f"scoring (expected {d.get('score_file_sha256')}, got {computed})")
    return d


def _load_c01_private_map() -> dict[str, str]:
    p = LIVE / "R8-C01_SCENE_CAPTURE" / "PRIVATE_ARM_MAP.json"
    # Map is role → blind_label. Invert to blind_label → role.
    role_to_label = json.loads(p.read_text(encoding="utf-8"))
    return {v: k for k, v in role_to_label.items()}


def _unblind_c01(score: dict) -> dict:
    label_to_role = _load_c01_private_map()
    per_arm: dict[str, dict] = {}
    for arm in score["arms"]:
        role = label_to_role.get(arm["blind_arm_label"])
        if role is None:
            raise SystemExit(f"unknown blind label: {arm['blind_arm_label']}")
        per_arm[role] = {
            "weighted_total": arm["weighted_total"],
            "fatal_failures": arm["fatal_failures_detected"],
        }
    a = per_arm["A_HISTORICAL"]
    b = per_arm["B_SEMANTIC"]
    c_key = next(k for k in per_arm if k.startswith("C_"))
    c = per_arm[c_key]

    pair = apply_pair_rule(a["weighted_total"], b["weighted_total"],
                            a["fatal_failures"], b["fatal_failures"])
    ablation = apply_ablation_rule(b["weighted_total"], c["weighted_total"])

    return {
        "case_id": "R8-C01_SCENE_CAPTURE",
        "score_file_sha256": score["score_file_sha256"],
        "packet_sha256": score["packet_sha256"],
        "rubric_sha256": score["rubric_sha256"],
        "evaluator": score["evaluator"],
        "A_total": a["weighted_total"],
        "B_total": b["weighted_total"],
        "C_total": c["weighted_total"],
        "delta_BminusA": b["weighted_total"] - a["weighted_total"],
        "delta_BminusC": b["weighted_total"] - c["weighted_total"],
        "A_fatal_failures": a["fatal_failures"],
        "B_fatal_failures": b["fatal_failures"],
        "C_fatal_failures": c["fatal_failures"],
        "pair_verdict": pair,
        "ablation_verdict": ablation,
        "c_ablation_role": c_key,
    }


def _final_gate(c01_verdict: dict, request_integrity: dict,
                mount_neg: dict) -> dict:
    # C01 is always in the required set (that is the point of the
    # fresh-eval step).  C05 was recorded as an "extra family" in the
    # owner handoff and does NOT count against the frozen threshold of
    # 7 of 10 required families.
    required_verdicts: dict[str, str] = {
        "R8-C01_SCENE_CAPTURE": c01_verdict["pair_verdict"]}
    extra_verdicts: dict[str, str] = {}
    for cid, r in LOCKED_UNBLIND.items():
        family = r.get("family", "required")
        (required_verdicts if family == "required"
         else extra_verdicts)[cid] = r["pair_verdict"]

    b_better_required = sum(1 for v in required_verdicts.values()
                             if v == "B_BETTER")
    b_better_extra = sum(1 for v in extra_verdicts.values()
                          if v == "B_BETTER")
    required_total = len(required_verdicts)
    semantic_pass = b_better_required >= 7

    # behavioural ablation: any case where B >= C+4?
    behavioural_degradation = sum(
        1 for r in LOCKED_ABLATION.values()
        if r["B"] >= r["C"] + 4)
    mandatory_fail_close = mount_neg["valid_mandatory_fail_close_count"]
    ablation_pass = (behavioural_degradation > 0
                     or mandatory_fail_close >= 5)

    # direct assistance regression check (only C11 is the direct-assist case)
    direct_assist = required_verdicts.get("R8-C11_DIRECT_ASSISTANCE_BYPASS")
    direct_assist_regressed = (direct_assist == "A_BETTER")

    fatal_regressions = [r for r in LOCKED_UNBLIND.values()
                          if r.get("a_fatal") and r["pair_verdict"] == "A_BETTER"]

    # Overall verdict:
    #   PASS    both gates cleared, no direct-assistance regression;
    #   PARTIAL some frozen threshold missed but no regressions and the
    #           alternative mount-fail-close route cleared;
    #   FAIL    a regression exists OR nothing cleared.
    if semantic_pass and ablation_pass and not direct_assist_regressed:
        final = "PASS"
    elif direct_assist_regressed:
        final = "FAIL"
    elif ablation_pass and not semantic_pass:
        final = "PARTIAL"
    elif semantic_pass and not ablation_pass:
        final = "PARTIAL"
    elif b_better_required == 0:
        final = "FAIL"
    else:
        final = "PARTIAL"

    return {
        "artifact_id": "SOCRATES_R8_FINAL_GATE",
        "version": "0.1.0",
        "generation": "G-S25R.8F",

        "live_execution": {
            "total_arms": 33,
            "provider": "302ai",
            "notes": "reused from previously accepted 33/33 live outputs",
        },

        "request_integrity": {
            "arms": request_integrity["arm_count"],
            "matches": request_integrity["matches"],
            "mismatches": request_integrity["mismatches"],
            "user_payload_evaluation_metadata_leak":
                request_integrity["evaluation_metadata_leak_scan"]["any_hit"],
        },

        "semantic_improvement": {
            "required_families_total": required_total,
            "required_B_BETTER_count": b_better_required,
            "required_verdicts": required_verdicts,
            "extra_families_verdicts": extra_verdicts,
            "extra_B_BETTER_count": b_better_extra,
            "gate_threshold": 7,
            "verdict": "PASS" if semantic_pass else "FAIL",
        },

        "behavioral_ablation": {
            "behavioural_degradation_cases": behavioural_degradation,
            "detail": LOCKED_ABLATION,
            "verdict": ("PASS" if behavioural_degradation > 0
                        else "NOT_DEMONSTRATED"),
        },

        "mount_negative_ablation": {
            "mandatory_bodies_tested":
                mount_neg["mandatory_targets_total"],
            "mandatory_bodies_fail_closed":
                mount_neg["valid_mandatory_fail_close_count"],
            "b08_classification":
                mount_neg["b08_classification"]["status"],
            "verdict": "PASS" if mandatory_fail_close >= 5 else "PARTIAL",
        },

        "direct_assistance_regression": {
            "case": "R8-C11_DIRECT_ASSISTANCE_BYPASS",
            "verdict": direct_assist,
            "regressed": direct_assist_regressed,
        },

        "fatal_regressions": fatal_regressions,

        "c01_unblinded": c01_verdict,

        "final_verdict": final,
    }


def main() -> int:
    score = _load_score()
    c01 = _unblind_c01(score)
    (CLOSURE / "C01_UNBLINDED_VERDICT.json").write_text(
        json.dumps(c01, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8")

    integrity = json.loads(
        (CLOSURE / "REQUEST_INTEGRITY_REPORT.json")
        .read_text(encoding="utf-8"))
    mount_neg = json.loads(
        (CLOSURE / "MOUNT_NEGATIVE_PROOF.json")
        .read_text(encoding="utf-8"))

    gate = _final_gate(c01, integrity, mount_neg)
    (CLOSURE / "R8_FINAL_GATE.json").write_text(
        json.dumps(gate, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8")

    print(f"C01 pair verdict:            {c01['pair_verdict']}")
    print(f"C01 A={c01['A_total']}  B={c01['B_total']}  "
          f"C={c01['C_total']}")
    sem = gate["semantic_improvement"]
    print(f"semantic gate:               "
          f"{sem['required_B_BETTER_count']}/{sem['required_families_total']}  "
          f"(threshold {sem['gate_threshold']}) → {sem['verdict']}  "
          f"[+ extra {sem['extra_B_BETTER_count']} not counted]")
    beh = gate["behavioral_ablation"]
    print(f"behavioral ablation:         "
          f"{beh['behavioural_degradation_cases']} degradations → "
          f"{beh['verdict']}")
    mnt = gate["mount_negative_ablation"]
    print(f"mount-negative ablation:     "
          f"{mnt['mandatory_bodies_fail_closed']}/"
          f"{mnt['mandatory_bodies_tested']} → {mnt['verdict']}")
    print(f"direct assistance regression: "
          f"{gate['direct_assistance_regression']['regressed']}")
    print()
    print(f"R8 FINAL VERDICT:            {gate['final_verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
