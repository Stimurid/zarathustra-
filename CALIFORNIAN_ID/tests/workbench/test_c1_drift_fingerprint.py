"""C1 — structural drift fingerprint.

A scalar defect count cannot prove defect identity: a candidate may repair one
baseline defect and introduce a different one while keeping the total unchanged.
These tests pin the six required behaviours.
"""
from __future__ import annotations

import pytest

from workbench_adapters import ZarathustraAdapter
from workbench_core import (
    DRIFT_CATEGORIES,
    DriftFingerprint,
    DriftWaiver,
    WorkbenchService,
    WorkbenchStore,
)

ASSET = "zarathustra.03_scene_reading"
BASE = "v_baseline_baseline_file"


@pytest.fixture()
def svc(tmp_path):
    s = WorkbenchService(WorkbenchStore(tmp_path / "state"))
    s.register_adapter(ZarathustraAdapter())
    s.bootstrap()
    return s


def _candidate(svc, mutate, intent="contract_revision"):
    """Field-level mutations live inside the protected contract region, so they
    are contract revisions by definition and must declare that intent (C2).
    Declaring it does not soften C1 — it is what puts the candidate under the
    full-force fingerprint comparison."""
    cand = svc.clone(ASSET, BASE)
    new = mutate(cand.source_text)
    assert new != cand.source_text, "mutation produced no change"
    return svc.update_source(ASSET, cand.variant_id, new, intent=intent)


# --------------------------------------------------------------------------
# fingerprint algebra
# --------------------------------------------------------------------------

def test_fingerprint_categories_are_closed():
    fp = DriftFingerprint()
    assert set(DRIFT_CATEGORIES) == set(fp.to_public()) - {"fingerprint_hash", "total"}


def test_equal_counts_different_identity_are_not_equal():
    a = DriftFingerprint(prompt_fields_not_consumed=["x", "y"])
    b = DriftFingerprint(prompt_fields_not_consumed=["x", "z"])
    assert len(a.as_set()) == len(b.as_set())
    assert not b.issubset(a)
    assert b.difference(a) == {("prompt_fields_not_consumed", "z")}
    assert a.fingerprint_hash() != b.fingerprint_hash()


def test_same_item_in_different_category_is_a_different_defect():
    a = DriftFingerprint(prompt_fields_not_consumed=["hidden_fear"])
    b = DriftFingerprint(prompt_fields_not_declared=["hidden_fear"])
    assert not b.issubset(a)


# --------------------------------------------------------------------------
# the real fixture: 03_scene_reading 17 -> 9 -> 7
# --------------------------------------------------------------------------

def test_real_fixture_baseline_fingerprint(svc):
    adapter = ZarathustraAdapter()
    base = svc.variant(ASSET, BASE)
    report = adapter.contract_report(ASSET, base.source_text)
    fp = report.fingerprint

    assert report.summary() == "17/9/7"
    assert len(fp.prompt_fields_not_consumed) == 10
    assert "hidden_fear" in fp.prompt_fields_not_consumed
    assert len(fp.prompt_fields_not_declared) == 8
    assert fp.required_fields_missing == []
    assert fp.dangling_asset_refs == []
    assert fp.fingerprint_hash().startswith("drift:")


# --------------------------------------------------------------------------
# 1. same exact baseline defects -> PASS
# --------------------------------------------------------------------------

def test_1_same_exact_defects_pass(svc):
    # Editable-region change: plain content intent, no contract revision.
    cand = _candidate(svc, lambda t: t.replace(
        "какая тревога делает вопрос срочным",
        "какая именно тревога делает вопрос срочным для говорящего"),
        intent="content")
    assert cand.contract_revision is False
    res = svc.validate(ASSET, cand.variant_id)
    assert res["verdict"] == "pass"
    assert res["drift_class"] == "KNOWN_BASELINE_DRIFT"
    assert res["contract"]["fingerprint"]["fingerprint_hash"] == \
        res["baseline_contract"]["fingerprint"]["fingerprint_hash"]


# --------------------------------------------------------------------------
# 2. strict subset of baseline defects -> PASS
# --------------------------------------------------------------------------

def test_2_subset_of_baseline_defects_pass(svc):
    """Dropping an unused field repairs a defect and introduces none."""
    cand = _candidate(svc, lambda t: t.replace(
        '  "potential_idol": "...",\n', ''))
    res = svc.validate(ASSET, cand.variant_id)
    assert res["verdict"] == "pass"
    assert res["drift_class"] == "KNOWN_BASELINE_DRIFT"
    cand_fp = res["contract"]["fingerprint"]
    base_fp = res["baseline_contract"]["fingerprint"]
    assert cand_fp["total"] < base_fp["total"]
    issue = next(i for i in res["issues"] if i["code"] == "inherited_baseline_drift")
    assert any("potential_idol" in r for r in issue["detail"]["repaired"])


# --------------------------------------------------------------------------
# 3. same count, one defect swapped for a new one -> FAIL
# --------------------------------------------------------------------------

