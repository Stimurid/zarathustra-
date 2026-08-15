"""WorkbenchService — the facade the HTTP layer talks to."""
from __future__ import annotations

import difflib
import uuid
from typing import Any

from .branch import BranchAdapter, Fixture, PipelineProjection
from .compiler import PromptCompiler
from .lifecycle import assert_not_baseline_removal, assert_transition, edit_resets_to
from .models import (
    ActivationSnapshot,
    CacheKey,
    CompiledPrompt,
    EvaluationRecord,
    PromptAsset,
    PromptVariant,
    RunConfigurationSnapshot,
    sha256_text,
)
from .rag import (
    RAGProfile,
    RetrievalCandidate,
    RetrievalEvent,
    assert_rag_transition,
    compare_retrieval,
    explain_candidate,
)
from .smoke import SmokeHarness, SmokeResult, compare as smoke_compare
from .store import WorkbenchStore, now_iso
from .validator import StaticValidator


def asdict_rag(p: RAGProfile) -> dict[str, Any]:
    import dataclasses
    d = dataclasses.asdict(p)
    d.pop("missing_capabilities", None)
    return d


def _bump(version: str) -> str:
    parts = version.split(".")
    try:
        parts[-1] = str(int(parts[-1]) + 1)
    except ValueError:
        return version + ".1"
    return ".".join(parts)


def _context_identity(included: list[RetrievalCandidate]) -> str:
    """Exact identity of the context handed downstream: ordered chunk hashes."""
    from .models import sha256_text
    payload = "|".join(f"{c.context_order}:{c.chunk_id}:{c.chunk_hash}"
                       for c in included)
    return "ctx:" + sha256_text(payload)[:24]


def _event_from_public(d: dict[str, Any]) -> RetrievalEvent:
    payload = dict(d)
    payload["candidates"] = [RetrievalCandidate(**c) for c in d.get("candidates", [])]
    return RetrievalEvent(**payload)


class WorkbenchError(RuntimeError):
    pass


#: Contract-shaped canned answer for the capture provider. Deliberately minimal:
#: the point of INTEGRATION_SMOKE is the invocation boundary and the real
#: parser, not the model's creativity.
_CANNED_SCENE_JSON = (
    '{"topic":"integration fixture","genre":"question","stakes":["s1"],'
    '"horizons":["short"],"concepts":["c1"],"tensions":["t1"],'
    '"uncertainties":["u1"]}'
)


