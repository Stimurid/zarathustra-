"""HTTP integration — L1 auth + configs endpoints.

Uses the real ``ThreadingHTTPServer`` on a random localhost port so the
tests exercise the exact request/response path the UI hits. Isolates state
per test by pointing ``WORKBENCH_STATE_DIR`` at a tmp path and calling
``reset_service`` before and after.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from workbench_api import server as srv


@pytest.fixture()
def api(tmp_path, monkeypatch):
    """Start the workbench server on a random port. Yield the base URL."""
    monkeypatch.setenv("WORKBENCH_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("WORKBENCH_JWT_SECRET", "test-secret-for-http-suite")
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    srv.reset_service()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)              # let the server finish binding
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
        srv.reset_service()


def _req(method: str, url: str, body: dict | None = None,
         token: str | None = None) -> tuple[int, dict]:
    data = json.dumps(body or {}).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except Exception:
            return exc.code, {"raw": ""}


def _seed(api_url: str) -> str:
    """Redeem the auto-minted admin code. Return the admin token."""
    # The seed code is printed to stdout by get_auth() on first call; grab
    # it directly from the store instead so the test does not depend on
    # capturing stdout.
    auth = srv.get_auth()
    codes = auth.store.list_codes(only_unredeemed=True)
    admin_code = next(c for c in codes if "admin" in c.roles)
    _, out = _req("POST", f"{api_url}/api/workbench/auth/redeem",
                  {"code": admin_code.code, "display_name": "admin"})
    return out["session"]["token"]


# ---------------- unauth / auth basics ----------------

def test_health_needs_no_auth(api):
    status, out = _req("GET", f"{api}/api/workbench/health")
    assert status == 200 and out["ok"] is True


def test_status_shows_unauthenticated_without_token(api):
    _, out = _req("GET", f"{api}/api/workbench/auth/status")
    assert out == {"authenticated": False, "user": None}


def test_me_requires_bearer(api):
    status, out = _req("GET", f"{api}/api/workbench/me")
    # GET routes turn WorkbenchError into 404; POST routes turn it into 400.
    # The specific status is a legacy convention — what matters here is that
    # the request was refused and the reason names the missing header.
    assert status in (400, 404)
    assert "требуется авторизация" in out["error"]


def test_seed_admin_can_redeem_and_call_me(api):
    token = _seed(api)
    _, out = _req("GET", f"{api}/api/workbench/me", token=token)
    assert out["user"]["display_name"] == "admin"
    assert "admin" in out["user"]["roles"]


def test_bad_token_is_treated_as_anonymous(api):
    _seed(api)                     # bootstrap so there is a real secret in place
    _, out = _req("GET", f"{api}/api/workbench/auth/status",
                  token="obviously.not.a.jwt")
    assert out["authenticated"] is False


# ---------------- mint + role invariants ----------------

def test_admin_mints_curator_code_curator_mints_user_code(api):
    admin_token = _seed(api)
    _, mint_resp = _req("POST", f"{api}/api/workbench/auth/mint",
                        {"roles": ["curator"], "note": "kate"},
                        token=admin_token)
    curator_code = mint_resp["code"]["code"]
    _, curator_session = _req("POST", f"{api}/api/workbench/auth/redeem",
                              {"code": curator_code, "display_name": "kate"})
    curator_token = curator_session["session"]["token"]

    # Curator may mint a user code
    status, _ = _req("POST", f"{api}/api/workbench/auth/mint",
                     {"roles": ["user"]}, token=curator_token)
    assert status == 200

    # …but not another curator code
    status, out = _req("POST", f"{api}/api/workbench/auth/mint",
                       {"roles": ["curator"]}, token=curator_token)
    assert status == 400
    assert "admin required" in out["error"]


# ---------------- configs CRUD + activation ----------------

def _make_user(api_url: str, admin_token: str, name: str,
               roles: list[str]) -> str:
    _, mint = _req("POST", f"{api_url}/api/workbench/auth/mint",
                   {"roles": roles}, token=admin_token)
    _, sess = _req("POST", f"{api_url}/api/workbench/auth/redeem",
                   {"code": mint["code"]["code"], "display_name": name})
    return sess["session"]["token"]


def test_configs_lifecycle_via_http(api):
    admin_token = _seed(api)
    alice = _make_user(api, admin_token, "alice", ["user"])

    # Create
    status, out = _req("POST", f"{api}/api/workbench/configs", {
        "workspace_id": "default", "branch": "zarathustra",
        "name": "my-research", "description": "less small talk",
    }, token=alice)
    assert status == 200
    cfg_id = out["config"]["config_id"]
    assert out["config"]["content_hash"].startswith("cfg:")
    assert out["config"]["status"] == "draft"

    # List — alice sees her config
    _, out = _req("GET", f"{api}/api/workbench/configs?branch=zarathustra",
                  token=alice)
    assert [c["config_id"] for c in out["configs"]] == [cfg_id]

    # Personal-activate
    _, out = _req("POST",
                  f"{api}/api/workbench/configs/{cfg_id}/personal_activate",
                  {}, token=alice)
    assert out["config"]["status"] == "personal_active"
    assert out["scope"] == "personal"

    # Effective for alice = her build
    _, out = _req("GET", f"{api}/api/workbench/effective/zarathustra", token=alice)
    assert out["config"]["config_id"] == cfg_id

    # Delete
    _, out = _req("POST", f"{api}/api/workbench/configs/{cfg_id}/delete",
                  {}, token=alice)
    assert out["ok"] is True

    # After delete effective is None again
    _, out = _req("GET", f"{api}/api/workbench/effective/zarathustra", token=alice)
    assert out["config"] is None


def test_publish_requires_curator_via_http(api):
    admin_token = _seed(api)
    alice = _make_user(api, admin_token, "alice", ["user"])
    kate = _make_user(api, admin_token, "kate", ["curator"])

    _, out = _req("POST", f"{api}/api/workbench/configs",
                  {"workspace_id": "default", "branch": "zarathustra",
                   "name": "candidate-default"}, token=alice)
    cfg_id = out["config"]["config_id"]

    # Alice cannot publish
    status, out = _req("POST",
                       f"{api}/api/workbench/configs/{cfg_id}/publish",
                       {}, token=alice)
    assert status == 400
    # But she also cannot even *see* the config as kate (until publish happens)
    # so kate has to be an admin here or the config has to be public. In our
    # model the curator publishes their OWN builds, or the admin proxies. Test
    # that path:
    _, out = _req("POST", f"{api}/api/workbench/configs",
                  {"workspace_id": "default", "branch": "zarathustra",
                   "name": "kate-ships"}, token=kate)
    kate_cfg = out["config"]["config_id"]
    status, out = _req("POST",
                       f"{api}/api/workbench/configs/{kate_cfg}/publish",
                       {}, token=kate)
    assert status == 200
    assert out["scope"] == "line_default"

    # Now everyone sees the line default as their effective
    _, out = _req("GET", f"{api}/api/workbench/effective/zarathustra", token=alice)
    assert out["config"]["config_id"] == kate_cfg


def test_alice_cannot_read_kates_configs(api):
    admin_token = _seed(api)
    alice = _make_user(api, admin_token, "alice", ["user"])
    kate = _make_user(api, admin_token, "kate", ["user"])

    _, out = _req("POST", f"{api}/api/workbench/configs",
                  {"workspace_id": "d", "branch": "zarathustra",
                   "name": "kate-only"}, token=kate)
    kid = out["config"]["config_id"]

    status, out = _req("GET", f"{api}/api/workbench/configs/{kid}", token=alice)
    assert status in (400, 404)
    assert "чужая" in out["error"]


def test_anonymous_effective_falls_back_to_line_default(api):
    admin_token = _seed(api)
    kate = _make_user(api, admin_token, "kate", ["curator"])
    _, out = _req("POST", f"{api}/api/workbench/configs",
                  {"workspace_id": "d", "branch": "zarathustra",
                   "name": "team-default"}, token=kate)
    _req("POST", f"{api}/api/workbench/configs/{out['config']['config_id']}/publish",
         {}, token=kate)

    # No token — landing page use case
    _, out = _req("GET", f"{api}/api/workbench/effective/zarathustra")
    assert out["config"]["name"] == "team-default"
