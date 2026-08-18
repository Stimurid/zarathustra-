#!/usr/bin/env python3
"""Production entry + real-provider proof. Run ON the VM. Never prints secrets."""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8085/api/socrates/run"
APP = Path("/opt/tinkuy/app")
ENV = Path("/etc/tinkuy/tinkuy.env")
PROOF_OUT = Path("/tmp/3a_plus_live/D_PROVIDER_PROOF.json")


def _md5(path: Path) -> str:
    import hashlib
    return hashlib.md5(path.read_bytes()).hexdigest()


def _env_names_and_safe_values() -> dict:
    """Read provider/model NAMES only. Never dump API keys."""
    out = {"env_file_exists": ENV.exists()}
    if not ENV.exists():
        return out
    raw = ENV.read_text(encoding="utf-8", errors="replace").splitlines()
    safe_keys = {
        "CALIFORNIAN_ID_PROVIDER",
        "SOCRATES_R8_MODEL_ID",
        "SOCRATES_R8_PROVIDER_BASE_URL",
        "PERSONA_LAYER_PROVIDER",
    }
    present_secret_keys = []
    for line in raw:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k in safe_keys:
            out[k] = v
        elif any(s in k.upper() for s in ("KEY", "TOKEN", "SECRET", "PASS", "AUTH")):
            present_secret_keys.append(k)
            out[k + "_PRESENT"] = bool(v)
            out[k + "_LEN"] = len(v)
    out["secret_keys_present"] = present_secret_keys
    provider = (out.get("CALIFORNIAN_ID_PROVIDER") or "").lower()
    out["mock_active"] = provider in {"mock", "fake", "stub", "test_double"}
    return out


def _extract_provider_proof(d: dict) -> dict:
    phases = d.get("mounted_phases") or []
    execs = []
    total_in = total_out = 0
    live_ok = 0
    mockish = 0
    for p in phases:
        ex = (p.get("execution") or {})
        pid = str(ex.get("provider_id") or "")
        mid = str(ex.get("model_id") or "")
        tin = int(ex.get("tokens_in") or 0)
        tout = int(ex.get("tokens_out") or 0)
        total_in += tin
        total_out += tout
        origin = ((ex.get("delta") or {}).get("origin_kind"))
        status = ex.get("provider_status")
        mode = ex.get("mode")
        if mode == "LIVE" and status == "OK":
            live_ok += 1
        if pid.lower() in {"mock", "fake", "stub"} or mid.lower() in {"mock", "fake"}:
            mockish += 1
        execs.append({
            "phase": p.get("phase"),
            "mode": mode,
            "provider_status": status,
            "provider_id": pid,
            "model_id": mid,
            "tokens_in": tin,
            "tokens_out": tout,
            "attempts": ex.get("attempts"),
            "latency_ms": ex.get("latency_ms"),
            "origin_kind": origin,
        })
    return {
        "runtime_layer": d.get("runtime_layer"),
        "execution_mode": d.get("execution_mode"),
        "top_provider_id": d.get("provider_id"),
        "top_model_id": d.get("model_id"),
        "duration_ms": d.get("duration_ms"),
        "run_id": d.get("run_id"),
        "trace_id": d.get("trace_id"),
        "phase_execs": execs,
        "live_ok_phases": live_ok,
        "mockish_phases": mockish,
        "tokens_in_sum": total_in,
        "tokens_out_sum": total_out,
        "terminal": (d.get("terminal") or {}).get("terminal"),
        "context_id": d.get("context_id"),
    }


def post(body: dict) -> dict:
    req = urllib.request.Request(
        BASE,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def main() -> None:
    PROOF_OUT.parent.mkdir(parents=True, exist_ok=True)
    status = subprocess.check_output(
        ["systemctl", "is-active", "tinkuy-web"], text=True).strip()
    modules = {
        "context_store.py": _md5(
            APP / "CALIFORNIAN_ID/src/socrates_runtime/context_store.py"),
        "context_continuity.py": _md5(
            APP / "CALIFORNIAN_ID/src/socrates_runtime/context_continuity.py"),
        "socrates_context_store.py": _md5(
            APP / "CALIFORNIAN_ID/src/californian_id/socrates_context_store.py"),
        "socrates_bridge.py": _md5(
            APP / "CALIFORNIAN_ID/src/californian_id/socrates_bridge.py"),
    }
    env_safe = _env_names_and_safe_values()
    body = {
        "text": (
            "Нужен короткий разбор: стоит ли запускать пилот нового "
            "внутреннего инструмента для трёх команд в одном квартале, "
            "или сначала собрать критерии отбора?"
        ),
        "execution_mode": "LIVE",
        "intervention_profile": "normal",
    }
    resp = post(body)
    proof = _extract_provider_proof(resp)
    (PROOF_OUT.parent / "D_PROVIDER_PROOF_full.json").write_text(
        json.dumps(resp, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {
        "deployed_sha_claimed": "dba32e1fcb2917e07846975ca4f7ca3d16e1b80d",
        "hostname": os.uname().nodename if hasattr(os, "uname") else "",
        "tinkuy_web": status,
        "module_md5": modules,
        "expected_context_store_md5": "cec751341c5e962da712029ba1f88cbd",
        "context_store_md5_match": modules["context_store.py"]
        == "cec751341c5e962da712029ba1f88cbd",
        "rollback_snapshot_exists": Path(
            "/opt/tinkuy/rollback_snapshot_pre_dba32e1.tar.gz").exists(),
        "env_safe": env_safe,
        "request": {"execution_mode": "LIVE",
                    "intervention_profile": "normal",
                    "text_len": len(body["text"])},
        "provider_proof": proof,
        "real_provider_invoked": (
            proof.get("execution_mode") == "LIVE"
            and proof.get("runtime_layer") == "socrates_runtime"
            and proof.get("live_ok_phases", 0) >= 1
            and not env_safe.get("mock_active")
            and proof.get("mockish_phases", 0) == 0
        ),
    }
    PROOF_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(json.dumps({
        "tinkuy_web": status,
        "context_store_md5_match": report["context_store_md5_match"],
        "mock_active": env_safe.get("mock_active"),
        "provider_name": env_safe.get("CALIFORNIAN_ID_PROVIDER"),
        "model_id_env": env_safe.get("SOCRATES_R8_MODEL_ID"),
        "runtime_layer": proof.get("runtime_layer"),
        "execution_mode": proof.get("execution_mode"),
        "top_provider_id": proof.get("top_provider_id"),
        "top_model_id": proof.get("top_model_id"),
        "live_ok_phases": proof.get("live_ok_phases"),
        "tokens_in_sum": proof.get("tokens_in_sum"),
        "tokens_out_sum": proof.get("tokens_out_sum"),
        "duration_ms": proof.get("duration_ms"),
        "real_provider_invoked": report["real_provider_invoked"],
        "context_id": proof.get("context_id"),
        "terminal": proof.get("terminal"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
