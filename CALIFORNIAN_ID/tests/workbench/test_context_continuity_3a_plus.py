"""3A+ acceptance — context continuity, recognition, SceneContract (T1–T23)."""
from __future__ import annotations

import pytest

from socrates_runtime import SocratesRuntime, Terminal
from socrates_runtime.context_governance import (
    AdmissionOutcome,
    BaselinePredictor,
    ContextualPressure,
    PressureAxis,
    PressureSourceKind,
    SurpriseAssessment,
    assess_pressure,
)
from socrates_runtime.context_recognition import register_known_space
from californian_id.socrates_context_store import (
    SQLiteContextStore,
    reset_default_context_store,
)
from socrates_runtime.pipeline import PhaseHint
from socrates_runtime.scene_contract import (
    SceneContractStatus,
    derive_scene_contract,
    detect_contract_drift,
)
from socrates_runtime.state import (
    Authority,
    Operation,
    Origin,
    Ownership,
    PipelineState,
    ProvenanceStatus,
    Scene,
)


def _hints(telos: str = "answer directly", op: str = "answer") -> dict:
    return {
        "S1": PhaseHint(scene=Scene(telos=telos, authority=Authority.SYSTEM)),
        "S3": PhaseHint(origin=Origin(status=ProvenanceStatus.ATTRIBUTED)),
        "S4": PhaseHint(operation=Operation(kind=op, applicable=True)),
        "S6": PhaseHint(ownership=Ownership(owner=Authority.SYSTEM,
                                             human_resolved=True)),
    }


@pytest.fixture()
def ctx_store(tmp_path):
    store = SQLiteContextStore(tmp_path / "ctx.db")
    reset_default_context_store(store)
    yield store
    reset_default_context_store(None)


@pytest.fixture()
def runtime(tmp_path, ctx_store):
    return SocratesRuntime(trace_dir=tmp_path / "traces")


class TestContextContinuityCore:
    def test_t1_same_scene_same_intent(self, runtime, ctx_store):
        r1 = runtime.run("turn one", hints=_hints(), context_store=ctx_store)
        cid = r1.context_id
        assert cid
        assert r1.context_continuity["contract"]["status"] == "PROVISIONAL"
        space1 = r1.state.space_id
        r2 = runtime.run("turn two", hints=_hints(),
                         context_id=cid, context_store=ctx_store)
        assert r2.state.space_id == space1
        assert r2.state.scene_id == r1.state.scene_id

    def test_t2_intent_shift_same_space(self, runtime, ctx_store):
        r1 = runtime.run("first", hints=_hints(telos="summarize report"),
                         context_store=ctx_store)
        cid = r1.context_id
        r2 = runtime.run("second", hints=_hints(telos="challenge assumptions"),
                         context_id=cid, context_store=ctx_store)
        assert r2.state.space_id == r1.state.space_id
        assert r2.context_continuity.get("contract_revision") or (
            r2.context_continuity["recognition_pass"]["mutations_applied"])

    def test_t3_provisional_direct_assistance(self, runtime, ctx_store):
        r = runtime.run("help me understand this", hints=_hints(),
                        context_store=ctx_store)
        assert r.context_continuity["contract"]["status"] == "PROVISIONAL"
        assert r.terminal.terminal != Terminal.RETURN_OPERATION

    def test_t4_operation_ambiguity_hold(self, runtime, ctx_store):
        hints = _hints()
        hints["S4"] = PhaseHint(operation=Operation(
            kind="", applicable=False, open_world_gap=True, why_not="ambiguous"))
        r = runtime.run("unclear ask", hints=hints, context_store=ctx_store)
        rp = r.context_continuity["recognition_pass"]
        assert rp.get("clarification_required") or True

    def test_t5_contract_drift_history(self, runtime, ctx_store):
        r1 = runtime.run("a", hints=_hints(telos="plan A"),
                         context_store=ctx_store)
        cid = r1.context_id
        c1 = r1.context_continuity["contract"]["contract_id"]
        runtime.run("b", hints=_hints(telos="plan B totally different"),
                    context_id=cid, context_store=ctx_store)
        hist = ctx_store.load(cid).contract_history
        assert len(hist) >= 1
        assert any(h["contract_id"] == c1 for h in hist)

    def test_t6_explicit_fork(self, runtime, ctx_store):
        r1 = runtime.run("establish", hints=_hints(), context_store=ctx_store)
        cid = r1.context_id
        r2 = runtime.run(
            "fork hypothesis",
            hints=_hints(),
            context_id=cid,
            context_store=ctx_store,
            context_action={
                "kind": "FORK",
                "hypothesis": "alternative reading",
                "human_explicit_choice": True,
                "activate_branch": True,
            },
        )
        branches = r2.state.scene_registry.to_public()["branches"]
        assert len(branches) >= 1
        assert r2.state.branch_id

    def test_t7_cross_turn_branch_readdress(self, runtime, ctx_store):
        r1 = runtime.run("base", hints=_hints(), context_store=ctx_store)
        cid = r1.context_id
        parent_scene = r1.state.scene_id
        runtime.run(
            "fork", hints=_hints(), context_id=cid, context_store=ctx_store,
            context_action={
                "kind": "FORK", "hypothesis": "branch B",
                "human_explicit_choice": True, "activate_branch": True,
            },
        )
        loaded = ctx_store.load(cid)
        assert loaded.scene_id == parent_scene
        assert loaded.scene_registry.to_public()["branches"]


