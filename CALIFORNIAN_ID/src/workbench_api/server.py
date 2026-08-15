"""Workbench HTTP layer.

Thin: parses the URL, calls :class:`workbench_core.WorkbenchService`, serialises.
All read endpoints are side-effect free. Mutating endpoints are POST/PUT only.
Static UI assets are served from ``workbench_ui/dist`` when present.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from workbench_adapters import SocratesBranchAdapter, ZarathustraAdapter
from workbench_adapters.runtime_resolver import WorkbenchConfigResolver
from workbench_core import WorkbenchError, WorkbenchService, WorkbenchStore
from workbench_core.compiler import ProvenanceError
from workbench_core.lifecycle import LifecycleError

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE = ROOT / "workbench_state"
UI_DIST = ROOT / "workbench_ui" / "dist"

_service: WorkbenchService | None = None


def get_service(state_dir: Path | None = None) -> WorkbenchService:
    global _service
    if _service is None:
        store = WorkbenchStore(state_dir or Path(os.environ.get(
            "WORKBENCH_STATE_DIR", str(DEFAULT_STATE))))
        svc = WorkbenchService(store)
        svc.register_adapter(ZarathustraAdapter())
        svc.register_adapter(SocratesBranchAdapter())
        svc.bootstrap()
        svc.bootstrap_rag()
        # The RUN button drives the real entrypoint, so the resolver that feeds
        # the production seam must be installed here, not only in tests.
        svc.install_runtime_resolver(WorkbenchConfigResolver(store))
        _service = svc
    return _service


def reset_service() -> None:
    global _service
    _service = None


class Handler(BaseHTTPRequestHandler):
    server_version = "TinkuyWorkbench/0.1"

    # ---------------- plumbing ----------------

    def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            return {}

    def log_message(self, fmt: str, *args: object) -> None:  # quiet
        return

    # ---------------- routing ----------------

    def do_GET(self) -> None:      # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        try:
            if path.startswith("/api/"):
                return self._json(self._route_get(path, query))
            return self._serve_static(path)
        except WorkbenchError as exc:
            self._json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
        except Exception as exc:                                  # noqa: BLE001
            self._json({"error": str(exc), "trace": traceback.format_exc()},
                       HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:     # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        body = self._body()
        try:
            return self._json(self._route_post(path, body))
        except (LifecycleError, ProvenanceError) as exc:
            self._json({"error": str(exc), "kind": type(exc).__name__},
                       HTTPStatus.CONFLICT)
        except WorkbenchError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:                                  # noqa: BLE001
            self._json({"error": str(exc), "trace": traceback.format_exc()},
                       HTTPStatus.INTERNAL_SERVER_ERROR)

    do_PUT = do_POST

    # ---------------- GET table ----------------

    def _route_get(self, path: str, q: dict[str, list[str]]) -> Any:
        svc = get_service()
        one = lambda k, d=None: (q.get(k) or [d])[0]            # noqa: E731

        if path == "/api/workbench/health":
            return {"ok": True, "branches": sorted(svc.adapters)}

        if path == "/api/workbench/pipelines":
            return {"pipelines": svc.pipelines()}

        if path == "/api/workbench/branches":
            return {"branches": svc.branches()}

        m = re.fullmatch(r"/api/workbench/branch/([^/]+)/"
                         r"(state|invariants|contracts|profiles|readiness|snapshot)", path)
        if m:
            branch, what = m.group(1), m.group(2)
            fn = {"state": "state_projection", "invariants": "branch_invariants",
                  "contracts": "contract_bindings", "profiles": "runtime_profiles",
                  "readiness": "branch_readiness",
                  "snapshot": "declarative_snapshot"}[what]
            return {what: svc.branch_feature(branch, fn)}

        m = re.fullmatch(r"/api/workbench/branch/([^/]+)/prompt_body/([^/]+)", path)
        if m:
            return {"prompt_body": svc.branch_feature(
                m.group(1), "prompt_body", unquote(m.group(2)))}

        m = re.fullmatch(r"/api/workbench/pipeline/([^/]+)/graph", path)
        if m:
            resolved = {k: v[0] for k, v in q.items()}
            return svc.pipeline(m.group(1), resolved).to_public()

        m = re.fullmatch(r"/api/workbench/node/([^/]+)/([^/]+)", path)
        if m:
            resolved = {k: v[0] for k, v in q.items() if k != "run_id"}
            return svc.node(m.group(1), m.group(2), resolved, one("run_id"))

        m = re.fullmatch(r"/api/workbench/projection/([^/]+)/([^/]+)", path)
        if m:
            branch, kind = m.group(1), m.group(2)
            adapter = svc.adapters.get(branch)
            if adapter is None:
                raise WorkbenchError(f"unknown branch: {branch}")
            from workbench_adapters import WhiteCrowProjectionAdapter
            resolved = {k: v[0] for k, v in q.items()}
            return WhiteCrowProjectionAdapter(adapter).to_public(kind, resolved)

        m = re.fullmatch(r"/api/workbench/controls/([^/]+)", path)
        if m:
            adapter = svc.adapters.get(m.group(1))
            if adapter is None:
                raise WorkbenchError(f"unknown branch: {m.group(1)}")
            return {"controls": [c.to_public() for c in adapter.semantic_controls()]}

        m = re.fullmatch(r"/api/workbench/asset/([^/]+)", path)
        if m:
            return svc.asset_view(m.group(1))

        m = re.fullmatch(r"/api/workbench/asset/([^/]+)/variant/([^/]+)/source", path)
        if m:
            asset = svc.asset(m.group(1))
            v = svc.variant(m.group(1), m.group(2))
            regions = []
            for r in asset.regions:
                loc = r.locate(v.source_text)
                regions.append({"name": r.name, "kind": r.kind, "reason": r.reason,
                                "start": loc[0] if loc else None,
                                "end": loc[1] if loc else None})
            return {"variant": v.to_public(with_source=True), "regions": regions,
                    "evaluations": svc.store.evaluations_for(v.variant_id)}

        m = re.fullmatch(r"/api/workbench/asset/([^/]+)/diff", path)
        if m:
            return svc.diff(m.group(1), one("base"), one("candidate"))

        m = re.fullmatch(r"/api/workbench/rag/([^/]+)", path)
        if m:
            return svc.rag_view(m.group(1))

        m = re.fullmatch(r"/api/workbench/rag/([^/]+)/explain/([^/]+)/(.+)", path)
        if m:
            return svc.explain_chunk(m.group(2), m.group(3))

        if path == "/api/workbench/rag":
            return {"profiles": [p.to_public() for p in svc.store.list_rag_profiles()],
                    "active": (svc.store.read_activations().get("rag_bindings") or {})}

        if path == "/api/workbench/retrieval_events":
            return {"events": [e.to_public() for e in
                               svc.store.retrieval_events(one("run_id"),
                                                          int(one("limit", "20")))]}

        if path == "/api/workbench/rejections":
            return {"rejections": svc.store.rejections(int(one("limit", "50")))}

        if path == "/api/workbench/waivers":
            return {"waivers": [w.to_public() for w in svc.store.read_waivers()]}

        if path == "/api/workbench/runs":
            return {"runs": svc.store.list_runs(int(one("limit", "20")))}

        if path == "/api/workbench/run_index":
            return {"runs": svc.run_index(int(one("limit", "30")))}

        m = re.fullmatch(r"/api/workbench/compare_runs/([^/]+)/([^/]+)", path)
        if m:
            return svc.compare_runs(m.group(1), m.group(2))

        m = re.fullmatch(r"/api/workbench/fixtures/([^/]+)", path)
        if m:
            return {"fixtures": svc.input_fixtures(m.group(1))}

        m = re.fullmatch(r"/api/workbench/run/([^/]+)", path)
        if m:
            trace = svc.store.read_run(m.group(1))
            if trace is None:
                raise WorkbenchError(f"unknown run: {m.group(1)}")
            return trace

        raise WorkbenchError(f"unknown endpoint: {path}")

    # ---------------- POST table ----------------

    def _route_post(self, path: str, body: dict[str, Any]) -> Any:
        svc = get_service()
        actor = str(body.get("actor") or "operator")

        m = re.fullmatch(r"/api/workbench/asset/([^/]+)/variant/([^/]+)/clone", path)
        if m:
            v = svc.clone(m.group(1), m.group(2), actor, str(body.get("title") or ""))
            return {"variant": v.to_public(with_source=True)}

        m = re.fullmatch(r"/api/workbench/asset/([^/]+)/variant/([^/]+)/source", path)
        if m:
            v = svc.update_source(m.group(1), m.group(2),
                                  str(body.get("source_text") or ""), actor,
                                  str(body.get("intent") or "content"))
            return {"variant": v.to_public(with_source=True)}

        if path == "/api/workbench/waiver":
            return svc.grant_waiver(
                str(body.get("category") or ""), str(body.get("item") or ""),
                str(body.get("reason") or ""), str(body.get("adr_ref") or ""),
                actor, str(body.get("asset_id") or "*"))

        m = re.fullmatch(r"/api/workbench/asset/([^/]+)/variant/([^/]+)/validate", path)
        if m:
            return svc.validate(m.group(1), m.group(2))

        m = re.fullmatch(r"/api/workbench/asset/([^/]+)/variant/([^/]+)/compile", path)
        if m:
            return svc.compile(m.group(1), m.group(2), body.get("fixture_id"))

        m = re.fullmatch(r"/api/workbench/asset/([^/]+)/variant/([^/]+)/smoke", path)
        if m:
            return svc.run_smoke(m.group(1), m.group(2), body.get("fixture_id")).to_public()

        m = re.fullmatch(r"/api/workbench/asset/([^/]+)/variant/([^/]+)/compare", path)
        if m:
            return svc.compare_with_baseline(m.group(1), m.group(2), body.get("fixture_id"))

        m = re.fullmatch(r"/api/workbench/asset/([^/]+)/variant/([^/]+)/accept", path)
        if m:
            return {"variant": svc.accept(m.group(1), m.group(2), actor)}

        m = re.fullmatch(r"/api/workbench/asset/([^/]+)/variant/([^/]+)/activate", path)
        if m:
            return svc.activate(m.group(1), m.group(2), actor)

        m = re.fullmatch(r"/api/workbench/asset/([^/]+)/rollback", path)
        if m:
            return svc.rollback(m.group(1), actor)

        m = re.fullmatch(r"/api/workbench/rag/([^/]+)/(clone|update|validate|test|"
                         r"compare|accept|activate)", path)
        if m:
            pid, op = m.group(1), m.group(2)
            if op == "clone":
                return {"profile": svc.clone_rag(pid, actor).to_public()}
            if op == "update":
                return {"profile": svc.update_rag(pid, body.get("changes") or {},
                                                  actor).to_public()}
            if op == "validate":
                return svc.validate_rag(pid)
            if op == "test":
                return svc.retrieval_test(pid, body.get("fixture_id"))
            if op == "compare":
                return svc.compare_rag(pid, body.get("fixture_id"))
            if op == "accept":
                return {"profile": svc.accept_rag(pid)}
            if op == "activate":
                return svc.activate_rag(pid, actor)

        m = re.fullmatch(r"/api/workbench/rag_engine/([^/]+)/rollback", path)
        if m:
            return svc.rollback_rag(m.group(1), actor)

        if path == "/api/workbench/run":
            return svc.start_run(str(body.get("branch") or "zarathustra"),
                                 str(body.get("asset_id") or ""),
                                 body.get("fixture_id"), actor)

        if path == "/api/workbench/production_run":
            text = str(body.get("text") or "").strip()
            if not text:
                raise WorkbenchError("нужен входной текст")
            return svc.start_production_run(
                str(body.get("branch") or "zarathustra"), text,
                str(body.get("mode") or "fast"), actor)

        raise WorkbenchError(f"unknown endpoint: {path}")

    # ---------------- static ----------------

    def _serve_static(self, path: str) -> None:
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        target = (UI_DIST / rel).resolve()
        if not str(target).startswith(str(UI_DIST.resolve())) or not target.is_file():
            target = UI_DIST / "index.html"
        if not target.is_file():
            body = (b"<h1>Tinkuy Workbench</h1><p>UI not built. Run "
                    b"<code>npm install &amp;&amp; npm run build</code> in workbench_ui/.</p>")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        data = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8" if ctype.startswith("text") else ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def serve(host: str = "127.0.0.1", port: int = 8790) -> None:
    get_service()
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Tinkuy Workbench on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    serve(port=int(os.environ.get("WORKBENCH_PORT", "8790")))
