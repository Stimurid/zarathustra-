"""Zarathustra BranchAdapter — the first branch projection.

This module MAY import both ``workbench_core`` and the Zarathustra runtime.
``workbench_core`` may import neither. Socrates will get its own adapter with
the same shape once its PipelinePack is materialised, which is what makes the
core's branch-independence testable rather than merely asserted.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from californian_id import prompt_assets
from californian_id.config import ZARATHUSTRA_DIR
from californian_id.models import Message
from workbench_core.branch import (
    ControlEffect,
    EdgeProjection,
    Fixture,
    Invocation,
    NodeProjection,
    PipelineProjection,
    SemanticControl,
)
from workbench_core.models import (
    CompilerProfile,
    ContractReport,
    DriftFingerprint,
    PromptAsset,
    Region,
)
from workbench_core.rag import (
    NOT_IMPLEMENTED,
    MissingCapability,
    RAGParameter,
    RAGProfile,
    RetrievalCandidate,
    RetrievalEvent,
)

_RAG_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _rag_tokens(text: str) -> list[str]:
    """Mirrors the engines' own tokeniser (len > 2, lowercased)."""
    return [t.lower() for t in _RAG_TOKEN_RE.findall(text or "") if len(t) > 2]


def _hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]

DATA = Path(ZARATHUSTRA_DIR)
PKG_DATA = DATA.parent
PIPELINE_YAML = PKG_DATA / "pipeline" / "pipeline.yaml"
DEP_MAP = DATA / "PROMPT_DEPENDENCY_MAP.yaml"
MANIFEST = DATA / "manifest.yaml"

SCENE_ASSET = "zarathustra.03_scene_reading"
SOCRATIC_ASSET = "argumentation.socratic_question_chain"

#: Fields actually read by ``Zarathustra.analyze_situation`` → SituationAnalysis.
#: Source of truth: src/californian_id/zarathustra.py (analyze_situation body).
CONSUMED_SCENE_FIELDS = [
    "topic", "genre", "stakes", "horizons", "concepts", "tensions", "uncertainties",
]

