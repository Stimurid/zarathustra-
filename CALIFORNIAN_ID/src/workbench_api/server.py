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
from workbench_auth import (
    AuthError,
    InvalidCode,
    Role,
    TokenError,
    UnknownUser,
    User,
    WorkbenchAuth,
    WorkbenchAuthStore,
)
from workbench_auth.tokens import looks_like_bearer
from workbench_configs import (
    ConfigError,
    ConfigNotFound,
    NotAuthorized,
    PipelineConfigService,
    PipelineConfigStore,
    PromptFragmentOverlay,
    PromptVariantSelection,
    RAGProfileSelection,
    SemanticControlOverride,
)
from workbench_core import WorkbenchError, WorkbenchService, WorkbenchStore
from workbench_core.compiler import ProvenanceError
from workbench_core.lifecycle import LifecycleError

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE = ROOT / "workbench_state"
UI_DIST = ROOT / "workbench_ui" / "dist"

_service: WorkbenchService | None = None
_auth: WorkbenchAuth | None = None
_configs: PipelineConfigService | None = None


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


def get_auth(state_dir: Path | None = None) -> WorkbenchAuth:
    global _auth
    if _auth is None:
        base = state_dir or Path(os.environ.get(
            "WORKBENCH_STATE_DIR", str(DEFAULT_STATE)))
        _auth = WorkbenchAuth(WorkbenchAuthStore(base / "auth.sqlite3"),
                              state_dir=base)
        # Bootstrap once: if no users exist, mint a seed admin code and print
        # it. On subsequent starts, ``ensure_seed_admin`` is a no-op.
        seed = _auth.ensure_seed_admin(note="startup-seed")
        if seed is not None:
            print(f"[workbench-auth] seed admin code: {seed.code}",
                  flush=True)
    return _auth


def get_configs(state_dir: Path | None = None) -> PipelineConfigService:
    global _configs
    if _configs is None:
        base = state_dir or Path(os.environ.get(
            "WORKBENCH_STATE_DIR", str(DEFAULT_STATE)))
        svc = get_service(state_dir)

        def regions_for_asset(_branch: str, asset_id: str) -> list[Any]:
            try:
                return list(svc.asset(asset_id).regions)
            except WorkbenchError:
                return []

        _configs = PipelineConfigService(
            PipelineConfigStore(base / "configs.sqlite3"),
            regions_for_asset=regions_for_asset)
    return _configs


_socrates_runtime = None


def _get_socrates_runtime():
    """Lazy singleton — a SemanticBodyRegistry load is not free."""
    global _socrates_runtime
    if _socrates_runtime is None:
        from socrates_runtime import SocratesRuntime
        base = Path(os.environ.get("WORKBENCH_STATE_DIR", str(DEFAULT_STATE)))
        _socrates_runtime = SocratesRuntime(trace_dir=base / "socrates_traces")
    return _socrates_runtime


