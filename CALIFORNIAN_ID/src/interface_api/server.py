"""HTTP layer for the vertical-slice interface_api.

Same shape as `workbench_api.server` (stdlib `http.server` +
`ThreadingHTTPServer`) so the deploy pattern is 1:1. New endpoints
live strictly under `/api/interface/*` and do not touch
`/api/workbench/*` (operator) or `/api/socrates/*` (runtime).
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import threading
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .comparative_arm import ArmKind, run_comparative
from .epistemic_events import extract_events
from .evaluation import (
    EvaluationRecord, EvaluationState, MetricEntry, MetricKind,
    MetricVerdict, auto_populate,
)
from .long_pressure import LongPressureError, run_long_pressure
from .models import (
    ArtifactKind, DecisionAction, InputArtifact, InputKind,
    Run, RunMode, RunStatus, Session, SessionStatus, _now_iso,
)
from .runtime_binding import execute_run
from .scenarios import ScenarioCategory, ScenarioState, get_registry
from .state import InterfaceStore


ROOT = Path(__file__).resolve().parents[2]
UI_DIST = ROOT / "interface_ui"


_state_lock = threading.Lock()
_store: InterfaceStore | None = None
_store_path: str = ""
_runs_dir: str = ""


def _resolve_paths() -> tuple[str, str]:
    """Read env for runtime dir + db path.

    * `CALIFORNIAN_ID_INTERFACE_DB` — full path to the SQLite file.
    * `CALIFORNIAN_ID_RUNS_DIR`     — where trace files land.
    """
    runs_dir = os.environ.get("CALIFORNIAN_ID_RUNS_DIR") or str(
        Path.cwd() / "runs")
    db_path = os.environ.get("CALIFORNIAN_ID_INTERFACE_DB") or str(
        Path(runs_dir) / "interface_state.sqlite")
    return db_path, runs_dir


def get_store() -> InterfaceStore:
    global _store, _store_path, _runs_dir
    with _state_lock:
        if _store is None:
            _store_path, _runs_dir = _resolve_paths()
            _store = InterfaceStore(_store_path)
        return _store


def reset_store_for_tests(db_path: str, runs_dir: str) -> None:
    """Test-only: point the process at a tmp DB + runs dir."""
    global _store, _store_path, _runs_dir
    with _state_lock:
        if _store is not None:
            _store.close()
            _store = None
        _store_path = db_path
        _runs_dir = runs_dir
        os.environ["CALIFORNIAN_ID_INTERFACE_DB"] = db_path
        os.environ["CALIFORNIAN_ID_RUNS_DIR"] = runs_dir
        _store = InterfaceStore(db_path)


class InterfaceError(Exception):
    """Typed error for client-visible refusals."""


class Handler(BaseHTTPRequestHandler):

    # ---------- boilerplate ----------

    def log_message(self, format: str, *args) -> None:      # noqa: A002
        # keep quiet; workbench pattern
        pass

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            raise InterfaceError(f"bad JSON body: {exc}") from None

    def _json(self, obj, status: int = HTTPStatus.OK) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # ---------- routing ----------

    def do_GET(self) -> None:                                # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path.startswith("/api/interface/"):
                return self._json(self._route_get(path))
            return self._serve_static(path)
        except InterfaceError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:                             # noqa: BLE001
            self._json({"error": str(exc),
                        "trace": traceback.format_exc()},
                       HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:                               # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            body = self._body()
            if path.startswith("/api/interface/"):
                return self._json(self._route_post(path, body))
            raise InterfaceError(f"unknown endpoint: {path}")
        except InterfaceError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:                             # noqa: BLE001
            self._json({"error": str(exc),
                        "trace": traceback.format_exc()},
                       HTTPStatus.INTERNAL_SERVER_ERROR)

    # ---------- GET table ----------

    def _route_get(self, path: str):
        store = get_store()

        if path == "/api/interface/health":
            return {"ok": True, "component": "interface_api"}

        if path == "/api/interface/scenarios":
            reg = get_registry()
            return {"scenarios": [s.to_public() for s in reg.list()],
                    "source_path": str(reg.source_path)}

        m = re.fullmatch(r"/api/interface/scenario/([^/]+)", path)
        if m:
            reg = get_registry()
            sc = reg.get(m.group(1))
            if sc is None:
                raise InterfaceError(f"unknown scenario: {m.group(1)}")
            return {"scenario": sc.to_public()}

        m = re.fullmatch(r"/api/interface/evaluation/([^/]+)", path)
        if m:
            ev = store.get_evaluation(m.group(1))
            if ev is None:
                raise InterfaceError(f"unknown evaluation: {m.group(1)}")
            return {"evaluation": ev.to_public()}

        m = re.fullmatch(r"/api/interface/evaluations/([^/]+)", path)
        if m:
            sid = m.group(1)
            if store.get_session(sid) is None:
                raise InterfaceError(f"unknown session: {sid}")
            return {"evaluations": [e.to_public()
                                    for e in store.list_evaluations(sid)]}

        m = re.fullmatch(r"/api/interface/events/([^/]+)", path)
        if m:
            sid = m.group(1)
            if store.get_session(sid) is None:
                raise InterfaceError(f"unknown session: {sid}")
            runs = store.list_runs(sid)
            all_events = []
            for r in runs:
                for e in extract_events(r):
                    all_events.append({"run_id": r.run_id,
                                       **e.to_public()})
            return {"events": all_events, "count": len(all_events)}

        m = re.fullmatch(r"/api/interface/session/([^/]+)", path)
        if m:
            sid = m.group(1)
            session = store.get_session(sid)
            if session is None:
                raise InterfaceError(f"unknown session: {sid}")
            return {
                "session": session.to_public(),
                "inputs": [x.to_public() for x in store.list_inputs(sid)],
                "runs": [r.to_public() for r in store.list_runs(sid)],
                "artifacts": [a.to_public()
                              for a in store.list_artifacts(sid)],
            }

        m = re.fullmatch(r"/api/interface/run/([^/]+)", path)
        if m:
            rid = m.group(1)
            run = store.get_run(rid)
            if run is None:
                raise InterfaceError(f"unknown run: {rid}")
            return {"run": run.to_public()}

        m = re.fullmatch(r"/api/interface/artifacts/([^/]+)", path)
        if m:
            sid = m.group(1)
            if store.get_session(sid) is None:
                raise InterfaceError(f"unknown session: {sid}")
            return {"artifacts": [a.to_public()
                                  for a in store.list_artifacts(sid)]}

        m = re.fullmatch(r"/api/interface/input/([^/]+)", path)
        if m:
            iid = m.group(1)
            inp = store.get_input(iid)
            if inp is None:
                raise InterfaceError(f"unknown input: {iid}")
            d = inp.to_public()
            # full body for detail view
            d["body_text"] = inp.body_text
            return d

        raise InterfaceError(f"unknown endpoint: {path}")

    # ---------- POST table ----------

    def _route_post(self, path: str, body: dict):
        store = get_store()

        if path == "/api/interface/session":
            have = str(body.get("have") or "").strip()
            want = str(body.get("want") or "").strip()
            actor = str(body.get("actor") or "anonymous").strip()
            scenario_id = str(body.get("scenario_id") or "").strip()
            if not have or not want:
                raise InterfaceError("need `have` and `want`")
            s = Session.new(have=have, want=want, actor=actor,
                            scenario_id=scenario_id)
            store.put_session(s)
            return {"session": s.to_public()}

        if path == "/api/interface/session/from_scenario":
            sid_scenario = str(body.get("scenario_id") or "").strip()
            actor = str(body.get("actor") or "anonymous").strip()
            if not sid_scenario:
                raise InterfaceError("need `scenario_id`")
            reg = get_registry()
            sc = reg.get(sid_scenario)
            if sc is None:
                raise InterfaceError(
                    f"unknown scenario: {sid_scenario}")
            if sc.state != ScenarioState.ENABLED:
                raise InterfaceError(
                    f"scenario {sid_scenario} state="
                    f"{sc.state.value}; refusing to seed a session "
                    f"(blocker={sc.blocker_reason or 'unknown'})")
            s = Session.new(have="TEXT", want="ПРОВЕРИТЬ",
                            actor=actor, scenario_id=sid_scenario)
            store.put_session(s)
            return {"session": s.to_public(),
                    "scenario": sc.to_public()}

        if path == "/api/interface/turn":
            sid = str(body.get("session_id") or "").strip()
            text = str(body.get("text") or "").strip()
            mode_raw = str(body.get("mode") or "FAST").strip().upper()
            if not sid or not text:
                raise InterfaceError("need `session_id` and `text`")
            session = store.get_session(sid)
            if session is None:
                raise InterfaceError(f"unknown session: {sid}")
            try:
                mode = RunMode(mode_raw)
            except ValueError:
                raise InterfaceError(f"unknown RunMode: {mode_raw}")
            inp = InputArtifact.new(sid, InputKind.TEXT, text,
                                    "text/plain")
            store.put_input(inp)
            run = execute_run(store, session, inp, mode=mode,
                              runs_dir=_runs_dir)
            events = extract_events(run)
            return {"run": run.to_public(),
                    "events": [e.to_public() for e in events]}

        if path == "/api/interface/long_pressure_run":
            sid = str(body.get("session_id") or "").strip()
            scenario_id = str(body.get("scenario_id") or "").strip()
            mode_raw = str(body.get("mode") or "FAST").strip().upper()
            max_turns = body.get("max_turns")
            if not sid or not scenario_id:
                raise InterfaceError(
                    "need `session_id` and `scenario_id`")
            session = store.get_session(sid)
            if session is None:
                raise InterfaceError(f"unknown session: {sid}")
            reg = get_registry()
            sc = reg.get(scenario_id)
            if sc is None:
                raise InterfaceError(
                    f"unknown scenario: {scenario_id}")
            try:
                mode = RunMode(mode_raw)
            except ValueError:
                raise InterfaceError(f"unknown RunMode: {mode_raw}")
            try:
                result = run_long_pressure(
                    store, session, sc, mode=mode,
                    runs_dir=_runs_dir,
                    max_turns=int(max_turns) if max_turns else None)
            except LongPressureError as exc:
                raise InterfaceError(str(exc))
            return result

        if path == "/api/interface/evaluation":
            sid = str(body.get("session_id") or "").strip()
            scenario_id = str(body.get("scenario_id") or "").strip()
            if not sid:
                raise InterfaceError("need `session_id`")
            session = store.get_session(sid)
            if session is None:
                raise InterfaceError(f"unknown session: {sid}")
            if not scenario_id:
                scenario_id = session.scenario_id
            runs = store.list_runs(sid)
            all_events = []
            for r in runs:
                all_events.extend(extract_events(r))
            evaluation = auto_populate(
                session_id=sid, scenario_id=scenario_id,
                events=all_events, turns=len(runs))
            store.put_evaluation(evaluation)
            return {"evaluation": evaluation.to_public()}

        if path == "/api/interface/evaluation/human_review":
            eval_id = str(body.get("evaluation_id") or "").strip()
            reviewer = str(body.get("reviewer") or "").strip()
            notes = str(body.get("human_notes") or "").strip()
            overrides = body.get("overrides") or {}
            if not eval_id or not reviewer:
                raise InterfaceError(
                    "need `evaluation_id` and `reviewer`")
            ev = store.get_evaluation(eval_id)
            if ev is None:
                raise InterfaceError(f"unknown evaluation: {eval_id}")
            # Optional per-metric human overrides: {metric_kind: {verdict, note}}
            if isinstance(overrides, dict) and overrides:
                new_metrics = []
                for m in ev.metrics:
                    key = m.kind.value
                    if key in overrides and isinstance(
                            overrides[key], dict):
                        ov = overrides[key]
                        try:
                            v = MetricVerdict(str(ov.get("verdict")
                                                  or m.verdict.value))
                        except ValueError:
                            v = m.verdict
                        note = str(ov.get("note") or m.note)
                        # Preserve original AUTO evidence as visible in
                        # the record; humans can add notes but do not
                        # rewrite the auto evidence trail.
                        new_metrics.append(MetricEntry(
                            kind=m.kind, verdict=v,
                            evidence=m.evidence,
                            note=("HUMAN: " + note) if note else "HUMAN",
                        ))
                    else:
                        new_metrics.append(m)
                ev.metrics = new_metrics
            ev.state = EvaluationState.HUMAN_REVIEWED
            ev.reviewer = reviewer
            ev.reviewed_at = _now_iso()
            ev.human_notes = notes
            store.put_evaluation(ev)
            return {"evaluation": ev.to_public()}

        if path == "/api/interface/comparative_run":
            scenario_id = str(body.get("scenario_id") or "").strip()
            arms_raw = body.get("arms") or ["SOCRATES", "KVAQIN",
                                             "BASE_MODEL"]
            max_turns = body.get("max_turns")
            if not scenario_id:
                raise InterfaceError("need `scenario_id`")
            reg = get_registry()
            sc = reg.get(scenario_id)
            if sc is None:
                raise InterfaceError(
                    f"unknown scenario: {scenario_id}")
            arms: list[ArmKind] = []
            for a in arms_raw:
                try:
                    arms.append(ArmKind(str(a).upper()))
                except ValueError:
                    raise InterfaceError(f"unknown arm: {a}")
            return run_comparative(
                store, sc, arms=arms, runs_dir=_runs_dir,
                max_turns=int(max_turns) if max_turns else None)

        if path == "/api/interface/input":
            sid = str(body.get("session_id") or "").strip()
            if not sid:
                raise InterfaceError("need `session_id`")
            session = store.get_session(sid)
            if session is None:
                raise InterfaceError(f"unknown session: {sid}")
            kind_raw = str(body.get("kind") or "TEXT").strip().upper()
            try:
                kind = InputKind(kind_raw)
            except ValueError:
                raise InterfaceError(f"unknown InputKind: {kind_raw}")
            body_text = str(body.get("body_text") or "")
            mime = str(body.get("mime") or "text/plain")
            if not body_text:
                raise InterfaceError("empty `body_text`")
            inp = InputArtifact.new(sid, kind, body_text, mime)
            store.put_input(inp)
            store.update_session_status(sid, SessionStatus.INPUT_RECEIVED)
            return {"input": inp.to_public()}

        if path == "/api/interface/run":
            sid = str(body.get("session_id") or "").strip()
            iid = str(body.get("input_id") or "").strip()
            mode_raw = str(body.get("mode") or "FAST").strip().upper()
            if not sid or not iid:
                raise InterfaceError("need `session_id` and `input_id`")
            session = store.get_session(sid)
            if session is None:
                raise InterfaceError(f"unknown session: {sid}")
            inp = store.get_input(iid)
            if inp is None or inp.session_id != sid:
                raise InterfaceError(f"unknown input: {iid}")
            try:
                mode = RunMode(mode_raw)
            except ValueError:
                raise InterfaceError(f"unknown RunMode: {mode_raw}")
            run = execute_run(store, session, inp, mode=mode,
                              runs_dir=_runs_dir)
            return {"run": run.to_public(),
                    "artifacts": [a.to_public()
                                  for a in store.list_artifacts(sid)]}

        raise InterfaceError(f"unknown endpoint: {path}")

    # ---------- static ----------

    def _serve_static(self, path: str) -> None:
        rel = "index.html" if path in ("/", "", "/workspace") \
            else path.lstrip("/")
        target = (UI_DIST / rel).resolve()
        if not str(target).startswith(str(UI_DIST.resolve())) \
                or not target.is_file():
            target = UI_DIST / "index.html"
        if not target.is_file():
            body = (
                b"<h1>Tinkuy Interface</h1>"
                b"<p>UI bundle missing. Check "
                b"<code>CALIFORNIAN_ID/interface_ui/index.html</code>.</p>")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        data = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] \
            or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header(
            "Content-Type",
            f"{ctype}; charset=utf-8" if ctype.startswith("text") else ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def serve(host: str = "127.0.0.1", port: int = 8791) -> None:
    get_store()  # initialize
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Tinkuy Interface API on http://{host}:{port}", flush=True)
    httpd.serve_forever()


__all__ = ["Handler", "InterfaceError", "get_store",
           "reset_store_for_tests", "serve"]
