"""Socrates runtime — S0–S10 executable, deterministic mount, honest failures."""
from __future__ import annotations

import ast
import json
import re
import sys
import tempfile
from pathlib import Path

import pytest

from socrates_runtime import (
    SemanticContextBudgetExceeded,
    SemanticMountMissing,
    SocratesIdentity,
    SocratesRunConfiguration,
    SocratesRuntime,
    Terminal,
)
from socrates_runtime.errors import (
    ConditionalTriggerRejected,
    HistoricalFallbackForbidden,
)
from socrates_runtime.governor import InterventionGovernor
from socrates_runtime.mount import (
    REJECTION_LEXICAL_ONLY,
    REJECTION_NON_MATERIAL,
    REJECTION_NO_TYPED_STATE_BASIS,
    REJECTION_PHASE_IRRELEVANT,
    REJECTION_UNAUTHORIZED_SOURCE,
    SemanticMountPolicy,
    TriggerAdmission,
)
from socrates_runtime.pipeline import PhaseHint
from socrates_runtime.routers import RouterRegistry
from socrates_runtime.semantic import SemanticBodyRegistry
from socrates_runtime.state import (
    Authority,
    MemoryProposal,
    Operation,
    Origin,
    Ownership,
    PipelineState,
    ProvenanceStatus,
    Scene,
)

SRC = Path(__file__).resolve().parents[2] / "src"
DATA = Path(__file__).resolve().parents[2] / "data" / "socrates"


# --------------------------------------------------------- fixtures

@pytest.fixture(autouse=True)
def _mock_provider(monkeypatch):
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")


@pytest.fixture()
def runtime(tmp_path):
    return SocratesRuntime(trace_dir=tmp_path / "traces")


@pytest.fixture()
def registry():
    return SemanticBodyRegistry()


@pytest.fixture()
def mount(registry):
    return SemanticMountPolicy(registry)


# --------------------------------------------------------- import integrity


def test_import_manifest_lists_11_current_bodies():
    mpath = DATA / "IMPORT_MANIFEST.yaml"
    text = mpath.read_text(encoding="utf-8")
    try:
        import yaml
        data = yaml.safe_load(text)
    except ImportError:
        data = json.loads(text)
    assert data["source_bundle_sha256"] == (
        "12b4e621a808aec16d70f4a25bc86fb66e7999cec5f9184ea0fefbd9ef04f245")
    files = data["files"]
    semantic = [f for f in files if f["repo_path"].startswith("current/semantic/")
                                    and f["repo_path"].endswith(".md")]
    ids = sorted({_body_id(f["repo_path"]) for f in semantic if _body_id(f["repo_path"])})
    assert ids == ["B01", "B02", "B03", "B04", "B05", "B06",
                   "B07", "B08", "B09", "B10", "CORE"]


def test_current_control_ablation_are_separately_addressable():
    """CURRENT | CONTROL | ABLATION are separate directory trees.

    A path prefix check is stronger than a role field, because a file
    accidentally imported into the wrong tree stays visibly wrong.
    """
    manifest = DATA / "IMPORT_MANIFEST.yaml"
    try:
        import yaml
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except ImportError:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    files = data["files"]
    current = [f for f in files if f["repo_path"].startswith("current/")]
    controls = [f for f in files if f["repo_path"].startswith(
        "controls/g_s25_historical/")]
    ablation = [f for f in files
                if "/C_ABLATION_" in f["repo_path"]]
    assert current, "current/ tree is empty"
    assert controls, "controls/g_s25_historical/ is empty"
    assert ablation, "ablation arms not addressable by naming"
    assert set(f["role"] for f in current) <= {"CURRENT"}
    assert set(f["role"] for f in controls) <= {"CONTROL"}
    assert set(f["role"] for f in ablation) <= {"ABLATION"}