def reset_service() -> None:
    global _service, _auth, _configs, _socrates_runtime
    _service = None
    _auth = None
    _configs = None
    _socrates_runtime = None


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

    # ---------------- identity ----------------

    def _identity(self) -> User | None:
        """Extract and verify the caller identity from Authorization header.

        Returns ``None`` for anonymous callers — endpoints that need identity
        raise if this is ``None``. Never falls back to a "default operator",
        because that would make anonymous edits look like real ones.
        """
        token = looks_like_bearer(self.headers.get("Authorization"))
        if not token:
            return None
        try:
            return get_auth().verify(token)
        except (TokenError, UnknownUser):
            return None

    def _require_identity(self) -> User:
        me = self._identity()
        if me is None:
            raise WorkbenchError("требуется авторизация: заголовок "
                                 "Authorization: Bearer <token>")
        return me

    def _require_role(self, user: User, *allowed: str) -> None:
        if not any(user.has_role(r) for r in allowed):
            raise WorkbenchError(
                f"недостаточно прав: нужна одна из ролей {sorted(set(allowed))}")

    def _legacy_actor(self, body: dict[str, Any]) -> str:
        """Actor for legacy variant/rag lifecycle endpoints.

        Prefer a verified identity if present — a signed-in user's actions
        should be attributed to them, not to whichever string the client sent
        as ``actor``. Falls back to the body's ``actor`` (or the historical
        default ``"operator"``) when the caller is anonymous, so pre-auth
        tooling keeps working.
        """
        me = self._identity()
        return me.display_name if me else str(body.get("actor") or "operator")

    def _route_socrates_run(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST /api/workbench/socrates/run — one Socrates pipeline run.

        Body:
            input           str, required
            workspace_id    str, optional (defaults to caller's or 'default')
            pipeline_config_id  str, optional — resolves through configs svc

        Anonymous callers may run Socrates (the runtime records the empty
        identity). If a bearer token is present, the run is attributed and
        its ``SocratesRunConfiguration`` picks up display_name/user_id.
        """
        text = str(body.get("input") or body.get("text") or "").strip()
        if not text:
            raise WorkbenchError("body.input is required")

        me = self._identity()
        workspace_id = str(body.get("workspace_id")
                           or (me.display_name + "_ws" if me else "default"))

        pipeline_config = None
        cid = body.get("pipeline_config_id")
        if cid:
            if me is None:
                raise WorkbenchError(
                    "pipeline_config_id requires authenticated caller")
            try:
                pipeline_config = get_configs().get(me, str(cid))
            except (ConfigNotFound, NotAuthorized) as exc:
                raise WorkbenchError(str(exc)) from None

        try:
            from socrates_runtime import ExecutionMode, SocratesRuntime
            from socrates_runtime.runtime import resolve_configuration
        except ImportError as exc:
            raise WorkbenchError(
                f"socrates_runtime unavailable: {exc}") from None

        runtime = _get_socrates_runtime()
        run_config = resolve_configuration(
            pipeline_config,
            user=me,
            workspace_id=workspace_id,
            semantic_pack_version=runtime.identity.pack.version,
            semantic_pack_sha256=runtime.identity.pack.source_bundle_sha256,
        )

        # Execution mode is explicit. Body may pass execution_mode='LIVE'|
        # 'DETERMINISTIC'|'TEST_DOUBLE'. LIVE with no provider fails
        # explicitly — never silently deterministic.
        raw_mode = str(body.get("execution_mode") or ExecutionMode.DETERMINISTIC).upper()
        if raw_mode not in {ExecutionMode.LIVE, ExecutionMode.DETERMINISTIC,
                             ExecutionMode.TEST_DOUBLE}:
            raise WorkbenchError(
                f"execution_mode must be LIVE | DETERMINISTIC | TEST_DOUBLE "
                f"(got {raw_mode!r})")

        result = runtime.run(text, configuration=run_config, mode=raw_mode)
        payload = result.to_public()
        # Surface a compact view distinguishing model_produced vs
        # deterministic phases so a UI can render provenance.
        payload["provenance_summary"] = {
            "execution_mode": result.execution_mode,
            "provider_id": result.provider_id,
            "model_id": result.model_id,
            "phase_origins": [
                {"phase": p["phase"],
                 "origin_kind": p["execution"]["delta"]["origin_kind"],
                 "provider_status": p["execution"]["provider_status"],
                 "attempts": p["execution"]["attempts"]}
                for p in result.mounted_phases],
        }
        return {"run": payload}

    @staticmethod
    def _as_prompt_selections(body: dict[str, Any], *, present_only: bool = False):
        raw = body.get("prompt_selections")
        if raw is None:
            return None if present_only else []
        return [PromptVariantSelection(asset_id=str(x["asset_id"]),
                                       variant_id=str(x["variant_id"]))
                for x in raw]

    @staticmethod
    def _as_prompt_overlays(body: dict[str, Any], *, present_only: bool = False):
        raw = body.get("prompt_overlays")
        if raw is None:
            return None if present_only else []
        return [PromptFragmentOverlay(asset_id=str(x["asset_id"]),
                                      region_id=str(x["region_id"]),
                                      text=str(x.get("text") or ""))
                for x in raw]

    @staticmethod
    def _as_rag_selections(body: dict[str, Any], *, present_only: bool = False):
        raw = body.get("rag_selections")
        if raw is None:
            return None if present_only else []
        return [RAGProfileSelection(engine_id=str(x["engine_id"]),
                                    profile_id=str(x["profile_id"]))
                for x in raw]

    @staticmethod
    def _as_semantic_overrides(body: dict[str, Any], *, present_only: bool = False):
        raw = body.get("semantic_overrides")
        if raw is None:
            return None if present_only else []
        return [SemanticControlOverride(control_id=str(x["control_id"]),
                                        value=str(x.get("value") or ""))
                for x in raw]

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

        # ---------------- identity + configs (L1) ----------------

        if path == "/api/workbench/auth/status":
            me = self._identity()
            return {"authenticated": me is not None,
                    "user": me.to_public() if me else None}

        if path == "/api/workbench/me":
            return {"user": self._require_identity().to_public()}

        if path == "/api/workbench/auth/codes":
            me = self._require_identity()
            self._require_role(me, Role.CURATOR, Role.ADMIN)
            only_unredeemed = one("only_unredeemed", "false") == "true"
            reveal = one("reveal", "false") == "true" and me.has_role(Role.ADMIN)
            codes = get_auth().store.list_codes(only_unredeemed=only_unredeemed)
            return {"codes": [c.to_public(reveal_code=reveal) for c in codes]}

        if path == "/api/workbench/configs":
            me = self._require_identity()
            configs = get_configs().list(me, branch=one("branch"))
            return {"configs": [c.to_public() for c in configs]}

        m = re.fullmatch(r"/api/workbench/configs/([^/]+)", path)
        if m:
            me = self._require_identity()
            try:
                cfg = get_configs().get(me, m.group(1))
            except ConfigNotFound as exc:
                raise WorkbenchError(str(exc)) from None
            except NotAuthorized as exc:
                raise WorkbenchError(str(exc)) from None
            return {"config": cfg.to_public()}

        m = re.fullmatch(r"/api/workbench/effective/([^/]+)", path)
        if m:
            # Anonymous callers may ask what the branch default is — used by
            # the UI landing page. Identified callers see their own resolution.
            cfg = get_configs().effective_for_run(self._identity(), m.group(1))
            return {"config": cfg.to_public() if cfg else None,
                    "branch": m.group(1)}

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

        # ---------------- identity + configs (L1) ----------------

        if path == "/api/workbench/auth/redeem":
            try:
                result = get_auth().redeem(
                    str(body.get("code") or ""),
                    str(body.get("display_name") or ""),
                    password=str(body.get("password") or ""))
            except InvalidCode as exc:
                raise WorkbenchError(str(exc)) from None
            return {"session": result.session.to_public()}

        if path == "/api/workbench/auth/login":
            try:
                session = get_auth().login(
                    str(body.get("display_name") or ""),
                    str(body.get("password") or ""))
            except AuthError as exc:
                raise WorkbenchError(str(exc)) from None
            return {"session": session.to_public()}

        if path == "/api/workbench/auth/mint":
            me = self._require_identity()
            roles = list(body.get("roles") or [Role.USER])
            try:
                code = get_auth().mint_code(
                    roles, minted_by_user=me,
                    expires_in_hours=int(body.get("expires_in_hours") or 168),
                    note=str(body.get("note") or ""))
            except AuthError as exc:
                raise WorkbenchError(str(exc)) from None
            # Full code is returned once, at mint time — never listed later.
            return {"code": code.to_public(reveal_code=True)}

        if path == "/api/workbench/auth/password":
            me = self._require_identity()
            try:
                get_auth().set_password(me, str(body.get("password") or ""))
            except AuthError as exc:
                raise WorkbenchError(str(exc)) from None
            return {"ok": True}

        # -- configs --

        if path == "/api/workbench/configs":
            me = self._require_identity()
            try:
                cfg = get_configs().create(
                    me,
                    workspace_id=str(body.get("workspace_id") or "default"),
                    branch=str(body.get("branch") or ""),
                    name=str(body.get("name") or ""),
                    description=str(body.get("description") or ""),
                    prompt_selections=self._as_prompt_selections(body),
                    prompt_overlays=self._as_prompt_overlays(body),
                    rag_selections=self._as_rag_selections(body),
                    semantic_overrides=self._as_semantic_overrides(body),
                    model_binding=body.get("model_binding") or {},
                    parent_config_id=str(body.get("parent_config_id") or ""))
            except (ConfigError, NotAuthorized) as exc:
                raise WorkbenchError(str(exc)) from None
            return {"config": cfg.to_public()}

        m = re.fullmatch(r"/api/workbench/configs/([^/]+)/update", path)
        if m:
            me = self._require_identity()
            try:
                cfg = get_configs().update(
                    me, m.group(1),
                    name=body.get("name"),
                    description=body.get("description"),
                    prompt_selections=self._as_prompt_selections(body, present_only=True),
                    prompt_overlays=self._as_prompt_overlays(body, present_only=True),
                    rag_selections=self._as_rag_selections(body, present_only=True),
                    semantic_overrides=self._as_semantic_overrides(body, present_only=True),
                    model_binding=body.get("model_binding"))
            except (ConfigError, ConfigNotFound, NotAuthorized) as exc:
                raise WorkbenchError(str(exc)) from None
            return {"config": cfg.to_public()}

        m = re.fullmatch(r"/api/workbench/configs/([^/]+)/personal_activate", path)
        if m:
            me = self._require_identity()
            try:
                cfg = get_configs().personal_activate(me, m.group(1))
            except (ConfigNotFound, NotAuthorized) as exc:
                raise WorkbenchError(str(exc)) from None
            return {"config": cfg.to_public(), "scope": "personal"}

        m = re.fullmatch(r"/api/workbench/configs/([^/]+)/publish", path)
        if m:
            me = self._require_identity()
            try:
                cfg = get_configs().publish_as_line_default(me, m.group(1))
            except (ConfigNotFound, NotAuthorized) as exc:
                raise WorkbenchError(str(exc)) from None
            return {"config": cfg.to_public(), "scope": "line_default"}

        m = re.fullmatch(r"/api/workbench/configs/([^/]+)/delete", path)
        if m:
            me = self._require_identity()
            try:
                get_configs().delete(me, m.group(1))
            except (ConfigNotFound, NotAuthorized) as exc:
                raise WorkbenchError(str(exc)) from None
            return {"ok": True, "config_id": m.group(1)}

        m = re.fullmatch(r"/api/workbench/personal_active/([^/]+)/clear", path)
        if m:
            me = self._require_identity()
            get_configs().clear_personal_active(me, m.group(1))
            return {"ok": True, "branch": m.group(1)}

        # -- Socrates runtime (P6) ------------------------------------
        if path == "/api/workbench/socrates/run":
            return self._route_socrates_run(body)

        # -- fall through to the legacy variant/rag lifecycle below --
        actor = self._legacy_actor(body)

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

        if path == "/api/workbench/copilot":
            return {"copilot": svc.branch_feature(
                str(body.get("branch") or "zarathustra"), "copilot",
                str(body.get("action") or ""), str(body.get("source_text") or ""),
                str(body.get("selection") or ""), str(body.get("context") or ""))}

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