class WorkbenchService:
    def __init__(self, store: WorkbenchStore, smoke: SmokeHarness | None = None) -> None:
        self.store = store
        self.adapters: dict[str, BranchAdapter] = {}
        self._assets: dict[str, tuple[str, PromptAsset]] = {}   # asset_id -> (branch, asset)
        self.validator = StaticValidator()
        self.compiler = PromptCompiler()
        self.smoke = smoke or SmokeHarness()
        self._compiled_cache: dict[str, CompiledPrompt] = {}
        self._rag_engines: dict[str, str] = {}   # rag profile_id -> branch

    # ---------------- registration ----------------

    def register_adapter(self, adapter: BranchAdapter) -> None:
        self.adapters[adapter.branch_id] = adapter
        for asset in adapter.list_assets():
            self._assets[asset.asset_id] = (adapter.branch_id, asset)

    def bootstrap(self) -> None:
        """Materialise BASELINE variants for every asset that has none."""
        for asset_id, (branch, asset) in self._assets.items():
            existing = {v.variant_id for v in self.store.list_variants(asset_id)}
            adapter = self.adapters[branch]
            for origin, version, text in adapter.baseline_variants(asset_id):
                vid = f"v_baseline_{origin}"
                if vid in existing:
                    continue
                self.store.save_variant(PromptVariant(
                    variant_id=vid, asset_id=asset_id, version=version,
                    state="BASELINE", origin=origin, source_text=text,
                    source_hash=sha256_text(text), author="system",
                    created_at=now_iso(), title=f"baseline ({origin})",
                ))
            if self.store.active_variant_id(asset_id) is None:
                # baseline_file wins over baseline_code — the on-disk head-zone
                # prompt is what the runtime actually uses when present.
                first = self.baseline(asset_id)
                if first is not None:
                    self.store.bind(asset_id, first.variant_id, "system",
                                    first.source_hash,
                                    adapter.compiler_profile(asset_id).profile_id)

    # ---------------- lookup ----------------

    def asset(self, asset_id: str) -> PromptAsset:
        entry = self._assets.get(asset_id)
        if entry is None:
            raise WorkbenchError(f"unknown asset: {asset_id}")
        return entry[1]

    def adapter_for(self, asset_id: str) -> BranchAdapter:
        entry = self._assets.get(asset_id)
        if entry is None:
            raise WorkbenchError(f"unknown asset: {asset_id}")
        return self.adapters[entry[0]]

    def pipelines(self) -> list[dict[str, Any]]:
        out = []
        for branch, adapter in self.adapters.items():
            p = adapter.describe_pipeline(None)
            out.append({"pipeline_id": p.pipeline_id, "branch": branch,
                        "version": p.version, "status": p.status,
                        "nodes_count": len(p.nodes)})
        return out

    def pipeline(self, branch: str, resolved_for: dict[str, str] | None = None) -> PipelineProjection:
        adapter = self.adapters.get(branch)
        if adapter is None:
            raise WorkbenchError(f"unknown branch: {branch}")
        return adapter.describe_pipeline(resolved_for)

    def node(self, branch: str, node_id: str, resolved_for: dict[str, str] | None = None) -> dict[str, Any]:
        proj = self.pipeline(branch, resolved_for)
        node = next((n for n in proj.nodes if n.node_id == node_id), None)
        if node is None:
            raise WorkbenchError(f"unknown node: {node_id}")
        payload: dict[str, Any] = {"node": node.to_public(), "branch": branch}

        if node.asset_id:
            payload["asset"] = self.asset_view(node.asset_id)
        else:
            payload["asset"] = None
            payload["editor_available"] = False
        payload["editor_available"] = bool(node.asset_id) and not (
            node.asset_id and self.asset(node.asset_id).reference_only)
        payload["effects"] = [
            c.to_public() for c in self.adapters[branch].semantic_controls()
            if c.subject == "asset" and c.control_id == (node.asset_id or "")
        ]
        return payload

    def asset_view(self, asset_id: str) -> dict[str, Any]:
        asset = self.asset(asset_id)
        adapter = self.adapter_for(asset_id)
        variants = self.store.list_variants(asset_id)
        active_id = self.store.active_variant_id(asset_id)
        active = next((v for v in variants if v.variant_id == active_id), None)
        contract = (adapter.contract_report(asset_id, active.source_text)
                    if active else None)
        return {
            "asset": asset.to_public(),
            "active_variant_id": active_id,
            "variants": [v.to_public() for v in variants],
            "contract": contract.to_public() if contract else None,
            "compiler_profile": adapter.compiler_profile(asset_id).to_public(),
            "fixtures": [f.__dict__ for f in adapter.fixtures(asset_id)],
        }

    def variant(self, asset_id: str, variant_id: str) -> PromptVariant:
        v = self.store.load_variant(asset_id, variant_id)
        if v is None:
            raise WorkbenchError(f"unknown variant: {variant_id}")
        return v

    def baseline(self, asset_id: str) -> PromptVariant | None:
        return next((v for v in self.store.list_variants(asset_id)
                     if v.state == "BASELINE" and v.origin == "baseline_file"),
                    next((v for v in self.store.list_variants(asset_id)
                          if v.state == "BASELINE"), None))

    # ---------------- editing ----------------

    def clone(self, asset_id: str, variant_id: str, author: str = "anonymous",
              title: str = "") -> PromptVariant:
        src = self.variant(asset_id, variant_id)
        new = PromptVariant(
            variant_id="v_" + uuid.uuid4().hex[:10],
            asset_id=asset_id, version=src.version, state="CANDIDATE_UNCHECKED",
            origin="user_edit", source_text=src.source_text,
            source_hash=src.source_hash, author=author, created_at=now_iso(),
            parent_variant_id=src.variant_id,
            title=title or f"копия {src.title or src.variant_id}",
        )
        return self.store.save_variant(new)

    def update_source(self, asset_id: str, variant_id: str, text: str,
                      actor: str = "anonymous", intent: str = "content") -> PromptVariant:
        """Server-side gate. The frontend is not trusted (C2).

        ``intent="content"`` (the default, and what the editor sends) requires
        every protected region to arrive byte-identical to the baseline. Any
        other mutation is refused here, before anything is written, and the
        refusal is recorded — a raw API call is no weaker than the UI.

        ``intent="contract_revision"`` is the only way to touch a protected
        contract region. It does not weaken anything: the edit is recorded as a
        contract revision and its drift fingerprint is then judged in full, so
        every newly introduced defect needs an explicit waiver (C1).
        """
        if intent not in {"content", "contract_revision"}:
            raise WorkbenchError(f"unknown edit intent: {intent}")

        v = self.variant(asset_id, variant_id)
        if v.state == "BASELINE":
            self._reject(asset_id, variant_id, actor, "baseline_not_editable")
            raise WorkbenchError("BASELINE не редактируется — сначала клонируйте")
        if v.state == "ACTIVE":
            self._reject(asset_id, variant_id, actor, "active_not_editable")
            raise WorkbenchError("ACTIVE вариант не редактируется — клонируйте")

        asset = self.asset(asset_id)
        base = self.baseline(asset_id)
        touched_protected: list[str] = []
        if base is not None:
            for region in asset.regions:
                if region.kind != "protected":
                    continue
                expected = region.extract(base.source_text)
                got = region.extract(text)
                if expected is None:
                    continue
                if got is None or got != expected:
                    touched_protected.append(region.name)
                    if intent == "content":
                        self._reject(asset_id, variant_id, actor,
                                     "protected_region_mutation",
                                     {"region": region.name, "reason": region.reason,
                                      "removed": got is None, "intent": intent})
                        raise WorkbenchError(
                            f"защищённая область «{region.name}» изменена или удалена: "
                            f"{region.reason}")

        if touched_protected:
            self.store.append_rejection({
                "code": "contract_revision_accepted", "asset_id": asset_id,
                "variant_id": variant_id, "actor": actor,
                "detail": {"regions": touched_protected, "intent": intent},
            })
        v.intent = intent
        v.contract_revision = bool(touched_protected)
        v.source_text = text
        v.source_hash = sha256_text(text)
        v.state = edit_resets_to(v.state)
        self.store.mark_evaluations_stale(variant_id)
        self._compiled_cache.clear()
        return self.store.save_variant(v)

    def _reject(self, asset_id: str, variant_id: str, actor: str,
                code: str, detail: dict[str, Any] | None = None) -> None:
        self.store.append_rejection({
            "code": code, "asset_id": asset_id, "variant_id": variant_id,
            "actor": actor, "detail": detail or {},
        })

    def grant_waiver(self, category: str, item: str, reason: str, adr_ref: str,
                     actor: str = "anonymous", asset_id: str = "*") -> dict[str, Any]:
        from .models import DriftWaiver
        w = self.store.grant_waiver(DriftWaiver(
            category=category, item=item, reason=reason, adr_ref=adr_ref,
            granted_by=actor, granted_at=now_iso(), asset_id=asset_id))
        return w.to_public()

    def diff(self, asset_id: str, base_id: str, candidate_id: str) -> dict[str, Any]:
        a = self.variant(asset_id, base_id)
        b = self.variant(asset_id, candidate_id)
        lines = list(difflib.unified_diff(
            a.source_text.splitlines(), b.source_text.splitlines(),
            fromfile=f"{a.variant_id}", tofile=f"{b.variant_id}", lineterm=""))
        added = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
        return {"base": base_id, "candidate": candidate_id,
                "unified": lines, "added": added, "removed": removed,
                "identical": a.source_text == b.source_text}

    # ---------------- validation ----------------

    def validate(self, asset_id: str, variant_id: str) -> dict[str, Any]:
        asset = self.asset(asset_id)
        adapter = self.adapter_for(asset_id)
        cand = self.variant(asset_id, variant_id)
        base = self.baseline(asset_id)
        cand_contract = adapter.contract_report(asset_id, cand.source_text)
        base_contract = (adapter.contract_report(asset_id, base.source_text)
                         if base else None)
        result = self.validator.validate(asset, cand, cand_contract, base,
                                         base_contract, self.store.read_waivers())

        self.store.append_evaluation(EvaluationRecord(
            variant_id=variant_id, asset_id=asset_id, kind="static",
            verdict=result.verdict,
            reasons=[i.message for i in result.issues],
            details=result.to_public(), source_hash=cand.source_hash,
            evaluated_at=now_iso()))

        if cand.state not in {"BASELINE", "ACTIVE"}:
            target = "STATIC_VALID" if result.verdict != "fail" else "INCOMPATIBLE"
            assert_not_baseline_removal(cand.state, target)
            assert_transition(cand.state, target)
            cand.state = target
            self.store.save_variant(cand)
        return {"variant": cand.to_public(), **result.to_public()}

    # ---------------- compilation ----------------

    def cache_key(self, asset_id: str, variant: PromptVariant, profile_id: str) -> CacheKey:
        return CacheKey(asset_id, variant.variant_id, variant.source_hash,
                        profile_id, self.store.activation_revision())

    def compile(self, asset_id: str, variant_id: str,
                fixture_id: str | None = None) -> dict[str, Any]:
        asset = self.asset(asset_id)
        adapter = self.adapter_for(asset_id)
        v = self.variant(asset_id, variant_id)
        profile = adapter.compiler_profile(asset_id)
        fixtures = adapter.fixtures(asset_id)
        fixture = next((f for f in fixtures if f.fixture_id == fixture_id), fixtures[0])

        key = self.cache_key(asset_id, v, profile.profile_id).as_str()
        compiled = self._compiled_cache.get(key)
        cache_hit = compiled is not None
        if compiled is None:
            step_id = (asset.used_by_steps or ["unknown"])[0]
            compiled = self.compiler.compile(adapter, asset, v, fixture, profile, step_id)
            self._compiled_cache[key] = compiled

        if v.state == "STATIC_VALID":
            assert_transition(v.state, "COMPILED")
            v.state = "COMPILED"
            self.store.save_variant(v)

        self.store.append_evaluation(EvaluationRecord(
            variant_id=variant_id, asset_id=asset_id, kind="compile",
            verdict="pass", compiled_hash=compiled.compiled_hash,
            source_hash=v.source_hash, evaluated_at=now_iso(),
            details={"cache_key": key, "cache_hit": cache_hit}))

        out = compiled.to_public()
        out["cache_key"] = key
        out["cache_hit"] = cache_hit
        out["variant"] = v.to_public()
        return out

    # ---------------- smoke + comparison ----------------

    def run_smoke(self, asset_id: str, variant_id: str,
                  fixture_id: str | None = None) -> SmokeResult:
        adapter = self.adapter_for(asset_id)
        v = self.variant(asset_id, variant_id)
        fixtures = adapter.fixtures(asset_id)
        fixture = next((f for f in fixtures if f.fixture_id == fixture_id), fixtures[0])
        compiled = self.compile(asset_id, variant_id, fixture.fixture_id)
        res = self.smoke.run(adapter, asset_id, v.source_text, fixture,
                             compiled["compiled_hash"])
        self.store.append_evaluation(EvaluationRecord(
            variant_id=variant_id, asset_id=asset_id, kind="smoke",
            verdict="pass" if res.ok else "fail", reasons=res.reasons,
            fixture_id=fixture.fixture_id, compiled_hash=res.compiled_hash,
            source_hash=v.source_hash, evaluated_at=now_iso(),
            details=res.to_public()))
        if res.ok and v.state == "COMPILED":
            assert_transition(v.state, "SMOKE_TESTED")
            v.state = "SMOKE_TESTED"
            self.store.save_variant(v)
        elif not res.ok and v.state not in {"BASELINE", "ACTIVE"}:
            v.state = "REJECTED"
            v.deprecation_reason = "; ".join(res.reasons) or "smoke failed"
            self.store.save_variant(v)
        return res

    def compare_with_baseline(self, asset_id: str, variant_id: str,
                              fixture_id: str | None = None) -> dict[str, Any]:
        base = self.baseline(asset_id)
        if base is None:
            raise WorkbenchError("baseline отсутствует")
        b = self.run_smoke(asset_id, base.variant_id, fixture_id)
        c = self.run_smoke(asset_id, variant_id, fixture_id)
        delta = smoke_compare(b, c)
        self.store.append_evaluation(EvaluationRecord(
            variant_id=variant_id, asset_id=asset_id, kind="compare",
            verdict="pass" if not delta["rollback_triggers"] else "fail",
            reasons=delta["rollback_triggers"], fixture_id=b.fixture_id,
            evaluated_at=now_iso(), details=delta))
        return {"baseline": b.to_public(), "candidate": c.to_public(), "delta": delta}

    def accept(self, asset_id: str, variant_id: str, actor: str = "anonymous") -> dict[str, Any]:
        v = self.variant(asset_id, variant_id)
        assert_transition(v.state, "ACCEPTED")
        v.state = "ACCEPTED"
        self.store.save_variant(v)
        return v.to_public()

    # ---------------- activation ----------------

    def activate(self, asset_id: str, variant_id: str, actor: str = "anonymous") -> dict[str, Any]:
        v = self.variant(asset_id, variant_id)
        assert_transition(v.state, "ACTIVE")
        adapter = self.adapter_for(asset_id)
        prev_id = self.store.active_variant_id(asset_id)
        binding = self.store.bind(asset_id, variant_id, actor, v.source_hash,
                                  adapter.compiler_profile(asset_id).profile_id)
        # A BASELINE keeps its BASELINE state forever: it is never consumed by
        # activation and can never be deleted. "Which variant is live" is
        # expressed by the binding, not by mutating the baseline's state.
        if v.state != "BASELINE":
            v.state = "ACTIVE"
            self.store.save_variant(v)
        if prev_id and prev_id != variant_id:
            prev = self.store.load_variant(asset_id, prev_id)
            if prev is not None and prev.state == "ACTIVE":
                prev.state = "DEPRECATED"
                self.store.save_variant(prev)
        # Cache identity already includes activation_revision; clearing is belt+braces.
        self._compiled_cache.clear()
        return {"binding": binding.to_public(), "variant": v.to_public()}

    def rollback(self, asset_id: str, actor: str = "anonymous") -> dict[str, Any]:
        acts = self.store.read_activations()
        current = acts["bindings"].get(asset_id) or {}
        prev_id = current.get("previous_variant_id")
        if not prev_id:
            base = self.baseline(asset_id)
            if base is None:
                raise WorkbenchError("нечего откатывать")
            prev_id = base.variant_id
        cur_id = current.get("variant_id")
        prev = self.variant(asset_id, prev_id)
        if prev.state == "DEPRECATED":
            assert_transition(prev.state, "ACTIVE")
            prev.state = "ACTIVE"
            self.store.save_variant(prev)
        # BASELINE keeps its state; the binding alone makes it live again.
        adapter = self.adapter_for(asset_id)
        binding = self.store.bind(asset_id, prev_id, actor, prev.source_hash,
                                  adapter.compiler_profile(asset_id).profile_id)
        if cur_id and cur_id != prev_id:
            cur = self.store.load_variant(asset_id, cur_id)
            if cur is not None:
                cur.state = "DEPRECATED"
                cur.rollback_of = prev_id
                cur.deprecation_reason = "rolled back"
                self.store.save_variant(cur)
        self._compiled_cache.clear()
        return {"binding": binding.to_public(), "active": prev.to_public()}

    # ==================================================================
    # STAGE 2 — RAG profiles
    # ==================================================================

    def bootstrap_rag(self) -> None:
        for branch, adapter in self.adapters.items():
            lister = getattr(adapter, "rag_profiles", None)
            if lister is None:
                continue
            for profile in lister():
                self._rag_engines[profile.profile_id] = branch
                if self.store.load_rag_profile(profile.profile_id) is None:
                    profile.created_at = profile.created_at or now_iso()
                    self.store.save_rag_profile(profile)
                if self.store.active_rag_profile_id(profile.engine_id) is None:
                    self.store.bind_rag(profile.engine_id, profile.profile_id,
                                        "system", profile.source_hash())

    def rag_adapter_for(self, profile_id: str):
        branch = self._rag_engines.get(profile_id)
        if branch is None:
            raise WorkbenchError(f"unknown rag profile: {profile_id}")
        return self.adapters[branch]

    def rag_profile(self, profile_id: str) -> RAGProfile:
        p = self.store.load_rag_profile(profile_id)
        if p is None:
            raise WorkbenchError(f"unknown rag profile: {profile_id}")
        return p

    def rag_view(self, profile_id: str) -> dict[str, Any]:
        profile = self.rag_profile(profile_id)
        adapter = self.rag_adapter_for(profile_id)
        siblings = self.store.list_rag_profiles(profile.engine_id)
        active = self.store.active_rag_profile_id(profile.engine_id)
        return {
            "profile": profile.to_public(),
            "active_profile_id": active,
            "profiles": [p.to_public() for p in siblings],
            "parameters": [p.to_public() for p in adapter.rag_parameters(profile.engine_id)],
            "missing_capabilities": [m.to_public() for m in profile.missing_capabilities],
            "fixtures": [f.__dict__ for f in adapter.rag_fixtures(profile.engine_id)],
        }

    def clone_rag(self, profile_id: str, actor: str = "anonymous") -> RAGProfile:
        src = self.rag_profile(profile_id)
        new = RAGProfile(**{**asdict_rag(src),
                            "profile_id": src.profile_id.rsplit(".", 1)[0] + "." +
                                          uuid.uuid4().hex[:8],
                            "version": _bump(src.version),
                            "state": "CANDIDATE_UNCHECKED",
                            "parent_profile_id": src.profile_id,
                            "parent_version": src.version,
                            "author": actor,
                            "created_at": now_iso(),
                            "title": f"кандидат от {src.profile_id}"})
        new.missing_capabilities = list(src.missing_capabilities)
        self._rag_engines[new.profile_id] = self._rag_engines[profile_id]
        return self.store.save_rag_profile(new)

    def update_rag(self, profile_id: str, changes: dict[str, Any],
                   actor: str = "anonymous") -> RAGProfile:
        """Only real, tunable parameters may move. NOT_IMPLEMENTED never can."""
        p = self.rag_profile(profile_id)
        if p.state in {"BASELINE", "ACTIVE"}:
            self._reject(profile_id, profile_id, actor, "rag_profile_not_editable")
            raise WorkbenchError(f"{p.state} профиль не редактируется — клонируйте")
        adapter = self.rag_adapter_for(profile_id)
        tunable = {q.parameter_id: q for q in adapter.rag_parameters(p.engine_id)}
        missing = {m.capability_id for m in p.missing_capabilities}

        for key, value in changes.items():
            if key.split(".")[-1] in missing or key in missing:
                self._reject(profile_id, profile_id, actor,
                             "not_implemented_parameter", {"key": key})
                raise WorkbenchError(
                    f"{key} — NOT_IMPLEMENTED в этом рантайме, активировать нельзя")
            spec = tunable.get(key)
            if spec is None:
                raise WorkbenchError(f"неизвестный параметр профиля: {key}")
            if not spec.runtime_mutable:
                self._reject(profile_id, profile_id, actor,
                             "immutable_parameter", {"key": key})
                raise WorkbenchError(f"{key} не изменяем в рантайме")
            section, name = key.split(".", 1)
            getattr(p, section)[name] = value

        p.state = "CANDIDATE_UNCHECKED"
        return self.store.save_rag_profile(p)

    def validate_rag(self, profile_id: str) -> dict[str, Any]:
        p = self.rag_profile(profile_id)
        adapter = self.rag_adapter_for(profile_id)
        base = self.rag_baseline(p.engine_id)
        issues: list[dict[str, Any]] = []

        specs = {q.parameter_id: q for q in adapter.rag_parameters(p.engine_id)}
        for key, value in p.tunable().items():
            spec = specs.get(key)
            if spec is None:
                continue
            rng = spec.value_range or {}
            if isinstance(rng, dict) and isinstance(value, (int, float)):
                if "min" in rng and value < rng["min"]:
                    issues.append({"code": "below_min", "severity": "error",
                                   "message": f"{key} < {rng['min']}"})
                if "max" in rng and value > rng["max"]:
                    issues.append({"code": "above_max", "severity": "error",
                                   "message": f"{key} > {rng['max']}"})

        # S2.9 — protected contracts must not move
        if base is not None:
            for surface in base.protected_contracts:
                if surface not in p.protected_contracts:
                    issues.append({"code": "protected_contract_dropped",
                                   "severity": "error",
                                   "message": f"снят защищённый контракт {surface}"})
            if p.contract_version != base.contract_version:
                issues.append({"code": "contract_version_changed", "severity": "error",
                               "message": "смена contract_version требует отдельной "
                                          "миграции, а не правки параметра"})

        verdict = "fail" if any(i["severity"] == "error" for i in issues) else "pass"
        if p.state not in {"BASELINE", "ACTIVE"}:
            target = "STATIC_VALID" if verdict == "pass" else "INCOMPATIBLE"
            assert_rag_transition(p.state, target)
            p.state = target
            self.store.save_rag_profile(p)
        self.store.append_evaluation(EvaluationRecord(
            variant_id=profile_id, asset_id=p.engine_id, kind="rag_static",
            verdict=verdict, reasons=[i["message"] for i in issues],
            source_hash=p.source_hash(), evaluated_at=now_iso(),
            details={"issues": issues}))
        return {"profile": p.to_public(), "verdict": verdict, "issues": issues}

    def rag_baseline(self, engine_id: str) -> RAGProfile | None:
        return next((p for p in self.store.list_rag_profiles(engine_id)
                     if p.state == "BASELINE"), None)

    def retrieval_test(self, profile_id: str, fixture_id: str | None = None,
                       run_id: str | None = None) -> dict[str, Any]:
        p = self.rag_profile(profile_id)
        adapter = self.rag_adapter_for(profile_id)
        fixtures = adapter.rag_fixtures(p.engine_id)
        fixture = next((f for f in fixtures if f.fixture_id == fixture_id), fixtures[0])
        rid = run_id or ("ragtest_" + uuid.uuid4().hex[:10])
        node_id = str(p.runtime_binding.get("node_id", "retrieve_initial_context"))
        event = adapter.run_retrieval(p, fixture, rid, node_id)
        self.store.append_retrieval_event(event)
        if p.state == "STATIC_VALID":
            assert_rag_transition(p.state, "TESTED")
            p.state = "TESTED"
            self.store.save_rag_profile(p)
        return {"event": event.to_public(), "fixture": fixture.__dict__}

    def explain_chunk(self, run_id: str, chunk_id: str) -> dict[str, Any]:
        events = self.store.retrieval_events(run_id=run_id)
        if not events:
            raise WorkbenchError(f"нет retrieval-событий для {run_id}")
        return explain_candidate(events[-1], chunk_id)

    def compare_rag(self, profile_id: str,
                    fixture_id: str | None = None) -> dict[str, Any]:
        cand = self.rag_profile(profile_id)
        base = self.rag_baseline(cand.engine_id)
        if base is None:
            raise WorkbenchError("baseline RAG-профиль отсутствует")
        b = self.retrieval_test(base.profile_id, fixture_id)
        c = self.retrieval_test(profile_id, fixture_id)
        adapter = self.rag_adapter_for(profile_id)
        fixtures = adapter.rag_fixtures(cand.engine_id)
        fixture = next((f for f in fixtures if f.fixture_id == fixture_id), fixtures[0])
        delta = compare_retrieval(
            _event_from_public(b["event"]), _event_from_public(c["event"]))
        self.store.append_evaluation(EvaluationRecord(
            variant_id=profile_id, asset_id=cand.engine_id, kind="rag_compare",
            verdict="pass", reasons=list(delta["verdicts"]),
            fixture_id=fixture.fixture_id, evaluated_at=now_iso(), details=delta))
        return {"baseline": b["event"], "candidate": c["event"], "delta": delta}

    def accept_rag(self, profile_id: str) -> dict[str, Any]:
        p = self.rag_profile(profile_id)
        assert_rag_transition(p.state, "ACCEPTED")
        p.state = "ACCEPTED"
        return self.store.save_rag_profile(p).to_public()

    def activate_rag(self, profile_id: str, actor: str = "anonymous") -> dict[str, Any]:
        p = self.rag_profile(profile_id)
        assert_rag_transition(p.state, "ACTIVE")
        prev_id = self.store.active_rag_profile_id(p.engine_id)
        binding = self.store.bind_rag(p.engine_id, profile_id, actor, p.source_hash())
        if p.state != "BASELINE":
            p.state = "ACTIVE"
            self.store.save_rag_profile(p)
        if prev_id and prev_id != profile_id:
            prev = self.store.load_rag_profile(prev_id)
            if prev is not None and prev.state == "ACTIVE":
                prev.state = "DEPRECATED"
                self.store.save_rag_profile(prev)
        return {"binding": binding, "profile": p.to_public()}

    def rollback_rag(self, engine_id: str, actor: str = "anonymous") -> dict[str, Any]:
        acts = self.store.read_activations()
        current = (acts.get("rag_bindings") or {}).get(engine_id) or {}
        prev_id = current.get("previous_profile_id")
        if not prev_id:
            base = self.rag_baseline(engine_id)
            if base is None:
                raise WorkbenchError("нечего откатывать")
            prev_id = base.profile_id
        cur_id = current.get("profile_id")
        prev = self.rag_profile(prev_id)
        if prev.state == "DEPRECATED":
            assert_rag_transition(prev.state, "ACTIVE")
            prev.state = "ACTIVE"
            self.store.save_rag_profile(prev)
        binding = self.store.bind_rag(engine_id, prev_id, actor, prev.source_hash())
        if cur_id and cur_id != prev_id:
            cur = self.store.load_rag_profile(cur_id)
            if cur is not None:
                cur.state = "DEPRECATED"
                cur.rollback_of = prev_id
                self.store.save_rag_profile(cur)
        return {"binding": binding, "active": prev.to_public()}

    # ==================================================================
    # STAGE 3 — unified snapshot + production runtime binding
    # ==================================================================

    def build_run_configuration(self, branch: str) -> RunConfigurationSnapshot:
        """T4 — one immutable configuration picture for one run."""
        adapter = self.adapters[branch]
        acts = self.store.read_activations()
        revision = int(acts.get("revision", 0))
        proj = adapter.describe_pipeline(None)

        prompt_bindings = []
        for asset_id, (b, asset) in self._assets.items():
            if b != branch:
                continue
            vid = self.store.active_variant_id(asset_id)
            if not vid:
                continue
            v = self.store.load_variant(asset_id, vid)
            if v is None:
                continue
            profile = adapter.compiler_profile(asset_id)
            prompt_bindings.append({
                "asset_id": asset_id, "variant_id": v.variant_id,
                "source_hash": v.source_hash, "version": v.version,
                "compiler_profile": profile.profile_id,
                "compiled_hash": None,   # filled lazily when the asset compiles
            })

        rag_bindings = []
        for engine_id, binding in (acts.get("rag_bindings") or {}).items():
            p = self.store.load_rag_profile(binding.get("profile_id") or "")
            if p is None:
                continue
            rag_bindings.append({
                "engine_id": engine_id, "rag_profile_id": p.profile_id,
                "version": p.version, "profile_hash": p.source_hash(),
                "index_version": p.version,
                "corpus_versions": p.source_bindings.get("namespace")
                                   or p.source_bindings.get("corpus_root"),
            })

        # A15-1 — the branch resolves provider/model/parameters once, here, and
        # the run is pinned to that. A branch that cannot resolve them says so
        # rather than letting the snapshot claim a binding it does not have.
        resolve_models = getattr(adapter, "effective_model_bindings", None)
        if resolve_models is not None:
            model_bindings = list(resolve_models())
        else:
            model_bindings = [{
                "role": None,
                "provider": None, "model": None,
                "resolution": "NOT_APPLICABLE",
                "reason": f"branch {branch} declares no model boundary",
                "evidence_grade": "MEASURED",
            }]

        # A15-2 — semantic hybrids are configuration, so they are frozen too.
        resolve_controls = getattr(adapter, "effective_semantic_controls", None)
        semantic_control_bindings = (list(resolve_controls())
                                     if resolve_controls is not None else [])

        resolve_algorithms = getattr(adapter, "algorithm_bindings", None)
        algorithm_bindings = (list(resolve_algorithms())
                              if resolve_algorithms is not None else [])

        # A15-3 — where the run's artefacts land, recorded with the run.
        resolve_storage = getattr(adapter, "storage_binding", None)
        storage_binding = (dict(resolve_storage()) if resolve_storage is not None
                           else {"runs_dir": None, "resolved_from": "NONE",
                                 "cwd_dependent": False,
                                 "evidence_grade": "MEASURED"})

        contract_bindings = [
            {"contract_id": a.output_object or a.asset_id,
             "version": a.contract_version,
             "hash": sha256_text(f"{a.asset_id}:{a.contract_version}")}
            for _, (b, a) in self._assets.items() if b == branch and a.output_object
        ]
        for rb in rag_bindings:
            p = self.store.load_rag_profile(rb["rag_profile_id"])
            for surface in (p.protected_contracts if p else []):
                contract_bindings.append({
                    "contract_id": surface, "version": p.contract_version,
                    "hash": sha256_text(f"{surface}:{p.contract_version}")})

        return RunConfigurationSnapshot.build(
            activation_revision=revision, created_at=now_iso(),
            pipeline={"pipeline_id": proj.pipeline_id, "version": proj.version,
                      "hash": sha256_text(f"{proj.pipeline_id}:{proj.version}")},
            prompt_bindings=prompt_bindings,
            rag_bindings=rag_bindings,
            model_bindings=model_bindings,
            algorithm_bindings=algorithm_bindings,
            orchestration_binding={"profile_id": proj.pipeline_id,
                                   "version": proj.version},
            contract_bindings=contract_bindings,
            semantic_control_bindings=semantic_control_bindings,
            storage_binding=storage_binding,
        )

    def install_runtime_resolver(self, resolver: Any) -> None:
        """Attach the Workbench resolver to the production runtime seam."""
        self._runtime_resolver = resolver

    def start_production_run(self, branch: str, text: str, mode: str = "fast",
                             actor: str = "anonymous") -> dict[str, Any]:
        """T2/T7 — a normal run through the real entrypoint, under a frozen
        configuration snapshot, with the Workbench resolver supplying effective
        retrieval parameters."""
        adapter = self.adapters[branch]
        entry = getattr(adapter, "production_entrypoint", None)
        if entry is None:
            raise WorkbenchError(f"branch {branch} exposes no production entrypoint")

        snapshot = self.build_run_configuration(branch)
        resolver = getattr(self, "_runtime_resolver", None)
        if resolver is None:
            raise WorkbenchError("runtime resolver not installed")
        resolver.calls.clear()

        # The core must not import any branch runtime, so installing the
        # resolver into the production seam is the adapter's job.
        bind = getattr(adapter, "bind_runtime_resolver", None)
        unbind = getattr(adapter, "unbind_runtime_resolver", None)
        if bind is None or unbind is None:
            raise WorkbenchError(f"branch {branch} cannot bind a runtime resolver")
        bind(resolver)
        try:
            with resolver.pinned(snapshot.as_resolver_view()):
                observed = entry(text=text, mode=mode)
        finally:
            unbind()

        effective = {}
        for b in snapshot.rag_bindings:
            eid = b["engine_id"]
            effective[eid] = {
                "top_k": resolver.effective(eid, "top_k"),
                "rag_profile_id": b["rag_profile_id"],
                "version": b["version"],
            }

        executions, edges = self._node_executions(observed, snapshot, resolver)

        trace = {
            "run_id": observed["run_id"],
            "branch": branch,
            "kind": "PRODUCTION_RUNTIME_VALIDATION",
            "entrypoint": observed["entrypoint"],
            "started_at": snapshot.created_at,
            "actor": actor,
            "run_configuration_snapshot": snapshot.to_public(),
            "effective_retrieval": effective,
            "resolver_calls": list(resolver.calls),
            "node_executions": executions,
            "edge_telemetry": edges,
            "production": observed,
        }
        self.store.write_run(observed["run_id"], trace)
        return trace

    # ---------------- branch capability passthrough ----------------
    #
    # The core does not know what these mean; it only knows that an adapter may
    # or may not offer them. Nothing here is branch-specific.

    def branch_capabilities(self, branch: str) -> dict[str, bool]:
        a = self.adapters.get(branch)
        if a is None:
            raise WorkbenchError(f"unknown branch: {branch}")
        return {cap: hasattr(a, cap) for cap in (
            "state_projection", "branch_invariants", "contract_bindings",
            "runtime_profiles", "declarative_snapshot", "branch_readiness",
            "production_entrypoint", "rag_profiles", "list_assets",
        )}

    def branch_feature(self, branch: str, name: str, *args, **kwargs) -> Any:
        a = self.adapters.get(branch)
        if a is None:
            raise WorkbenchError(f"unknown branch: {branch}")
        fn = getattr(a, name, None)
        if fn is None:
            raise WorkbenchError(f"branch {branch} does not offer {name}")
        result = fn(*args, **kwargs)
        if hasattr(result, "to_public"):
            return result.to_public()
        if isinstance(result, list):
            return [r.to_public() if hasattr(r, "to_public") else r for r in result]
        return result

    def branches(self) -> list[dict[str, Any]]:
        out = []
        for branch, adapter in self.adapters.items():
            proj = adapter.describe_pipeline(None)
            caps = self.branch_capabilities(branch)
            out.append({
                "branch": branch,
                "pipeline_id": proj.pipeline_id,
                "version": proj.version,
                "status": proj.status,
                "nodes": len(proj.nodes),
                "capabilities": caps,
                "has_live_runtime": bool(getattr(adapter, "PRODUCTION_ENTRYPOINT", None)),
                "generation": getattr(adapter, "generation", None),
                "owner": getattr(adapter, "owner", None),
            })
        return out

    # ---------------- T6: unified telemetry projection ----------------

    def _node_executions(self, observed: dict[str, Any],
                         snapshot: RunConfigurationSnapshot,
                         resolver: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Project the production run's own trace into node_execution records.

        Everything comes from the run's ``events.jsonl`` or from resolver
        observations. Cost is UNKNOWN: there is no pricing profile in this
        runtime, and inventing one would be worse than admitting it.
        """
        import json as _json
        from pathlib import Path as _Path

        run_id = observed["run_id"]
        events: list[dict[str, Any]] = []
        trace_dir = _Path(observed.get("trace_dir") or "")
        ev_path = trace_dir / "events.jsonl"
        if ev_path.exists():
            for line in ev_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        events.append(_json.loads(line))
                    except _json.JSONDecodeError:
                        continue

        def of(kind: str) -> list[dict[str, Any]]:
            return [e for e in events if e.get("kind") == kind]

        rag_binding = {b["engine_id"]: b for b in snapshot.rag_bindings}
        prompt_binding = {b["asset_id"]: b for b in snapshot.prompt_bindings}
        no_cost = {"value": None, "currency": None, "evidence_grade": "UNKNOWN",
                   "note": "pricing profile отсутствует в этом рантайме"}

        executions: list[dict[str, Any]] = []

        for e in of("situation"):
            payload = e.get("payload") or e
            executions.append({
                "run_id": run_id, "node_id": "analyze_situation",
                "node_kind": "MODEL_CALL",
                "input_object_ids": ["RawInput"],
                "output_object_ids": ["SituationAnalysis"],
                "prompt_binding": prompt_binding.get("zarathustra.03_scene_reading"),
                "rag_binding": None,
                "model_binding": {"provider": payload.get("reader_provider"),
                                  "grade": "MEASURED"},
                "algorithm_binding": None,
                "context_tokens": None, "input_tokens": None, "output_tokens": None,
                "retries": 0, "cache_state": "n/a", "cost": no_cost,
                "evidence": "trace.situation",
            })

        for i, e in enumerate(of("cultural_context_injected")):
            payload = e.get("payload") or e
            cards = payload.get("cards") or []
            executions.append({
                "run_id": run_id, "node_id": "cultural_context", "node_kind": "RAG",
                "turn_index": i,
                "input_object_ids": ["SituationAnalysis", "RoutingDecision"],
                "output_object_ids": [c.get("card_id") for c in cards],
                "prompt_binding": None,
                "rag_binding": rag_binding.get("zarathustra.cultural_cards_bm25"),
                "model_binding": None,
                "algorithm_binding": {"required_function": payload.get("required_function")},
                "retrieved_chunks": len(cards),
                "retrieval_candidates": None,
                "effective_top_k": resolver.effective(
                    "zarathustra.cultural_cards_bm25", "top_k"),
                "cache_state": "index_process_cache",
                "retries": 0, "cost": no_cost,
                "evidence": "trace.cultural_context_injected",
            })

        for i, e in enumerate(of("turn")):
            payload = e.get("payload") or e
            executions.append({
                "run_id": run_id, "node_id": "persona_turn", "node_kind": "MODEL_CALL",
                "turn_index": payload.get("turn_index", i),
                "input_object_ids": ["EvidenceChunk[]", "RetrievedCard[]"],
                "output_object_ids": ["TurnRecord"],
                "prompt_binding": prompt_binding.get("zarathustra.05_move_assignment"),
                "rag_binding": None,
                "model_binding": {"provider": payload.get("model_provider"),
                                  "grade": "MEASURED"},
                "persona_id": payload.get("persona_id"),
                "operation": payload.get("operation"),
                "retries": 0, "cost": no_cost,
                "evidence": "trace.turn",
            })

        for i, e in enumerate(of("dispute_assessment")):
            executions.append({
                "run_id": run_id, "node_id": "assess_turn",
                "node_kind": "DETERMINISTIC", "turn_index": i,
                "input_object_ids": ["TurnRecord"],
                "output_object_ids": ["DisputeAssessment"],
                "prompt_binding": None, "rag_binding": None, "model_binding": None,
                "cost": no_cost, "evidence": "trace.dispute_assessment",
            })

        # Edge telemetry describes the object that actually crossed the boundary.
        edges: list[dict[str, Any]] = []
        for ex in executions:
            if ex["node_id"] != "cultural_context":
                continue
            ids = [c for c in ex["output_object_ids"] if c]
            edges.append({
                "edge_id": "cultural_context->persona_turn",
                "turn_index": ex.get("turn_index"),
                "object_type": "RetrievedCard[]",
                "object_ids": ids,
                "chunk_count": len(ids),
                "hash": sha256_text("|".join(ids))[:24],
                "bytes": None, "tokens": None,
                "grade": "MEASURED" if ids else "UNKNOWN",
            })
        return executions, edges

    # ---------------- integration smoke (C3) ----------------

    def run_integration_smoke(self, branch: str, asset_id: str,
                              fixture_id: str | None = None,
                              client: Any | None = None,
                              actor: str = "anonymous") -> dict[str, Any]:
        """INTEGRATION_SMOKE — the whole external chain, one run, one snapshot.

        ACTIVE variant -> ActivationBinding -> resolver -> compiler ->
        immutable snapshot -> branch runtime entry point -> real model
        invocation boundary (capture provider) -> real parser -> contract
        validation -> evaluation -> RunTrace.
        """
        adapter = self.adapter_for(asset_id)
        runner = getattr(adapter, "integration_run", None)
        if runner is None:
            raise WorkbenchError(f"branch {branch} has no integration path")

        snapshot = self.store.take_snapshot()
        entry = snapshot.entry(asset_id) or {}
        variant_id = entry.get("variant_id")
        if not variant_id:
            raise WorkbenchError("нет активного варианта для ассета")
        v = self.variant(asset_id, variant_id)

        fixtures = adapter.fixtures(asset_id)
        fixture = next((f for f in fixtures if f.fixture_id == fixture_id), fixtures[0])
        profile = adapter.compiler_profile(asset_id)
        compiled = self.compiler.compile(
            adapter, self.asset(asset_id), v, fixture, profile,
            (self.asset(asset_id).used_by_steps or ["unknown"])[0])

        from .smoke import CaptureClient
        capture = client or CaptureClient(canned=_CANNED_SCENE_JSON)
        result = runner(asset_id, v.source_text, fixture, capture)

        emitted = getattr(capture, "captured", [])
        emitted_system = emitted[-1]["messages"][0]["content"] if emitted else ""
        payload_matches_compiled = emitted_system == compiled.system_text

        ok, reasons, _ = adapter.validate_output(asset_id, _CANNED_SCENE_JSON)
        parsed = result["situation"]
        for f in result["consumed_fields"]:
            if f not in parsed:
                ok, reasons = False, reasons + [f"parser_dropped:{f}"]

        run_id = "wbint_" + uuid.uuid4().hex[:12]
        trace = {
            "run_id": run_id, "branch": branch, "kind": "INTEGRATION_SMOKE",
            "started_at": now_iso(), "actor": actor,
            "activation_snapshot": snapshot.to_public(),
            "nodes": [{
                "node_id": "analyze_situation", "asset_id": asset_id,
                "variant_id": v.variant_id, "source_hash": v.source_hash,
                "compiled_hash": compiled.compiled_hash, "profile_id": profile.profile_id,
                "fixture_id": fixture.fixture_id,
                "provider": "capture", "model": "capture",
                "emitted_payload_matches_compiled": payload_matches_compiled,
                "emitted_settings": emitted[-1]["settings"] if emitted else {},
                "parsed": parsed, "output_valid": ok, "output_reasons": reasons,
                "measured": True,
            }],
        }
        self.store.write_run(run_id, trace)
        self.store.append_evaluation(EvaluationRecord(
            variant_id=v.variant_id, asset_id=asset_id, kind="integration_smoke",
            verdict="pass" if (ok and payload_matches_compiled) else "fail",
            reasons=reasons, fixture_id=fixture.fixture_id,
            compiled_hash=compiled.compiled_hash, source_hash=v.source_hash,
            evaluated_at=now_iso(),
            details={"payload_matches_compiled": payload_matches_compiled}))
        return trace

    # ---------------- runs ----------------

    def start_run(self, branch: str, asset_id: str,
                  fixture_id: str | None = None, actor: str = "anonymous") -> dict[str, Any]:
        """Execute the node under an immutable activation snapshot."""
        snapshot: ActivationSnapshot = self.store.take_snapshot()
        entry = snapshot.entry(asset_id) or {}
        variant_id = entry.get("variant_id")
        if not variant_id:
            raise WorkbenchError("нет активного варианта для ассета")
        v = self.variant(asset_id, variant_id)
        adapter = self.adapter_for(asset_id)
        fixtures = adapter.fixtures(asset_id)
        fixture = next((f for f in fixtures if f.fixture_id == fixture_id), fixtures[0])

        compiled = self.compiler.compile(
            adapter, self.asset(asset_id), v, fixture,
            adapter.compiler_profile(asset_id),
            (self.asset(asset_id).used_by_steps or ["unknown"])[0])
        res = self.smoke.run(adapter, asset_id, v.source_text, fixture,
                             compiled.compiled_hash)

        run_id = "wbrun_" + uuid.uuid4().hex[:12]

        # ---- RAG under the SAME immutable snapshot -----------------------
        rag_nodes: list[dict[str, Any]] = []
        rag_snapshot: dict[str, Any] = {}
        rag_lister = getattr(adapter, "rag_profiles", None)
        if rag_lister is not None:
            acts = self.store.read_activations()
            for engine_id, binding in (acts.get("rag_bindings") or {}).items():
                pid = binding.get("profile_id")
                if not pid:
                    continue
                profile = self.store.load_rag_profile(pid)
                if profile is None:
                    continue
                rag_snapshot[engine_id] = {
                    "profile_id": pid, "version": profile.version,
                    "source_hash": profile.source_hash(),
                }
                rag_fixtures = adapter.rag_fixtures(engine_id)
                rag_fx = rag_fixtures[0]
                node_id = str(profile.runtime_binding.get("node_id", "retrieval"))
                event = adapter.run_retrieval(profile, rag_fx, run_id, node_id)
                self.store.append_retrieval_event(event)
                included = event.included()
                rag_nodes.append({
                    "node_id": node_id, "kind": "RAG",
                    "rag_profile_id": pid, "rag_profile_version": profile.version,
                    "rag_profile_hash": profile.source_hash(),
                    "index_id": event.index_id, "index_version": event.index_version,
                    "corpus_ids": event.corpus_ids,
                    "fixture_id": rag_fx.fixture_id,
                    "retrieved": [{"chunk_id": c.chunk_id, "chunk_hash": c.chunk_hash,
                                   "rank": c.rank, "score": c.score,
                                   "locator": c.locator,
                                   "included_in_context": c.included_in_context}
                                  for c in event.candidates],
                    "context_identity": _context_identity(included),
                    "context_tokens": sum(c.token_count or 0 for c in included),
                    "context_bytes": sum(c.byte_count or 0 for c in included),
                    "considered_count": event.considered_count,
                    "returned_count": event.returned_count,
                    "latency_ms": event.latency_ms,
                    "cache_state": event.cache_state,
                    "measured": True,
                })

        trace = {
            "run_id": run_id,
            "branch": branch,
            "started_at": now_iso(),
            "actor": actor,
            "activation_snapshot": snapshot.to_public(),
            "rag_snapshot": rag_snapshot,
            "rag_nodes": rag_nodes,
            "nodes": [{
                "node_id": (self.asset(asset_id).used_by_steps or ["unknown"])[0],
                "asset_id": asset_id,
                "variant_id": v.variant_id,
                "source_hash": v.source_hash,
                "compiled_hash": compiled.compiled_hash,
                "profile_id": compiled.profile_id,
                "fixture_id": fixture.fixture_id,
                "provider": res.provider, "model": res.model,
                "tokens_in": res.tokens_in, "tokens_out": res.tokens_out,
                "latency_ms": res.latency_ms,
                "output_valid": res.ok, "output_reasons": res.reasons,
                "output_text": res.raw_text,
                "measured": True,
            }],
        }
        self.store.write_run(run_id, trace)
        return trace
