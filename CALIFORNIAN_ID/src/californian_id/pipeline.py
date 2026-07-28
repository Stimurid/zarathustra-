"""Main pipeline. Sequential inner council under Zarathustra."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .config import (
    INTERACTION_DIR,
    PACKAGE_ROOT,
    PERSONAS_DIR,
    load_config,
)
from .affect import AffectBook
from .architectonic import TurnDelta, reconstruct_turn_delta
from .argumentation import DisputeAssessment, assess_turn, check_anti_slop
from .cultural_rag import CulturalIndex, infer_required_function
from .interaction import assess_input, detect_repetition, to_security_events
from .ingress import (
    RawStreamEnvelope,
    SemanticUnitsEnvelope,
    envelope_to_unit_pack,
    normalise_envelope,
)
from .memory import ConversationMemory
from .models import Message, build_client
from .personas import PersonaRegistry, load_registry
from .regimes import CRITIQUE_REGIMES, VARIATION_REGIMES
from .retrieval import LexicalPersonaRetriever
from .router_scoring import summarize_route_trace
from .schemas import (
    Action,
    ArgumentMap,
    Assumption,
    Attack,
    BodyProjection,
    ChorusReflection,
    Claim,
    FutureImage,
    OntologicalPremise,
    ProjectAction,
    Question,
    RiskItem,
    SituationAnalysis,
    Support,
    TransformationRecord,
    TurnRecord,
    UnitPack,
    Value,
    to_plain,
)
from .state import RunState
from .trace import TraceRecorder, new_run_id
from .zarathustra import Zarathustra


logger = logging.getLogger("californian_id.pipeline")


@dataclass
class PipelineResult:
    run_state: RunState
    memory: ConversationMemory
    trace_dir: Path


class Pipeline:
    def __init__(self) -> None:
        self.config = load_config()
        self.zarathustra = Zarathustra()
        self.retriever = LexicalPersonaRetriever(PERSONAS_DIR)
        self.cultural = CulturalIndex()

    # ---------- Public entry (raw text) ----------
    def run(
        self,
        text: str,
        mode: str | None = None,
        run_id: str | None = None,
        critique_regime: str = "balanced",
        variation_regime: str = "normal",
    ) -> PipelineResult:
        mode = mode or self.config.default_mode
        critique_regime = critique_regime if critique_regime in CRITIQUE_REGIMES else "balanced"
        variation_regime = variation_regime if variation_regime in VARIATION_REGIMES else "normal"
        run_id = run_id or new_run_id()
        state = RunState(run_id=run_id, mode=mode, input_text=text)
        state.stamp("run_started")
        trace = TraceRecorder(run_id)
        trace.event("run_started", {
            "mode": mode,
            "input_chars": len(text),
            "critique_regime": critique_regime,
            "variation_regime": variation_regime,
        })

        registry = load_registry()
        state.persona_registry_snapshot = registry.snapshot()

        # S01 — intake + security assessment
        findings = assess_input(text)
        state.security_events.extend(to_security_events(findings, turn_index=None))
        for f in findings:
            trace.event("security", {"kind": f.kind, "level": f.level, "detail": f.detail})

        # If input tries to jailbreak Zarathustra: we still analyse the content
        # (it becomes an *object* of analysis), but flag the security event.
        state.transition("ANALYZED")
        situation_reading_provider = self.config.role_provider("zarathustra_situation_reading")
        situation_reading_client = build_client(
            situation_reading_provider,
            self.config.provider_config(situation_reading_provider),
        )
        state.situation = self.zarathustra.analyze_situation(
            text, client=situation_reading_client,
        )
        trace.event("situation", {
            **to_plain(state.situation),
            "reader_provider": situation_reading_client.provider,
        })

        # S02 — cast selection
        mode_cfg = self.config.mode_settings(mode)
        max_voices = int(mode_cfg.get("max_voices", 4))
        max_turns = int(mode_cfg.get("max_turns", 5))

        active_personas = registry.enabled(include_fixtures=True)
        if not active_personas:
            state.errors.append("no personas loaded")
            state.transition("FAILED")
            trace.dump_state(state.as_json())
            return PipelineResult(state, ConversationMemory(topic=state.situation.topic), trace.dir)

        state.selected_personas = self.zarathustra.cast(
            active_personas, state.situation, max_voices
        )
        state.transition("CAST_SELECTED")
        trace.event("cast", {"personas": state.selected_personas, "max_voices": max_voices})

        memory = ConversationMemory(topic=state.situation.topic)
        argument_map = state.argument_map
        state.body.topic = state.situation.topic
        affect = AffectBook()

        state.transition("COUNCIL_RUNNING")

        # ---------- Sequential inner council ----------
        persona_turn_client = build_client(
            self.config.role_provider("persona_turn"),
            self.config.provider_config(self.config.role_provider("persona_turn")),
        )
        routing_client = build_client(
            self.config.role_provider("zarathustra_orchestration"),
            self.config.provider_config(self.config.role_provider("zarathustra_orchestration")),
        )
        synth_client = build_client(
            self.config.role_provider("synthesis"),
            self.config.provider_config(self.config.role_provider("synthesis")),
        )

        already_called: list[str] = []
        registry_ids = state.selected_personas or [p.persona_id for p in active_personas]
        route_traces: list[dict[str, Any]] = []

        for turn_index in range(max_turns):
            state.transition("STOPPING_CHECK")
            if turn_index == 0:
                # Zarathustra opens with a canonical first voice from cast
                first = registry_ids[0]
                decision = self.zarathustra.route_next(
                    routing_client,
                    registry_ids,
                    already_called,
                    state.turns,
                    state.situation,
                    critique_regime=critique_regime,
                    variation_regime=variation_regime,
                )
                if decision.next_persona not in registry_ids:
                    decision = type(decision)(next_persona=first, operation="initial_position", reason="seed")
                else:
                    decision.operation = "initial_position"
                if decision.trace is not None:
                    decision.trace["selected_operation"] = "initial_position"
                    decision.trace["selected_class"] = "stabilize"
            else:
                decision = self.zarathustra.route_next(
                    routing_client,
                    registry_ids,
                    already_called,
                    state.turns,
                    state.situation,
                    critique_regime=critique_regime,
                    variation_regime=variation_regime,
                )
            if decision.trace:
                route_traces.append(decision.trace)
            trace.event("route", {
                "turn_index": turn_index,
                "persona_id": decision.next_persona,
                "operation": decision.operation,
                "reason": decision.reason,
                **(decision.trace or {}),
            })

            state.transition("COUNCIL_RUNNING")
            persona = registry.by_id(decision.next_persona)
            if persona is None:
                state.errors.append(f"router picked unknown persona {decision.next_persona}")
                continue

            evidence = self.retriever.retrieve(persona.persona_id, state.situation.topic, top_k=2)

            # --- B2: cultural cards for THIS turn (advisory but now actually in prompt) ---
            required_fn_for_turn = infer_required_function(
                state.body.snapshot_for_head(max_items=4),
                dispute_hint=(
                    {"fallacies_or_tricks": state.turns[-1].__dict__.get("fallacies", [])}
                    if state.turns else {}
                ),
                active_operation=decision.operation,
            )
            turn_cards, turn_card_event = self.cultural.retrieve_cards(
                query=f"{state.situation.topic} {decision.operation} {persona.persona_id}",
                required_function=required_fn_for_turn,
                top_k=2,
            )
            trace.event("cultural_context_injected", {
                "for_persona": persona.persona_id,
                "for_operation": decision.operation,
                "required_function": required_fn_for_turn,
                "cards": [
                    {"card_id": c.card_id, "card_type": c.card_type,
                     "title": c.title, "reason": c.reason}
                    for c in turn_cards
                ],
            })

            turn = self._run_persona_turn(
                client=persona_turn_client,
                persona=persona,
                situation_topic=state.situation.topic,
                operation=decision.operation,
                turn_index=turn_index,
                prior_turns=state.turns,
                body=state.body,           # <-- голова получает срез тела
                evidence=evidence,
                cultural_cards=turn_cards, # <-- + культурные карты
                routing_reason=decision.reason,
                critique_regime=critique_regime,
                variation_regime=variation_regime,
                route_trace=decision.trace or {},
            )
            state.turns.append(turn)
            already_called.append(persona.persona_id)
            memory.observe_turn(turn)
            _fold_turn_into_argument_map(turn, argument_map)
            _fold_turn_into_body(turn, state.body)

            # Аффект: обновить после хода. Target = предыдущий говорящий, если ход — атака.
            target = state.turns[-2].persona_id if len(state.turns) > 1 else None
            affect.observe(persona.persona_id, decision.operation, target)

            # --- P4: architectonic reconstruction of THIS turn as typed delta ---
            prev_turn = state.turns[-2] if len(state.turns) >= 2 else None
            delta = reconstruct_turn_delta(
                current_body=state.body,
                previous_turn=prev_turn,
                new_turn=turn,
                source_context={"evidence": evidence, "cultural_cards": []},
            )
            trace.event("architectonic_delta", to_plain(delta))

            # --- P4: dispute assessment after each turn ---
            assessment = assess_turn(turn, state.turns[:-1], state.argument_map)
            trace.event("dispute_assessment", assessment.__dict__)
            # Fold high-severity fallacies into security events (visible in output)
            for f in assessment.fallacies_or_tricks:
                from .schemas import SecurityEvent
                state.security_events.append(SecurityEvent(
                    kind=f"argumentation:{f}",
                    level=2,
                    detail=f"turn={turn.turn_index}, persona={turn.persona_id}",
                    turn_index=turn.turn_index,
                ))

            # --- P4: cultural retrieval for NEXT turn hint ---
            body_snap = state.body.snapshot_for_head(max_items=4)
            required_fn = infer_required_function(
                body_snap,
                dispute_hint={
                    "fallacies_or_tricks": assessment.fallacies_or_tricks,
                    "thesis_preserved": assessment.thesis_preserved,
                },
                active_operation=decision.operation,
            )
            cards, card_event = self.cultural.retrieve_cards(
                query=state.situation.topic + " " + turn.utterance[:200],
                required_function=required_fn, top_k=2,
            )
            trace.event("cultural_retrieval", {
                "required_function": required_fn,
                "query_preview": card_event.query[:120],
                "filters": card_event.filters,
                "hits": card_event.hits_card,
            })
            # We do not mutate persona.system_prompt here; cards are advisory
            # and go into trace. Live LLM provider can consume them via prompt
            # module in a future pass.

            trace.event("turn", to_plain(turn))

            # Chorus mode: каждые 2 хода Заратустра проводит рефлексию тела.
            # Не голос, не решение. Пишется в trace и body.chorus_reflections[].
            if (turn_index + 1) % 2 == 0:
                chorus = self.zarathustra.chorus_reflect(state.turns, state.body)
                # Кто молчит — из ВСЕГО реестра линз, а не только из cast'а.
                spoken = {t.persona_id for t in state.turns}
                full_pool = {p.persona_id for p in active_personas}
                chorus.who_is_silent = sorted(full_pool - spoken)
                state.body.chorus_reflections.append(chorus)
                trace.event("chorus", to_plain(chorus))

            # repetition check
            if turn_index > 0:
                overlap = detect_repetition(
                    turn.utterance,
                    [t.utterance for t in state.turns[:-1] if t.persona_id == turn.persona_id],
                )
                if overlap > 0.8:
                    state.security_events.append(
                        _make_repetition_event(overlap, turn_index)
                    )
                    trace.event("repetition_detected", {"score": overlap, "turn_index": turn_index})

            # early stopping
            if self._should_stop(state, mode_cfg, turn_index):
                state.stopping_reason = self._stopping_reason(state, mode_cfg, turn_index)
                break
        else:
            state.stopping_reason = "max_turns_reached"

        state.transition("STOPPING_CHECK")
        state.transition("COMPLETING")

        # Заратустра сначала ВЫБИРАЕТ форму завершения (одну из 10),
        # затем СОБИРАЕТ её. Синтез — только если явно выбран.
        choice = self.zarathustra.choose_completion_form(
            synth_client, state.situation, state.turns, state.argument_map
        )
        trace.event("completion_choice", {"form": choice.form, "reason": choice.reason})

        # P4: anti-slop gate — если candidate = synthesis, но совет не отработал
        # attack_presupposition + defend, форма меняется.
        anti_slop = check_anti_slop(choice.form, state.turns, state.argument_map)
        if not anti_slop.passes_anti_slop:
            trace.event("anti_slop_block", {
                "original_form": choice.form,
                "signals": anti_slop.detected_slop_signals,
                "suggested": anti_slop.suggested_alternative_form,
            })
            choice.form = anti_slop.suggested_alternative_form or "polyphony"
            choice.reason = (
                f"anti-slop gate: {', '.join(anti_slop.detected_slop_signals)} — "
                f"переключено на {choice.form}"
            )

        completion = self.zarathustra.assemble_completion(
            synth_client, choice, state.situation, state.turns, state.argument_map
        )
        state.completion = completion
        # backward-compat: synthesis populated only when form == synthesis
        if completion.form == "synthesis" and completion.synthesis is not None:
            state.synthesis = completion.synthesis
            memory.final_position = completion.synthesis.direct_position
        else:
            memory.final_position = _memory_position_for(completion)

        memory.unresolved_conflicts = [c.__dict__ for c in completion.conflict_map if c.status == "unresolved"]
        memory.security_events = [se.__dict__ for se in state.security_events]

        trace.event("completion", to_plain(completion))
        state.transition("VALIDATING")
        _validate(state)
        state.transition("COMPLETED")
        state.stamp("run_completed")
        trace.event("run_completed", {
            "turns": len(state.turns),
            "stopping_reason": state.stopping_reason,
            "completion_form": completion.form,
            "regime_metrics": summarize_route_trace(route_traces),
        })
        trace.dump_state({"state": state.as_json(), "memory": memory.as_dict()})
        return PipelineResult(state, memory, trace.dir)

    def run_from_envelope(
        self,
        envelope: RawStreamEnvelope | SemanticUnitsEnvelope,
        mode: str | None = None,
        critique_regime: str = "balanced",
        variation_regime: str = "normal",
    ) -> PipelineResult:
        """Run using the official Tinkuy ingress contract."""
        normalized = normalise_envelope(envelope)
        pack = envelope_to_unit_pack(normalized)
        return self.run_from_units(
            pack,
            mode=mode,
            run_id=normalized.run_id,
            critique_regime=critique_regime,
            variation_regime=variation_regime,
        )

    # ---------- Public entry (pre-parsed units from external cutter) ----------
    def run_from_units(
        self,
        pack: UnitPack,
        mode: str | None = None,
        run_id: str | None = None,
        critique_regime: str = "balanced",
        variation_regime: str = "normal",
    ) -> PipelineResult:
        """Seed council state from a UnitPack instead of raw text.

        Skips `analyze_situation` completely: topic/concepts come from unit
        metadata, not from the hardcoded keyword sniffer. Toulmin structures
        become typed argument_map claims/supports/attacks/assumptions.
        Source audit (if present) becomes the first chorus_reflection so
        that Zarathustra knows attribution is unreliable.
        """
        mode = mode or self.config.default_mode
        critique_regime = critique_regime if critique_regime in CRITIQUE_REGIMES else "balanced"
        variation_regime = variation_regime if variation_regime in VARIATION_REGIMES else "normal"
        run_id = run_id or new_run_id()
        input_summary = (
            f"UnitPack: {len(pack.units)} units | "
            f"seminar={pack.seminar_title!r} | "
            f"cutter={pack.cutter_id!r} model={pack.cutter_model!r}"
        )
        state = RunState(run_id=run_id, mode=mode, input_text=input_summary)
        state.stamp("run_started")
        trace = TraceRecorder(run_id)
        trace.event("run_started", {
            "mode": mode,
            "entrypoint": "run_from_units",
            "unit_count": len(pack.units),
            "seminar_title": pack.seminar_title,
            "source_path": pack.source_path,
            "cutter_id": pack.cutter_id,
            "cutter_model": pack.cutter_model,
            "critique_regime": critique_regime,
            "variation_regime": variation_regime,
        })

        registry = load_registry()
        state.persona_registry_snapshot = registry.snapshot()

        # No jailbreak assessment on units (they came from a trusted cutter).
        state.transition("ANALYZED")
        state.situation = _situation_from_pack(pack)
        trace.event("situation", to_plain(state.situation))

        # Seed body from units — this is the whole point.
        state.body.topic = state.situation.topic
        _seed_body_from_pack(state.body, pack)
        _seed_argument_map_from_pack(state.argument_map, pack)
        trace.event("body_seeded", {
            "claims": len(state.argument_map.claims),
            "supports": len(state.argument_map.supports),
            "attacks": len(state.argument_map.attacks),
            "assumptions": len(state.argument_map.assumptions),
            "unresolved_questions": len(state.body.unresolved_questions_from_pack()),
        })

        # Cast + council loop unchanged — reuse `run`'s core.
        mode_cfg = self.config.mode_settings(mode)
        max_voices = int(mode_cfg.get("max_voices", 4))
        max_turns = int(mode_cfg.get("max_turns", 5))

        active_personas = registry.enabled(include_fixtures=True)
        if not active_personas:
            state.errors.append("no personas loaded")
            state.transition("FAILED")
            trace.dump_state(state.as_json())
            return PipelineResult(state, ConversationMemory(topic=state.situation.topic), trace.dir)

        state.selected_personas = self.zarathustra.cast(active_personas, state.situation, max_voices)
        state.transition("CAST_SELECTED")
        trace.event("cast", {"personas": state.selected_personas, "max_voices": max_voices})

        memory = ConversationMemory(topic=state.situation.topic)
        affect = AffectBook()

        persona_turn_client = build_client(
            self.config.role_provider("persona_turn"),
            self.config.provider_config(self.config.role_provider("persona_turn")),
        )
        routing_client = build_client(
            self.config.role_provider("zarathustra_orchestration"),
            self.config.provider_config(self.config.role_provider("zarathustra_orchestration")),
        )
        synth_client = build_client(
            self.config.role_provider("synthesis"),
            self.config.provider_config(self.config.role_provider("synthesis")),
        )

        state.transition("COUNCIL_RUNNING")
        already_called: list[str] = []
        registry_ids = state.selected_personas or [p.persona_id for p in active_personas]
        route_traces: list[dict[str, Any]] = []

        # Chorus turn -1: source-audit signals go in BEFORE the first head speaks.
        if pack.source_audit is not None:
            audit = pack.source_audit
            signals = []
            if audit.ambiguous_vocatives:
                signals.append("attribution_ambiguous")
                signals.extend(audit.ambiguous_vocatives)
            if audit.diarization_defects:
                signals.append(f"diarization_defects_count={len(audit.diarization_defects)}")
            if audit.recognition_damage:
                signals.append(f"OCR_damage_count={len(audit.recognition_damage)}")
            state.body.chorus_reflections.append(ChorusReflection(
                at_turn_index=-1,
                scene_temperature="alert" if signals else "quiet",
                who_speaks_most="",
                who_is_silent=[],
                signals_observed=signals or ["source audit clean"],
                suggested_next_move=(
                    "не приписывать позицию конкретному человеку "
                    "при неоднозначной атрибуции"
                    if signals else "продолжать обычным ходом"
                ),
            ))
            trace.event("source_audit_ingested", {
                "speaker_role_count": len(audit.speaker_roles),
                "diarization_defect_count": len(audit.diarization_defects),
                "recognition_damage_count": len(audit.recognition_damage),
                "ambiguous_vocatives": audit.ambiguous_vocatives,
            })

        for turn_index in range(max_turns):
            state.transition("STOPPING_CHECK")
            decision = self.zarathustra.route_next(
                routing_client,
                registry_ids,
                already_called,
                state.turns,
                state.situation,
                critique_regime=critique_regime,
                variation_regime=variation_regime,
            )
            if turn_index == 0 and decision.next_persona not in registry_ids:
                decision.next_persona = registry_ids[0]
                decision.operation = "initial_position"
            if turn_index == 0 and decision.trace is not None:
                decision.trace["selected_operation"] = "initial_position"
                decision.trace["selected_class"] = "stabilize"
            if decision.trace:
                route_traces.append(decision.trace)
            trace.event("route", {
                "turn_index": turn_index,
                "persona_id": decision.next_persona,
                "operation": decision.operation,
                "reason": decision.reason,
                **(decision.trace or {}),
            })
            state.transition("COUNCIL_RUNNING")
            persona = registry.by_id(decision.next_persona)
            if persona is None:
                state.errors.append(f"router picked unknown persona {decision.next_persona}")
                continue
            evidence = self.retriever.retrieve(persona.persona_id, state.situation.topic, top_k=2)

            required_fn_for_turn = infer_required_function(
                state.body.snapshot_for_head(max_items=4),
                dispute_hint={},
                active_operation=decision.operation,
            )
            turn_cards, turn_card_event = self.cultural.retrieve_cards(
                query=f"{state.situation.topic} {decision.operation} {persona.persona_id}",
                required_function=required_fn_for_turn,
                top_k=2,
            )
            trace.event("cultural_context_injected", {
                "for_persona": persona.persona_id,
                "for_operation": decision.operation,
                "required_function": required_fn_for_turn,
                "cards": [
                    {"card_id": c.card_id, "card_type": c.card_type,
                     "title": c.title, "reason": c.reason}
                    for c in turn_cards
                ],
            })

            turn = self._run_persona_turn(
                client=persona_turn_client,
                persona=persona,
                situation_topic=state.situation.topic,
                operation=decision.operation,
                turn_index=turn_index,
                prior_turns=state.turns,
                body=state.body,
                evidence=evidence,
                cultural_cards=turn_cards,
                routing_reason=decision.reason,
                critique_regime=critique_regime,
                variation_regime=variation_regime,
                route_trace=decision.trace or {},
            )
            state.turns.append(turn)
            already_called.append(persona.persona_id)
            memory.observe_turn(turn)
            _fold_turn_into_argument_map(turn, state.argument_map)
            _fold_turn_into_body(turn, state.body)
            target = state.turns[-2].persona_id if len(state.turns) > 1 else None
            affect.observe(persona.persona_id, decision.operation, target)

            prev_turn = state.turns[-2] if len(state.turns) >= 2 else None
            delta = reconstruct_turn_delta(
                current_body=state.body,
                previous_turn=prev_turn,
                new_turn=turn,
                source_context={"evidence": evidence, "cultural_cards": []},
            )
            trace.event("architectonic_delta", to_plain(delta))
            assessment = assess_turn(turn, state.turns[:-1], state.argument_map)
            trace.event("dispute_assessment", assessment.__dict__)
            for f in assessment.fallacies_or_tricks:
                from .schemas import SecurityEvent
                state.security_events.append(SecurityEvent(
                    kind=f"argumentation:{f}", level=2,
                    detail=f"turn={turn.turn_index}, persona={turn.persona_id}",
                    turn_index=turn.turn_index,
                ))
            trace.event("turn", to_plain(turn))

            if (turn_index + 1) % 2 == 0:
                chorus = self.zarathustra.chorus_reflect(state.turns, state.body)
                spoken = {t.persona_id for t in state.turns}
                full_pool = {p.persona_id for p in active_personas}
                chorus.who_is_silent = sorted(full_pool - spoken)
                state.body.chorus_reflections.append(chorus)
                trace.event("chorus", to_plain(chorus))

            if self._should_stop(state, mode_cfg, turn_index):
                state.stopping_reason = self._stopping_reason(state, mode_cfg, turn_index)
                break
        else:
            state.stopping_reason = "max_turns_reached"

        state.transition("STOPPING_CHECK")
        state.transition("COMPLETING")
        choice = self.zarathustra.choose_completion_form(
            synth_client, state.situation, state.turns, state.argument_map
        )
        trace.event("completion_choice", {"form": choice.form, "reason": choice.reason})
        anti_slop = check_anti_slop(choice.form, state.turns, state.argument_map)
        if not anti_slop.passes_anti_slop:
            trace.event("anti_slop_block", {
                "original_form": choice.form,
                "signals": anti_slop.detected_slop_signals,
                "suggested": anti_slop.suggested_alternative_form,
            })
            choice.form = anti_slop.suggested_alternative_form or "polyphony"
            choice.reason = (
                f"anti-slop gate: {', '.join(anti_slop.detected_slop_signals)} — "
                f"переключено на {choice.form}"
            )
        completion = self.zarathustra.assemble_completion(
            synth_client, choice, state.situation, state.turns, state.argument_map
        )
        state.completion = completion
        if completion.form == "synthesis" and completion.synthesis is not None:
            state.synthesis = completion.synthesis
            memory.final_position = completion.synthesis.direct_position
        else:
            memory.final_position = _memory_position_for(completion)
        memory.unresolved_conflicts = [c.__dict__ for c in completion.conflict_map if c.status == "unresolved"]
        memory.security_events = [se.__dict__ for se in state.security_events]
        trace.event("completion", to_plain(completion))
        state.transition("VALIDATING")
        _validate(state)
        state.transition("COMPLETED")
        state.stamp("run_completed")
        trace.event("run_completed", {
            "turns": len(state.turns),
            "stopping_reason": state.stopping_reason,
            "completion_form": completion.form,
            "entrypoint": "run_from_units",
            "regime_metrics": summarize_route_trace(route_traces),
        })
        trace.dump_state({"state": state.as_json(), "memory": memory.as_dict()})
        return PipelineResult(state, memory, trace.dir)

    # ---------- Persona turn ----------
    def _run_persona_turn(
        self,
        client,
        persona,
        situation_topic: str,
        operation: str,
        turn_index: int,
        prior_turns: list[TurnRecord],
        body: BodyProjection,
        evidence: list,
        cultural_cards: list | None = None,
        routing_reason: str = "",
        critique_regime: str = "balanced",
        variation_regime: str = "normal",
        route_trace: dict[str, Any] | None = None,
    ) -> TurnRecord:
        prior_snippets = [
            f"[{t.persona_id} — {t.operation}]: {t.utterance[:220]}"
            for t in prior_turns[-3:]
        ]
        evidence_snippets = [
            f"[{e.source_id}#{e.locator}]: {e.text[:280]}" for e in evidence
        ]
        body_snapshot = body.snapshot_for_head(max_items=4)
        route_trace = route_trace or {}

        # B2: cultural cards visible to the persona at turn time
        cultural_hints = []
        for c in (cultural_cards or [])[:2]:
            hint = {
                "card_id": c.card_id,
                "card_type": c.card_type,
                "title": c.title,
                "operation": (c.metadata.get("operation") or {}).get("name", ""),
                "activation_conditions": c.metadata.get("activation_conditions", [])[:3],
                "contraindications": c.metadata.get("contraindications", [])[:2],
                "provenance": {
                    "primary_sources": [
                        {"source_id": p.get("source_id"),
                         "locator": p.get("locator")}
                        for p in (c.provenance.get("primary_sources") or [])[:2]
                    ],
                    "provenance_status": c.metadata.get("provenance_status", "unknown"),
                },
            }
            cultural_hints.append(hint)

        user_payload = json.dumps({
            "topic": situation_topic,
            "operation": operation,
            "turn_index": turn_index,
            "critique_regime": critique_regime,
            "variation_regime": variation_regime,
            # Голова видит текущее СОСТОЯНИЕ ОБЩЕГО ТЕЛА.
            "body": body_snapshot,
            "prior_snippets": prior_snippets,
            "evidence": evidence_snippets,
            "routing_contract": {
                "canonical_operation": route_trace.get("canonical_operation"),
                "selected_operation": route_trace.get("selected_operation", operation),
                "selected_class": route_trace.get("selected_class"),
                "recent_operations": route_trace.get("recent_operations", []),
                "recent_classes": route_trace.get("recent_classes", []),
                "selection_reason": route_trace.get("selection_reason", []),
            },
            # B2: культурные карты — не обязательны к цитированию, но входят
            # в контекст. При provenance_status != quoted — не цитировать.
            "cultural_hints": cultural_hints,
            "regime_instruction": {
                "critique": CRITIQUE_REGIMES[critique_regime].directness_hint,
                "variation": VARIATION_REGIMES[variation_regime].prompt_hint,
            },
            "instruction": (
                "Верни JSON согласно схеме persona turn: "
                "persona_id, operation, utterance, claims, assumptions, values, "
                "supports, attacks, actions, questions, confidence. "
                "Реагируй на текущее состояние body (futures, ontological_premises, "
                "risks, projects, transformations), а не только на topic. "
                "Если cultural_hints содержит карту, её operation.name — "
                "рекомендованный способ хода. Не цитируй primary_sources дословно; "
                "используй только как ориентир."
            ),
        }, ensure_ascii=False)

        messages = [
            Message(role="system", content=persona.system_prompt),
            Message(role="user", content=user_payload),
        ]
        result = client.generate(
            messages,
            settings={
                "role": "persona_turn",
                "persona_id": persona.persona_id,
                "operation": operation,
                "topic": situation_topic,
                "attack_target": prior_turns[-1].persona_id if prior_turns else "previous_turn",
                "critique_regime": critique_regime,
                "variation_regime": variation_regime,
            },
        )

        parsed = _parse_persona_turn(result.text, persona.persona_id, operation)
        return TurnRecord(
            turn_index=turn_index,
            persona_id=persona.persona_id,
            operation=operation,
            utterance=parsed["utterance"],
            claims=[Claim(**{**c, "persona_id": persona.persona_id}) for c in parsed["claims"]],
            assumptions=[Assumption(**{**a, "persona_id": persona.persona_id}) for a in parsed["assumptions"]],
            values=[Value(**{**v, "persona_id": persona.persona_id}) for v in parsed["values"]],
            supports=[Support(**{**s, "persona_id": persona.persona_id}) for s in parsed["supports"]],
            attacks=[Attack(**{**a, "persona_id": persona.persona_id}) for a in parsed["attacks"]],
            actions=[Action(**{**a, "persona_id": persona.persona_id}) for a in parsed["actions"]],
            questions=[Question(**{**q, "persona_id": persona.persona_id}) for q in parsed["questions"]],
            confidence=float(parsed.get("confidence", 0.5)),
            routing_reason=routing_reason,
            model_provider=result.provider,
            model_name=result.model,
        )

    # ---------- Stopping ----------
    def _should_stop(self, state: RunState, mode_cfg: dict[str, Any], turn_index: int) -> bool:
        if turn_index + 1 >= int(mode_cfg.get("max_turns", 5)):
            return True
        stopping = mode_cfg.get("stopping", {}) or {}
        need_minority = bool(stopping.get("require_minority_voice", False))
        if need_minority:
            distinct = {t.persona_id for t in state.turns}
            if len(distinct) < 2:
                return False
        # Novelty check: if the last two turns are near-duplicates, stop
        if len(state.turns) >= 2:
            last, prev = state.turns[-1], state.turns[-2]
            score = detect_repetition(last.utterance, [prev.utterance])
            if score > 0.85:
                state.novelty_scores.append(1.0 - score)
                return True
        return False

    def _stopping_reason(self, state: RunState, mode_cfg: dict[str, Any], turn_index: int) -> str:
        if turn_index + 1 >= int(mode_cfg.get("max_turns", 5)):
            return "max_turns_reached"
        return "novelty_exhausted"


# --------- helpers ---------
def _fold_turn_into_argument_map(turn: TurnRecord, amap: ArgumentMap) -> None:
    amap.claims.extend(turn.claims)
    amap.assumptions.extend(turn.assumptions)
    amap.values.extend(turn.values)
    amap.supports.extend(turn.supports)
    amap.attacks.extend(turn.attacks)
    amap.actions.extend(turn.actions)
    amap.questions.extend(turn.questions)


def _fold_turn_into_body(turn: TurnRecord, body: BodyProjection) -> None:
    """Каждый ход изменяет общее тело Змея — по семантике своей операции.

    Это ключевая механика Пика 2: тело меняется, а следующая голова
    видит уже изменённое состояние.
    """
    body.voices_history.append({
        "persona_id": turn.persona_id,
        "operation": turn.operation,
        "turn_index": turn.turn_index,
    })
    op = turn.operation
    if op == "build_future_image":
        body.futures.append(FutureImage(
            persona_id=turn.persona_id,
            utterance=turn.utterance,
            horizon="unspecified",
        ))
    elif op == "attack_presupposition":
        # тезис голоса — это и есть вскрытая предпосылка
        for a in turn.assumptions:
            body.ontological_premises.append(OntologicalPremise(
                exposed_by=turn.persona_id,
                text=a.text,
                target="previous_turn",
            ))
        if not turn.assumptions:
            body.ontological_premises.append(OntologicalPremise(
                exposed_by=turn.persona_id,
                text=turn.utterance,
                target="previous_turn",
            ))
    elif op == "show_cost":
        body.risks.append(RiskItem(
            named_by=turn.persona_id,
            text=turn.utterance,
        ))
    elif op == "draw_practical_implication":
        for act in turn.actions:
            body.projects.append(ProjectAction(
                proposed_by=turn.persona_id,
                action=act.text,
            ))
        if not turn.actions:
            body.projects.append(ProjectAction(
                proposed_by=turn.persona_id,
                action=turn.utterance,
            ))
    elif op in {"problematize_question", "shift_ontology"}:
        body.transformations.append(TransformationRecord(
            performed_by=turn.persona_id,
            from_question=body.topic,
            to_question=turn.utterance,
            what_reveals="исходная постановка не удерживает существенное",
        ))
    elif op == "propose_alliance":
        body.alliances_proposed.append({
            "proposed_by": turn.persona_id,
            "action": turn.utterance,
        })
    elif op == "refuse_alliance":
        body.alliances_refused.append({
            "refused_by": turn.persona_id,
            "reason": turn.utterance,
        })


def _make_repetition_event(score: float, turn_index: int):
    from .schemas import SecurityEvent
    return SecurityEvent(
        kind="repetition",
        level=1,
        detail=f"near-duplicate persona utterance, jaccard={score:.2f}",
        turn_index=turn_index,
    )


def _validate(state: RunState) -> None:
    """Contract checks — surface as errors but do not corrupt state.

    Post-Пик-1: синтез больше НЕ обязателен. Обязательно только:
      - непустая completion с валидной form;
      - для формы synthesis — непустое direct_position или сохранённые minorities;
      - для любой другой формы — своя специфичная валидация.
    """
    from .schemas import COMPLETION_FORMS
    if not state.turns and state.completion is None:
        state.errors.append("council produced zero turns and no completion")
        return
    c = state.completion
    if c is None:
        state.errors.append("no completion assembled")
        return
    if c.form not in COMPLETION_FORMS:
        state.errors.append(f"invalid completion form: {c.form}")
        return
    # Per-form contract checks:
    if c.form == "synthesis":
        if c.synthesis is None:
            state.errors.append("form=synthesis but synthesis object missing")
        elif c.synthesis.direct_position == "" and not c.minority_positions:
            state.errors.append("synthesis is empty and preserved no minority voice")
    elif c.form == "decision_with_dissent" and not c.decision:
        state.errors.append("form=decision_with_dissent but decision text missing")
    elif c.form == "aporia" and not c.aporia_statement:
        state.errors.append("form=aporia but aporia_statement missing")
    elif c.form == "transformed_question" and not c.transformed_question:
        state.errors.append("form=transformed_question but transformed_question missing")
    elif c.form == "world_fork" and not c.world_branches:
        state.errors.append("form=world_fork but no world branches assembled")
    elif c.form == "delegation" and not c.delegated_to:
        state.errors.append("form=delegation but no delegated_to persona")
    elif c.form == "polyphony" and not c.polyphonic_voices:
        state.errors.append("form=polyphony but no polyphonic_voices")
    elif c.form == "alliance" and c.alliance is None:
        state.errors.append("form=alliance but no alliance record")
    elif c.form == "refusal_to_close" and not c.refusal_reason:
        state.errors.append("form=refusal_to_close but no reason recorded")

    distinct = {t.persona_id for t in state.turns}
    if len(distinct) < 2 and len(state.turns) >= 2:
        state.errors.append("only one distinct voice spoke over multiple turns")


def _situation_from_pack(pack: UnitPack) -> SituationAnalysis:
    """Строит situation НАПРЯМУЮ из UnitPack, минуя заточенный словарь."""
    concepts: list[str] = []
    seen = set()
    for u in pack.units:
        for c in u.key_concepts:
            if c not in seen:
                seen.add(c)
                concepts.append(c)
    tensions = []
    for u in pack.units:
        if u.toulmin and (u.toulmin.rebuttal or u.toulmin.counterclaim):
            tensions.append(f"{u.unit_id}: {u.title[:120]}")
    intentions = {u.intention for u in pack.units if u.intention}
    genre = "long_form"
    if any(i in intentions for i in ("аргументация", "проблематизация")):
        genre = "normative"
    return SituationAnalysis(
        topic=pack.seminar_title or (pack.units[0].title if pack.units else "unnamed pack"),
        genre=genre,
        stakes=[],  # намеренно пусто — не выдумываем, если резчик не сказал
        horizons=[],
        concepts=concepts[:20],
        tensions=tensions[:10],
        uncertainties=[],
    )


def _seed_body_from_pack(body, pack: UnitPack) -> None:
    body.seeded_from_units = [u.unit_id for u in pack.units]
    body.pack_unresolved_questions = list(pack.unresolved_questions_pack)
    # per-unit unresolved
    for u in pack.units:
        for q in u.unresolved_questions_here:
            if q not in body.pack_unresolved_questions:
                body.pack_unresolved_questions.append(q)


def _seed_argument_map_from_pack(amap: ArgumentMap, pack: UnitPack) -> None:
    """Toulmin структура резчика → typed claims/supports/attacks/assumptions."""
    for u in pack.units:
        pid_hint = _dominant_participant(u)
        # Тема-Рема → claims
        for tr in u.theme_rheme:
            amap.claims.append(Claim(
                text=f"[{u.unit_id}/{tr.theme}] {tr.rheme[:280]}",
                confidence=0.7,
                source=tr.locator or None,
                persona_id=tr.participant_label or pid_hint,
            ))
        # Toulmin
        if u.toulmin:
            t = u.toulmin
            if t.claim:
                amap.claims.append(Claim(
                    text=f"[{u.unit_id}/claim] {t.claim[:280]}",
                    confidence=0.85,
                    persona_id=pid_hint,
                ))
            if t.data:
                amap.supports.append(Support(
                    target=f"{u.unit_id}/claim",
                    text=t.data[:280],
                    persona_id=pid_hint,
                ))
            if t.warrant:
                amap.assumptions.append(Assumption(
                    text=f"[{u.unit_id}/warrant] {t.warrant[:280]}",
                    persona_id=pid_hint,
                    exposed_by=None,
                ))
            if t.rebuttal:
                amap.attacks.append(Attack(
                    target=f"{u.unit_id}/claim",
                    text=f"[rebuttal] {t.rebuttal[:280]}",
                    persona_id=pid_hint,
                ))
            if t.counterclaim:
                amap.attacks.append(Attack(
                    target=f"{u.unit_id}/claim",
                    text=f"[counterclaim] {t.counterclaim[:280]}",
                    persona_id=t.counter_persona or pid_hint,
                ))
        # unresolved
        for q in u.unresolved_questions_here:
            amap.questions.append(Question(text=q, persona_id=pid_hint, unresolved=True))


def _dominant_participant(u) -> str | None:
    if not u.participants:
        return None
    for p in u.participants:
        if p.name:
            return p.name
    for p in u.participants:
        if p.normalized_role:
            return p.normalized_role
    return u.participants[0].label or None


def _memory_position_for(completion) -> str:
    """Короткая текстовая метка позиции для conversation memory."""
    form = completion.form
    if form == "synthesis" and completion.synthesis:
        return completion.synthesis.direct_position
    if form == "decision_with_dissent":
        return f"[decision_with_dissent] {completion.decision[:220]}"
    if form == "aporia":
        return f"[aporia] {completion.aporia_statement[:220]}"
    if form == "transformed_question":
        return f"[transformed_question] {completion.transformed_question[:220]}"
    if form == "world_fork":
        labels = ", ".join(b.label for b in completion.world_branches)
        return f"[world_fork] {labels}"
    if form == "delegation":
        return f"[delegation → {completion.delegated_to}] {completion.delegated_utterance[:200]}"
    if form == "polyphony":
        return f"[polyphony of {len(completion.polyphonic_voices)} voices]"
    if form == "alliance" and completion.alliance:
        return f"[alliance of {', '.join(completion.alliance.partners)}] {completion.alliance.action}"
    if form == "unresolvable_conflict":
        return f"[unresolvable_conflict] {len(completion.incompatible_pictures)} несводимых картин"
    if form == "refusal_to_close":
        return f"[refusal_to_close] {completion.refusal_reason[:220]}"
    return f"[{form}]"


def _parse_persona_turn(text: str, persona_id: str, operation: str) -> dict[str, Any]:
    import re
    text = (text or "").strip()
    try:
        if text.startswith("{"):
            data = json.loads(text)
        else:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise ValueError("no json")
            data = json.loads(match.group(0))
    except Exception:
        data = {
            "utterance": text[:400] or f"[{persona_id}] пустой ход по операции {operation}",
            "claims": [], "assumptions": [], "values": [],
            "supports": [], "attacks": [], "actions": [], "questions": [],
            "confidence": 0.3,
        }
    return {
        "utterance": str(data.get("utterance", ""))[:1200],
        "claims": _norm_list(data.get("claims"), {"text", "confidence", "source"}),
        "assumptions": _norm_list(data.get("assumptions"), {"text", "exposed_by"}),
        "values": _norm_list(data.get("values"), {"text"}),
        "supports": _norm_list(data.get("supports"), {"target", "text"}),
        "attacks": _norm_list(data.get("attacks"), {"target", "text"}),
        "actions": _norm_list(data.get("actions"), {"text"}),
        "questions": _norm_list(data.get("questions"), {"text", "unresolved"}),
        "confidence": data.get("confidence", 0.5),
    }


def _norm_list(items: Any, allowed: set[str]) -> list[dict[str, Any]]:
    if not items:
        return []
    out: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, str):
            out.append({"text": item})
        elif isinstance(item, dict):
            filt = {k: v for k, v in item.items() if k in allowed}
            if "text" not in filt and "target" not in filt:
                continue
            out.append(filt)
    return out