def _body_id(path: str) -> str:
    name = Path(path).name.upper()
    for i in range(1, 11):
        if name.startswith(f"B{i:02d}_"):
            return f"B{i:02d}"
    if "_CORE_" in name or name.startswith("CORE"):
        return "CORE"
    return ""


# --------------------------------------------------------- semantic registry


def test_registry_loads_core_and_all_ten_bodies(registry):
    assert set(registry.all_ids()) == {"CORE", "B01", "B02", "B03", "B04",
                                        "B05", "B06", "B07", "B08", "B09",
                                        "B10"}
    core = registry.get("CORE")
    assert core.semantic_version.startswith("0.2")
    assert core.bytes > 0 and len(core.sha256) == 64
    assert core.text.strip()


def test_registry_refuses_summary_substitution(registry):
    from socrates_runtime.errors import SemanticSummarySubstitutionAttempted
    with pytest.raises(SemanticSummarySubstitutionAttempted):
        registry.get_summary("B01")


# --------------------------------------------------------- mount deterministic


def test_core_always_mounts(mount):
    ctx = mount.mount(router_id="P00", phase="S0")
    assert "CORE" in ctx.body_ids()


def test_phase_required_bodies_come_from_manifest(mount):
    ctx = mount.mount(router_id="P01", phase="S1")
    assert set(b.body_id for b in ctx.required) == {"CORE", "B01"}


def test_mount_records_byte_budget(mount):
    ctx = mount.mount(router_id="P00", phase="S0")
    assert ctx.total_bytes > 0
    assert ctx.budget_bytes > 0


# --------------------------------------------------------- conditional admission


def test_typed_state_trigger_is_admitted(mount):
    """MEMORY_RECRUITMENT is a legitimate P02-conditional trigger (mounts B05)."""
    triggers = [TriggerAdmission(
        trigger_id="MEMORY_RECRUITMENT",
        generating_state_ref="state.origin.temporal_stale",
        cause_object_ref="memory.working_memory_query",
        source_status="typed_state",
        phase_relevance="P02",
        materiality_reason="prior binding needs to be recalled")]
    ctx = mount.mount(router_id="P02", phase="S3", proposed_triggers=triggers)
    assert len(ctx.admitted_triggers) == 1
    # B05 IS in P02's conditional set and MEMORY_RECRUITMENT triggers it,
    # so the body was actually mounted, not just the trigger admitted.
    assert any(b.body_id == "B05" for b in ctx.conditional_admitted)
    assert not ctx.rejected_triggers


def test_lexical_only_trigger_is_rejected(mount):
    triggers = [TriggerAdmission(
        trigger_id="MEMORY_RECRUITMENT",
        generating_state_ref="",              # no typed state
        cause_object_ref="memory.working_memory_query",
        source_status="model_prior",           # unauthorized source
        phase_relevance="P02",
        materiality_reason="model saw a familiar word")]
    ctx = mount.mount(router_id="P02", phase="S3", proposed_triggers=triggers)
    assert not ctx.admitted_triggers
    assert ctx.rejected_triggers
    assert ctx.rejected_triggers[0]["rejection_reason"] == REJECTION_UNAUTHORIZED_SOURCE


def test_duplicate_cause_coalesces(mount):
    """CTA-004 — same (trigger_id, cause_object_ref) never inflates authority."""
    t = TriggerAdmission(trigger_id="MEMORY_RECRUITMENT",
                          generating_state_ref="state.origin.temporal_stale",
                          cause_object_ref="memory.working_memory_query",
                          source_status="typed_state",
                          phase_relevance="P02",
                          materiality_reason="prior binding")
    dup = TriggerAdmission(trigger_id="MEMORY_RECRUITMENT",
                            generating_state_ref="state.origin.temporal_stale",
                            cause_object_ref="memory.working_memory_query",
                            source_status="typed_state",
                            phase_relevance="P02",
                            materiality_reason="prior binding (rephrased)")
    ctx = mount.mount(router_id="P02", phase="S3",
                      proposed_triggers=[t, dup])
    assert len(ctx.admitted_triggers) == 1
    assert any(r["rejection_reason"] == "DUPLICATE_CAUSE"
               for r in ctx.rejected_triggers)


