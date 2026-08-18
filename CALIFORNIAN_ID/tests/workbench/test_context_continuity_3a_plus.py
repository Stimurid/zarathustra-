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
    ContractRevisionOutcome,
    OperationShiftKind,
    SceneContractStatus,
    derive_scene_contract,
    detect_contract_drift,
    assess_scene_contract_drift,
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


def _hints(telos: str = "answer directly", op: str = "answer",
           materials: tuple[str, ...] = ()) -> dict:
    return {
        "S1": PhaseHint(scene=Scene(
            telos=telos, authority=Authority.SYSTEM, materials=materials)),
        "S3": PhaseHint(origin=Origin(status=ProvenanceStatus.ATTRIBUTED)),
        "S4": PhaseHint(operation=Operation(kind=op, applicable=True)),
        "S6": PhaseHint(ownership=Ownership(owner=Authority.SYSTEM,
                                             human_resolved=True)),
    }


_HIRE_MAT = ("backend hiring plan", "five-person team", "role sequence risks")
_INCIDENT_MAT = ("payment webhook outage", "overnight incident", "postmortem report")
_MAP_MAT = ("corporate training market", "decision map of forks")


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
        c1 = r1.context_continuity["contract"]["contract_id"]
        v1 = r1.context_continuity["contract"]["version"]
        r2 = runtime.run("turn two", hints=_hints(),
                         context_id=cid, context_store=ctx_store)
        assert r2.state.space_id == space1
        assert r2.state.scene_id == r1.state.scene_id
        assert r2.context_continuity["contract"]["contract_id"] == c1
        assert r2.context_continuity["contract"]["version"] == v1
        rp = r2.context_continuity["recognition_pass"]
        assert rp.get("revision_candidates") == []
        applied = " ".join(rp.get("mutations_applied") or [])
        assert "contract_revision_proposed" not in applied
        assert "contract_revision_admitted" not in applied
        assert "contract_revision_held" not in applied

    def test_t2_intent_shift_same_space(self, runtime, ctx_store):
        r1 = runtime.run(
            "first",
            hints=_hints(telos="draft a hiring plan", op="plan",
                         materials=_HIRE_MAT),
            context_store=ctx_store)
        cid = r1.context_id
        c1 = r1.context_continuity["contract"]["contract_id"]
        r2 = runtime.run(
            "second",
            hints=_hints(telos="write an incident postmortem", op="postmortem",
                         materials=_INCIDENT_MAT),
            context_id=cid, context_store=ctx_store)
        assert r2.state.space_id == r1.state.space_id
        rp = r2.context_continuity["recognition_pass"]
        assert rp.get("revision_candidates")
        assert r2.context_continuity["contract"]["contract_id"] == c1
        admissions = rp.get("revision_admissions") or []
        assert admissions
        assert admissions[-1]["outcome"] == "HOLD_PROPOSAL"
        assert admissions[-1]["active_contract_id"] == c1

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
        assert rp.get("clarification_required") is True
        assert "open_world_gap" in (rp.get("clarification_reason") or "")

    def test_t5_contract_drift_history(self, runtime, ctx_store):
        r1 = runtime.run(
            "a", hints=_hints(telos="draft a hiring plan",
                              materials=_HIRE_MAT),
            context_store=ctx_store)
        cid = r1.context_id
        c1 = r1.context_continuity["contract"]["contract_id"]
        r2 = runtime.run(
            "b", hints=_hints(telos="write an incident postmortem",
                              materials=_INCIDENT_MAT),
            context_id=cid, context_store=ctx_store)
        hist = ctx_store.load(cid).contract_history
        assert len(hist) >= 1
        assert any(h["contract_id"] == c1 for h in hist)
        assert ctx_store.load(cid).active_contract_id == c1
        assert r2.context_continuity["contract"]["contract_id"] == c1

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
        from socrates_runtime.context_governance import SurpriseAssessment
        assert SurpriseAssessment.__dataclass_fields__["authority"].default == (
            "NO_TRANSITION_AUTHORITY")

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
    def test_telos_wording_alone_is_not_drift(self):
        state = PipelineState(run_id="r", input_text="x")
        state.scene = Scene(telos="map the hiring options")
        state.operation = Operation(kind="map")
        prior = derive_scene_contract(state)
        state.scene = Scene(telos="chart hiring options for the team")
        drift = detect_contract_drift(prior, state)
        assert drift is None

    def test_operation_kind_alone_is_suboperation_not_drift(self):
        state = PipelineState(run_id="r", input_text="x")
        state.scene_id = "scene_stable"
        state.space_id = "space_default_workspace"
        state.scene = Scene(telos="build a decision map",
                            materials=_MAP_MAT)
        state.operation = Operation(kind="DECISION_MAP")
        prior = derive_scene_contract(state)
        state.operation = Operation(kind="DATA_GAP_IDENTIFICATION")
        assessment = assess_scene_contract_drift(prior, state)
        assert assessment.operation_shift_kind == OperationShiftKind.SUBOPERATION
        assert assessment.material_drift is False
        assert detect_contract_drift(prior, state) is None

    def test_material_object_telos_drift_produces_candidate(self):
        state = PipelineState(run_id="r", input_text="x")
        state.scene_id = "scene_stable"
        state.space_id = "space_default_workspace"
        state.scene = Scene(telos="draft a three-month hiring plan",
                            materials=_HIRE_MAT)
        state.operation = Operation(kind="HIRING_PLAN")
        prior = derive_scene_contract(state)
        state.scene = Scene(telos="write a payment-webhook incident postmortem",
                            materials=_INCIDENT_MAT)
        state.operation = Operation(kind="INCIDENT_POSTMORTEM")
        drift = detect_contract_drift(prior, state)
        assert drift is not None
        assert drift.authority == "NO_TRANSITION_AUTHORITY"
        assert drift.proposed_contract.status == SceneContractStatus.REVISION_PROPOSED
        assert drift.proposed_contract.contract_id != prior.contract_id


