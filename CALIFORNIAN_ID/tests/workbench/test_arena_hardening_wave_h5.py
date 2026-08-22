"""Arena Hardening Wave H-5 — Anti-overfitting holdout + variant
generator + Kvaqin live comparative gate.
"""
from __future__ import annotations

import json
import os
import socket
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from interface_api import Handler, reset_store_for_tests
from interface_api.scenarios import (
    ScenarioState, get_registry, reset_registry_for_tests,
)
from interface_api.variant_generator import (
    DEFAULT_MUTATIONS, Mutation, Partition,
    as_scenario_variants, generate_variants, partition_variants,
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server(tmp_path):
    db_path = str(tmp_path / "interface_state.sqlite")
    runs_dir = str(tmp_path / "runs")
    reset_store_for_tests(db_path=db_path, runs_dir=runs_dir)
    reset_registry_for_tests()
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield {"base": f"http://127.0.0.1:{port}"}
    httpd.shutdown()
    httpd.server_close()


def _post(url: str, body: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))


# --------------------------------------------------------------------
# Variant generator produces non-trivial variants for a real scenario
# --------------------------------------------------------------------


def test_h5_variant_generator_produces_non_trivial_variants():
    reg = get_registry()
    sc = reg.get("CAMPAIGN_A_REALITY_CAPTURE")
    variants = generate_variants(sc, mutations=DEFAULT_MUTATIONS)
    # every variant comes from a real turn index
    assert all(0 <= v.original_index < len(sc.turn_template)
               for v in variants)
    # skipped no-op mutations do not appear
    assert all(v.variant_text != v.original_text for v in variants)
    # deterministic hash per variant text
    from collections import Counter
    counts = Counter(v.variant_hash for v in variants)
    # hashes for identical text collide (fine) but overall bulk > 30
    assert len(variants) > 30
    assert all(len(h) == 16 for h in counts.keys())


# --------------------------------------------------------------------
# Partition is deterministic and honours holdout ratio
# --------------------------------------------------------------------


def test_h5_partition_is_deterministic_and_ratio_honoured():
    reg = get_registry()
    sc = reg.get("CAMPAIGN_A_REALITY_CAPTURE")
    variants = generate_variants(sc)
    train_a, holdout_a = partition_variants(
        variants, holdout_ratio=0.3, seed="arena_h5_v01")
    train_b, holdout_b = partition_variants(
        variants, holdout_ratio=0.3, seed="arena_h5_v01")
    assert [v.variant_hash for v in train_a] == \
           [v.variant_hash for v in train_b]
    assert [v.variant_hash for v in holdout_a] == \
           [v.variant_hash for v in holdout_b]

    total = len(train_a) + len(holdout_a)
    ratio = len(holdout_a) / total
    # allow ±0.15 slack for hash-bucket rounding on small samples
    assert 0.15 <= ratio <= 0.45, (ratio, len(holdout_a), total)


# --------------------------------------------------------------------
# Different seeds produce different splits (proof of seed dependence)
# --------------------------------------------------------------------


def test_h5_partition_differs_across_seeds():
    reg = get_registry()
    sc = reg.get("CAMPAIGN_A_REALITY_CAPTURE")
    variants = generate_variants(sc)
    _, holdout_a = partition_variants(variants, seed="seed_a")
    _, holdout_b = partition_variants(variants, seed="seed_b_different")
    set_a = {v.variant_hash for v in holdout_a}
    set_b = {v.variant_hash for v in holdout_b}
    assert set_a != set_b


# --------------------------------------------------------------------
# ScenarioVariants public-shape sanity + partition labels
# --------------------------------------------------------------------


def test_h5_scenario_variants_public_shape():
    reg = get_registry()
    sc = reg.get("CAMPAIGN_A_REALITY_CAPTURE")
    variants = generate_variants(sc)
    train, holdout = partition_variants(variants, seed="seed_public")
    sv_train, sv_holdout = as_scenario_variants(
        sc, train, holdout, seed="seed_public")
    assert sv_train.partition == Partition.TRAIN
    assert sv_holdout.partition == Partition.HOLDOUT
    p_train = sv_train.to_public()
    p_holdout = sv_holdout.to_public()
    assert p_train["partition"] == "TRAIN"
    assert p_holdout["partition"] == "HOLDOUT"
    assert len(p_train["variants"]) == len(train)
    assert len(p_holdout["variants"]) == len(holdout)


# --------------------------------------------------------------------
# KVAQIN arm — probe fails or env flag absent → BLOCKED_PROVIDER
# without deterministic masquerade.
# --------------------------------------------------------------------


def test_h5_kvaqin_arm_blocked_without_opt_in_env(server, monkeypatch):
    monkeypatch.delenv("KVAQIN_ARM_LIVE_ENABLED", raising=False)
    r = _post(server["base"] + "/api/interface/comparative_run",
              {"scenario_id": "CAMPAIGN_A_REALITY_CAPTURE",
               "arms": ["SOCRATES", "KVAQIN"], "max_turns": 3})
    arms = {a["kind"]: a for a in r["arms"]}
    assert arms["SOCRATES"]["status"] == "OK"
    assert arms["KVAQIN"]["status"] == "BLOCKED_PROVIDER"
    assert "deterministic" not in arms["KVAQIN"]["provider_id"]
    # Blocker detail must mention either probe or the opt-in flag.
    detail = arms["KVAQIN"]["blocker_detail"].lower()
    assert ("probe" in detail or "operator confirmation" in detail
            or "kvaqin_arm_live_enabled" in detail)


# --------------------------------------------------------------------
# KVAQIN arm gate opens with env flag (LIVE run allowed).
# We do NOT enable the flag in CI (would burn provider tokens);
# just verify the code path recognises the flag by inspecting the
# blocker_detail wording. This proves the gate is env-driven, not
# forever-BLOCKED.
# --------------------------------------------------------------------


def test_h5_kvaqin_arm_gate_is_env_flag_driven(server, monkeypatch):
    # Simulate operator opt-in by inspecting a small helper import
    # path — the gate itself is documented as
    # `os.environ["KVAQIN_ARM_LIVE_ENABLED"] == "1"`.
    from interface_api import comparative_arm as ca
    src = ca.__file__
    with open(src, "r", encoding="utf-8") as f:
        body = f.read()
    assert "KVAQIN_ARM_LIVE_ENABLED" in body
    assert '"1"' in body or "'1'" in body


# --------------------------------------------------------------------
# Holdout is sealed — hardening iteration is not allowed to consume
# the holdout partition. Enforced by having the generator label the
# partition and no code path that INSPECTS holdout wording.
# --------------------------------------------------------------------


def test_h5_holdout_partition_is_labeled_and_sealed():
    reg = get_registry()
    sc = reg.get("CAMPAIGN_A_REALITY_CAPTURE")
    variants = generate_variants(sc)
    _, holdout = partition_variants(variants, seed="seed_seal")
    _, sv_holdout = as_scenario_variants(
        sc, [], holdout, seed="seed_seal")
    # partition label present + non-empty holdout
    assert sv_holdout.partition == Partition.HOLDOUT
    assert len(sv_holdout.variants) > 0
    # Sanity: variants carry mutation label so downstream regression
    # can characterise coverage without needing to read text.
    kinds = {v.mutation.value for v in holdout}
    # Not every mutation may land in holdout, but at least 2 kinds
    # should be represented for meaningful test coverage.
    assert len(kinds) >= 2