def test_3_same_count_one_defect_replaced_fails(svc):
    """The exact case a scalar comparison cannot catch."""
    cand = _candidate(svc, lambda t: t.replace(
        '"potential_idol": "..."', '"invented_replacement_field": "..."'))
    res = svc.validate(ASSET, cand.variant_id)

    cand_total = res["contract"]["fingerprint"]["total"]
    base_total = res["baseline_contract"]["fingerprint"]["total"]
    assert cand_total == base_total, "test premise: totals must be equal"

    assert res["drift_class"] == "NEW_CANDIDATE_DRIFT"
    assert res["verdict"] == "fail"
    detail = next(i for i in res["issues"]
                  if i["code"] == "new_candidate_drift")["detail"]
    assert any("invented_replacement_field" in x for x in detail["introduced"])
    assert any("potential_idol" in x for x in detail["repaired"])
    assert svc.variant(ASSET, cand.variant_id).state == "INCOMPATIBLE"


# --------------------------------------------------------------------------
# 4. superset -> FAIL
# --------------------------------------------------------------------------

def test_4_superset_fails(svc):
    cand = _candidate(svc, lambda t: t.replace(
        '"possible_transformation": "..."',
        '"possible_transformation": "...",\n  "brand_new_unused_field": "..."'))
    res = svc.validate(ASSET, cand.variant_id)
    assert res["drift_class"] == "NEW_CANDIDATE_DRIFT"
    assert res["verdict"] == "fail"
    assert res["contract"]["fingerprint"]["total"] > \
        res["baseline_contract"]["fingerprint"]["total"]


# --------------------------------------------------------------------------
# 5. new *category* of defect -> FAIL
# --------------------------------------------------------------------------

def test_5_new_defect_category_fails(svc):
    """Turning an array field into a string is a schema_type_mismatch —
    a category the baseline has none of."""
    cand = _candidate(svc, lambda t: t.replace(
        '"stakes": ["..."]', '"stakes": "..."'))
    res = svc.validate(ASSET, cand.variant_id)
    fp = res["contract"]["fingerprint"]
    assert fp["schema_type_mismatches"], "type mismatch not detected"
    assert res["baseline_contract"]["fingerprint"]["schema_type_mismatches"] == []
    assert res["drift_class"] == "NEW_CANDIDATE_DRIFT"
    assert res["verdict"] == "fail"


def test_5b_required_field_removal_is_always_fatal(svc):
    cand = _candidate(svc, lambda t: t.replace('"topic": "..."', '"headline": "..."'))
    res = svc.validate(ASSET, cand.variant_id)
    assert res["verdict"] == "fail"
    codes = {i["code"] for i in res["issues"]}
    assert "contract_missing_field" in codes
    assert res["contract"]["fingerprint"]["required_fields_missing"] == ["topic"]


# --------------------------------------------------------------------------
# 6. explicit waiver with provenance -> controlled PASS
# --------------------------------------------------------------------------

def test_6_explicit_waiver_gives_controlled_pass(svc):
    cand = _candidate(svc, lambda t: t.replace(
        '"possible_transformation": "..."',
        '"possible_transformation": "...",\n  "brand_new_unused_field": "..."'))

    fail = svc.validate(ASSET, cand.variant_id)
    assert fail["drift_class"] == "NEW_CANDIDATE_DRIFT"

    for category in ("prompt_fields_not_consumed", "prompt_fields_not_declared"):
        svc.grant_waiver(category, "brand_new_unused_field",
                         reason="поле готовится к потреблению в ADR-09",
                         adr_ref="ADR-09", actor="operator", asset_id=ASSET)

    ok = svc.validate(ASSET, cand.variant_id)
    assert ok["drift_class"] == "WAIVED_CANDIDATE_DRIFT"
    assert ok["verdict"] == "warn"
    assert svc.variant(ASSET, cand.variant_id).state == "STATIC_VALID"
    issue = next(i for i in ok["issues"] if i["code"] == "waived_candidate_drift")
    assert issue["detail"]["waivers"][0]["adr_ref"] == "ADR-09"
    assert issue["detail"]["waivers"][0]["granted_by"] == "operator"


def test_6b_waiver_requires_reason_and_adr(svc):
    with pytest.raises(ValueError):
        svc.store.grant_waiver(DriftWaiver(
            category="prompt_fields_not_consumed", item="x", reason="",
            adr_ref="", granted_by="a", granted_at="now"))


def test_6c_waiver_rejects_unknown_category(svc):
    with pytest.raises(ValueError):
        svc.store.grant_waiver(DriftWaiver(
            category="made_up_category", item="x", reason="r",
            adr_ref="ADR-1", granted_by="a", granted_at="now"))


def test_6d_waiver_is_scoped_to_its_asset(svc):
    svc.grant_waiver("prompt_fields_not_consumed", "brand_new_unused_field",
                     reason="r", adr_ref="ADR-09", asset_id="some.other.asset")
    cand = _candidate(svc, lambda t: t.replace(
        '"possible_transformation": "..."',
        '"possible_transformation": "...",\n  "brand_new_unused_field": "..."'))
    res = svc.validate(ASSET, cand.variant_id)
    assert res["drift_class"] == "NEW_CANDIDATE_DRIFT"


# --------------------------------------------------------------------------
# dangling reference category is wired to a real check
# --------------------------------------------------------------------------

def test_dangling_asset_refs_category_is_live(svc):
    adapter = ZarathustraAdapter()
    report = adapter.contract_report(ASSET, svc.variant(ASSET, BASE).source_text)
    assert report.fingerprint.dangling_asset_refs == []

    original = adapter.list_assets
    adapter.list_assets = lambda: [a for a in original()
                                   if a.asset_id != "zarathustra.04_head_calling"]
    broken = adapter.contract_report(ASSET, svc.variant(ASSET, BASE).source_text)
    assert "zarathustra.04_head_calling" in broken.fingerprint.dangling_asset_refs