class TestContractRevisionRepairR1R8:
    def test_r1_same_intent_paraphrase(self, runtime, ctx_store):
        h = _hints(telos="prepare a seminar on the Republic",
                   op="prepare", materials=("plato republic", "second-year seminar"))
        r1 = runtime.run("first phrasing", hints=h, context_store=ctx_store)
        cid = r1.context_id
        c1 = r1.context_continuity["contract"]["contract_id"]
        v1 = r1.context_continuity["contract"]["version"]
        r2 = runtime.run("restated same work", hints=h,
                         context_id=cid, context_store=ctx_store)
        assert r2.context_id == cid
        assert r2.state.scene_id == r1.state.scene_id
        assert r2.state.space_id == r1.state.space_id
        assert (r2.state.branch_id or "") == (r1.state.branch_id or "")
        assert r2.context_continuity["contract"]["contract_id"] == c1
        assert r2.context_continuity["contract"]["version"] == v1
        rp = r2.context_continuity["recognition_pass"]
        assert not rp.get("revision_candidates")
        applied = " ".join(rp.get("mutations_applied") or [])
        assert "contract_revision" not in applied

    def test_r2_same_scene_suboperation(self, runtime, ctx_store):
        r1 = runtime.run(
            "map",
            hints=_hints(telos="build a decision map for market entry",
                         op="DECISION_MAP", materials=_MAP_MAT),
            context_store=ctx_store)
        cid = r1.context_id
        c1 = r1.context_continuity["contract"]["contract_id"]
        r2 = runtime.run(
            "missing evidence for the same map",
            hints=_hints(telos="build a decision map for market entry",
                         op="DATA_GAP_IDENTIFICATION", materials=_MAP_MAT),
            context_id=cid, context_store=ctx_store)
        assert r2.state.scene_id == r1.state.scene_id
        assert r2.context_continuity["contract"]["contract_id"] == c1
        assert r2.state.operation.kind == "DATA_GAP_IDENTIFICATION"
        rp = r2.context_continuity["recognition_pass"]
        assert not rp.get("revision_candidates")
        da = rp.get("drift_assessment") or {}
        assert da.get("operation_shift_kind") == "SUBOPERATION"
        assert da.get("material_drift") is False

    def test_r3_material_drift_candidate_not_active(self, runtime, ctx_store):
        r1 = runtime.run(
            "hire",
            hints=_hints(telos="draft a three-month hiring plan",
                         op="HIRING_PLAN", materials=_HIRE_MAT),
            context_store=ctx_store)
        cid = r1.context_id
        c1 = r1.context_continuity["contract"]["contract_id"]
        r2 = runtime.run(
            "incident",
            hints=_hints(telos="write a payment-webhook incident postmortem",
                         op="INCIDENT_POSTMORTEM", materials=_INCIDENT_MAT),
            context_id=cid, context_store=ctx_store)
        rp = r2.context_continuity["recognition_pass"]
        assert rp.get("revision_candidates")
        assert r2.context_continuity["contract"]["contract_id"] == c1
        assert ctx_store.load(cid).active_contract_id == c1
        adm = (rp.get("revision_admissions") or [{}])[-1]
        assert adm.get("outcome") == "HOLD_PROPOSAL"
        assert adm.get("active_contract_id") == c1
        proposed = rp["revision_candidates"][0]["proposed_contract"]["contract_id"]
        assert proposed != c1

    def test_r4_material_drift_admit(self, runtime, ctx_store):
        r1 = runtime.run(
            "hire",
            hints=_hints(telos="draft a three-month hiring plan",
                         op="HIRING_PLAN", materials=_HIRE_MAT),
            context_store=ctx_store)
        cid = r1.context_id
        c1 = r1.context_continuity["contract"]["contract_id"]
        r2 = runtime.run(
            "incident",
            hints=_hints(telos="write a payment-webhook incident postmortem",
                         op="INCIDENT_POSTMORTEM", materials=_INCIDENT_MAT),
            context_id=cid, context_store=ctx_store,
            context_action={
                "kind": "CONTRACT_ADMIT_REVISION",
                "human_explicit_choice": True,
            },
        )
        c2 = r2.context_continuity["contract"]["contract_id"]
        assert c2 != c1
        assert r2.context_continuity["contract"]["supersedes"] == c1
        assert r2.context_continuity["contract"]["provenance"] == "USER_EXPLICIT"
        adm = r2.context_continuity["recognition_pass"]["revision_admissions"][-1]
        assert adm["outcome"] == "ADMIT_REVISION"
        assert adm["authority"] == "USER_EXPLICIT"
        assert ctx_store.load(cid).active_contract_id == c2
        hist = ctx_store.load(cid).contract_history
        assert any(h["contract_id"] == c1 for h in hist)
        assert any(h["contract_id"] == c2 for h in hist)
        pub_hist = r2.context_continuity.get("contract_history") or []
        assert any(h["contract_id"] == c1 for h in pub_hist)
        assert r2.context_continuity.get("active_contract_id") == c2

    def test_r5_material_drift_hold(self, runtime, ctx_store):
        r1 = runtime.run(
            "hire",
            hints=_hints(telos="draft a three-month hiring plan",
                         op="HIRING_PLAN", materials=_HIRE_MAT),
            context_store=ctx_store)
        cid = r1.context_id
        c1 = r1.context_continuity["contract"]["contract_id"]
        r2 = runtime.run(
            "incident",
            hints=_hints(telos="write a payment-webhook incident postmortem",
                         op="INCIDENT_POSTMORTEM", materials=_INCIDENT_MAT),
            context_id=cid, context_store=ctx_store)
        assert r2.context_continuity["contract"]["contract_id"] == c1
        held = ctx_store.load(cid).recognition_state.get("held_revision")
        assert held
        assert held["proposed_contract"]["contract_id"] != c1
        assert ctx_store.load(cid).active_contract_id == c1
        applied = " ".join(
            r2.context_continuity["recognition_pass"]["mutations_applied"])
        assert "contract_revision_held:" in applied
        assert "contract_revision_admitted:" not in applied

    def test_r6_user_explicit_confirm_and_edit(self, runtime, ctx_store):
        r1 = runtime.run("start", hints=_hints(), context_store=ctx_store)
        cid = r1.context_id
        c1 = r1.context_continuity["contract"]["contract_id"]
        r2 = runtime.run(
            "confirm", hints=_hints(), context_id=cid, context_store=ctx_store,
            context_action={
                "kind": "CONTRACT_CONFIRM",
                "human_explicit_choice": True,
            },
        )
        assert r2.context_continuity["contract"]["contract_id"] == c1
        assert r2.context_continuity["contract"]["status"] == "CONFIRMED"
        assert r2.context_continuity["contract"]["provenance"] == "USER_EXPLICIT"
        r3 = runtime.run(
            "edit",
            hints=_hints(telos="write a payment-webhook incident postmortem",
                         op="INCIDENT_POSTMORTEM", materials=_INCIDENT_MAT),
            context_id=cid, context_store=ctx_store,
            context_action={
                "kind": "CONTRACT_EDIT",
                "human_explicit_choice": True,
                "fields": {"intent": "user-authored incident postmortem"},
            },
        )
        c3 = r3.context_continuity["contract"]["contract_id"]
        assert c3 != c1
        assert r3.context_continuity["contract"]["intent"] == (
            "user-authored incident postmortem")
        assert r3.context_continuity["contract"]["provenance"] == "USER_EXPLICIT"
        adm = r3.context_continuity["recognition_pass"]["revision_admissions"][-1]
        assert adm["outcome"] == "ADMIT_REVISION"
        assert adm["authority"] == "USER_EXPLICIT"
        # model cannot mint admit without human_explicit_choice
        r4_base = runtime.run(
            "hire2",
            hints=_hints(telos="draft a three-month hiring plan",
                         op="HIRING_PLAN", materials=_HIRE_MAT),
            context_store=ctx_store)
        cid4 = r4_base.context_id
        c4 = r4_base.context_continuity["contract"]["contract_id"]
        r4 = runtime.run(
            "incident2",
            hints=_hints(telos="write a payment-webhook incident postmortem",
                         op="INCIDENT_POSTMORTEM", materials=_INCIDENT_MAT),
            context_id=cid4, context_store=ctx_store,
            context_action={"kind": "CONTRACT_ADMIT_REVISION"},
        )
        assert r4.context_continuity["contract"]["contract_id"] == c4
        adm4 = r4.context_continuity["recognition_pass"]["revision_admissions"][-1]
        assert adm4["outcome"] == "HOLD_PROPOSAL"
        assert adm4["authority"] == "NO_TRANSITION_AUTHORITY"

    def test_r7_paraphrase_stability(self, runtime, ctx_store):
        h = _hints(telos="plan a justice seminar without textbook recap",
                   op="plan", materials=("justice seminar", "plato republic"))
        r1 = runtime.run("p1", hints=h, context_store=ctx_store)
        cid = r1.context_id
        c1 = r1.context_continuity["contract"]["contract_id"]
        for text in ("p2 restated", "p3 another phrasing", "p4 same scene work"):
            r = runtime.run(text, hints=h, context_id=cid, context_store=ctx_store)
            assert r.context_continuity["contract"]["contract_id"] == c1
            assert not r.context_continuity["recognition_pass"].get(
                "revision_candidates")

    def test_r8_rapid_suboperations_one_contract(self, runtime, ctx_store):
        telos = "build a decision map for market entry"
        r1 = runtime.run(
            "map", hints=_hints(telos=telos, op="DECISION_MAP",
                                materials=_MAP_MAT),
            context_store=ctx_store)
        cid = r1.context_id
        c1 = r1.context_continuity["contract"]["contract_id"]
        for op in ("DATA_GAP_IDENTIFICATION", "STRESS_TEST_BRANCH",
                   "COMPARE_OPTIONS"):
            r = runtime.run(
                op, hints=_hints(telos=telos, op=op, materials=_MAP_MAT),
                context_id=cid, context_store=ctx_store)
            assert r.context_continuity["contract"]["contract_id"] == c1
            assert not r.context_continuity["recognition_pass"].get(
                "revision_candidates")
        hist_ids = [h["contract_id"] for h in ctx_store.load(cid).contract_history
                    if h.get("status") != "REVISION_PROPOSED"]
        assert hist_ids.count(c1) == 1
        assert ctx_store.load(cid).active_contract_id == c1