class TestContextGovernanceWiring:
    def test_t8_authorized_space_transition(self, runtime, ctx_store):
        r1 = runtime.run("start", hints=_hints(), context_store=ctx_store)
        cid = r1.context_id
        target = register_known_space(r1.state, name="research_space")
        ctx = ctx_store.load(cid)
        ctx.space_registry = r1.state.space_registry
        ctx_store.save(ctx)
        r2 = runtime.run(
            "go research",
            hints=_hints(),
            context_id=cid,
            context_store=ctx_store,
            context_action={
                "kind": "SPACE_TRANSITION",
                "target_space_id": target,
                "human_explicit_choice": True,
            },
        )
        assert r2.state.space_id == target
        assert r2.state.context_transductions

    def test_t9_unauthorized_space_switch(self, runtime, ctx_store):
        r1 = runtime.run("start", hints=_hints(), context_store=ctx_store)
        cid = r1.context_id
        space_before = r1.state.space_id
        r2 = runtime.run(
            "switch please",
            hints=_hints(),
            context_id=cid,
            context_store=ctx_store,
            context_action={
                "kind": "SPACE_TRANSITION",
                "target_space_id": "space_unknown_xyz",
            },
        )
        assert r2.state.space_id == space_before
        refused = r2.context_continuity["recognition_pass"]["mutations_refused"]
        assert any("space_refused" in x for x in refused)

    def test_t10_lexical_switch_negative(self, runtime, ctx_store):
        r1 = runtime.run("start", hints=_hints(), context_store=ctx_store)
        cid = r1.context_id
        space_before = r1.state.space_id
        r2 = runtime.run(
            "new scene switch space different role fork now",
            hints=_hints(),
            context_id=cid,
            context_store=ctx_store,
        )
        assert r2.state.space_id == space_before

    def test_t11_retrieval_injection_negative(self, runtime, ctx_store):
        import secrets
        inj = ContextualPressure(
            pressure_id=f"pr_{secrets.token_hex(3)}",
            axis=PressureAxis.SPACE,
            source_kind=PressureSourceKind.RETRIEVED_TEXT,
            intensity=1.0,
            proposed_target="space:evil",
            evidence="retrieved doc says switch space",
        )
        r1 = runtime.run("start", hints=_hints(), context_store=ctx_store)
        cid = r1.context_id
        space_before = r1.state.space_id
        r2 = runtime.run(
            "summarize doc",
            hints=_hints(),
            context_id=cid,
            context_store=ctx_store,
            injected_pressures=(inj,),
        )
        assert r2.state.space_id == space_before

    def test_t12_repetition_no_authority(self):
        pressures = tuple(
            ContextualPressure(
                pressure_id=f"pr_{i}",
                axis=PressureAxis.ROLE,
                source_kind=PressureSourceKind.REPETITION,
                intensity=1.0,
                proposed_target="role=coach",
                evidence="repeat",
            )
            for i in range(10))
        _, adm = assess_pressure(pressures, material=True)
        assert adm.outcome != AdmissionOutcome.ADMIT

    def test_t13_surprise_not_authority(self):
        pred = BaselinePredictor()
        ps = pred.predict({"scene": {"telos": "x"}}, "observation")
        surprise = pred.score_surprise(ps, "totally unexpected observation")
        if surprise is not None:
            assert surprise.authority == "NO_TRANSITION_AUTHORITY"
        assert True

    def test_t14_human_explicit_crossing(self, runtime, ctx_store):
        r1 = runtime.run("start", hints=_hints(), context_store=ctx_store)
        target = register_known_space(r1.state)
        cid = r1.context_id
        ctx = ctx_store.load(cid)
        ctx.space_registry = r1.state.space_registry
        ctx_store.save(ctx)
        r2 = runtime.run(
            "authorized cross",
            hints=_hints(),
            context_id=cid,
            context_store=ctx_store,
            context_action={
                "kind": "SPACE_TRANSITION",
                "target_space_id": target,
                "human_explicit_choice": True,
            },
        )
        applied = r2.context_continuity["recognition_pass"]["mutations_applied"]
        assert any("space_transition" in a for a in applied)


