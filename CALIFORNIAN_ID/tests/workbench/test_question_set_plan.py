"""B2Q — Q1..Q18 metamorphic suite + output-level acceptance.

Deterministic. No provider. Proves the plan causally governs the
returned question set on identical inputs.

§4 causal requirement: the final rendering text must be authored
from the plan when the plan is present. Bridge tests validate that.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest


from socrates_runtime.question_set_plan import (
    AUTHORITY, HierarchyPolicy, MetaEscalation, QuestionCandidate,
    QuestionRegime, QuestionSetPlan, StopReason,
    derive_question_set_plan, render_plan_as_text,
)


# ================================================================ helpers


def _op(kind: str = ""):
    return SimpleNamespace(kind=kind, applicable=True, why_not="",
                            open_world_gap=False)


def _scene(telos: str = ""):
    return SimpleNamespace(telos=telos)


def _own(owner: str = "SYSTEM", human_resolved: bool = True):
    return SimpleNamespace(owner=owner, human_resolved=human_resolved,
                            return_reason="")


def _topology(n_forks: int, subs_per: int = 0,
              base: str = "F", label_prefix: str = "Развилка"):
    forks = [{"id": f"{base}{i+1}", "label": f"{label_prefix} {i+1}"}
             for i in range(n_forks)]
    subs = []
    for f in forks:
        for j in range(subs_per):
            subs.append({"parent": f["id"],
                          "id": f"{f['id']}.{j+1}",
                          "label": f"Деталь {j+1} для {f['id']}"})
    return {"forks": forks, "subordinates": subs}


def _derive(request: dict[str, Any],
             *, operation_kind: str = "",
             owner: str = "SYSTEM",
             human_resolved: bool = True) -> QuestionSetPlan | None:
    return derive_question_set_plan(
        scene=_scene(), operation=_op(operation_kind),
        ownership=_own(owner, human_resolved), request=request)


# ================================================================ Q1..Q18


class TestQ1_NoCount_SmallTopology:
    def test_three_peers_no_count_gives_three(self):
        p = _derive({"topology": _topology(3)})
        assert p.total_count == 3
        assert p.primary_count == 3
        assert p.subordinate_count == 0
        assert p.explicit_count_constraint is None
        assert p.stop_reason == StopReason.COVERAGE_SATURATED.value

    def test_three_peers_no_pad_to_10(self):
        p = _derive({"topology": _topology(3)})
        assert p.total_count != 10                          # anti-attractor


class TestQ2_NoCount_LargeTopology:
    def test_eleven_peers_no_count_gives_eleven(self):
        p = _derive({"topology": _topology(11)})
        assert p.total_count == 11
        assert p.primary_count == 11
        assert p.stop_reason == StopReason.COVERAGE_SATURATED.value

    def test_no_arbitrary_small_cap(self):
        p = _derive({"topology": _topology(11)})
        assert p.total_count > 7                              # no default cap


class TestQ3_SameWording_DifferentTopology:
    def test_same_request_shape_but_topology_swap_changes_count(self):
        p_small = _derive({"topology": _topology(3)})
        p_large = _derive({"topology": _topology(11)})
        assert p_small.total_count != p_large.total_count
        assert p_large.total_count > p_small.total_count


class TestQ4_SameTopology_ParaphrasedWording:
    def test_wording_does_not_alter_shape(self):
        """Two callers, same topology, different scene.telos wording —
        plan shape stays the same because derivation reads structured
        state, not text.
        """
        req = {"topology": _topology(6)}
        p1 = derive_question_set_plan(
            scene=_scene(telos="выбрать стратегию запуска"),
            operation=_op(""), ownership=_own(), request=req)
        p2 = derive_question_set_plan(
            scene=_scene(telos="определить путь для нового продукта"),
            operation=_op(""), ownership=_own(), request=req)
        assert p1.total_count == p2.total_count == 6
        assert p1.question_regime == p2.question_regime
        assert p1.selected_level == p2.selected_level


class TestQ5_NoCount_LevelCoherence:
    def test_six_peers_plus_subordinates_no_count_primary_stays_peer(self):
        # topology has 6 peers + 3 subordinates per peer
        p = _derive({"topology": _topology(6, subs_per=3)})
        # No count -> PRIMARY_ONLY at the peer level
        assert p.hierarchy_policy == HierarchyPolicy.PRIMARY_ONLY.value
        assert p.primary_count == 6
        assert p.subordinate_count == 0
        # No mixing subordinates into peer set
        for q in p.selected_questions:
            assert not q.is_subordinate


class TestQ6_ExplicitTen_WithTenPeers:
    def test_exactly_ten_when_ten_peers(self):
        p = _derive({"count": 10, "topology": _topology(10)})
        assert p.total_count == 10
        assert p.primary_count == 10
        assert p.subordinate_count == 0
        assert p.stop_reason == StopReason.EXPLICIT_COUNT_MET.value


class TestQ7_ExplicitTen_ButSixTopLevelForks:
    def test_no_fabrication_of_fake_peers(self):
        # 6 peers + 4 subordinates available => explicit 10 => 6 primary + 4 real subs
        p = _derive({"count": 10, "topology": _topology(6, subs_per=1)})
        # Wait: 6 peers each with 1 sub => 6 subs total. Take 4.
        assert p.primary_count == 6
        assert p.subordinate_count == 4
        assert p.total_count == 10
        assert p.hierarchy_policy == HierarchyPolicy.PRIMARY_PLUS_TYPED_SUBORDINATE.value
        assert p.stop_reason == StopReason.EXPLICIT_COUNT_EXCEEDS_PEERS.value
        # Verify subordinates are TYPED as subordinate
        peers = [q for q in p.selected_questions if not q.is_subordinate]
        subs = [q for q in p.selected_questions if q.is_subordinate]
        assert len(peers) == 6
        assert len(subs) == 4
        # Every subordinate carries a parent_fork_ref
        for s in subs:
            assert s.parent_fork_ref in {"F1", "F2", "F3", "F4", "F5", "F6"}

    def test_no_fake_peer_fabrication_when_no_subordinates_available(self):
        # 6 peers, NO subordinates, N=10 -> honest under-return (6 + 0 = 6),
        # NOT 10 fake peers.
        p = _derive({"count": 10, "topology": _topology(6, subs_per=0)})
        assert p.primary_count == 6
        assert p.subordinate_count == 0
        assert p.total_count == 6                              # < N, honest
        assert p.stop_reason == StopReason.EXPLICIT_COUNT_EXCEEDS_PEERS.value


class TestQ8_AmbiguousButRepresentable:
    def test_representable_ambiguity_does_not_block(self):
        p = _derive({"topology": _topology(4),
                       "ambiguity": {"kind": "REPRESENTABLE",
                                       "grounds": "two framings"}})
        assert p.clarification_required is False
        assert p.total_count == 4


class TestQ9_OperationChangingAmbiguity:
    def test_operation_changing_ambiguity_triggers_clarification(self):
        p = _derive({"topology": _topology(6),
                       "ambiguity": {"kind": "OPERATION_CHANGING",
                                       "grounds": "выбор между стратегией и планом"}})
        assert p.clarification_required is True
        assert p.stop_reason == StopReason.CLARIFICATION_REQUIRED.value
        assert "стратегией и планом" in p.clarification_grounds
        # No questions produced when clarification is required
        assert p.total_count == 0


class TestQ10_DirectAssistance_LowMetaTax:
    def test_ordinary_planning_intent_stays_non_meta(self):
        # Ordinary planning: no "meta" intent, no meta-hint. Should not
        # ascend to REFLECTIVE_OR_META.
        p = _derive({"topology": _topology(4)}, operation_kind="DECIDE")
        assert p.question_regime != QuestionRegime.REFLECTIVE_OR_META.value
        assert p.meta_escalation == MetaEscalation.NONE.value


class TestQ11_MetaIsActuallyTheTask:
    def test_explicit_meta_intent_selects_meta_regime(self):
        p = _derive({"intent": "meta", "topology": _topology(3)})
        assert p.question_regime == QuestionRegime.REFLECTIVE_OR_META.value
        assert p.meta_escalation == MetaEscalation.LEGITIMATE.value


class TestQ12_LexicalPhilosophyDecoy:
    def test_lexical_socratic_bait_does_not_activate_meta_via_regime_hint(self):
        """The regime derivation does NOT inspect user text. Even if
        the scene.telos or operation.kind carry bait, only an
        explicit intent=meta escalates. Here we use a plain planning
        operation with a scene.telos full of philosophical vocabulary.
        """
        req = {"topology": _topology(5)}
        p = derive_question_set_plan(
            scene=_scene(telos="Сократ, Алкивиад, мимесис, майевтика — "
                                "провести планирование квартала"),
            operation=_op("PLAN_QUARTER"),
            ownership=_own(),
            request=req)
        assert p.question_regime != QuestionRegime.REFLECTIVE_OR_META.value
        assert p.meta_escalation == MetaEscalation.NONE.value


class TestQ13_ParaphraseDuplication:
    def test_duplicate_labels_dedupe(self):
        # Two forks with the same label -> dedupe to one primary
        forks = [
            {"id": "F1", "label": "Ускорить"},
            {"id": "F2", "label": "Ускорить"},                # duplicate
            {"id": "F3", "label": "Углубить"},
        ]
        p = _derive({"topology": {"forks": forks, "subordinates": []}})
        assert p.primary_count == 2
        assert p.total_count == 2


class TestQ14_MinorityFork:
    def test_minority_fork_preserved(self):
        # Introduce 4 forks; the last one has a materially distinct
        # label. It must appear in selected_questions.
        forks = [
            {"id": f"F{i}", "label": f"Обычный вариант {i}"} for i in range(3)
        ] + [{"id": "MINOR", "label": "Радикально иная рамка"}]
        p = _derive({"topology": {"forks": forks, "subordinates": []}})
        assert p.primary_count == 4
        refs = {q.fork_ref for q in p.selected_questions}
        assert "MINOR" in refs


class TestQ15_HighStakesHumanOwned:
    def test_human_owned_unresolved_records_ownership_but_does_not_bind(self):
        p = _derive({"count": 5, "topology": _topology(5)},
                     owner="HUMAN", human_resolved=False)
        # Plan runs — it can surface clarifying questions
        assert p.total_count == 5
        assert p.ownership_owner == "HUMAN"
        assert p.ownership_resolved is False
        # Ownership recorded in stop_reason_grounds (evidence)
        assert "human-owned" in p.stop_reason_grounds

    def test_human_owned_resolved_records_no_note(self):
        p = _derive({"count": 3, "topology": _topology(3)},
                     owner="HUMAN", human_resolved=True)
        assert "human-owned" not in p.stop_reason_grounds


class TestQ16_FormatPressureDecoy:
    def test_only_typed_count_activates_N(self):
        """The plan only reads request['count'] for N. Examples/formats
        in the user text can never reach it.
        """
        # No 'count' in request -> plan behaves as no-count
        p = _derive({"topology": _topology(7)})
        assert p.explicit_count_constraint is None
        assert p.total_count == 7                               # topology-driven
        assert p.total_count != 10


class TestQ17_ExplicitCountChangesFormNotOntology:
    def test_six_peer_topology_same_primary_across_count_variants(self):
        topo = _topology(6, subs_per=2)
        a = _derive({"topology": topo})                         # no count
        b = _derive({"count": 10, "topology": topo})             # explicit 10
        # Both plans have the SAME 6 primary peers
        a_peers = [q.fork_ref for q in a.selected_questions if not q.is_subordinate]
        b_peers = [q.fork_ref for q in b.selected_questions if not q.is_subordinate]
        assert a_peers == b_peers
        # b adds real subordinates, not fake peers
        assert b.subordinate_count == 4
        assert b.primary_count == 6


class TestQ18_RoundNumberNegative:
    def test_seven_peers_no_count_returns_seven(self):
        p = _derive({"topology": _topology(7)})
        assert p.primary_count == 7
        assert p.total_count == 7
        assert p.total_count not in (5, 10)                     # no rounding


# ============================================================= §6 output


class TestOutputLevelAcceptance:
    def test_q1_small_topology_output_mapping(self):
        topo = _topology(3)
        p = _derive({"topology": topo})
        # Every selected question maps to a fork id in the topology
        peer_ids = {f["id"] for f in topo["forks"]}
        for q in p.selected_questions:
            assert q.fork_ref in peer_ids
        # No orphans, no padding
        assert len(p.selected_questions) == len(peer_ids)

    def test_q2_large_topology_output_mapping(self):
        topo = _topology(11)
        p = _derive({"topology": topo})
        peer_ids = {f["id"] for f in topo["forks"]}
        for q in p.selected_questions:
            assert q.fork_ref in peer_ids
        assert len(p.selected_questions) == 11

    def test_q7_explicit10_six_peers_hierarchy_survives_public_projection(self):
        p = _derive({"count": 10, "topology": _topology(6, subs_per=1)})
        pub = p.to_public()
        assert pub["primary_count"] == 6
        assert pub["subordinate_count"] == 4
        assert pub["total_count"] == 10
        # Public list preserves is_subordinate flag
        subs = [q for q in pub["selected_questions"] if q["is_subordinate"]]
        peers = [q for q in pub["selected_questions"] if not q["is_subordinate"]]
        assert len(subs) == 4
        assert len(peers) == 6
        # Each subordinate carries parent_fork_ref
        for s in subs:
            assert s["parent_fork_ref"] != ""

    def test_q13_paraphrase_dedupe_no_duplicate_coverage(self):
        forks = [
            {"id": "F1", "label": "Первый"},
            {"id": "F2", "label": "Первый"},          # dup label
            {"id": "F3", "label": "Второй"},
        ]
        p = _derive({"topology": {"forks": forks, "subordinates": []}})
        texts = [q.text for q in p.selected_questions]
        assert len(texts) == len(set(texts))
        assert len(texts) == 2

    def test_q18_seven_peers_output_is_seven(self):
        topo = _topology(7)
        p = _derive({"topology": topo})
        assert len(p.selected_questions) == 7
        # No orphan text without a fork_ref
        for q in p.selected_questions:
            assert q.fork_ref != ""


# ============================================================= structural


class TestStructuralInvariants:
    def test_authority_invariance(self):
        p = _derive({"topology": _topology(3)})
        assert p.authority == AUTHORITY == "NO_TRUTH_STATUS_AUTHORITY"
        assert p.to_public()["authority"] == "NO_TRUTH_STATUS_AUTHORITY"

    def test_none_request_returns_none(self):
        assert derive_question_set_plan(
            scene=_scene(), operation=_op(), ownership=_own(),
            request=None) is None

    def test_derive_does_not_read_user_text(self):
        import inspect
        from socrates_runtime import question_set_plan as m
        src = inspect.getsource(m.derive_question_set_plan)
        for forbidden in ("input_text", ".input_text",
                           "state.input_text"):
            assert forbidden not in src, (
                f"derive_question_set_plan must not read user text: "
                f"found {forbidden!r}")

    def test_no_placeholder_assert_true_in_test_file(self):
        import pathlib, re
        here = pathlib.Path(__file__)
        text = here.read_text(encoding="utf-8")
        forbidden_lines = [ln for ln in text.splitlines()
                            if ln.strip() == "assert True"]
        assert not forbidden_lines
        # Only assert lines (stripped, starting with 'assert ') that
        # END with a tautological `or True` are forbidden. This avoids
        # false positives from f-string message text.
        for ln in text.splitlines():
            stripped = ln.strip()
            if not stripped.startswith("assert "):
                continue
            if re.search(r"\bor\s+True\s*(?:,|$)", stripped):
                raise AssertionError(
                    f"tautological assertion found: {stripped!r}")


# ============================================================= renderer


class TestRenderPlanAsText:
    def test_no_topology_produces_grounded_response(self):
        p = _derive({})
        text = render_plan_as_text(p)
        assert "не составлен" in text
        assert "NO_TOPOLOGY" in text

    def test_three_peers_no_count_produces_three_numbered_lines(self):
        p = _derive({"topology": _topology(3)})
        text = render_plan_as_text(p)
        assert "1." in text
        assert "2." in text
        assert "3." in text
        assert "4." not in text
        assert "Всего: 3" in text

    def test_ten_with_six_peers_shows_hierarchy(self):
        p = _derive({"count": 10, "topology": _topology(6, subs_per=1)})
        text = render_plan_as_text(p)
        assert "Всего: 10" in text
        assert "Подвопросы:" in text
        assert "родитель:" in text
        # 6 primary numbered lines
        for i in (1, 2, 3, 4, 5, 6):
            assert f"{i}. " in text

    def test_clarification_produced_when_required(self):
        p = _derive({"topology": _topology(3),
                       "ambiguity": {"kind": "OPERATION_CHANGING",
                                       "grounds": "TEST-CLARIFICATION-XYZ"}})
        text = render_plan_as_text(p)
        assert "Уточнение обязательно" in text
        assert "TEST-CLARIFICATION-XYZ" in text

    def test_human_owned_unresolved_appends_ownership_note(self):
        p = _derive({"count": 3, "topology": _topology(3)},
                     owner="HUMAN", human_resolved=False)
        text = render_plan_as_text(p)
        assert "принадлежит человеку" in text
        assert "не связывают решение" in text


# ============================================================= bridge


class TestBridgeQuestionSetSurface:
    def test_bridge_surfaces_plan_in_payload(self, monkeypatch):
        monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
        from californian_id.socrates_bridge import dispatch_socrates_run
        request = {
            "count": 10,
            "topology": {
                "forks": [{"id": f"F{i}", "label": f"Fork {i}"}
                          for i in range(6)],
                "subordinates": [
                    {"parent": f"F{i}",
                     "id": f"F{i}.a",
                     "label": f"Detail A for F{i}"}
                    for i in range(6)
                ]}}
        payload = dispatch_socrates_run(
            text="Помоги подумать о выборе.",
            execution_mode="DETERMINISTIC",
            question_set_request=request)
        qsp = payload["question_set_plan"]
        assert qsp is not None
        assert qsp["primary_count"] == 6
        assert qsp["subordinate_count"] == 4
        assert qsp["total_count"] == 10
        assert qsp["stop_reason"] == StopReason.EXPLICIT_COUNT_EXCEEDS_PEERS.value
        assert qsp["authority"] == "NO_TRUTH_STATUS_AUTHORITY"

    def test_bridge_no_request_no_plan(self, monkeypatch):
        """Without question_set_request, the payload's plan is None
        and the runtime's normal rendering path executes."""
        monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
        from californian_id.socrates_bridge import dispatch_socrates_run
        payload = dispatch_socrates_run(
            text="просто вопрос", execution_mode="DETERMINISTIC")
        assert payload["question_set_plan"] is None

    def test_bridge_rendering_text_authored_by_plan(self, monkeypatch):
        """Verify §4 causal requirement: when a plan is present the
        response TEXT comes from the plan, not from the LLM or the
        stochastic renderer.
        """
        monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
        from californian_id.socrates_bridge import dispatch_socrates_run
        payload = dispatch_socrates_run(
            text="анализ",
            execution_mode="DETERMINISTIC",
            question_set_request={"topology": {
                "forks": [{"id": "A", "label": "МАРКЕР-А"},
                           {"id": "B", "label": "МАРКЕР-Б"}],
                "subordinates": []}})
        rendering = payload["rendering"]
        assert rendering is not None
        assert rendering["mode"] == "QUESTION_SET_PLAN_AUTHORED"
        # The plan-authored text contains BOTH fork labels (proof the
        # count/shape came from the plan)
        assert "МАРКЕР-А" in rendering["text"]
        assert "МАРКЕР-Б" in rendering["text"]
        assert "Всего: 2" in rendering["text"]