def test_phase_irrelevant_trigger_rejected(mount):
    t = TriggerAdmission(trigger_id="SCENE_TRANSITION",
                          generating_state_ref="state.scene",
                          cause_object_ref="scene.epoch",
                          source_status="typed_state",
                          phase_relevance="P01",   # ok for P01, not P07
                          materiality_reason="new scene")
    ctx = mount.mount(router_id="P07", phase="S8", proposed_triggers=[t])
    assert not ctx.admitted_triggers
    assert ctx.rejected_triggers[0]["rejection_reason"] == REJECTION_PHASE_IRRELEVANT


# --------------------------------------------------------- context budget


def test_context_budget_fail_closed(registry, mount):
    tight = SemanticMountPolicy(registry, budget_bytes=1_000)
    with pytest.raises(SemanticContextBudgetExceeded):
        tight.mount(router_id="P00", phase="S0")


# --------------------------------------------------------- historical fallback


def test_historical_fallback_is_forbidden(mount):
    with pytest.raises(HistoricalFallbackForbidden):
        mount.refuse_historical_fallback("adversarial_caller")


# --------------------------------------------------------- routers


def test_routers_cover_all_ten_p_modules():
    reg = RouterRegistry()
    assert [r.module_id for r in reg.all()] == [f"P{i:02d}" for i in range(10)]


def test_every_pipeline_phase_has_a_router():
    reg = RouterRegistry()
    for phase in ("S0", "S1", "S2", "S3", "S4", "S5",
                  "S6", "S7", "S8", "S9", "S10"):
        assert reg.router_for_phase(phase) is not None


def test_no_router_permits_historical_fallback():
    reg = RouterRegistry()
    for r in reg.all():
        assert r.historical_fallback_allowed is False


# --------------------------------------------------------- pipeline S0..S10


def test_optional_s7_skipped_when_not_needed(runtime):
    hints = {
        "S1": PhaseHint(scene=Scene(telos="ответить", authority=Authority.SYSTEM)),
        "S3": PhaseHint(origin=Origin(status=ProvenanceStatus.ATTRIBUTED,
                                      binding_authority=Authority.SYSTEM)),
        "S4": PhaseHint(operation=Operation(kind="answer", applicable=True)),
        "S6": PhaseHint(ownership=Ownership(owner=Authority.SYSTEM,
                                            human_resolved=True)),
    }
    result = runtime.run("простой вопрос", hints=hints)
    phases = [p["phase"] for p in result.mounted_phases]
    assert "S7" not in phases


def test_conditional_s9_skipped_when_human_ownership(runtime):
    hints = {
        "S6": PhaseHint(ownership=Ownership(owner=Authority.HUMAN,
                                            human_resolved=False,
                                            return_reason="human owns it")),
    }
    result = runtime.run("что делать?", hints=hints)
    phases = [p["phase"] for p in result.mounted_phases]
    assert "S9" not in phases
    assert result.terminal.terminal == Terminal.RETURN_OPERATION


def test_terminal_return_operation_when_human_unresolved(runtime):
    hints = {
        "S6": PhaseHint(ownership=Ownership(owner=Authority.HUMAN,
                                            human_resolved=False,
                                            return_reason="student decides")),
    }
    result = runtime.run("...", hints=hints)
    assert result.terminal.terminal == Terminal.RETURN_OPERATION
    assert "INV-009" in result.terminal.rationale


def test_terminal_preserve_aporia_for_open_world_gap(runtime):
    hints = {
        "S4": PhaseHint(operation=Operation(kind="classify", applicable=True,
                                             open_world_gap=True)),
        "S6": PhaseHint(ownership=Ownership(owner=Authority.SYSTEM,
                                             human_resolved=True)),
    }
    result = runtime.run("что это?", hints=hints)
    assert result.terminal.terminal == Terminal.PRESERVE_APORIA