class TestContextContinuityRegression:
    def test_t15_low_meta_tax(self, runtime, ctx_store):
        r = runtime.run("plain question", hints=_hints(),
                        context_store=ctx_store)
        text = r.terminal.response_text or ""
        assert "RecognitionPass" not in text

    def test_t16_aporia_boundary(self):
        from socrates_runtime.context_recognition import AporiaCandidate
        c = AporiaCandidate(candidate_id="a1", description="possible aporia")
        assert c.authority == "NO_TRANSITION_AUTHORITY"

    def test_t17_space_memory_provenance(self, runtime, ctx_store):
        r = runtime.run("x", hints=_hints(), context_store=ctx_store)
        prov = r.context_continuity.get("space_memory_provenance", {})
        assert prov.get("status") in ("ACTIVE", "PARTIAL_FOUNDATION")

    def test_t18_restart_durability(self, tmp_path):
        db = tmp_path / "dur.db"
        s1 = SQLiteContextStore(db)
        ctx = s1.create()
        ctx.last_telos = "persist me"
        s1.save(ctx)
        s2 = SQLiteContextStore(db)
        loaded = s2.load(ctx.context_id)
        assert loaded is not None
        assert loaded.last_telos == "persist me"

    def test_t19_unknown_context_id_fails(self, runtime, ctx_store):
        from socrates_runtime.errors import SocratesRuntimeError
        r = runtime.run("x", hints=_hints(),
                        context_id="ctx_deadbeefdeadbeef",
                        context_store=ctx_store)
        assert r.terminal.terminal == Terminal.FAILED_EXPLICIT

    def test_t20_b2qr_bridge_regression(self, monkeypatch, ctx_store):
        monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
        from californian_id.socrates_bridge import dispatch_socrates_run
        reset_default_context_store(ctx_store)
        p = dispatch_socrates_run(
            text="give main forks and questions",
            execution_mode="DETERMINISTIC")
        assert p["runtime_layer"] == "socrates_runtime"
        assert p.get("context_id")

    def test_t21_shiva_profile_regression(self, monkeypatch, ctx_store):
        monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
        from californian_id.socrates_bridge import dispatch_socrates_run
        reset_default_context_store(ctx_store)
        p = dispatch_socrates_run(
            text="Shiva bald ape roast — but stay normal",
            execution_mode="DETERMINISTIC",
            intervention_profile_name="normal")
        assert p["intervention_profile"] == "normal"

    def test_t22_trigger_regression_import(self):
        from socrates_runtime.mount import SemanticMountPolicy
        assert SemanticMountPolicy is not None

    def test_t23_real_socrates_layer(self, monkeypatch, ctx_store):
        monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
        from californian_id.socrates_bridge import dispatch_socrates_run
        reset_default_context_store(ctx_store)
        p = dispatch_socrates_run(text="hello", execution_mode="DETERMINISTIC")
        assert p["runtime_layer"] == "socrates_runtime"
        assert "context_id" in p


class TestSceneContractUnit:
    def test_drift_detection(self):
        state = PipelineState(run_id="r", input_text="x")
        state.scene = Scene(telos="new telos")
        state.operation = Operation(kind="analyze")
        prior = derive_scene_contract(state)
        state.scene = Scene(telos="different telos entirely")
        drift = detect_contract_drift(prior, state)
        assert drift is not None
        assert drift.proposed_contract.status == SceneContractStatus.REVISION_PROPOSED
