"""Socrates G-S24 structural BranchAdapter.

Reads the READ-ONLY G-S24 mirror and projects it through the universal
WorkbenchCore types. It never executes anything: G-S24 is a host-neutral
declarative package, and the README states plainly that live host execution is
G-S26. Nothing here claims otherwise.

Dependency invariant: this module may import ``workbench_core`` and read the
Socrates declarative package. ``workbench_core`` imports neither.

WRITE BOUNDARY: the Socrates package is owned by LOCAL_SOCRATES. This adapter
opens the mirror read-only, creates no candidate inside it, and reports source
defects instead of repairing them.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from workbench_core.branch import (
    BranchInvariant,
    EdgeProjection,
    Fixture,
    NodeProjection,
    PipelineProjection,
    Readiness,
    SemanticControl,
    StateNode,
    StateProjection,
    StateTransition,
)
from workbench_core.models import (
    CompilerProfile,
    ContractReport,
    DriftFingerprint,
    PromptAsset,
)

MIRROR = Path(__file__).resolve().parents[2] / "socrates_mirror"

#: Human-readable step labels. Taken from the step contract filenames declared
#: in the byte-exact pipeline.yaml, not invented.
STEP_LABELS = {
    "S0": "Приём и юрисдикция контекста",
    "S1": "Сцена и телос",
    "S2": "Проверка захвата давлением/ролью",
    "S3": "Происхождение, статус, полномочия",
    "S4": "Объявление операции и применимость",
    "S5": "Конфигурация внимания/памяти/воображения",
    "S6": "Человеческая операция и владение",
    "S7": "Рефлексивный отход / совет",
    "S8": "Выбор вмешательства",
    "S9": "Исполнение через Тинкуй",
    "S10": "Контраст, provenance, запись состояния, открытая петля",
}


def _load(rel: str) -> dict[str, Any]:
    p = MIRROR / rel
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


class SocratesBranchAdapter:
    branch_id = "socrates"
    generation = "G-S24"
    owner = "LOCAL_SOCRATES"

    #: This adapter's ``PRODUCTION_ENTRYPOINT`` intentionally stays ``None``:
    #: the Workbench's generic ``start_production_run`` expects a
    #: ``(text, mode)`` entrypoint, which the Socrates runtime does not have
    #: (it takes a :class:`SocratesRunConfiguration`). Socrates has its own
    #: HTTP entrypoint at ``POST /api/workbench/socrates/run``. The branch
    #: remains a declarative surface in Workbench; live runs go through the
    #: Socrates endpoint and the Arena SocratesParticipant.
    PRODUCTION_ENTRYPOINT = None
    LIVE_RUNTIME_STATUS = "PARTIAL_LIVE_ORCHESTRATION_DETERMINISTIC"

    def __init__(self) -> None:
        self.pipeline = _load("pipeline.yaml")
        self.state_model = _load("extracted/state_model.extracted.yaml")
        self.facts = _load("extracted/branch_facts.extracted.yaml")
        self.manifest = _load("source_manifest.yaml")

    # ------------------------------------------------------------------
    # A4 — node kind from the step spec, not from the name
    # ------------------------------------------------------------------

    def _kind_and_evidence(self, step_id: str) -> tuple[str, str]:
        """Classify by what the declarative package actually says.

        A declared prompt binding does NOT by itself make a step a MODEL_CALL:
        every S0-S10 step is a contract-driven orchestration composite, so the
        honest default is HYBRID, narrowed only where the package is explicit.
        """
        bindings = {tuple(e["steps"]): e for e in
                    (self.facts.get("prompt_bindings", {}).get("entries") or [])}
        binding = next((e for k, e in bindings.items() if step_id in k), None)

        if step_id == "S6":
            return "HUMAN_GATE", (
                "state_model: S6 → PAUSED_AWAITING_HUMAN_INPUT when "
                "human_binding_or_user_only_evidence_required; component "
                "binding twin_runtime OWNERSHIP_SLICE_ONLY")
        if step_id == "S8":
            return "ROUTER", (
                "pipeline.yaml: S9 conditional_on "
                "InterventionSelection.execution_status == EXECUTE — S8 decides "
                "the route, including not executing at all")
        if step_id == "S9":
            return "OTHER", (
                "binding TINKUY_EXECUTION_ADAPTER, concrete host binding "
                "deferred to G-S26 — execution kind is not yet decidable")
        if step_id == "S10":
            return "STORE", (
                "binding CONTRACT_DRIVEN_PROVENANCE_AND_WRITE_GATE; "
                "state_and_memory/state_write_binding.yaml")
        if step_id == "S7":
            return "HYBRID", (
                "optional: true; council/arbitration by reference to G-S23; "
                "forbidden ArbitrationRecord → HUMAN binding")
        # S0-S5
        return "HYBRID", (
            f"prompt binding = {binding['binding'] if binding else 'unknown'}; "
            "orchestration composite over shared substrate, no single "
            "model call declared")

    # ------------------------------------------------------------------
    # A5 — readiness
    # ------------------------------------------------------------------

    def _readiness(self, step_id: str) -> Readiness:
        entries = self.facts.get("prompt_bindings", {}).get("entries") or []
        binding = next((e for e in entries if step_id in e.get("steps", [])), None)
        body = (binding or {}).get("body_status", "UNKNOWN")

        if body == "MIRRORED_READ_ONLY":
            # The body exists and is readable, so the operator can explain it.
            # Rewriting still waits: no runtime consumes it, and it is owned by
            # LOCAL_SOCRATES. PROMPT_BODY_READY says exactly that much.
            return Readiness(
                "PROMPT_BODY_READY",
                "тело промпта втянуто и читаемо; переписывание ждёт рантайма",
                expected_in="G-S26",
                evidence=f"socrates_mirror/{binding['mirror_path']} "
                         f"({binding['body_fidelity']})")
        if body == "DECLARED_NOT_FETCHED":
            return Readiness(
                "PROMPT_BINDING_READY",
                "binding объявлен, тело существует в Drive, но не втянуто",
                expected_in="G-S25",
                evidence=f"prompt_bindings_v0.3.yaml → {binding['binding']}")
        if body == "DEFERRED_TO_G_S26":
            return Readiness(
                "CONTRACT_READY",
                "исполнительный адаптер не связан с хостом",
                expected_in="G-S26",
                evidence="prompt_bindings_v0.3.yaml: TINKUY_EXECUTION_ADAPTER")
        if body == "DEFERRED_TO_G_S25":
            return Readiness(
                "CONTRACT_READY",
                "исполнение управляется контрактом; иерархия промптов отложена",
                expected_in="G-S25",
                evidence=f"prompt_bindings_v0.3.yaml → {binding['binding']}")
        return Readiness("DECLARATIVE_READY", "шаг объявлен в pipeline.yaml")

    def branch_readiness(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "owner": self.owner,
            "canonical_claim": self.facts.get("canonical_claim", False),
            "matrix": {
                "pipeline_structure": "DECLARATIVE_READY",
                "state_model": "DECLARATIVE_READY",
                "step_declarations": "DECLARATIVE_READY",
                "runtime_profiles": "DECLARATIVE_READY",
                "trace_schema": "CONTRACT_READY",
                # G-S25R.8 semantic pack imported into data/socrates/current/;
                # CORE + B01..B10 + SEM_P00..P09 all materialised.
                "prompt_hierarchy": "PROMPT_BODY_READY",
                "prompt_bodies": "PROMPT_BODY_READY",
                # socrates_runtime executes S0..S10 with deterministic
                # orchestration; a live LLM executor for phase bodies is
                # future R8 work.
                "live_runtime": "PARTIAL_LIVE_ORCHESTRATION_DETERMINISTIC",
            },
            "live_runtime_status": self.LIVE_RUNTIME_STATUS,
            "generation_boundary": self.facts.get("generation_boundary", {}),
            "structural_evaluation": self.facts.get("structural_evaluation", {}),
        }

    # ------------------------------------------------------------------
    # A3 — pipeline projection with conditional semantics preserved
    # ------------------------------------------------------------------

    def describe_pipeline(self, resolved_for: dict[str, str] | None = None) -> PipelineProjection:
        resolved = {"profile": (resolved_for or {}).get(
            "profile", self.pipeline.get("default_profile", "DIRECT_ASSISTANCE"))}

        nodes: list[NodeProjection] = []
        for step in self.pipeline.get("steps", []):
            sid = step["id"]
            kind, evidence = self._kind_and_evidence(sid)
            entries = self.facts.get("prompt_bindings", {}).get("entries") or []
            binding = next((e for e in entries if sid in e.get("steps", [])), None)
            nodes.append(NodeProjection(
                node_id=sid,
                label=f"{sid} · {STEP_LABELS.get(sid, sid)}",
                kind=kind,
                implementation=step.get("contract", ""),
                source_ref=f"pipeline.yaml → {step.get('contract','')}",
                asset_id=None,                    # A6: never a fake prompt asset
                optional=bool(step.get("optional")),
                conditional_on=str(step.get("conditional_on") or ""),
                readiness=self._readiness(sid),
                contract_refs=[step.get("contract", "")],
                prompt_binding=binding,
                layer="DECLARED_PIPELINE",        # G-S24 declares; it does not run
                topology_status="UNKNOWN",        # no runtime to compare against
                note=evidence,
            ))

        # Terminal outcomes are first-class in this branch.
        for outcome in self.pipeline.get("terminal_outcomes", []):
            nodes.append(NodeProjection(
                node_id=f"TERMINAL:{outcome}", label=outcome, kind="STORE",
                implementation="terminal outcome",
                source_ref="pipeline.yaml → terminal_outcomes",
                layer="DECLARED_PIPELINE", topology_status="UNKNOWN",
                readiness=Readiness("DECLARATIVE_READY", "типизированный терминал"),
            ))

        edges = self._edges()
        return PipelineProjection(
            pipeline_id=self.pipeline.get("pipeline_id", "SOCRATES_FULL_PIPELINE"),
            branch=self.branch_id,
            version=str(self.pipeline.get("version", "0.3.0")),
            status=str(self.pipeline.get("status", "candidate")),
            nodes=nodes, edges=edges, resolved_for=resolved,
        )

    def _edges(self) -> list[EdgeProjection]:
        """Conditional route, not a flattened line.

        S7 is entered only when triggered; S9 only when authorized; five typed
        outcomes may finalize without any execution at all.
        """
        e: list[EdgeProjection] = []
        default = [("S0", "S1"), ("S1", "S2"), ("S2", "S3"), ("S3", "S4"),
                   ("S4", "S5"), ("S5", "S6")]
        for a, b in default:
            e.append(EdgeProjection(f"{a}->{b}", a, b, carries="step_completed",
                                    layer="DECLARED_PIPELINE"))
        e += [
            EdgeProjection("S6->S7", "S6", "S7", carries="retreat_or_council_required",
                           layer="DECLARED_PIPELINE", note="условный — S7 не ритуал"),
            EdgeProjection("S6->S8", "S6", "S8", carries="direct_bypass_authorized",
                           layer="DECLARED_PIPELINE",
                           note="стабильная SYSTEM-работа обходит совет"),
            EdgeProjection("S6->PAUSE", "S6", "TERMINAL:PAUSED_AWAITING_HUMAN_INPUT",
                           carries="human_binding_or_user_only_evidence_required",
                           layer="DECLARED_PIPELINE"),
            EdgeProjection("S7->S8", "S7", "S8",
                           carries="arbitration_completed_or_aporia_typed",
                           layer="DECLARED_PIPELINE"),
            EdgeProjection("S8->S9", "S8", "S9",
                           carries="execution_status == EXECUTE",
                           layer="DECLARED_PIPELINE", note="условный"),
            EdgeProjection("S8->S10", "S8", "S10",
                           carries="DO_NOT_EXECUTE | pause | refusal",
                           layer="DECLARED_PIPELINE",
                           note="обход S9 — исполнения может не быть"),
            EdgeProjection("S9->S10", "S9", "S10",
                           carries="execution_completed_or_explicit_failure",
                           layer="DECLARED_PIPELINE"),
        ]
        for outcome in self.pipeline.get("terminal_outcomes", []):
            if outcome == "PAUSED_AWAITING_HUMAN_INPUT":
                continue
            e.append(EdgeProjection(
                f"S10->{outcome}", "S10", f"TERMINAL:{outcome}",
                carries=f"terminal_outcome == {outcome}", layer="DECLARED_PIPELINE"))
        return e

    # ------------------------------------------------------------------
    # A9 — state machine is a separate projection
    # ------------------------------------------------------------------

    def state_projection(self) -> StateProjection:
        sm = self.state_model
        states = [StateNode(s["id"], s["kind"],
                            sm.get("terminal_semantics", {}).get(s["id"], "")
                            or sm.get("dispatcher_semantics", {}).get(s["id"], ""))
                  for s in sm.get("states", [])]
        transitions = [StateTransition(t["from"], t["to"], t.get("when", ""),
                                       t.get("note", ""), guarded=bool(t.get("when")))
                       for t in sm.get("transitions", [])]
        # per-step failure/retry edges are declared once and apply to every step
        for s in sm.get("states", []):
            if s["kind"] != "active" or s["id"] == "RECEIVED":
                continue
            for edge in sm.get("per_step_failure_edges", []):
                transitions.append(StateTransition(
                    s["id"], edge["to"], edge.get("when", ""), guarded=True))
            ret = sm.get("per_step_retry_return", {})
            if ret:
                transitions.append(StateTransition(
                    "RETRY_PENDING", s["id"],
                    ret.get("when", "").replace("<self>", s["id"]),
                    ret.get("note", ""), guarded=True))
        return StateProjection(
            projection_id="socrates.state_model.v0.3.0",
            branch=self.branch_id,
            version=str(sm.get("version", "0.3.0")),
            states=states, transitions=transitions,
            forbidden_transitions=list(sm.get("forbidden_transitions", [])),
            retry_budget=dict(sm.get("retry_budget", {})),
            dispatcher_semantics=dict(sm.get("dispatcher_semantics", {})),
            terminal_semantics=dict(sm.get("terminal_semantics", {})),
            source_ref="state_model.yaml (Drive 1kAHBbL6oQl4yeBvo-8DfrX3aR5qAzJYL)",
        )

    # ------------------------------------------------------------------
    # A7 — branch invariants come from data, never from core assumptions
    # ------------------------------------------------------------------

    def branch_invariants(self) -> list[BranchInvariant]:
        out = [BranchInvariant(i["id"], i["text"],
                               source_ref="README.md · Authority invariants",
                               source_id="1FiepAVg0IuRe9ztYY6qbU6X3iuPZFnjR")
               for i in self.facts.get("branch_invariants", [])]
        out += [BranchInvariant(f"GUARD-{n}", g,
                                source_ref="pipeline.yaml · global_guards",
                                source_id="1cNyy952FrOL0shWm2J26DVeaFN7l5Tzm")
                for n, g in enumerate(self.facts.get("global_guards", []), start=1)]
        return out

    # ------------------------------------------------------------------
    # A8 — contracts
    # ------------------------------------------------------------------

    def contract_bindings(self) -> list[dict[str, Any]]:
        used_by = {
            "pipeline_trace.schema.json": ["S10", "trace"],
            "intervention_selection.schema.json": ["S8"],
            "arbitration_record.schema.json": ["S7"],
            "council_recipe.schema.json": ["S7"],
            "human_operation.schema.json": ["S6"],
            "human_operation_return.schema.json": ["S6"],
            "ownership_assessment_v0.2.schema.json": ["S6"],
            "competence_after_interaction.schema.json": ["S6"],
            "development_risk.schema.json": ["S6"],
        }
        out = []
        for s in self.manifest.get("schemas", []):
            name = s["name"]
            out.append({
                "contract_id": name,
                "drive_id": s.get("drive_id"),
                "owner_sha256": s.get("owner_sha256"),
                "in_owner_manifest": s.get("in_owner_manifest"),
                "used_by": used_by.get(name, []),
                "role": "output" if name.endswith("record.schema.json") else "io",
                "protected": True,
                "readiness": ("CONTRACT_READY" if s.get("in_owner_manifest")
                              else "CONTRACT_READY / NOT_IN_G-S24_MANIFEST"),
                "provenance": "Drive 07_SOCRATES_PIPELINE_PACK/schemas",
            })
        for step_id, binding in (self.facts.get("component_bindings") or {}).items():
            out.append({
                "contract_id": binding.get("contract"),
                "drive_id": binding.get("drive_id"),
                "used_by": [step_id],
                "role": "component_binding",
                "protected": True,
                "readiness": "CONTRACT_READY",
                "provenance": "manifest.yaml · bounded_components",
            })
        return out

    # ------------------------------------------------------------------
    # A10 — runtime profiles, inspectable but NOT activatable
    # ------------------------------------------------------------------

    def runtime_profiles(self) -> list[dict[str, Any]]:
        default = self.pipeline.get("default_profile")
        return [{
            "profile_id": p["id"],
            "note": p.get("note", ""),
            "is_default": p["id"] == default,
            "version": str(self.pipeline.get("version", "0.3.0")),
            "source_ref": "pipeline.yaml · profiles / README.md",
            "available_actions": ["inspect", "compare", "clone_candidate",
                                  "validate_declaratively"],
            "activate_in_live_runtime": {
                "enabled": False,
                "status": self.LIVE_RUNTIME_STATUS,
            },
        } for p in self.facts.get("runtime_profiles", [])]

    # ------------------------------------------------------------------
    # A11 — declarative prospective snapshot
    # ------------------------------------------------------------------

    def declarative_snapshot(self, profile: str | None = None) -> dict[str, Any]:
        """Prospective, not executed. Same contract shape as a real one so that
        G-S26 evidence can be accepted later without a new data model."""
        from workbench_core.models import sha256_text

        entries = self.facts.get("prompt_bindings", {}).get("entries") or []
        available = [e for e in entries if e.get("body_status") in
                     {"MIRRORED_READ_ONLY", "DECLARED_NOT_FETCHED"}]
        missing = [e for e in entries if e.get("body_status", "").startswith("DEFERRED")]
        return {
            "snapshot_kind": "DECLARATIVE_SNAPSHOT",
            "is_executed_run": False,
            "live_runtime_status": self.LIVE_RUNTIME_STATUS,
            "pipeline": {
                "pipeline_id": self.pipeline.get("pipeline_id"),
                "version": self.pipeline.get("version"),
                "hash": self.manifest.get("sources", [{}])[0].get("owner_sha256"),
            },
            "state_model": {
                "version": self.state_model.get("version"),
                "owner_sha256": next(
                    (s.get("owner_sha256") for s in self.manifest.get("sources", [])
                     if s.get("source_path") == "state_model.yaml"), None),
            },
            "runtime_profile": profile or self.pipeline.get("default_profile"),
            "contract_bindings": [c["contract_id"] for c in self.contract_bindings()],
            "prompt_bindings_available": [e["binding"] for e in available],
            "missing_prompt_bodies": [
                {"steps": e["steps"], "binding": e["binding"],
                 "expected_in": "G-S25" if e["body_status"].endswith("S25") else "G-S26"}
                for e in missing],
            "host_binding": {"status": "NONE", "expected_in": "G-S26"},
            "snapshot_id": "decl_" + sha256_text(
                f"{self.pipeline.get('pipeline_id')}|{self.pipeline.get('version')}|"
                f"{profile or self.pipeline.get('default_profile')}")[:16],
        }

    # ------------------------------------------------------------------
    # BranchAdapter surface — declarative branch has no prompt assets yet
    # ------------------------------------------------------------------

    def prompt_body(self, binding: str) -> dict[str, Any]:
        """Read-only body of a materialised binding — explanation, not editing.

        This is the whole difference between PROMPT_BODY_READY and an editable
        asset: the operator can read and reason about the text, and the
        Workbench offers no lifecycle over it, because nothing executes it and
        LOCAL_SOCRATES owns it.
        """
        entries = self.facts.get("prompt_bindings", {}).get("entries") or []
        entry = next((e for e in entries if e.get("binding") == binding), None)
        if entry is None:
            raise KeyError(f"unknown binding: {binding}")
        rel = entry.get("mirror_path")
        if not rel:
            return {"binding": binding, "body_status": entry.get("body_status"),
                    "text": None, "editable": False,
                    "reason": "тело не втянуто"}
        path = MIRROR / rel
        return {
            "binding": binding,
            "body_status": entry["body_status"],
            "body_fidelity": entry.get("body_fidelity"),
            "steps": entry.get("steps", []),
            "source_ref": f"socrates_mirror/{rel}",
            "drive_id": entry.get("drive_id"),
            "text": path.read_text(encoding="utf-8"),
            "editable": False,
            "reason": "владелец LOCAL_SOCRATES; рантайма, который бы это "
                      "исполнял, ещё нет (G-S26)",
        }

    def list_assets(self) -> list[PromptAsset]:
        """A6: no invented prompts. A declared binding without a materialised
        body is reported through the node's readiness, not as a fake asset."""
        return []

    def baseline_variants(self, asset_id: str) -> list[tuple[str, str, str]]:
        return []

    def contract_report(self, asset_id: str, source_text: str) -> ContractReport:
        return ContractReport(asset_id, [], [], [], [], [], [], "UNDECLARED",
                              DriftFingerprint())

    def compiler_profile(self, asset_id: str) -> CompilerProfile:
        return CompilerProfile(profile_id="socrates.declarative.none",
                               branch=self.branch_id, model_id="none",
                               allow_superprompt=False)

    def build_invocation(self, asset_id: str, source_text: str, fixture: Fixture):
        raise NotImplementedError(
            "G-S24 is host-neutral and declarative; invocation is G-S26")

    def semantic_controls(self) -> list[SemanticControl]:
        return []

    def fixtures(self, asset_id: str) -> list[Fixture]:
        return []

    def validate_output(self, asset_id: str, raw_text: str):
        return False, ["socrates_g_s24_has_no_runtime_output"], {}