class TestEvaluatorAndB2qrOrdering:
    def test_eval_scripts_contain_no_tautologies(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[2] / "scripts"
        for name in ("eval_3a_plus_live.py", "eval_3a_plus_repair.py"):
            text = (root / name).read_text(encoding="utf-8")
            assert " or True" not in text, name
            assert " and True" not in text, name
            assert "assert True" not in text, name
            assert "if hist else True" not in text, name

    def test_preserve_aporia_outranks_question_overlay(self):
        import inspect
        from socrates_runtime import runtime as m
        from socrates_runtime.governor import InterventionGovernor
        src = inspect.getsource(m.SocratesRuntime.run)
        overlay = src.split("_q_overlayable = {")[1].split("}")[0]
        assert "Terminal.ANSWER" in overlay
        assert "Terminal.CHALLENGE" in overlay
        assert "Terminal.DWELL" in overlay
        assert "PRESERVE_APORIA" not in overlay
        gov_src = inspect.getsource(InterventionGovernor.decide)
        gap_idx = gov_src.index("open_world_gap")
        overlay_note = src.index("_q_overlayable")
        assert "PRESERVE_APORIA" in gov_src[gap_idx:gap_idx + 400]
        # overlay is gated on allowlist; aporia terminal is not overlayable
        assert overlay_note > 0