def test_terminal_return_when_operation_inapplicable(runtime):
    hints = {
        "S4": PhaseHint(operation=Operation(kind="predict", applicable=False,
                                             why_not="нет применимой рамки")),
        "S6": PhaseHint(ownership=Ownership(owner=Authority.SYSTEM,
                                             human_resolved=True)),
    }
    result = runtime.run("...", hints=hints)
    assert result.terminal.terminal == Terminal.RETURN_OPERATION
    assert "inapplicable" in result.terminal.rationale


def test_terminal_challenge_on_status_dispute(runtime):
    triggers = [TriggerAdmission(
        trigger_id="STATUS_DISPUTE",
        generating_state_ref="state.origin.status",
        cause_object_ref="origin.epistemic_claim",
        source_status="typed_state",
        phase_relevance="P02",
        materiality_reason="attribution is contested")]
    hints = {
        "S3": PhaseHint(origin=Origin(status=ProvenanceStatus.UNKNOWN),
                        triggers=triggers),
        "S6": PhaseHint(ownership=Ownership(owner=Authority.SYSTEM,
                                             human_resolved=True)),
    }
    result = runtime.run("говорят что...", hints=hints)
    assert result.terminal.terminal == Terminal.CHALLENGE
    assert "STATUS_DISPUTE" in result.state.admitted_trigger_causes


def test_terminal_answer_when_conditions_clear(runtime):
    hints = {
        "S1": PhaseHint(scene=Scene(telos="дать краткий ответ")),
        "S6": PhaseHint(ownership=Ownership(owner=Authority.SYSTEM,
                                             human_resolved=True)),
    }
    result = runtime.run("сколько?", hints=hints)
    assert result.terminal.terminal == Terminal.ANSWER


def test_council_invoked_via_typed_trigger(runtime):
    """S7 is CONDITIONAL — it fires only when a prior phase's admitted
    trigger causes name a council reason. We inject COUNCIL_REQUIRED via
    S6 (which has 'triggers' in its jurisdiction) so it lands in state
    BEFORE the pipeline decides whether S7 runs."""
    triggers = [TriggerAdmission(
        trigger_id="COUNCIL_REQUIRED",
        generating_state_ref="state.scene.authority",
        cause_object_ref="council.decision",
        source_status="typed_state",
        phase_relevance="P05",
        materiality_reason="minority position at risk")]
    hints = {
        "S6": PhaseHint(ownership=Ownership(owner=Authority.SYSTEM,
                                             human_resolved=True),
                        triggers=triggers),
    }
    result = runtime.run("нужен ли совет?", hints=hints)
    phases = [p["phase"] for p in result.mounted_phases]
    assert "S7" in phases


# --------------------------------------------------------- config binding


def test_configuration_is_recorded_verbatim_in_trace(runtime):
    config = SocratesRunConfiguration(
        pipeline_config_id="cfg_test_001",
        workspace_id="ws_test",
        user_id="u_test",
        display_name="alice",
        semantic_pack_version=runtime.identity.pack.version,
        semantic_pack_sha256=runtime.identity.pack.source_bundle_sha256,
        prompt_variant_selections=(("persona_turn", "v_alt"),),
        constitutional_status="custom_constitutional_variant",
        protected_edits=(("analyze_situation", "constitution"),),
    )
    result = runtime.run("тестовый вход",
                         configuration=config,
                         hints={"S6": PhaseHint(ownership=Ownership(
                             owner=Authority.SYSTEM, human_resolved=True))})
    trace = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    assert trace["configuration"]["pipeline_config_id"] == "cfg_test_001"
    assert trace["configuration"]["user_id"] == "u_test"
    assert trace["configuration"]["constitutional_status"] == \
        "custom_constitutional_variant"
    assert trace["configuration"]["content_hash"].startswith("src:")


