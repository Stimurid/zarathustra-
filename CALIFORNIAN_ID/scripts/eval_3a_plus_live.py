#!/usr/bin/env python3
"""Evaluate L1-L20 LIVE evidence. Run on VM after suite. No secrets."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path("/tmp/3a_plus_live")


def load(name: str) -> dict | None:
    p = OUT / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def c(rec: dict | None) -> dict:
    return (rec or {}).get("continuity") or {}


def pp(rec: dict | None) -> dict:
    return (rec or {}).get("provider_proof") or {}


def live_ok(rec: dict | None) -> bool:
    p = pp(rec)
    return bool(
        rec
        and p.get("runtime_layer") == "socrates_runtime"
        and p.get("execution_mode") == "LIVE"
        and p.get("live_ok_phases", 0) >= 1
        and p.get("mockish_phases", 0) == 0
    )


def same(a, b, *keys):
    ca, cb = c(a), c(b)
    return {k: (ca.get(k) == cb.get(k) and bool(ca.get(k))) for k in keys}


def no_space_mutation(rec) -> bool:
    ca = c(rec)
    applied = " ".join(ca.get("mutations_applied") or [])
    return "space_transition" not in applied and not (ca.get("transductions") or [])


def no_fork_mutation(rec) -> bool:
    ca = c(rec)
    applied = " ".join(ca.get("mutations_applied") or [])
    return "fork_admitted" not in applied


def same_branch_or_trunk(a, b) -> bool:
    ba = (c(a).get("branch_id") or "")
    bb = (c(b).get("branch_id") or "")
    return ba == bb


def no_revision_candidate(rec) -> bool:
    ca = c(rec)
    if ca.get("revision_candidates"):
        return False
    if ca.get("contract_status") == "REVISION_PROPOSED":
        return False
    applied = " ".join(ca.get("mutations_applied") or [])
    if "contract_revision_proposed" in applied:
        return False
    if "contract_revision_admitted" in applied:
        return False
    if "contract_revision_held" in applied:
        return False
    return True


def admission_outcome(rec) -> str | None:
    ca = c(rec)
    adms = ca.get("revision_admissions") or []
    if adms:
        return adms[-1].get("outcome")
    meta = (rec or {}).get("continuity") or {}
    cra = meta.get("contract_revision_admission") or (
        (rec or {}).get("response") or {}).get("context_continuity", {}).get(
            "contract_revision_admission")
    if isinstance(cra, dict):
        return cra.get("outcome")
    return None


def verdict(ok: bool, reason: str, **extra) -> dict:
    d = {"result": "PASS" if ok else "FAIL", "reason": reason}
    d.update(extra)
    return d


def has_revision(rec) -> bool:
    return not no_revision_candidate(rec)


def same_active_contract(t1, t2) -> bool:
    c1, c2 = c(t1), c(t2)
    return bool(c1.get("contract_id")) and (
        c1.get("contract_id") == c2.get("contract_id")
        and c1.get("contract_version") == c2.get("contract_version"))


def pair_l1(t1n, t2n, label):
    """SAME-SCENE / SAME-INTENT. Fails if any contract revision appears."""
    t1, t2 = load(t1n), load(t2n)
    if not t1 or not t2:
        return verdict(False, "missing evidence files", t1=bool(t1), t2=bool(t2))
    s = same(t1, t2, "context_id", "scene_id", "space_id")
    ok = (live_ok(t1) and live_ok(t2) and all(s.values())
          and same_branch_or_trunk(t1, t2)
          and no_fork_mutation(t2) and no_space_mutation(t2)
          and no_revision_candidate(t2)
          and same_active_contract(t1, t2))
    return verdict(ok, label, live=(live_ok(t1), live_ok(t2)), identity=s,
                   branch_same=same_branch_or_trunk(t1, t2),
                   applied_t2=c(t2).get("mutations_applied"),
                   contract=(c(t1).get("contract_status"),
                             c(t2).get("contract_status")),
                   contract_ids=(c(t1).get("contract_id"),
                                 c(t2).get("contract_id")),
                   telos=(c(t1).get("telos"), c(t2).get("telos")),
                   op=(c(t1).get("operation_kind"), c(t2).get("operation_kind")),
                   revision_on_continue=has_revision(t2))


def pair_suboperation(t1n, t2n, label):
    """Same scene sub-operation: op.kind may change; no SceneContract revision."""
    v = pair_l1(t1n, t2n, label)
    t1, t2 = load(t1n), load(t2n)
    if t1 and t2:
        op_changed = (c(t1).get("operation_kind") or "") != (
            c(t2).get("operation_kind") or "")
        v["operation_changed"] = op_changed
        v["reason"] = label
    return v


def pair_l2(t1n, t2n, label):
    t1, t2 = load(t1n), load(t2n)
    if not t1 or not t2:
        return verdict(False, "missing")
    s = same(t1, t2, "context_id", "space_id")
    intent_shift = (
        (c(t1).get("telos") or "") != (c(t2).get("telos") or "")
        or (c(t1).get("operation_kind") or "") != (c(t2).get("operation_kind") or "")
        or has_revision(t2)
    )
    ok = (live_ok(t1) and live_ok(t2) and all(s.values())
          and no_fork_mutation(t2) and no_space_mutation(t2) and intent_shift)
    return verdict(ok, label, live=(live_ok(t1), live_ok(t2)), identity=s,
                   intent_shift=intent_shift, revision=has_revision(t2),
                   telos=(c(t1).get("telos"), c(t2).get("telos")),
                   op=(c(t1).get("operation_kind"), c(t2).get("operation_kind")),
                   contract=c(t2).get("contract_status"),
                   admission=admission_outcome(t2))


def pair_l5(t1n, t2n, label):
    """Material drift HOLD: candidate exists; old active remains; admission explicit."""
    t1, t2 = load(t1n), load(t2n)
    if not t1 or not t2:
        return verdict(False, "missing")
    s = same(t1, t2, "context_id", "space_id")
    old_id = c(t1).get("contract_id")
    new_id = c(t2).get("contract_id")
    outcome = admission_outcome(t2)
    candidate = bool(c(t2).get("revision_candidates")) or has_revision(t2)
    old_still_active = bool(old_id) and old_id == new_id
    activated_without_admit = (
        bool(old_id) and old_id != new_id
        and outcome != "ADMIT_REVISION")
    ok = (live_ok(t1) and live_ok(t2) and all(s.values())
          and no_fork_mutation(t2) and no_space_mutation(t2)
          and candidate and old_still_active
          and outcome in {"HOLD_PROPOSAL", "ASK_HUMAN"}
          and not activated_without_admit)
    return verdict(
        ok, label, live=(live_ok(t1), live_ok(t2)), identity=s,
        revision=has_revision(t2),
        admission=outcome,
        old_contract_id=old_id, new_contract_id=new_id,
        old_still_active=old_still_active,
        activated_without_admit=activated_without_admit,
        telos=(c(t1).get("telos"), c(t2).get("telos")),
        op=(c(t1).get("operation_kind"), c(t2).get("operation_kind")),
        contract=c(t2).get("contract_status"))


def pair_drift_admit(t1n, t2n, label):
    """Material drift ADMIT: explicit ADMIT_REVISION; new active; old addressable."""
    t1, t2 = load(t1n), load(t2n)
    if not t1 or not t2:
        return verdict(False, "missing")
    old_id = c(t1).get("contract_id")
    new_id = c(t2).get("contract_id")
    outcome = admission_outcome(t2)
    hist = c(t2).get("contract_history") or []
    old_in_hist = any(
        (h.get("contract_id") == old_id) for h in hist) if hist else True
    applied = " ".join(c(t2).get("mutations_applied") or [])
    ok = (live_ok(t1) and live_ok(t2)
          and outcome == "ADMIT_REVISION"
          and bool(old_id) and bool(new_id) and old_id != new_id
          and "contract_revision_admitted:" in applied
          and old_in_hist)
    return verdict(
        ok, label, live=(live_ok(t1), live_ok(t2)),
        admission=outcome,
        old_contract_id=old_id, new_contract_id=new_id,
        applied=c(t2).get("mutations_applied"))


def main():
    report = {}
    report["L1A"] = pair_l1("L1A_t1.json", "L1A_t2.json", "same scene topic A")
    report["L1B"] = pair_l1("L1B_t1.json", "L1B_t2.json", "same scene topic B")
    report["L2A"] = pair_l2("L2A_t1.json", "L2A_t2.json", "intent shift A")
    report["L2B"] = pair_l2("L2B_t1.json", "L2B_t2.json", "intent shift B")

    l3 = load("L3.json")
    l3_status = c(l3).get("contract_status")
    report["L3"] = verdict(
        live_ok(l3) and l3_status in {"PROVISIONAL", "CONFIRMED"}
        and c(l3).get("clarification_required") is not True,
        "direct assistance",
        live=live_ok(l3),
        contract=l3_status,
        terminal=c(l3).get("terminal"),
        clarification=c(l3).get("clarification_required"))

    l4 = load("L4.json")
    l4_hold = bool(
        c(l4).get("clarification_required")
        or c(l4).get("terminal") in {"HOLD", "RETURN_OPERATION", "PRESERVE_APORIA"}
        or c(l4).get("open_world_gap")
        or c(l4).get("operation_applicable") is False
    )
    report["L4"] = verdict(
        live_ok(l4) and no_space_mutation(l4) and no_fork_mutation(l4) and l4_hold,
        "operation ambiguity",
        live=live_ok(l4), hold_signal=l4_hold,
        terminal=c(l4).get("terminal"),
        clarification=c(l4).get("clarification_required"),
        applicable=c(l4).get("operation_applicable"),
        gap=c(l4).get("open_world_gap"),
        op=c(l4).get("operation_kind"))

    report["L5A"] = pair_l5("L5A_t1.json", "L5A_t2.json", "drift A")
    report["L5B"] = pair_l5("L5B_t1.json", "L5B_t2.json", "drift B")

    l6t1, l6t2 = load("L6_t1.json"), load("L6_t2.json")
    l6_child = bool(c(l6t2).get("branch_id") or (c(l6t2).get("branches") or {}))
    l6_parent = (c(l6t1).get("scene_id") and
                 c(l6t1).get("scene_id") == c(l6t2).get("scene_id"))
    applied = " ".join(c(l6t2).get("mutations_applied") or [])
    report["L6"] = verdict(
        live_ok(l6t1) and live_ok(l6t2) and l6_child and l6_parent
        and "fork_admitted" in applied,
        "explicit human fork",
        live=(live_ok(l6t1), live_ok(l6t2)),
        parent_scene_preserved=l6_parent,
        branch_id=c(l6t2).get("branch_id"),
        branches=list((c(l6t2).get("branches") or {}).keys()),
        applied=c(l6t2).get("mutations_applied"))

    l7t2 = load("L7_t2.json")
    report["L7"] = verdict(
        live_ok(load("L7_t1.json")) and live_ok(l7t2) and no_fork_mutation(l7t2)
        and no_space_mutation(l7t2),
        "natural fork pressure no mutation",
        live=live_ok(l7t2),
        fork_cands=len(c(l7t2).get("fork_candidates") or []),
        applied=c(l7t2).get("mutations_applied"),
        refused=c(l7t2).get("mutations_refused"))

    l8c, l8p = load("L8_child.json"), load("L8_parent.json")
    report["L8"] = verdict(
        live_ok(l8c) and live_ok(l8p)
        and c(l8p).get("scene_id") == c(l6t1).get("scene_id")
        and c(l8c).get("context_id") == c(l6t2).get("context_id"),
        "branch re-address",
        live=(live_ok(l8c), live_ok(l8p)),
        parent_scene=(c(l6t1).get("scene_id"), c(l8p).get("scene_id")),
        child_branch=c(l8c).get("branch_id"),
        parent_branches=list((c(l8p).get("branches") or {}).keys()))

    l9s = load("L9_STATUS.json")
    l9 = load("L9.json")
    if l9s and l9s.get("status") == "NOT_APPLICABLE_NO_SECOND_REGISTERED_SPACE":
        report["L9"] = {
            "result": "N/A",
            "reason": "no legitimate second registered EpistemicSpace in production",
            "status": l9s,
            "probe_live": live_ok(load("L9_no_second_space.json")),
        }
    elif l9:
        applied = " ".join(c(l9).get("mutations_applied") or [])
        report["L9"] = verdict(
            live_ok(l9) and "space_transition" in applied
            and bool(c(l9).get("transductions")),
            "authorized known space transition",
            live=live_ok(l9), applied=c(l9).get("mutations_applied"),
            transductions=c(l9).get("transductions"))
    else:
        report["L9"] = verdict(False, "missing L9 evidence")

    l10 = load("L10_t2.json")
    space_same = c(load("L10_t1.json")).get("space_id") == c(l10).get("space_id")
    report["L10"] = verdict(
        live_ok(load("L10_t1.json")) and live_ok(l10)
        and no_space_mutation(l10) and space_same,
        "unauthorized space switch negative",
        live=live_ok(l10), space_same=space_same,
        applied=c(l10).get("mutations_applied"),
        space_cands=len(c(l10).get("space_candidates") or []))

    l11a, l11b = load("L11A.json"), load("L11B.json")
    report["L11"] = verdict(
        live_ok(l11a) and live_ok(l11b)
        and no_space_mutation(l11a) and no_space_mutation(l11b)
        and no_fork_mutation(l11a) and no_fork_mutation(l11b),
        "lexical negative",
        live=(live_ok(l11a), live_ok(l11b)),
        applied=(c(l11a).get("mutations_applied"),
                 c(l11b).get("mutations_applied")))

    l12 = load("L12.json")
    report["L12"] = verdict(
        live_ok(l12) and no_space_mutation(l12) and no_fork_mutation(l12),
        "source-instruction negative",
        live=live_ok(l12), applied=c(l12).get("mutations_applied"),
        terminal=c(l12).get("terminal"))

    l13 = load("L13_t2.json")
    report["L13"] = verdict(
        live_ok(load("L13_t1.json")) and live_ok(l13)
        and no_space_mutation(l13) and no_fork_mutation(l13),
        "surprise != authority",
        live=live_ok(l13), applied=c(l13).get("mutations_applied"),
        revision=has_revision(l13),
        space_same=(c(load("L13_t1.json")).get("space_id") == c(l13).get("space_id")))

    l14a, l14b = load("L14A.json"), load("L14B.json")
    a_mut = not no_space_mutation(l14a)
    b_mut = not no_space_mutation(l14b)
    # Anti-keyword: B must not mutate. A as natural request also should not
    # self-authorize without control surface. Different outcome is recorded.
    report["L14"] = verdict(
        live_ok(l14a) and live_ok(l14b) and (not b_mut),
        "same words different function",
        live=(live_ok(l14a), live_ok(l14b)),
        A_space_mutation=a_mut, B_space_mutation=b_mut,
        A_cands=len(c(l14a).get("space_candidates") or []),
        B_cands=len(c(l14b).get("space_candidates") or []),
        different_outcome=(a_mut != b_mut) or (
            len(c(l14a).get("space_candidates") or [])
            != len(c(l14b).get("space_candidates") or [])))

    l15b, p1, p2 = load("L15_base.json"), load("L15_p1.json"), load("L15_p2.json")
    report["L15"] = verdict(
        live_ok(l15b) and live_ok(p1) and live_ok(p2)
        and c(p1).get("context_id") == c(l15b).get("context_id")
        and c(p2).get("context_id") == c(l15b).get("context_id")
        and c(p1).get("space_id") == c(p2).get("space_id")
        and c(p1).get("scene_id") == c(p2).get("scene_id")
        and no_fork_mutation(p1) and no_fork_mutation(p2)
        and no_space_mutation(p1) and no_space_mutation(p2)
        and no_revision_candidate(p1) and no_revision_candidate(p2)
        and same_active_contract(p1, p2),
        "paraphrase stability",
        live=(live_ok(p1), live_ok(p2)),
        scene=(c(p1).get("scene_id"), c(p2).get("scene_id")),
        space=(c(p1).get("space_id"), c(p2).get("space_id")),
        contract_ids=(c(p1).get("contract_id"), c(p2).get("contract_id")))

    def q16(name, expect_requested=None, expect_n=None, expect_false=False,
            allow_aporia=False):
        rec = load(name)
        prop = c(rec).get("question_intent_proposal") or (
            rec or {}).get("response", {}).get("question_intent_proposal")
        plan = c(rec).get("question_set_plan") or (
            rec or {}).get("response", {}).get("question_set_plan")
        requested = (prop or {}).get("requested")
        n = (prop or {}).get("explicit_count_constraint")
        origin = (plan or {}).get("origin")
        ok_live = live_ok(rec)
        terminal = c(rec).get("terminal")
        if allow_aporia and terminal == "PRESERVE_APORIA":
            ok = ok_live
        elif expect_false:
            ok = ok_live and (requested is False or plan in (None, {}))
        elif expect_requested:
            ok = ok_live and requested is True and origin == "MODEL_PRODUCED_VALIDATED"
            if expect_n is not None:
                ok = ok and n == expect_n
        else:
            ok = ok_live and requested is True
        return verdict(ok, name, live=ok_live, requested=requested,
                       n=n, origin=origin,
                       terminal=terminal,
                       qsr_in_request=("question_set_request" in (
                           (rec or {}).get("request") or {})))

    report["L16_nocount"] = q16(
        "L16_nocount.json", expect_requested=True, allow_aporia=True)
    report["L16_count"] = q16("L16_count.json", expect_requested=True, expect_n=7)
    report["L16_decoy"] = q16("L16_decoy.json", expect_false=True)

    nrm, bald, lex = load("L17_normal.json"), load("L17_bald.json"), load("L17_lex.json")
    lex_not_self = c(lex).get("intervention_profile") == "normal"
    profile_effect = (
        c(nrm).get("intervention_profile") == "normal"
        and c(bald).get("intervention_profile") == "bald_ape"
    )
    report["L17"] = verdict(
        live_ok(nrm) and live_ok(bald) and live_ok(lex)
        and lex_not_self and profile_effect,
        "shiva live",
        live=(live_ok(nrm), live_ok(bald), live_ok(lex)),
        profiles=(c(nrm).get("intervention_profile"),
                  c(bald).get("intervention_profile"),
                  c(lex).get("intervention_profile")),
        terminals=(c(nrm).get("terminal"), c(bald).get("terminal"),
                   c(lex).get("terminal")))

    l18 = load("L18.json")
    fail_closed = (
        c(l18).get("terminal") == "FAILED_EXPLICIT"
        or "unknown" in str((l18 or {}).get("response", {}).get("error") or "").lower()
        or "unknown" in str(c(l18).get("response_text") or "").lower()
        or ((l18 or {}).get("response") or {}).get("terminal", {}).get("terminal")
        == "FAILED_EXPLICIT"
    )
    returned_cid = c(l18).get("context_id") or ""
    silent_sub = bool(returned_cid) and returned_cid != "ctx_deadbeefdeadbeef" and (
        fail_closed is False)
    report["L18"] = verdict(
        fail_closed and not silent_sub,
        "unknown context fail closed",
        terminal=c(l18).get("terminal"),
        returned_context_id=returned_cid,
        error=((l18 or {}).get("response") or {}).get("error"),
        execution_mode=pp(l18).get("execution_mode"),
        request_mode=((l18 or {}).get("request") or {}).get("execution_mode"))

    l19s = load("L19_sqlite.json")
    l19r = load("L19_resume.json")
    l1a2 = load("L1A_t2.json")
    ptr = (l19s or {}).get("snapshot_pointers") or {}
    report["L19"] = verdict(
        live_ok(l19r)
        and (l19s or {}).get("exists")
        and (l19s or {}).get("row") is not None
        and c(l19r).get("context_id") == c(l1a2).get("context_id")
        and c(l19r).get("scene_id") == (ptr.get("scene_id") or c(l1a2).get("scene_id")),
        "durable reload",
        live=live_ok(l19r),
        sqlite_row=(l19s or {}).get("row"),
        pointers=ptr,
        resume_scene=c(l19r).get("scene_id"),
        prior_scene=c(l1a2).get("scene_id"))

    report["L20_L1"] = pair_l1("L20_L1_t1.json", "L20_L1_t2.json", "repeat L1")
    report["L20_L2"] = pair_l2("L20_L2_t1.json", "L20_L2_t2.json", "repeat L2")
    report["L20_L5"] = pair_l5("L20_L5_t1.json", "L20_L5_t2.json", "repeat L5")
    l20_10 = load("L20_L10_t2.json")
    report["L20_L10"] = verdict(
        live_ok(load("L20_L10_t1.json")) and live_ok(l20_10)
        and no_space_mutation(l20_10)
        and c(load("L20_L10_t1.json")).get("space_id") == c(l20_10).get("space_id"),
        "repeat L10", live=live_ok(l20_10),
        applied=c(l20_10).get("mutations_applied"))
    l20_12 = load("L20_L12.json")
    report["L20_L12"] = verdict(
        live_ok(l20_12) and no_space_mutation(l20_12) and no_fork_mutation(l20_12),
        "repeat L12", live=live_ok(l20_12),
        applied=c(l20_12).get("mutations_applied"))

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
        "note": "evaluator uses only LIVE saved JSON; DETERMINISTIC never consulted; "
                "all_pass is false whenever any case is FAIL",
    }
    if counts["FAIL"] > 0:
        out["note"] += "; REPORT MUST NOT CLAIM ALL PASS"
    (OUT / "EVALUATION.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"counts": counts, "all_pass": all_pass},
                     ensure_ascii=False, indent=2))
    for k, v in report.items():
        print(f"{k:12} {v.get('result'):6} {v.get('reason')}")


if __name__ == "__main__":
    main()
