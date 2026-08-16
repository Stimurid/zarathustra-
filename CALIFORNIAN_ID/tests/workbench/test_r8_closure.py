"""G-S25R.8F closure — tests for request integrity, mount-negative
fail-close, and C01 score-file immutability.

Runs deterministic checks against the committed R8 closure artifacts.
No provider calls anywhere.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
CLOSURE = REPO / "docs" / "socrates_gs26" / "live_acceptance" / "r8_closure"
DATA_CURRENT = REPO / "CALIFORNIAN_ID" / "data" / "socrates" / "current"
sys.path.insert(0, str(REPO / "CALIFORNIAN_ID" / "src"))

from socrates_runtime.errors import (               # noqa: E402
    HistoricalFallbackForbidden,
    SemanticContextBudgetExceeded,
    SemanticMountMissing,
    SemanticSummarySubstitutionAttempted,
)
from socrates_runtime.mount import SemanticMountPolicy  # noqa: E402
from socrates_runtime.routers import RouterRegistry  # noqa: E402
from socrates_runtime.semantic import SemanticBodyRegistry  # noqa: E402


# ============================================================ Task A


@pytest.fixture(scope="module")
def integrity_report() -> dict:
    return json.loads(
        (CLOSURE / "REQUEST_INTEGRITY_REPORT.json")
        .read_text(encoding="utf-8"))


def test_request_integrity_33_of_33(integrity_report):
    assert integrity_report["arm_count"] == 33
    assert integrity_report["matches"] == 33
    assert integrity_report["mismatches"] == 0


def test_every_arm_records_a_match(integrity_report):
    for arm in integrity_report["arms"]:
        assert arm["match"] is True
        assert (arm["live_request_sha256"]
                == arm["reconstructed_request_sha256"])


def test_evaluation_metadata_absent_from_every_user_payload(integrity_report):
    scan = integrity_report["evaluation_metadata_leak_scan"]
    assert scan["any_hit"] is False
    assert set(scan["tokens_checked"]) >= {
        "target_distinctions", "positive_behavior", "fatal_failures",
        "evaluator_rubric", "pair_verdict", "ablation_decision",
        "expected_arm", "B_BETTER"}
    for per_case in scan["per_case"]:
        assert per_case["evaluation_metadata_hits"] == []


# ============================================================ Task B


MANDATORY_TARGETS = {
    "B01": ["P01"], "B02": ["P02", "P08"], "B03": ["P03"],
    "B04": ["P04"], "B05": ["P00", "P04", "P09"], "B06": ["P05"],
    "B07": ["P00", "P09"], "B09": ["P06", "P08"],
    "B10": ["P07", "P08", "P09"],
}


@pytest.fixture(scope="module")
def mount_neg_report() -> dict:
    return json.loads(
        (CLOSURE / "MOUNT_NEGATIVE_PROOF.json").read_text(encoding="utf-8"))


def test_mount_negative_covers_all_mandatory_bodies(mount_neg_report):
    covered = {r["body"] for r in mount_neg_report["per_body_results"]}
    assert covered == set(MANDATORY_TARGETS)


def test_all_mandatory_bodies_fail_closed(mount_neg_report):
    for r in mount_neg_report["per_body_results"]:
        assert r["all_required_routers_failed_closed"] is True, r["body"]


def test_no_historical_fallback_used(mount_neg_report):
    for r in mount_neg_report["per_body_results"]:
        assert r["historical_fallback"] == "NOT_USED", r["body"]


def test_no_summary_substitution_used(mount_neg_report):
    for r in mount_neg_report["per_body_results"]:
        assert r["summary_substitution"] == "NOT_USED", r["body"]


def test_no_provider_calls_during_mount_negatives(mount_neg_report):
    for r in mount_neg_report["per_body_results"]:
        assert r["provider_calls"] == 0, r["body"]


def test_b08_classified_conditional_not_mandatory(mount_neg_report):
    b08 = mount_neg_report["b08_classification"]
    assert b08["status"] == "CONDITIONAL_NOT_MANDATORY"
    assert set(b08["cases_targeting_b08"]) == {
        "C04_ONTOLOGY_GAP", "C09_FALSE_SYNTHESIS"}


# Independent live re-execution of a single body's fail-close, so the
# test suite itself proves the mechanism — not just reads the report.

@pytest.mark.parametrize("body_id,router_id", [
    ("B01", "P01"), ("B03", "P03"), ("B04", "P04"),
    ("B06", "P05"), ("B10", "P07"),
])
def test_isolated_missing_body_fails_closed(body_id, router_id, tmp_path):
    dst = tmp_path / f"minus_{body_id}"
    shutil.copytree(DATA_CURRENT, dst)
    dropped = [p for p in (dst / "semantic").iterdir()
               if p.name.upper().startswith(body_id + "_")]
    assert dropped, f"no file for {body_id}"
    for p in dropped:
        p.unlink()

    registry = SemanticBodyRegistry(semantic_dir=dst / "semantic",
                                     mount_dir=dst / "mount")
    routers = RouterRegistry(routers_dir=dst / "routers")
    policy = SemanticMountPolicy(registry, mount_dir=dst / "mount")

    phase = routers.get(router_id).pipeline_phases[0]
    with pytest.raises(SemanticMountMissing) as ctx:
        policy.mount(router_id, phase)
    # verify no other typed failure was raised, and no historical
    # fallback path exists to be taken
    assert body_id.lower() in str(ctx.value).lower() or body_id in str(ctx.value)


# ============================================================ Task C


@pytest.fixture(scope="module")
def c01_score() -> dict:
    return json.loads(
        (CLOSURE / "C01_FRESH_BLIND_SCORE.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def c01_verdict() -> dict:
    return json.loads(
        (CLOSURE / "C01_UNBLINDED_VERDICT.json").read_text(encoding="utf-8"))


def test_c01_score_file_self_hash_intact(c01_score):
    """The score file's own SHA — recomputed from its bytes-minus-that-
    field — must match the stored ``score_file_sha256``. Anyone editing
    the file after it was written breaks this check."""
    body_no_hash = json.dumps(
        {k: v for k, v in c01_score.items() if k != "score_file_sha256"},
        ensure_ascii=False, indent=2, sort_keys=True)
    computed = hashlib.sha256(body_no_hash.encode("utf-8")).hexdigest()
    assert computed == c01_score["score_file_sha256"], (
        "C01 fresh blind score file has been modified after scoring "
        "— immutability broken")


def test_c01_verdict_matches_score(c01_score, c01_verdict):
    assert c01_verdict["score_file_sha256"] == c01_score["score_file_sha256"]
    assert c01_verdict["case_id"] == "R8-C01_SCENE_CAPTURE"
    assert c01_verdict["pair_verdict"] in (
        "B_BETTER", "NO_MATERIAL_DIFFERENCE", "A_BETTER", "INCOMPARABLE")
    assert c01_verdict["ablation_verdict"] in (
        "B_BETTER", "C_BETTER", "NO_MATERIAL_DIFFERENCE")


def test_c01_verdict_derived_by_frozen_pair_rule(c01_verdict):
    """Recompute the verdict from the same three totals + fatals — must
    match. Guards against manual editing of the verdict file."""
    a, b = c01_verdict["A_total"], c01_verdict["B_total"]
    a_fatal = c01_verdict["A_fatal_failures"]
    b_fatal = c01_verdict["B_fatal_failures"]
    new_b_fatal = any(f not in a_fatal for f in b_fatal)
    if new_b_fatal:
        expected = "A_BETTER"
    elif b >= a + 4:
        expected = "B_BETTER"
    elif a >= b + 4:
        expected = "A_BETTER"
    else:
        expected = "NO_MATERIAL_DIFFERENCE"
    assert c01_verdict["pair_verdict"] == expected


# ============================================================ Final gate


@pytest.fixture(scope="module")
def final_gate() -> dict:
    return json.loads(
        (CLOSURE / "R8_FINAL_GATE.json").read_text(encoding="utf-8"))


def test_final_gate_shape(final_gate):
    for section in ("live_execution", "request_integrity",
                    "semantic_improvement", "behavioral_ablation",
                    "mount_negative_ablation",
                    "direct_assistance_regression",
                    "fatal_regressions", "c01_unblinded",
                    "final_verdict"):
        assert section in final_gate, section


def test_final_gate_verdict_is_one_of_three(final_gate):
    assert final_gate["final_verdict"] in {"PASS", "PARTIAL", "FAIL"}


def test_final_gate_uses_required_families_count_of_10(final_gate):
    sem = final_gate["semantic_improvement"]
    assert sem["required_families_total"] == 10
    # C05 lives in the extras — never counted against the frozen threshold
    assert "R8-C05_RETRIEVAL_ATTENTION" in sem["extra_families_verdicts"]
    assert "R8-C05_RETRIEVAL_ATTENTION" not in sem["required_verdicts"]


def test_final_gate_semantic_and_ablation_derived_correctly(final_gate,
                                                             c01_verdict,
                                                             mount_neg_report):
    sem = final_gate["semantic_improvement"]
    expected_b_better_req = sum(
        1 for v in sem["required_verdicts"].values() if v == "B_BETTER")
    assert sem["required_B_BETTER_count"] == expected_b_better_req
    assert (sem["verdict"] == "PASS") == (expected_b_better_req >= 7)

    mnt = final_gate["mount_negative_ablation"]
    assert (mnt["mandatory_bodies_fail_closed"]
            == mount_neg_report["valid_mandatory_fail_close_count"])
    assert (mnt["mandatory_bodies_tested"]
            == mount_neg_report["mandatory_targets_total"])


def test_final_gate_no_regression_on_direct_assistance(final_gate):
    da = final_gate["direct_assistance_regression"]
    assert da["case"] == "R8-C11_DIRECT_ASSISTANCE_BYPASS"
    assert da["regressed"] is False