def test_snapshot_content_hash_changes_when_selection_changes():
    a = SocratesRunConfiguration(prompt_variant_selections=(("x", "v1"),))
    b = SocratesRunConfiguration(prompt_variant_selections=(("x", "v2"),))
    assert a.content_hash() != b.content_hash()


# --------------------------------------------------------- trace has identities


def test_trace_records_identity_and_mount(runtime):
    result = runtime.run(
        "тест", hints={"S6": PhaseHint(ownership=Ownership(
            owner=Authority.SYSTEM, human_resolved=True))})
    trace = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    # runtime identity
    assert trace["identity"]["pack"]["source_bundle_sha256"].startswith("12b4e621")
    assert trace["identity"]["mount_policy_version"]
    # every phase event has body-level identity
    # Since G-S26L the event name is phase_executed (was phase_completed).
    phase_events = [e for e in trace["events"] if e["kind"] == "phase_executed"]
    assert phase_events
    for e in phase_events:
        for body in e["payload"]["mount"]["required"]:
            assert len(body["sha256"]) == 64
            assert body["bytes"] > 0


# --------------------------------------------------------- state-write gate


def test_memory_proposal_refused_without_authority(runtime):
    proposal = MemoryProposal(kind="distinction",
                              text="рантайм-предложение без человеческого полномочия",
                              grounds="test")
    hints = {
        "S6": PhaseHint(ownership=Ownership(owner=Authority.SYSTEM,
                                             human_resolved=True),
                        memory_proposal=proposal),
    }
    result = runtime.run("предложение", hints=hints,
                         configuration=SocratesRunConfiguration(
                             workspace_id="wm_test_refuse"))
    assert result.memory_outcome is not None
    assert result.memory_outcome["status"] == "refused_no_authority"


# --------------------------------------------------------- native organs


def test_native_organ_evidence_flows_into_result(runtime):
    result = runtime.run(
        "тест", hints={"S6": PhaseHint(ownership=Ownership(
            owner=Authority.SYSTEM, human_resolved=True))})
    organs = {o["organ"]: o for o in result.native_organs}
    assert "argumentation" in organs
    assert "semantic_fabric" in organs
    for organ in organs.values():
        # every organ report carries identity — even the ones that came back
        # unavailable
        assert (organ.get("identity") is not None
                or organ.get("available") is False)


# --------------------------------------------------------- architecture


def test_socrates_runtime_does_not_import_workbench():
    root = SRC / "socrates_runtime"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            heads: set[str] = set()
            if isinstance(node, ast.ImportFrom) and node.module and not node.level:
                heads.add(node.module.split(".")[0])
            elif isinstance(node, ast.Import):
                heads |= {a.name.split(".")[0] for a in node.names}
            for m in heads:
                assert m not in {"workbench_core", "workbench_adapters",
                                 "workbench_api", "workbench_auth",
                                 "workbench_configs", "tinkuy_arena"}, \
                    f"{path.name} imports {m} — dependency direction inverted"


def test_no_reverse_import_from_california_into_socrates():
    for path in (SRC / "californian_id").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "socrates_runtime" not in text, \
            f"{path} imports socrates_runtime — forbidden"


def test_socrates_uses_native_organs_not_reimplementations():
    """The runtime must reach memory/fabric/argumentation through
    tinkuy_runtime, never build its own store."""
    for path in (SRC / "socrates_runtime").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        code = "\n".join(l for l in text.splitlines()
                         if not l.lstrip().startswith("#"))
        for banned in ("CREATE TABLE", "INSERT INTO", "sqlite3.connect"):
            assert banned not in code, f"{path.name} contains own SQL: {banned}"
        for banned_class in ("SocratesFabricStore", "SocratesMemoryDB",
                             "SocratesArgumentStore"):
            assert banned_class not in code, \
                f"{path.name} declares shadow organ {banned_class}"