# ============================================================= regime


class TestRegimeSelection:
    def test_meta_intent_wins(self):
        p = _derive({"intent": "meta", "topology": _topology(3)})
        assert p.question_regime == QuestionRegime.REFLECTIVE_OR_META.value

    def test_explicit_regime_hint_honoured(self):
        p = _derive({"regime": QuestionRegime.FALSIFICATION_OR_COUNTEREXAMPLE.value,
                       "topology": _topology(3)})
        assert p.question_regime == QuestionRegime.FALSIFICATION_OR_COUNTEREXAMPLE.value

    def test_operation_kind_refute_selects_falsification(self):
        p = _derive({"topology": _topology(3)}, operation_kind="REFUTE_CLAIM")
        assert p.question_regime == QuestionRegime.FALSIFICATION_OR_COUNTEREXAMPLE.value

    def test_operation_kind_diagnose_selects_diagnostic(self):
        p = _derive({"topology": _topology(3)}, operation_kind="DIAGNOSE_ROOT_CAUSE")
        assert p.question_regime == QuestionRegime.DIAGNOSTIC.value

    def test_operation_kind_attribute_selects_source(self):
        p = _derive({"topology": _topology(3)}, operation_kind="VERIFY_SOURCE_ATTRIBUTION")
        assert p.question_regime == QuestionRegime.SOURCE_OR_ATTRIBUTION.value

    def test_operation_kind_meta_selects_meta_legitimate(self):
        p = _derive({"topology": _topology(3)},
                     operation_kind="META_REFLECT_ON_QUESTIONING")
        assert p.question_regime == QuestionRegime.REFLECTIVE_OR_META.value
        assert p.meta_escalation == MetaEscalation.LEGITIMATE.value