_JSON_KEY_RE = re.compile(r'"([a-z_][a-z0-9_]*)"\s*:')
_SITUATION_CAP = 100_000
_GENRES = {"question", "statement", "normative", "long_form", "transcript"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(_read(path)) or {} if path.exists() else {}


class ZarathustraAdapter:
    branch_id = "zarathustra"

    def __init__(self) -> None:
        self._dep_map = _yaml(DEP_MAP)
        self._manifest = _yaml(MANIFEST)
        self._pipeline = _yaml(PIPELINE_YAML)

    # ------------------------------------------------------------------
    # pipeline projection
    # ------------------------------------------------------------------

    def describe_pipeline(self, resolved_for: dict[str, str] | None = None) -> PipelineProjection:
        resolved = {"input_mode": "raw", "runtime_layer": "californian_id"}
        resolved.update(resolved_for or {})

        nodes: list[NodeProjection] = [
            NodeProjection("intake", "Приём входа", "STORE",
                           "pipeline.intake", "data/pipeline/pipeline.yaml:19",
                           note="receive input text or file"),
            NodeProjection("normalize_input", "Нормализация", "DETERMINISTIC",
                           "pipeline.normalize_input", "data/pipeline/pipeline.yaml:21"),
        ]

        if resolved["input_mode"] in {"raw+fabric", "auto-slice", "semantic-units"}:
            nodes.append(NodeProjection(
                "fabric_chain", "Ткань (12 ступеней)", "PROMPT",
                "fabric.00..11", "data/fabric/",
                note=f"активна только при input_mode={resolved['input_mode']}"))

        nodes += [
            NodeProjection(
                "analyze_situation", "Чтение сцены", "MODEL_CALL",
                "zarathustra.analyze_situation",
                "src/californian_id/zarathustra.py:238",
                asset_id=SCENE_ASSET,
                output_contract="schemas.SituationAnalysis",
                params=[{"id": "CALIFORNIAN_ID_SITUATION_MAX_CHARS", "class": "E",
                         "value": _SITUATION_CAP, "range": [1000, 200000],
                         "authority": "env", "runtime_mutable": False}]),
            NodeProjection("load_persona_registry", "Реестр персон", "STORE",
                           "personas.load_registry", "data/personas/",
                           actual_callers=["Pipeline.run"]),
            NodeProjection("select_initial_voice", "Первичный кастинг", "HYBRID",
                           "zarathustra.cast", "src/californian_id/pipeline.py:440",
                           declared_predecessors=["retrieve_initial_context"],
                           actual_callers=["Pipeline.run"],
                           topology_status="DECLARATION_DRIFT",
                           note="в рантайме идёт сразу после analyze_situation; "
                                "объявленный между ними retrieve_initial_context "
                                "не исполняется"),

            # ---- объявлено, но не исполняется -----------------------------
            NodeProjection("retrieve_initial_context",
                           "Извлечение контекста (только объявление)", "RAG",
                           "— нет runtime-точки входа —",
                           "data/pipeline/pipeline.yaml:29",
                           rag_profile_id="rag.persona_lexical.baseline",
                           output_contract="EvidenceChunk",
                           layer="DECLARED_PIPELINE",
                           topology_status="DEAD_DECLARATION",
                           declared_predecessors=["validate_personas"],
                           declared_successors=["select_initial_voice"],
                           note="Объявлен отдельным шагом перед кастингом, но Pipeline.run "
                                "такого шага не делает. Реальное извлечение — per-turn "
                                "узел evidence_retrieval."),

            # ---- настоящий цикл совета ------------------------------------
            NodeProjection("route_next", "Маршрутизация", "ROUTER",
                           "zarathustra.route_next",
                           "src/californian_id/pipeline.py:~500 → zarathustra.py:390",
                           asset_id="zarathustra.04_head_calling",
                           actual_callers=["Pipeline.run (council loop)"], in_loop=True),
            NodeProjection("evidence_retrieval", "Извлечение evidence (per-turn)", "RAG",
                           "retrieval.LexicalPersonaRetriever.retrieve",
                           "src/californian_id/pipeline.py:545 → retrieval.py:54",
                           rag_profile_id="rag.persona_lexical.baseline",
                           output_contract="EvidenceChunk",
                           actual_callers=["Pipeline.run (council loop)"],
                           actual_callees=["_run_persona_turn"],
                           in_loop=True, topology_status="DECLARATION_DRIFT",
                           note="реальный per-turn узел; запрос = state.situation.topic, "
                                "потребитель = persona_turn; корпуса персон пусты → 0 чанков"),
            NodeProjection("cultural_context", "Культурные карты (per-turn)", "RAG",
                           "cultural_rag.CulturalIndex.retrieve_cards",
                           "src/californian_id/pipeline.py:561 → cultural_rag.py:276",
                           rag_profile_id="rag.cultural_cards.baseline",
                           output_contract="RetrievedCard",
                           actual_callers=["Pipeline.run (council loop)"],
                           actual_callees=["_run_persona_turn"],
                           in_loop=True,
                           note="в pipeline.yaml не объявлен вовсе; корпус присутствует"),
            NodeProjection("persona_turn", "Ход персоны", "MODEL_CALL",
                           "pipeline._run_persona_turn",
                           "src/californian_id/pipeline.py:575",
                           asset_id="zarathustra.05_move_assignment",
                           input_contract="EvidenceChunk[] + RetrievedCard[]",
                           output_contract="schemas.TurnRecord",
                           actual_callers=["Pipeline.run (council loop)"], in_loop=True,
                           note="фактический потребитель обоих извлечений"),
            NodeProjection("assess_turn", "Оценка спора", "DETERMINISTIC",
                           "argumentation.assess_turn",
                           "src/californian_id/argumentation.py:138",
                           output_contract="data/argumentation/schemas/dispute_assessment.schema.json"),
            NodeProjection("checkpoint", "HIL-чекпойнт", "HUMAN_GATE",
                           "runtime_control.wait_if_paused",
                           "src/californian_id/runtime_control.py:294"),
            NodeProjection("synthesize", "Синтез", "MODEL_CALL",
                           "zarathustra.closing_speech",
                           "src/californian_id/zarathustra.py:857",
                           asset_id="zarathustra.13_closing_speech"),
            NodeProjection("validate_output", "Валидация выхода", "DETERMINISTIC",
                           "pipeline._validate", "src/californian_id/pipeline.py:1636"),
            NodeProjection("persist_trace", "Трасса", "STORE",
                           "pipeline.persist_trace", "runs/<run_id>/events.jsonl"),
        ]

        # Explicit control flow, not a zip over a list: the loop is drawn as a
        # loop, and the dead declaration lives on its own layer so a harness or
        # declared edge is never mistaken for a production edge (T1).
        chain = [
            ("intake", "normalize_input", "RawInput"),
            ("normalize_input", "analyze_situation", "NormalisedText"),
            ("analyze_situation", "load_persona_registry", "SituationAnalysis"),
            ("load_persona_registry", "select_initial_voice", "PersonaRegistry"),
            ("select_initial_voice", "route_next", "SelectedPersonas"),
            ("route_next", "evidence_retrieval", "RoutingDecision"),
            ("evidence_retrieval", "persona_turn", "EvidenceChunk[]"),
            ("route_next", "cultural_context", "RoutingDecision"),
            ("cultural_context", "persona_turn", "RetrievedCard[]"),
            ("persona_turn", "assess_turn", "TurnRecord"),
            ("assess_turn", "checkpoint", "DisputeAssessment"),
            ("checkpoint", "route_next", "RunState (следующий ход)"),
            ("checkpoint", "synthesize", "RunState (остановка)"),
            ("synthesize", "validate_output", "Completion"),
            ("validate_output", "persist_trace", "RunState"),
        ]
        if resolved["input_mode"] in {"raw+fabric", "auto-slice", "semantic-units"}:
            chain = [e for e in chain
                     if e[:2] != ("normalize_input", "analyze_situation")]
            chain.insert(1, ("normalize_input", "fabric_chain", "NormalisedText"))
            chain.insert(2, ("fabric_chain", "analyze_situation", "UnitPack"))

        edges = [EdgeProjection(f"{a}->{b}", a, b, carries=c) for a, b, c in chain]
        edges.append(EdgeProjection(
            "declared:load_persona_registry->retrieve_initial_context",
            "load_persona_registry", "retrieve_initial_context",
            carries="(только объявление)", layer="DECLARED_PIPELINE",
            note="ребро существует лишь в pipeline.yaml"))

        return PipelineProjection(
            pipeline_id=self._pipeline.get("pipeline_id", "californian_id.inner_council"),
            branch=self.branch_id,
            version=str(self._pipeline.get("version", "0.1.0")),
            status=str(self._pipeline.get("status", "candidate")),
            nodes=nodes, edges=edges, resolved_for=resolved,
        )

    # ------------------------------------------------------------------
    # assets
    # ------------------------------------------------------------------

    def _scene_regions(self) -> list[Region]:
        return [
            Region("output_json_contract", "protected", "```", "```",
                   "потребитель парсит эти ключи; изменение ломает SituationAnalysis"),
            Region("anti_speculation_rules", "protected",
                   "Не приписывай пользователю позицию", "не заполняй домыслом.",
                   "эпистемический инвариант: запрет домысливания"),
            Region("signal_definitions", "editable",
                   "## Признаки, которые ищешь", "разговор стал возможным.",
                   "содержательная часть — переписывается свободно"),
            Region("prohibitions", "protected", "## Что запрещено", None,
                   "правила, на которые опираются соседние шаги"),
        ]

    def _declared_scene_fields(self) -> list[str]:
        for mod in self._dep_map.get("modules", []):
            if mod.get("id") == "03_scene_reading":
                schema = mod.get("output_schema")
                if isinstance(schema, dict):
                    return list(schema.keys())
                if isinstance(schema, str):
                    return _JSON_KEY_RE.findall(schema)
        return []

    def list_assets(self) -> list[PromptAsset]:
        invariants = [s for s in (self._manifest.get("non_negotiable_identity") or [])
                      if isinstance(s, str)][:0]  # applied at branch level, not inlined
        scene = PromptAsset(
            asset_id=SCENE_ASSET,
            branch=self.branch_id,
            owner_id=str(self._manifest.get("agent_id", "HEAD_ZARATHUSTRA")),
            purpose="структурная реконструкция входа",
            operation_class="scene_reading",
            used_by_steps=["analyze_situation"],
            transition="raw scene text -> SituationAnalysis",
            upstream_objects=["RawInput"],
            output_object="SituationAnalysis",
            depends_on=["01_identity_and_laws"],
            composition_allowed=True,
            runtime_allowed="true",
            regions=self._scene_regions(),
            invariants=invariants,
            declared_output_fields=self._declared_scene_fields(),
            consumed_output_fields=list(CONSUMED_SCENE_FIELDS),
            contract_version="0.2.0",
            baseline_fallback_ref="californian_id.zarathustra._DEFAULT_SCENE_READING_PROMPT",
            source_path=str((DATA / "03_scene_reading.md").relative_to(PKG_DATA.parent.parent)),
        )
        # Defect WB-001 fix: nodes referenced these two assets while list_assets()
        # did not register them, producing dangling asset_id links (404 from the
        # projection API). They are real file-backed prompts with code baselines,
        # so they are registered rather than unlinked.
        secondary = [
            PromptAsset(
                asset_id="zarathustra.04_head_calling",
                branch=self.branch_id,
                owner_id=str(self._manifest.get("agent_id", "HEAD_ZARATHUSTRA")),
                purpose="выбор следующей головы + операции",
                operation_class="head_calling",
                used_by_steps=["route_next"],
                transition="scene + turns -> RoutingDecision",
                output_object="RoutingDecision",
                depends_on=["01_identity_and_laws"],
                runtime_allowed="true",
                contract_version="0.2.0",
                baseline_fallback_ref="californian_id.zarathustra._DEFAULT_ROUTE_PROMPT",
                source_path="src/californian_id/data/zarathustra/04_head_calling.md",
            ),
            PromptAsset(
                asset_id="zarathustra.13_closing_speech",
                branch=self.branch_id,
                owner_id=str(self._manifest.get("agent_id", "HEAD_ZARATHUSTRA")),
                purpose="финальная речь Заратустры",
                operation_class="closing_speech",
                used_by_steps=["synthesize"],
                transition="council turns + completion form -> closing speech",
                output_object="ClosingSpeech",
                depends_on=["01_identity_and_laws"],
                runtime_allowed="true",
                contract_version="0.2.0",
                baseline_fallback_ref="californian_id.zarathustra._DEFAULT_CLOSING_SPEECH_PROMPT",
                source_path="src/californian_id/data/zarathustra/13_closing_speech.md",
            ),
            PromptAsset(
                asset_id="zarathustra.05_move_assignment",
                branch=self.branch_id,
                owner_id=str(self._manifest.get("agent_id", "HEAD_ZARATHUSTRA")),
                purpose="выдаётся голове перед её ходом",
                operation_class="move_assignment",
                used_by_steps=["persona_turn"],
                transition="routing decision + evidence + cards -> TurnRecord",
                upstream_objects=["RoutingDecision", "EvidenceChunk", "RetrievedCard"],
                output_object="TurnRecord",
                depends_on=["01_identity_and_laws"],
                runtime_allowed="true",
                contract_version="0.2.0",
                source_path="src/californian_id/data/zarathustra/05_move_assignment.md",
            ),
        ]
        socratic = PromptAsset(
            asset_id=SOCRATIC_ASSET,
            branch=self.branch_id,
            owner_id="californian_id.argumentation",
            purpose="reference-only template для problematize_question / create_aporia",
            operation_class="socratic_question_chain",
            used_by_steps=[],
            transition="(не подключён к рантайму)",
            output_object="",
            runtime_allowed="false",
            reference_only=True,
            source_path="src/californian_id/data/argumentation/prompts/socratic_question_chain.md",
        )
        return [scene, *secondary, socratic]

    _SECONDARY_FILES = {
        "zarathustra.04_head_calling": ("04_head_calling.md", "zarathustra.default_route"),
        "zarathustra.05_move_assignment": ("05_move_assignment.md", None),
        "zarathustra.13_closing_speech": ("13_closing_speech.md",
                                          "zarathustra.default_closing_speech"),
    }

    def baseline_variants(self, asset_id: str) -> list[tuple[str, str, str]]:
        if asset_id == SCENE_ASSET:
            out = []
            file_text = _read(DATA / "03_scene_reading.md")
            if file_text:
                out.append(("baseline_file", "0.2.0", file_text))
            out.append(("baseline_code", "0.1",
                        prompt_assets.runtime_block("zarathustra.default_scene_reading")))
            return out
        if asset_id in self._SECONDARY_FILES:
            filename, fallback_id = self._SECONDARY_FILES[asset_id]
            out = []
            text = _read(DATA / filename)
            if text:
                out.append(("baseline_file", "0.2.0", text))
            if fallback_id:
                out.append(("baseline_code", "0.1",
                            prompt_assets.runtime_block(fallback_id)))
            return out
        if asset_id == SOCRATIC_ASSET:
            p = PKG_DATA / "argumentation" / "prompts" / "socratic_question_chain.md"
            return [("baseline_file", "0.1", _read(p))] if p.exists() else []
        return []

    # ------------------------------------------------------------------
    # contracts
    # ------------------------------------------------------------------

    def contract_report(self, asset_id: str, source_text: str) -> ContractReport:
        if asset_id != SCENE_ASSET:
            return ContractReport(asset_id, [], [], [], [], [], [], "UNDECLARED",
                                  DriftFingerprint())

        prompt_fields = list(dict.fromkeys(_JSON_KEY_RE.findall(source_text)))
        declared = self._declared_scene_fields()
        consumed = list(CONSUMED_SCENE_FIELDS)

        unconsumed = [f for f in prompt_fields if f not in consumed]
        undeclared = [f for f in prompt_fields if f not in declared]
        missing = [f for f in consumed if f not in prompt_fields]

        # C1: structural fingerprint. Categories are populated only where this
        # runtime can actually prove the defect.
        fingerprint = DriftFingerprint(
            prompt_fields_not_declared=undeclared,
            declared_fields_not_consumed=[f for f in declared if f not in consumed],
            prompt_fields_not_consumed=unconsumed,
            required_fields_missing=missing,
            schema_type_mismatches=self._scene_type_mismatches(source_text),
            dangling_asset_refs=self._dangling_refs(asset_id),
        ).normalised()

        if missing:
            status = "INCOMPATIBLE"
        elif unconsumed or undeclared:
            status = "MISMATCH"
        else:
            status = "OK"

        return ContractReport(
            asset_id=asset_id, prompt_fields=prompt_fields, declared_fields=declared,
            consumed_fields=consumed, unconsumed=unconsumed,
            undeclared_in_map=undeclared, missing_from_prompt=missing, status=status,
            fingerprint=fingerprint,
        )

    def _scene_type_mismatches(self, source_text: str) -> list[str]:
        """Fields whose declared JSON shape contradicts the consumer's type.

        ``analyze_situation`` coerces five fields with a list comprehension and
        two with ``str``; a prompt that asks for the opposite shape is a typed
        contract defect, not a stylistic one.
        """
        list_fields = {"stakes", "horizons", "concepts", "tensions", "uncertainties"}
        scalar_fields = {"topic", "genre"}
        out: list[str] = []
        for field_name in list_fields:
            m = re.search(rf'"{field_name}"\s*:\s*(\[|")', source_text)
            if m and m.group(1) == '"':
                out.append(f"{field_name}:expected_array_got_string")
        for field_name in scalar_fields:
            m = re.search(rf'"{field_name}"\s*:\s*(\[|")', source_text)
            if m and m.group(1) == "[":
                out.append(f"{field_name}:expected_string_got_array")
        return out

    def _dangling_refs(self, asset_id: str) -> list[str]:
        """Nodes referencing assets this adapter does not register (defect WB-001)."""
        known = {a.asset_id for a in self.list_assets()}
        proj = self.describe_pipeline(None)
        return sorted({n.asset_id for n in proj.nodes
                       if n.asset_id and n.asset_id not in known})

    # ------------------------------------------------------------------
    # compilation + invocation
    # ------------------------------------------------------------------

    def compiler_profile(self, asset_id: str) -> CompilerProfile:
        return CompilerProfile(
            profile_id="tinkuy.zarathustra.lazy",
            branch=self.branch_id,
            model_id="from-preset",
            supports_system_role=True,
            allow_superprompt=False,     # PROMPT_DEPENDENCY_MAP: «никакого мега-промпта»
            module_loading="lazy",
            variable_policy="strict",
            assembly_order=["operation"],
            max_user_chars=_SITUATION_CAP,
        )

    def build_invocation(self, asset_id: str, source_text: str, fixture: Fixture) -> Invocation:
        """Byte-for-byte reproduction of Zarathustra.analyze_situation's call.

        Mirrors src/californian_id/zarathustra.py:260-266 — a single system
        message carrying the prompt and one user message carrying the capped
        scene text. Nothing else is added.
        """
        messages = [
            Message(role="system", content=source_text),
            Message(role="user", content=fixture.text[:_SITUATION_CAP]),
        ]
        return Invocation(
            system_text=messages[0].content,
            user_text=messages[1].content,
            settings={"role": "zarathustra_situation_reading",
                      "input_len": len(fixture.text)},
        )

    # ------------------------------------------------------------------
    # C3 — integration path through the real branch runtime
    # ------------------------------------------------------------------

    def integration_run(self, asset_id: str, source_text: str, fixture: Fixture,
                        client: Any) -> dict[str, Any]:
        """Drive the *actual* runtime function, not a reimplementation.

        The active variant's text is materialised into a private prompt dir and
        a real ``Zarathustra`` instance is pointed at it, so the call path is:

            variant source -> Zarathustra.prompt() -> analyze_situation()
            -> models.Message assembly -> client.generate() (capture boundary)
            -> _json_from_text (real parser) -> SituationAnalysis

        Returns the parsed object plus everything needed to prove what was sent.
        """
        import tempfile

        from californian_id.zarathustra import Zarathustra

        if asset_id != SCENE_ASSET:
            raise ValueError(f"integration path not defined for {asset_id}")

        with tempfile.TemporaryDirectory(prefix="wb_prompt_") as tmp:
            tmp_dir = Path(tmp)
            (tmp_dir / "03_scene_reading.md").write_text(source_text, encoding="utf-8")
            z = Zarathustra(prompt_dir=tmp_dir)
            # cache is cold by construction; invalidate anyway to exercise C4 wiring
            z.invalidate_prompt_cache()
            resolved = z.prompt("03_scene_reading.md")
            assert resolved == source_text, "runtime did not read the variant source"
            situation = z.analyze_situation(fixture.text, client)

        return {
            "resolved_prompt": resolved,
            "situation": {
                "topic": situation.topic, "genre": situation.genre,
                "stakes": list(situation.stakes), "horizons": list(situation.horizons),
                "concepts": list(situation.concepts), "tensions": list(situation.tensions),
                "uncertainties": list(situation.uncertainties),
            },
            "consumed_fields": list(CONSUMED_SCENE_FIELDS),
        }

    # ---------------- T2/T7: the normal public runtime entrypoint ----------

    #: The real production entrypoint. Everything else in this adapter is
    #: observation or configuration; nothing re-implements it.
    PRODUCTION_ENTRYPOINT = "californian_id.pipeline.Pipeline.run"

    def bind_runtime_resolver(self, resolver: Any) -> None:
        """Install the Workbench resolver into this branch's runtime seam.

        Lives here, not in the core: only an adapter may touch its own runtime.
        """
        from californian_id import runtime_bindings

        runtime_bindings.set_resolver(resolver)

    def unbind_runtime_resolver(self) -> None:
        from californian_id import runtime_bindings

        runtime_bindings.set_resolver(None)

    def production_entrypoint(self, text: str, mode: str = "fast",
                              run_id: str | None = None,
                              workspace_id: str = "workbench-t7") -> dict[str, Any]:
        """Drive the ordinary Zarathustra run — no Workbench-specific path.

        Returns only observations of what the production run did.
        """
        from californian_id.pipeline import Pipeline

        pipe = Pipeline(workspace_id=workspace_id)
        result = pipe.run(text=text, mode=mode, run_id=run_id)
        state = result.run_state
        return {
            "entrypoint": self.PRODUCTION_ENTRYPOINT,
            "run_id": state.run_id,
            "status": state.status,
            "topic": getattr(state.situation, "topic", ""),
            "genre": getattr(state.situation, "genre", ""),
            "selected_personas": list(state.selected_personas or []),
            "turns": [{"turn_index": t.turn_index, "persona_id": t.persona_id,
                       "operation": t.operation,
                       "provider": getattr(t, "model_provider", None)}
                      for t in state.turns],
            "trace_dir": str(result.trace_dir),
            "errors": list(state.errors or []),
        }

    def legacy_invocation(self, fixture: Fixture) -> Invocation:
        """The OLD code path: the Python constant, not the PromptAsset.

        Used only to prove invocation-level equivalence of the Stage 0 extraction.
        """
        from californian_id import zarathustra as z
        return Invocation(
            system_text=z._DEFAULT_SCENE_READING_PROMPT,
            user_text=fixture.text[:_SITUATION_CAP],
            settings={"role": "zarathustra_situation_reading",
                      "input_len": len(fixture.text)},
        )

    # ------------------------------------------------------------------
    # controls with multiple effects (hybrids are represented, not split)
    # ------------------------------------------------------------------

    def semantic_controls(self) -> list[SemanticControl]:
        from californian_id.regimes import CRITIQUE_REGIMES, VARIATION_REGIMES

        critique = SemanticControl(
            control_id="critique_regime", label="Critique Regime",
            values=["gentle", "balanced", "hard"], default="balanced",
            semantics="единый пользовательский режим; в UI не расщепляется",
            effects=[
                ControlEffect("PROMPT_BEHAVIOR",
                              "regimes.CritiqueRegime.directness_hint",
                              ["persona_turn"],
                              "src/californian_id/regimes.py:24,29,34",
                              value_map={k: v.directness_hint[:60] + "…"
                                         for k, v in CRITIQUE_REGIMES.items()}),
                ControlEffect("DETERMINISTIC_ALGORITHM",
                              "regimes.CritiqueRegime.attack_bias",
                              ["router_scoring", "route_next"],
                              "src/californian_id/regimes.py:26,31,36",
                              value_map={k: v.attack_bias for k, v in CRITIQUE_REGIMES.items()}),
            ])
        variation = SemanticControl(
            control_id="variation_regime", label="Variation Regime",
            values=["strict", "normal", "jazz"], default="normal",
            semantics="единый пользовательский режим; в UI не расщепляется",
            effects=[
                ControlEffect("PROMPT_BEHAVIOR",
                              "regimes.VariationRegime.prompt_hint",
                              ["persona_turn"],
                              "src/californian_id/regimes.py:44,51,58",
                              value_map={k: v.prompt_hint[:60] + "…"
                                         for k, v in VARIATION_REGIMES.items()}),
                ControlEffect("DETERMINISTIC_ALGORITHM",
                              "regimes.VariationRegime.repeat_penalty / class_repeat_penalty",
                              ["router_scoring"],
                              "src/californian_id/regimes.py:45,52,59",
                              value_map={k: [v.repeat_penalty, v.class_repeat_penalty]
                                         for k, v in VARIATION_REGIMES.items()}),
            ])
        v054 = SemanticControl(
            control_id="persona.position_model", label="Persona position_model / argumentation",
            values=[], default="", subject="asset",
            semantics="ассет-гибрид: один и тот же YAML участвует и в композиции "
                      "промпта персоны, и в детерминированном кастинге",
            effects=[
                ControlEffect("PROMPT_BEHAVIOR",
                              "data/personas/LENS_*/position_model.yaml → persona turn composition",
                              ["persona_turn"],
                              "src/californian_id/persona_layer.py"),
                ControlEffect("DETERMINISTIC_ALGORITHM",
                              "manifest.routing.topics/tensions overlap → cast ranking",
                              ["select_initial_voice", "zarathustra.cast"],
                              "src/californian_id/zarathustra.py:294; data/pipeline/pipeline.yaml:32"),
            ])
        return [critique, variation, v054]

    # ==================================================================
    # STAGE 2 — RAG
    # ==================================================================

    #: Two retrieval engines actually exist in this runtime.
    ENGINE_PERSONA = "tinkuy.persona_lexical_bm25"
    ENGINE_CARDS = "zarathustra.cultural_cards_bm25"

    def rag_parameters(self, engine_id: str) -> list[RAGParameter]:
        """Census of real, code-backed parameters. Nothing invented.

        ``current_default`` is the literal in the code; ``effective_value`` is
        what the pipeline actually passes. For top_k they differ: the defaults
        say 3, every call site passes 2.
        """
        if engine_id == self.ENGINE_PERSONA:
            return [
                RAGParameter(
                    "chunking.chunk_size", "Размер чанка (символы)",
                    "src/californian_id/retrieval.py:34", "_chunk_file",
                    800, 800, {"min": 1}, False, True,
                    "LexicalPersonaRetriever.retrieve", "chunking.chunk_size",
                    note="символьное окно после схлопывания пробелов"),
                RAGParameter(
                    "chunking.overlap", "Перекрытие (символы)",
                    "src/californian_id/retrieval.py:34", "_chunk_file",
                    200, 200, {"min": 0}, False, True,
                    "LexicalPersonaRetriever.retrieve", "chunking.overlap",
                    note="шаг окна = chunk_size - overlap"),
                RAGParameter(
                    "retrieval.top_k", "top_k",
                    "src/californian_id/retrieval.py:58", "Pipeline._council_turn",
                    3, 2, {"min": 1, "max": 20}, True, True,
                    "pipeline.py:544,1223", "retrieval.top_k",
                    note="ДЕФОЛТ 3 НЕ ИСПОЛЬЗУЕТСЯ: оба вызова передают 2"),
                RAGParameter(
                    "scoring.bm25_k1", "BM25 k1",
                    "src/californian_id/retrieval.py:85", "retrieve",
                    1.5, 1.5, {"min": 0.0}, False, True,
                    "LexicalPersonaRetriever.retrieve", "scoring.bm25_k1"),
                RAGParameter(
                    "scoring.bm25_b", "BM25 b",
                    "src/californian_id/retrieval.py:85", "retrieve",
                    0.75, 0.75, {"min": 0.0, "max": 1.0}, False, True,
                    "LexicalPersonaRetriever.retrieve", "scoring.bm25_b"),
                RAGParameter(
                    "filtering.min_token_len", "Минимальная длина токена",
                    "src/californian_id/retrieval.py:31", "_tokens",
                    3, 3, {"min": 1}, False, True,
                    "LexicalPersonaRetriever.retrieve", "filtering.min_token_len",
                    note="len(t) > 2"),
                RAGParameter(
                    "filtering.min_score", "Порог попадания в кандидаты",
                    "src/californian_id/retrieval.py:100", "retrieve",
                    0.0, 0.0, {"fixed": "score > 0"}, False, True,
                    "LexicalPersonaRetriever.retrieve", "filtering.min_score",
                    note="жёстко зашитый `if score > 0`, не настраиваемый порог схожести"),
                RAGParameter(
                    "source_bindings.file_types", "Типы файлов корпуса",
                    "src/californian_id/retrieval.py:65", "retrieve",
                    [".md", ".txt"], [".md", ".txt"], None, False, True,
                    "LexicalPersonaRetriever.retrieve", "source_bindings.file_types"),
                RAGParameter(
                    "source_bindings.persona_scoped", "Изоляция корпусов персон",
                    "src/californian_id/retrieval.py:60", "retrieve",
                    True, True, {"fixed": True}, False, True,
                    "pipeline.yaml:30", "source_bindings.persona_scoped",
                    note="no cross-persona bleed — инвариант пайплайна"),
            ]
        if engine_id == self.ENGINE_CARDS:
            return [
                RAGParameter(
                    "retrieval.top_k", "top_k",
                    "src/californian_id/cultural_rag.py:280", "Pipeline._council_turn",
                    3, 2, {"min": 1, "max": 20}, True, True,
                    "pipeline.py:555,630,1230", "retrieval.top_k",
                    note="ДЕФОЛТ 3 НЕ ИСПОЛЬЗУЕТСЯ: все три вызова передают 2"),
                RAGParameter(
                    "filtering.required_function", "Функциональный фильтр карт",
                    "src/californian_id/cultural_rag.py:283", "retrieve_cards",
                    "any", "any", {"enum": "ROUTE_MAP keys"}, True, True,
                    "pipeline.infer_required_function", "filtering.required_function",
                    note="сужает card_type; при пустом результате фильтр снимается"),
                RAGParameter(
                    "filtering.min_score", "Отсечение неположительных",
                    "src/californian_id/cultural_rag.py:299", "retrieve_cards",
                    0.0, 0.0, {"fixed": "score > 0"}, False, True,
                    "retrieve_cards", "filtering.min_score"),
                RAGParameter(
                    "source_bindings.namespace", "Пространство карт",
                    "src/californian_id/cultural_rag.py:CARDS_DIRS", "_load_all_cards",
                    "scenes+operations+constraints+risks",
                    "scenes+operations+constraints+risks", None, False, True,
                    "retrieve_cards", "source_bindings.namespace"),
                RAGParameter(
                    "scoring.algorithm", "Алгоритм ранжирования",
                    "src/californian_id/cultural_rag.py:168", "_bm25_score",
                    "bm25", "bm25", {"fixed": "bm25"}, False, True,
                    "retrieve_cards", "scoring.score_kind"),
            ]
        raise ValueError(f"unknown rag engine: {engine_id}")

    def rag_missing_capabilities(self, engine_id: str) -> list[MissingCapability]:
        """Capabilities this runtime genuinely lacks. Never rendered as knobs."""
        common = [
            MissingCapability("similarity_threshold", "Порог схожести",
                              note="есть только жёсткое `score > 0`, не порог"),
            MissingCapability("reranker", "Ре-ранкер"),
            MissingCapability("diversity_control", "Диверсификация выдачи"),
            MissingCapability("saturation_criterion", "Условие насыщения"),
            MissingCapability("retrieval_budget", "Бюджет извлечения"),
            MissingCapability("query_rewriting", "Переписывание запроса",
                              note="запрос собирается конкатенацией в pipeline.py, "
                                   "LLM-перезаписи нет"),
            MissingCapability("source_weighting", "Веса источников"),
            MissingCapability("embeddings", "Векторный индекс",
                              note="лексический BM25, эмбеддингов нет"),
            MissingCapability("cache", "Кеш извлечения",
                              note="индексы кешируются в процессе, кеша результатов нет"),
        ]
        return common

    def rag_profiles(self) -> list[RAGProfile]:
        """Baseline profiles reconstructed from the code as it runs today."""
        persona = RAGProfile(
            profile_id="rag.persona_lexical.baseline",
            engine_id=self.ENGINE_PERSONA,
            version="0.1.0", state="BASELINE",
            title="persona-scoped BM25 (как в коде)",
            source_bindings={
                "corpus_root": "data/personas/<persona_id>/corpus",
                "file_types": [".md", ".txt"],
                "persona_scoped": True,
                "corpora_present": False,
            },
            chunking={"strategy": "char_window", "chunk_size": 800, "overlap": 200,
                      "normalise_whitespace": True},
            retrieval={"top_k": 2, "query_source": "state.situation.topic"},
            scoring={"algorithm": "bm25", "k1": 1.5, "b": 0.75, "score_kind": "bm25"},
            filtering={"min_token_len": 3, "min_score": 0.0},
            caching={"result_cache": NOT_IMPLEMENTED},
            runtime_binding={"node_id": "retrieve_initial_context",
                             "call_site": "pipeline.py:544,1223"},
            protected_contracts=["EvidenceChunk", "persona_scoped_isolation",
                                 "provenance_required"],
            missing_capabilities=self.rag_missing_capabilities(self.ENGINE_PERSONA),
        )
        cards = RAGProfile(
            profile_id="rag.cultural_cards.baseline",
            engine_id=self.ENGINE_CARDS,
            version="0.1.0", state="BASELINE",
            title="культурные карты Заратустры BM25 (как в коде)",
            source_bindings={
                "namespace": "zarathustra_scenes+operations+constraints+risks",
                "corpus_root": "data/corpus/zarathustra",
                "corpora_present": True,
            },
            chunking={"strategy": "whole_card", "note": "карты не режутся"},
            retrieval={"top_k": 2, "query_source": "topic + operation + persona_id"},
            scoring={"algorithm": "bm25", "score_kind": "bm25"},
            filtering={"required_function": "any", "min_score": 0.0,
                       "fallback_when_empty": "drop_card_type_filter"},
            caching={"index_cache": "process_local", "result_cache": NOT_IMPLEMENTED},
            runtime_binding={"node_id": "cultural_context",
                             "call_site": "pipeline.py:555,630,1230"},
            protected_contracts=["RetrievedCard", "provenance.primary_sources"],
            missing_capabilities=self.rag_missing_capabilities(self.ENGINE_CARDS),
        )
        return [persona, cards]

    def rag_fixtures(self, engine_id: str) -> list[Fixture]:
        """Fixtures the real corpus can actually answer.

        Queries were chosen by probing the shipped corpus, not invented: a query
        the engine answers with zero hits would make baseline↔candidate
        comparison vacuous and hide the very behaviour under test.
        """
        if engine_id == self.ENGINE_CARDS:
            return [
                Fixture("fx_rag_cards_001", "сцена спор истина",
                        "5+ карт с ненулевым BM25 — рабочая фикстура сравнения"),
                Fixture("fx_rag_cards_002", "полифония голос диалог",
                        "вторая фикстура, другой профиль ранжирования"),
                Fixture("fx_rag_cards_003",
                        "ответственность университета за трудоустройство",
                        "негативная фикстура: корпус карт на неё не отвечает (0 хитов)"),
            ]
        return [
            Fixture("fx_rag_persona_001", "ответственность и последствия решения",
                    "корпуса персон в поставке пусты — ожидается 0 чанков"),
        ]

    # ---------------- instrumented retrieval (observation only) ----------

    def run_retrieval(self, profile: RAGProfile, fixture: Fixture,
                      run_id: str, node_id: str) -> RetrievalEvent:
        """Execute the real engine and observe it. No semantics are changed.

        Every field below is either read from the engine's own return values or
        computed from them; nothing is invented and nothing is fed back in.
        """
        started = time.perf_counter()
        candidates: list[RetrievalCandidate] = []
        considered = 0
        corpus_ids: list[str] = []
        index_id = profile.engine_id
        cache_state = "cold"

        if profile.engine_id == self.ENGINE_CARDS:
            from californian_id.cultural_rag import CulturalIndex

            rag = CulturalIndex()
            cards_index, _ = rag._cards_index()
            considered = len(cards_index)
            cache_state = "index_process_cache"
            top_k = int(profile.retrieval.get("top_k", 2))
            required = str(profile.filtering.get("required_function", "any"))
            cards, engine_event = rag.retrieve_cards(
                query=fixture.text, required_function=required, top_k=top_k)
            corpus_ids = [engine_event.namespace]
            # Matched terms are DERIVED from the engine's OWN searchable text
            # (_card_search_text is exactly what BM25 tokenises), not from the
            # title — otherwise the field would be silently empty and useless.
            from californian_id.cultural_rag import _card_search_text

            by_id = {c.get("card_id"): c for c in cards_index}
            q_tokens = set(_rag_tokens(fixture.text))
            for rank, c in enumerate(cards, start=1):
                raw = by_id.get(c.card_id)
                searchable = _card_search_text(raw) if raw else f"{c.title} {c.card_id}"
                text_blob = f"{c.title} {c.card_id}"
                matched = sorted(q_tokens & set(_rag_tokens(searchable)))
                candidates.append(RetrievalCandidate(
                    chunk_id=c.card_id, chunk_hash=_hash(c.card_id + c.file_path),
                    source_id=c.file_path or c.card_id,
                    locator=f"{c.card_type}/{c.card_id}",
                    rank=rank, score=float(c.score), score_kind="bm25",
                    included_in_context=True, context_order=rank,
                    token_count=max(1, round(len(text_blob) / 3.5)),
                    byte_count=len(text_blob.encode("utf-8")),
                    matched_terms=matched,
                    matched_features=[],
                    filters_applied=[f"card_type_in={engine_event.filters.get('card_type_in')}",
                                     f"required_function={required}"],
                    grades={"score": "MEASURED", "rank": "MEASURED",
                            "matched_terms": "DERIVED",
                            "token_count": "ESTIMATED",
                            "matched_features": "UNKNOWN"},
                ))
        elif profile.engine_id == self.ENGINE_PERSONA:
            from californian_id.config import PERSONAS_DIR
            from californian_id.retrieval import LexicalPersonaRetriever

            root = Path(profile.source_bindings.get("corpus_root_abs") or PERSONAS_DIR)
            retriever = LexicalPersonaRetriever(root)
            top_k = int(profile.retrieval.get("top_k", 2))
            persona_id = str(profile.retrieval.get("persona_id") or "LENS_RATIONALIST")
            corpus_ids = [f"{persona_id}/corpus"]
            chunks = retriever.retrieve(persona_id, fixture.text, top_k=top_k)
            considered = len(chunks)
            q_tokens = set(_rag_tokens(fixture.text))
            for rank, ch in enumerate(chunks, start=1):
                candidates.append(RetrievalCandidate(
                    chunk_id=ch.locator, chunk_hash=_hash(ch.text),
                    source_id=ch.source_id, locator=ch.locator,
                    rank=rank, score=float(ch.score), score_kind="bm25",
                    included_in_context=True, context_order=rank,
                    token_count=max(1, round(len(ch.text) / 3.5)),
                    byte_count=len(ch.text.encode("utf-8")),
                    matched_terms=sorted(q_tokens & set(_rag_tokens(ch.text))),
                    filters_applied=["persona_scoped", "score>0"],
                    grades={"score": "MEASURED", "matched_terms": "DERIVED",
                            "token_count": "ESTIMATED"},
                ))
        else:
            raise ValueError(f"unknown rag engine: {profile.engine_id}")

        latency = int((time.perf_counter() - started) * 1000)
        return RetrievalEvent(
            run_id=run_id, node_id=node_id,
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            query_hash=_hash(fixture.text), query_text=fixture.text,
            rewrite_applied=False,
            rag_profile_id=profile.profile_id,
            rag_profile_version=profile.version,
            rag_profile_hash=profile.source_hash(),
            index_id=index_id, index_version=profile.version,
            corpus_ids=corpus_ids, candidates=candidates,
            latency_ms=max(latency, 1), cache_state=cache_state,
            considered_count=considered, returned_count=len(candidates),
            grades={"latency_ms": "MEASURED", "considered_count": "MEASURED",
                    "rewrite_applied": "MEASURED"},
        )

    # ------------------------------------------------------------------
    # fixtures + output validation
    # ------------------------------------------------------------------

    def fixtures(self, asset_id: str) -> list[Fixture]:
        return [
            Fixture(
                fixture_id="fx_scene_reading_001",
                text=("Должен ли университет отвечать за трудоустройство своих "
                      "выпускников? Работодатели жалуются на разрыв между "
                      "программами и практикой, а деканы отвечают, что рынок "
                      "меняется быстрее, чем успевает меняться учебный план."),
                description="короткий нормативный вопрос со скрытой рамкой ответственности",
            ),
            Fixture(
                fixture_id="fx_scene_reading_002",
                text=("— Мы же не бюро трудоустройства.\n"
                      "— А кто тогда? Родители платят за результат.\n"
                      "— Результат — это мышление, а не вакансия."),
                description="короткий транскрипт спора",
            ),
        ]

    def validate_output(self, asset_id: str, raw_text: str) -> tuple[bool, list[str], dict[str, Any]]:
        reasons: list[str] = []
        try:
            from californian_id.zarathustra import _json_from_text
            parsed = _json_from_text(raw_text)
        except Exception as exc:                                  # noqa: BLE001
            return False, [f"output_not_json: {exc}"], {}

        if not isinstance(parsed, dict):
            return False, ["output_not_object"], {}

        for field in CONSUMED_SCENE_FIELDS:
            if field not in parsed:
                reasons.append(f"missing_consumed_field:{field}")

        topic = str(parsed.get("topic") or "")
        if not topic.strip():
            reasons.append("topic_empty")
        if len(topic) > 280:
            reasons.append("topic_too_long")

        genre = str(parsed.get("genre") or "")
        if genre and genre not in _GENRES:
            reasons.append(f"genre_out_of_enum:{genre}")

        return (not reasons), reasons, parsed
