"""3C+3D production closure regression suite.

Guards the three defects addressed by the closure repair:

  * D-S26-3D-LIVE-TELOS-001 — same-context continuation with S1 telos
    rephrasing must not fire SCENE_SHIFT; distinction reuse and user-
    hypothesis revision must survive across HTTP request boundaries
    (separate SocratesRuntime instances) sharing one context_id.
  * D-S26-3C-LIVE-REPEAT-001 — apparatus repeat evidence must accumulate
    across HTTP requests (separate SocratesRuntime instances) sharing
    one context_id and reach APPARATUS_MISMATCH_CANDIDATE when warranted,
    but must not leak into a fresh context.
  * D-S26-3C-LIVE-ORGAN-PRIORITY-001 — a PRESERVE_APORIA terminal
    combined with an organ/source gap must classify as GENUINE_APORIA
    with the specific gap type retained as a contributing ground.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from socrates_runtime import SocratesRuntime, Terminal
from socrates_runtime.aporia_and_world_map import (
    GapKind,
    run_apparatus_diagnostic,
)
from socrates_runtime.hybrid_dyad import (
    DyadCategory,
    HypothesisStatus,
    SurpriseClass,
    scene_scope_key,
)
from socrates_runtime.pipeline import PhaseHint
from socrates_runtime.projection import (
    DiagnosticSignal,
    ProjectedObject,
    ProjectionDiagnostics,
    ProjectionResult,
    Residue,
)
from socrates_runtime.state import (
    Authority,
    Operation,
    Ownership,
    PipelineState,
    Scene,
    Terminal as TerminalEnum,
    TerminalOutcome,
)


def _hints(telos: str = "answer directly") -> dict:
    return {
        "S1": PhaseHint(scene=Scene(telos=telos, authority=Authority.SYSTEM)),
        "S4": PhaseHint(operation=Operation(kind="answer", applicable=True)),
        "S6": PhaseHint(ownership=Ownership(owner=Authority.SYSTEM,
                                            human_resolved=True)),
    }


def _inject_mismatch(runtime: SocratesRuntime, *,
                     suggested_operation: str = "EXTRACT_CONCEPTS"):
    inner = runtime.executor.projection_step

    def wrapped(state):
        if inner is not None:
            inner(state)
        diag = ProjectionDiagnostics(
            projection_id="pd_repeat",
            signals=(DiagnosticSignal.OPERATION_MISMATCH,),
            reason="injected typed mismatch for cross-http accumulation",
            residue_ratio=0.6,
            recognition_failure_count=1,
            suggested_operation=suggested_operation)
        state.pending_diagnostic = diag
        state.projection_lineage.add_diagnostics(diag)
        state.projection_lineage.add_projection(ProjectionResult(
            projection_id="pr_repeat",
            spec_fingerprint="fp_repeat",
            source_id=state.source_id,
            objects=[ProjectedObject(
                object_id="o_ok", object_family="concept",
                source_id=state.source_id, source_span=(0, 1),
                evidence="concept", recognition_basis="test")],
            residue=[Residue(
                residue_id="r_lost", source_id=state.source_id,
                source_span=(0, 1), evidence="lost",
                apparent_family="lost", reason="unclassified")],
        ))

    runtime.executor.projection_step = wrapped


# --------------------------------------------------------------- fixture


@pytest.fixture()
def store(tmp_path):
    from californian_id.socrates_context_store import SQLiteContextStore
    return SQLiteContextStore(tmp_path / "closure_ctx.db")


# ============================================================
# CASE A — D-S26-3D-LIVE-TELOS-001: distinction reuse survives
# S1 telos rephrasing across two runtime instances.
# ============================================================
class TestCaseA_DistinctionReuseAcrossTelosRephrase:
    def test_reuse_holds_when_telos_wording_drifts(self, store, tmp_path):
        rt1 = SocratesRuntime(trace_dir=tmp_path / "t1")
        r1 = rt1.run(
            "Distinguish implementation consequence from abstraction.",
            hints=_hints("clarify the distinction requested"),
            context_store=store)
        cid = r1.context_id
        assert cid
        # Turn 2: brand-new runtime instance; deliberately different telos
        # wording (the production S1-drift symptom that was killing reuse).
        rt2 = SocratesRuntime(trace_dir=tmp_path / "t2")
        r2 = rt2.run(
            "Apply that to the next step without reconstructing it.",
            hints=_hints("apply the previously established distinction"),
            context_id=cid, context_store=store)
        d2 = r2.dyad or {}
        assert d2.get("surprise_class") != SurpriseClass.SCENE_SHIFT.value
        assert d2.get("causal_effect") == "reuse_prior_distinction"
        assert d2.get("used_prior_record_ids")
        assert r2.terminal.terminal == Terminal.DISTINGUISH


# ============================================================
# CASE B — D-S26-3D-LIVE-TELOS-001 negative: genuine scene
# boundary within a single in-process session still isolates.
# ============================================================
class TestCaseB_GenuineSceneBoundaryStillIsolates:
    def test_different_telos_without_context_id_still_shifts(self, tmp_path):
        rt = SocratesRuntime(trace_dir=tmp_path / "t")
        rt.run(
            "Distinguish implementation consequence from abstraction.",
            hints=_hints("scene alpha hiring"))
        r2 = rt.run(
            "Apply that to the next step without reconstructing it.",
            hints=_hints("scene beta incident"))
        d2 = r2.dyad or {}
        assert d2.get("surprise_class") == SurpriseClass.SCENE_SHIFT.value
        assert d2.get("causal_effect") != "reuse_prior_distinction"
        assert not d2.get("used_prior_record_ids")


# ============================================================
# CASE C — D-S26-3D-LIVE-TELOS-001: user-hypothesis revision
# survives across two runtime instances sharing context_id.
# ============================================================
class TestCaseC_UserHypothesisRevisionAcrossHttp:
    def test_explicit_reject_revises_across_runtime_instances(
            self, store, tmp_path):
        rt1 = SocratesRuntime(trace_dir=tmp_path / "t1")
        r1 = rt1.run(
            "You will accept interpretation X as the working frame.",
            hints=_hints("frame the working hypothesis"),
            context_store=store)
        cid = r1.context_id
        assert cid
        # Fresh runtime, same context — production LIVE topology exactly.
        rt2 = SocratesRuntime(trace_dir=tmp_path / "t2")
        r2 = rt2.run(
            "I explicitly reject interpretation X.",
            hints=_hints("revise the hypothesis"),
            context_id=cid, context_store=store)
        d2 = r2.dyad or {}
        assert d2.get("surprise_class") == SurpriseClass.INFORMATIVE_SURPRISE.value
        assert d2.get("user_hypothesis_revised") is True
        assert r2.terminal.terminal == Terminal.CHALLENGE


# ============================================================
# CASE E — D-S26-3C-LIVE-REPEAT-001: repeated apparatus
# evidence accumulates across separate runtime instances that
# share one context_id, reaching APPARATUS_MISMATCH_CANDIDATE.
# ============================================================
class TestCaseE_RepeatedProjectionAcumulatesAcrossHttp:
    def test_second_runtime_instance_promotes_to_mismatch_candidate(
            self, store, tmp_path):
        rt1 = SocratesRuntime(trace_dir=tmp_path / "rt1")
        _inject_mismatch(rt1)
        r1 = rt1.run(
            "first cross-http loss", hints=_hints(),
            context_store=store)
        assert (r1.apparatus_diagnostic or {}).get("classification") == (
            GapKind.PROJECTION_GAP.value)
        cid = r1.context_id
        assert cid
        # Fresh runtime — mirrors production HTTP: new SocratesRuntime per
        # request. Without the closure repair, `_apparatus_repeat` here
        # is empty and Order 5 (repeats>=2) is unreachable.
        rt2 = SocratesRuntime(trace_dir=tmp_path / "rt2")
        _inject_mismatch(rt2)
        r2 = rt2.run(
            "second cross-http loss", hints=_hints(),
            context_id=cid, context_store=store)
        ad2 = r2.apparatus_diagnostic or {}
        assert ad2.get("classification") == (
            GapKind.APPARATUS_MISMATCH_CANDIDATE.value)
        assert ad2.get("mismatch_candidate")
        # Authority remains proposal-only — never a durable write.
        assert ad2.get("durable_write_attempted") is False


# ============================================================
# CASE F — D-S26-3C-LIVE-REPEAT-001 negative: a fresh context
# does not inherit accumulated apparatus_repeat state.
# ============================================================
class TestCaseF_RepeatStateIsolatedFromFreshContext:
    def test_new_context_gets_ordinary_projection_gap_not_mismatch(
            self, store, tmp_path):
        # Warm one context to APPARATUS_MISMATCH_CANDIDATE.
        rt1 = SocratesRuntime(trace_dir=tmp_path / "warm1")
        _inject_mismatch(rt1)
        r_warm1 = rt1.run(
            "warm 1", hints=_hints(), context_store=store)
        cid_warm = r_warm1.context_id
        rt2 = SocratesRuntime(trace_dir=tmp_path / "warm2")
        _inject_mismatch(rt2)
        r_warm2 = rt2.run(
            "warm 2", hints=_hints(),
            context_id=cid_warm, context_store=store)
        assert (r_warm2.apparatus_diagnostic or {}).get("classification") == (
            GapKind.APPARATUS_MISMATCH_CANDIDATE.value)
        # Now: a fresh context_id (no context_id passed → new one minted).
        # It must start clean — PROJECTION_GAP, not APPARATUS_MISMATCH_CANDIDATE.
        rt3 = SocratesRuntime(trace_dir=tmp_path / "fresh")
        _inject_mismatch(rt3)
        r_fresh = rt3.run(
            "fresh context first loss", hints=_hints(),
            context_store=store)
        assert r_fresh.context_id != cid_warm
        assert (r_fresh.apparatus_diagnostic or {}).get("classification") == (
            GapKind.PROJECTION_GAP.value)


# ============================================================
# CASE J — D-S26-3C-LIVE-ORGAN-PRIORITY-001: PRESERVE_APORIA
# terminal combined with organ/source gap classifies as
# GENUINE_APORIA with the specific gap retained as contributing
# ground.
# ============================================================
class TestCaseJ_PreserveAporiaOverridesOrganGapForClassification:
    def test_preserve_aporia_plus_source_gap_yields_genuine_aporia(self):
        # Compose a state that reaches Order 1 (organ/source gap → EVIDENCE_GAP)
        # AND an outcome forced to Terminal.PRESERVE_APORIA. The repair
        # promotes classification to GENUINE_APORIA while retaining
        # `contributing:typed_source_or_organ_gap` in grounds.
        state = PipelineState(run_id="r_j", input_text="preserve+organ")
        state.operation = Operation(
            kind="cite", applicable=False, why_not="SOURCE_GAP")
        outcome = TerminalOutcome(
            terminal=Terminal.PRESERVE_APORIA,
            response_text="")
        result = run_apparatus_diagnostic(state, outcome,
                                          input_text=state.input_text)
        pub = result.to_public()
        assert pub["classification"] == GapKind.GENUINE_APORIA.value
        grounds = tuple(pub.get("grounds") or ())
        assert "contributing:typed_source_or_organ_gap" in grounds
        assert "preserve_aporia_terminal_promoted_over_evidence_gap" in grounds

    def test_non_preserve_aporia_source_gap_still_evidence_gap(self):
        # Regression guard: an ordinary source-gap without PRESERVE_APORIA
        # terminal MUST still classify as EVIDENCE_GAP (the pre-repair
        # priority chain is preserved for non-terminal-aporia paths).
        state = PipelineState(run_id="r_j_neg", input_text="ordinary")
        state.operation = Operation(
            kind="cite", applicable=False, why_not="SOURCE_GAP")
        outcome = TerminalOutcome(
            terminal=Terminal.ANSWER, response_text="")
        result = run_apparatus_diagnostic(state, outcome,
                                          input_text=state.input_text)
        assert result.classification == GapKind.EVIDENCE_GAP


# ============================================================
# CASE K — hydration invariants: dyad projection AND
# apparatus_repeat both ride the existing context snapshot,
# not a second database.
# ============================================================
class TestCaseK_NoNewStore:
    def test_repeat_state_persists_on_recognition_state_not_a_new_db(
            self, store, tmp_path):
        rt = SocratesRuntime(trace_dir=tmp_path / "k")
        _inject_mismatch(rt)
        r = rt.run("loss", hints=_hints(), context_store=store)
        cid = r.context_id
        loaded = store.load(cid)
        rec_state = loaded.recognition_state or {}
        assert "apparatus_repeat" in rec_state
        assert isinstance(rec_state["apparatus_repeat"], dict)
        # Sanity: at least one keyed counter recorded.
        assert any(int(v or 0) >= 1
                   for v in rec_state["apparatus_repeat"].values())


# ============================================================
# CASE L — scope-key unit test: verifies the priority order
# (scene_id > telos) used by the dyad seam.
# ============================================================
class TestCaseL_SceneScopeKeyPreference:
    def test_scene_id_wins_over_telos(self):
        state = PipelineState(run_id="rl", input_text="")
        state.scene = Scene(telos="whatever the wording",
                             authority=Authority.SYSTEM)
        state.scene_id = "scn_stable_123"
        assert scene_scope_key(state) == "scene:scn_stable_123"

    def test_telos_fallback_when_no_scene_id(self):
        state = PipelineState(run_id="rl2", input_text="")
        state.scene = Scene(telos="Working On Something",
                             authority=Authority.SYSTEM)
        state.scene_id = ""
        assert scene_scope_key(state) == "telos:working on something"

    def test_default_when_neither(self):
        state = PipelineState(run_id="rl3", input_text="")
        state.scene = Scene(telos="", authority=Authority.SYSTEM)
        state.scene_id = ""
        assert scene_scope_key(state) == "scene:default"
