"""C2 — protected-region enforcement does not depend on frontend honesty.

Every test here goes through the raw HTTP API, i.e. exactly what an attacker or
a buggy client would do, bypassing the editor entirely.
"""
from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from workbench_api.server import Handler, get_service, reset_service

ASSET = "zarathustra.03_scene_reading"
BASE = "v_baseline_baseline_file"


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKBENCH_STATE_DIR", str(tmp_path / "state"))
    reset_service()
    svc = get_service(Path(tmp_path / "state"))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{httpd.server_address[1]}"

    def call(method: str, path: str, body: dict | None = None):
        req = Request(base_url + path, method=method,
                      headers={"Content-Type": "application/json"},
                      data=json.dumps(body).encode() if body is not None else None)
        try:
            with urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode())

    yield call, svc
    httpd.shutdown()
    reset_service()


def _clone(call):
    status, data = call("POST", f"/api/workbench/asset/{ASSET}/variant/{BASE}/clone")
    assert status == 200
    return data["variant"]


def test_raw_api_cannot_mutate_protected_region(api):
    call, svc = api
    cand = _clone(call)
    original = cand["source_text"]

    active_before = svc.store.active_variant_id(ASSET)
    revision_before = svc.store.activation_revision()
    baseline_before = svc.variant(ASSET, BASE).source_hash

    tampered = original.replace('"topic": "..."', '"headline": "..."')
    assert tampered != original

    status, data = call(
        "POST", f"/api/workbench/asset/{ASSET}/variant/{cand['variant_id']}/source",
        {"source_text": tampered, "actor": "raw-api-client"})

    # 1. server rejects
    assert status == 400, data
    assert "output_json_contract" in data["error"]

    # 2. candidate source unchanged
    assert svc.variant(ASSET, cand["variant_id"]).source_text == original

    # 3. active binding unchanged
    assert svc.store.active_variant_id(ASSET) == active_before
    assert svc.store.activation_revision() == revision_before

    # 4. baseline unchanged
    assert svc.variant(ASSET, BASE).source_hash == baseline_before

    # 5. rejection event recorded
    status, rej = call("GET", "/api/workbench/rejections")
    assert status == 200
    events = [r for r in rej["rejections"] if r["code"] == "protected_region_mutation"]
    assert events, rej
    assert events[-1]["actor"] == "raw-api-client"
    assert events[-1]["detail"]["region"] == "output_json_contract"


def test_raw_api_cannot_delete_protected_region(api):
    call, svc = api
    cand = _clone(call)
    without = cand["source_text"].split("## Что запрещено")[0]
    status, data = call(
        "POST", f"/api/workbench/asset/{ASSET}/variant/{cand['variant_id']}/source",
        {"source_text": without})
    assert status == 400
    assert "prohibitions" in data["error"] or "output_json_contract" in data["error"]
    assert svc.variant(ASSET, cand["variant_id"]).source_text == cand["source_text"]


def test_raw_api_cannot_edit_baseline(api):
    call, svc = api
    status, data = call(
        "POST", f"/api/workbench/asset/{ASSET}/variant/{BASE}/source",
        {"source_text": "anything"})
    assert status == 400
    assert svc.variant(ASSET, BASE).state == "BASELINE"
    codes = {r["code"] for r in svc.store.rejections()}
    assert "baseline_not_editable" in codes


def test_editable_region_change_is_accepted_through_raw_api(api):
    call, svc = api
    cand = _clone(call)
    edited = cand["source_text"].replace(
        "какая тревога делает вопрос срочным",
        "какая именно тревога делает вопрос срочным")
    assert edited != cand["source_text"]
    status, data = call(
        "POST", f"/api/workbench/asset/{ASSET}/variant/{cand['variant_id']}/source",
        {"source_text": edited})
    assert status == 200, data
    assert data["variant"]["contract_revision"] is False
    assert svc.variant(ASSET, cand["variant_id"]).source_text == edited


def test_contract_revision_intent_is_recorded_and_audited(api):
    call, svc = api
    cand = _clone(call)
    revised = cand["source_text"].replace(
        '"possible_transformation": "..."',
        '"possible_transformation": "...",\n  "extra_field": "..."')
    status, data = call(
        "POST", f"/api/workbench/asset/{ASSET}/variant/{cand['variant_id']}/source",
        {"source_text": revised, "intent": "contract_revision", "actor": "operator"})
    assert status == 200, data
    assert data["variant"]["contract_revision"] is True
    codes = [r["code"] for r in svc.store.rejections()]
    assert "contract_revision_accepted" in codes

    status, val = call(
        "POST", f"/api/workbench/asset/{ASSET}/variant/{cand['variant_id']}/validate")
    assert val["drift_class"] == "NEW_CANDIDATE_DRIFT"
    assert val["verdict"] == "fail"


def test_unknown_intent_is_rejected(api):
    call, _ = api
    cand = _clone(call)
    status, data = call(
        "POST", f"/api/workbench/asset/{ASSET}/variant/{cand['variant_id']}/source",
        {"source_text": cand["source_text"], "intent": "whatever"})
    assert status == 400
    assert "intent" in data["error"]
