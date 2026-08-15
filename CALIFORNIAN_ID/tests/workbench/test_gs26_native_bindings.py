"""D-S26-001, local repository side: do the three native organs actually run?

The Drive-side G-S26 environment could not reach a semantic fabric, an
argumentation service or a Working Memory endpoint. This repository has the
executable code. These tests answer, per organ:

    * was REAL code invoked (identity: file + sha256 + qualname),
    * is the returned object TYPED (the organ's own dataclass, not prose),
    * is unavailability EXPLICIT (never a substitute, never a silent zero),
    * and for memory: does the authority gate actually gate.

They also guard the thing that would quietly undo all of it — a shadow runtime
growing inside the adapter layer.
"""
from __future__ import annotations

import ast
import sqlite3
from pathlib import Path

import pytest

from californian_id.fabric import (
    FabricBlock,
    FabricRelation,
    FabricSceneState,
    FabricSnapshot,
    FabricSourceSpan,
    FabricStore,
    FabricThread,
    FabricUnit,
)
from californian_id.narrative_memory import NarrativeNote, NarrativeStore
from tinkuy_runtime import NativeOrganUnavailable, argumentation, fabric, working_memory
from tinkuy_runtime.working_memory import WriteAuthority

SRC = Path(__file__).resolve().parents[2] / "src"


# --------------------------------------------------------------- fixtures

def _snapshot() -> FabricSnapshot:
    """A minimal but structurally real fabric: claim + assumption + counter."""
    span = FabricSourceSpan(span_id="sp1", source_id="src_gs26", version="v1",
                            char_start=0, char_end=48, locator="§1")
    u1 = FabricUnit(unit_id="u001", intention="claim",
                    text="Университет отвечает за мышление, а не за вакансию.",
                    evidence_span_ids=["sp1"], speaker_ref="Декан")
    u2 = FabricUnit(unit_id="u002", intention="assumption",
                    text="Образование измеряется способностью различать.",
                    evidence_span_ids=["sp1"], speaker_ref="Декан")
    u3 = FabricUnit(unit_id="u003", intention="counterexample",
                    text="Родители платят за трудоустройство.",
                    evidence_span_ids=["sp1"], speaker_ref="Работодатель")
    b1 = FabricBlock(block_id="b001", block_type="argument",
                     title="Ответственность университета",
                     unit_ids=["u001", "u002", "u003"])
    r1 = FabricRelation(relation_id="r001", relation_type="contradicts",
                        source_id="u001", target_id="u003")
    t1 = FabricThread(thread_id="t001", thread_type="tension",
                      label="результат против мышления")
    scene = FabricSceneState(scene_id="sc1", question="За что отвечает университет?",
                             open_loops=["чей это вопрос — рынка или факультета?"],
                             phase="exploration")
    return FabricSnapshot(
        snapshot_id="snap_gs26", source_id="src_gs26", source_version="v1",
        parser_run_id="fabric_gs26_fixture",
        units=[u1, u2, u3], blocks=[b1], relations=[r1], threads=[t1],
        spans=[span], evidence=[], scene=scene,
        stats={"n_units": 3, "coverage_pct": 1.0})


@pytest.fixture()
def fabric_db(tmp_path) -> Path:
    """A REAL FabricStore database, written by the real store."""
    db = tmp_path / "fabric.sqlite3"
    store = FabricStore(db)
    try:
        store.register_source("src_gs26", "G-S26 fixture", "note",
                              "Университет и рынок труда.")
        store.save_snapshot(_snapshot())
    finally:
        store.close()
    return db


@pytest.fixture()
def memory_db(tmp_path) -> Path:
    return tmp_path / "narrative.sqlite3"


# =============================================================== FABRIC

def test_fabric_query_invokes_the_real_store(fabric_db):
    res = fabric.query(fabric_db, fabric.FabricQuery(snapshot_id="snap_gs26"))
    assert res.available, res.reason
    ident = res.identity
    assert ident.module == "californian_id.fabric.store"
    assert ident.qualname == "FabricStore.load_snapshot"
    assert ident.source_path.endswith("californian_id/fabric/store.py")
    assert len(ident.source_sha256) == 64
    assert ident.execution_kind == "MODEL_FREE"


def test_fabric_query_returns_canonical_typed_objects(fabric_db):
    r = fabric.query(fabric_db, fabric.FabricQuery()).unwrap()
    assert all(isinstance(u, FabricUnit) for u in r.units)
    assert all(isinstance(b, FabricBlock) for b in r.blocks)
    assert all(isinstance(x, FabricRelation) for x in r.relations)
    assert all(isinstance(t, FabricThread) for t in r.threads)
    assert isinstance(r.scene, FabricSceneState)
    assert r.counts() == {"units": 3, "blocks": 1, "relations": 1,
                          "threads": 1, "evidence": 0, "open_loops": 1}
    assert r.open_loops == ["чей это вопрос — рынка или факультета?"]


def test_fabric_query_filters_on_the_substrates_own_dimensions(fabric_db):
    r = fabric.query(fabric_db, fabric.FabricQuery(
        unit_intentions=["claim"], relation_types=["contradicts"])).unwrap()
    assert [u.unit_id for u in r.units] == ["u001"]
    assert [x.relation_id for x in r.relations] == ["r001"]


def test_fabric_query_resolves_latest_snapshot_when_unspecified(fabric_db):
    r = fabric.query(fabric_db, fabric.FabricQuery(source_id="src_gs26")).unwrap()
    assert r.snapshot_id == "snap_gs26"


def test_fabric_unavailability_is_explicit_not_substituted(tmp_path):
    res = fabric.query(tmp_path / "nothing.sqlite3", fabric.FabricQuery())
    assert res.available is False
    assert res.value is None
    assert "не найдено" in res.reason
    assert res.identity is not None, "even a refusal names the organ it failed to reach"
    with pytest.raises(NativeOrganUnavailable):
        res.unwrap()


def test_fabric_empty_store_is_emptiness_not_failure_of_nerve(tmp_path):
    db = tmp_path / "empty.sqlite3"
    FabricStore(db).close()
    res = fabric.query(db, fabric.FabricQuery())
    assert res.available is False
    assert "нет ни одного снимка" in res.reason


def test_fabric_list_snapshots_reads_the_real_index(fabric_db):
    rows = fabric.list_snapshots(fabric_db).unwrap()
    assert [r["snapshot_id"] for r in rows] == ["snap_gs26"]
    assert rows[0]["parser_run_id"] == "fabric_gs26_fixture"


# ========================================================= ARGUMENTATION

def test_argumentation_project_invokes_the_production_projector():
    res = argumentation.project(_snapshot())
    assert res.available, res.reason
    assert res.identity.module == "californian_id.pipeline"
    assert res.identity.qualname == "_fabric_snapshot_to_unit_pack"
    assert res.identity.source_path.endswith("californian_id/pipeline.py")
    assert res.identity.execution_kind == "MODEL_FREE"


def test_argumentation_returns_typed_toulmin_structure_not_prose():
    proj = argumentation.project(_snapshot()).unwrap()
    assert proj.arguments, "the fixture contains a claim; a projection must find it"
    a = proj.arguments[0]
    assert a.claim.startswith("Университет отвечает")
    # warrant comes from the assumption unit, rebuttal from the `contradicts`
    # relation — i.e. from the fabric's own semantics, not from our reading
    assert a.warrant == "Образование измеряется способностью различать."
    assert a.rebuttal == "Родители платят за трудоустройство."
    assert a.complete is True
    assert isinstance(a.claim, str) and isinstance(proj.counts(), dict)
    assert proj.counts()["toulmin_complete"] >= 1


def test_argumentation_absence_is_reported_not_improvised():
    empty = FabricSnapshot(snapshot_id="s0", source_id="x", source_version="v1")
    res = argumentation.project(empty)
    assert res.available is False
    assert res.value is None
    assert "ни одной единицы" in res.reason

    none_res = argumentation.project(None)
    assert none_res.available is False and none_res.value is None


def _turns():
    from californian_id.schemas import Attack, TurnRecord

    return [
        TurnRecord(turn_index=0, persona_id="A", operation="initial_position",
                   utterance="Университет отвечает за мышление."),
        TurnRecord(turn_index=1, persona_id="B", operation="attack",
                   utterance="Родители платят за результат.",
                   attacks=[Attack(text="Родители платят за результат.",
                                   target="previous_turn")]),
    ]


def test_turn_assessment_is_a_separate_call_from_projection():
    """Turn assessment != argumentation service; the seam keeps them apart."""
    from californian_id.argumentation import DisputeAssessment
    from californian_id.schemas import ArgumentMap

    turns = _turns()
    res = argumentation.assess_turn(turns[-1], turns[:-1], ArgumentMap())
    assert res.available, res.reason
    assert isinstance(res.value, DisputeAssessment)
    assert res.identity.qualname == "assess_turn"
    assert res.identity.module == "californian_id.argumentation"
    assert res.call != "argumentation.project"
    assert res.provenance["dispute_mode"]


def test_live_argument_graph_is_reachable_and_accumulates():
    """The graph the council loop maintains — not one this layer rebuilds."""
    from californian_id.schemas import ArgumentMap

    amap = ArgumentMap()
    read0 = argumentation.map_of(amap)
    assert read0.available
    assert read0.provenance == {"claims": 0, "assumptions": 0, "values": 0,
                                "supports": 0, "attacks": 0, "actions": 0,
                                "questions": 0, "unresolved_conflicts": 0}

    for t in _turns():
        folded = argumentation.fold_turn(t, amap)
        assert folded.available
        assert folded.identity.qualname == "_fold_turn_into_argument_map"

    after = argumentation.map_of(amap).unwrap()
    assert after is amap, "the seam must return the live graph, not a copy"
    counts = argumentation.map_of(amap).provenance
    assert counts["attacks"] >= 1, counts
    assert sum(counts.values()) > 0


def test_map_of_refuses_a_foreign_object():
    res = argumentation.map_of({"claims": []})
    assert res.available is False and "не ArgumentMap" in res.reason


# ========================================================= WORKING MEMORY

def test_memory_read_touches_the_real_store(memory_db):
    res = working_memory.read("gs26_ws", db_path=memory_db)
    assert res.available, res.reason
    assert res.identity.module == "californian_id.narrative_memory"
    assert res.identity.qualname == "NarrativeStore.list"
    assert res.value == []


def test_proposal_persists_nothing(memory_db):
    res = working_memory.propose_write(
        "gs26_ws", "distinction", "Ответственность за мышление ≠ за вакансию.")
    assert res.available
    assert res.provenance["persisted"] is False
    proposal = res.value
    assert proposal.state == working_memory.PROPOSED

    # the store must be untouched — checked against the database itself
    assert working_memory.read("gs26_ws", db_path=memory_db).unwrap() == []


def test_rejected_write_leaves_no_trace_in_the_store(memory_db):
    p = working_memory.propose_write("gs26_ws", "hypothesis", "Слишком рано.").unwrap()
    rejected = working_memory.reject_write(p, "не подтверждено свидетельством").unwrap()
    assert rejected.state == working_memory.REJECTED
    assert rejected.decision_reason
    assert working_memory.read("gs26_ws", db_path=memory_db).unwrap() == []


def test_commit_without_authority_is_refused_and_writes_nothing(memory_db):
    p = working_memory.propose_write("gs26_ws", "observation", "Пишем без права.").unwrap()
    res = working_memory.commit_if_authorized(
        p, WriteAuthority.denied("шлюз G-S18 не выдал полномочие"), db_path=memory_db)
    assert res.available is False
    assert res.provenance["persisted"] is False
    assert "порождение информации ≠ полномочие" in res.provenance["invariant"]
    assert p.state == working_memory.REJECTED
    assert working_memory.read("gs26_ws", db_path=memory_db).unwrap() == []


def test_authorized_commit_persists_and_reads_back(memory_db):
    p = working_memory.propose_write(
        "gs26_ws", "distinction",
        "Ответственность за мышление ≠ ответственность за трудоустройство.",
        related_run_ids=["run_gs26_proof"]).unwrap()
    authority = WriteAuthority(granted=True, granted_by="operator",
                               basis="подтверждено человеком в сцене",
                               authority_kind="HUMAN")
    res = working_memory.commit_if_authorized(p, authority, db_path=memory_db)
    assert res.available, res.reason
    assert res.provenance["persisted"] is True
    assert p.state == working_memory.COMMITTED

    # readback through the seam …
    back = working_memory.read_one(p.committed_note_id, "gs26_ws",
                                   db_path=memory_db).unwrap()
    assert isinstance(back, NarrativeNote)
    assert back.text.startswith("Ответственность за мышление")
    assert back.related_run_ids == ["run_gs26_proof"]

    # … and directly against the file, so persistence is not taken on trust
    rows = sqlite3.connect(memory_db).execute(
        "SELECT note_id, kind, text FROM narrative_note").fetchall()
    assert len(rows) == 1 and rows[0][1] == "distinction"


def test_committed_proposal_cannot_be_committed_twice(memory_db):
    p = working_memory.propose_write("gs26_ws", "observation", "Однократно.").unwrap()
    authority = WriteAuthority(granted=True, granted_by="operator", basis="ok",
                               authority_kind="HUMAN")
    working_memory.commit_if_authorized(p, authority, db_path=memory_db)
    again = working_memory.commit_if_authorized(p, authority, db_path=memory_db)
    assert again.available is False
    assert "повторная фиксация запрещена" in again.reason


def test_proposal_validation_borrows_the_stores_own_vocabulary(memory_db):
    res = working_memory.propose_write("gs26_ws", "не-такой-вид", "текст")
    assert res.available is False
    assert "неизвестный вид записи" in res.reason
    assert working_memory.read("gs26_ws", db_path=memory_db).unwrap() == []


# ============================================================ ARCHITECTURE

ADAPTER_FILES = sorted((SRC / "tinkuy_runtime").glob("*.py"))


def test_adapters_create_no_store_of_their_own():
    """`create_new_*_store: false` — the seam must own no schema and no SQL."""
    for path in ADAPTER_FILES:
        text = path.read_text(encoding="utf-8")
        code = "\n".join(l for l in text.splitlines()
                         if not l.strip().startswith("#"))
        for forbidden in ("CREATE TABLE", "CREATE INDEX", "INSERT INTO",
                          "UPDATE ", "DELETE FROM", "sqlite3.connect"):
            assert forbidden not in code, f"{path.name} contains {forbidden!r}"


def test_dependency_direction_is_one_way():
    """Adapters may import the runtime; the runtime may not import adapters."""
    for path in ADAPTER_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        heads = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module and not n.level:
                heads.add(n.module.split(".")[0])
            elif isinstance(n, ast.Import):
                heads |= {a.name.split(".")[0] for a in n.names}
        assert "workbench_core" not in heads and "workbench_adapters" not in heads

    for path in (SRC / "californian_id").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "tinkuy_runtime" not in text, \
            f"{path} imports the adapter layer — dependency direction inverted"


def test_no_shadow_organ_reimplementation():
    """The seams must delegate, not reimplement.

    A shadow runtime looks exactly like a class named after an organ living in
    the adapter layer, so the check is on class definitions, not on prose.
    """
    banned = ("WorkbenchSemanticFabric", "SocratesArgumentEngine",
              "SocratesMemoryDB", "FabricParser", "NarrativeStore", "FabricStore")
    for path in ADAPTER_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
        assert not (defined & set(banned)), f"{path.name} defines {defined & set(banned)}"


def test_every_binding_carries_implementation_identity():
    """A result without identity cannot prove which code ran."""
    from tinkuy_runtime.identity import BindingResult

    results = [
        fabric.query("nonexistent.sqlite3", fabric.FabricQuery()),
        argumentation.project(None),
        working_memory.propose_write("ws", "observation", "x"),
    ]
    for r in results:
        assert isinstance(r, BindingResult)
        assert r.identity is not None
        pub = r.to_public()
        assert pub["identity"]["source_path"] and pub["identity"]["qualname"]


# ==================================================== WORKBENCH INTEGRATION

def test_production_run_carries_native_organ_evidence(tmp_path, monkeypatch):
    """The proof reaches the operator through the tooling that already exists.

    No new trace object, no new panel: native organ evidence rides inside the
    ordinary production RunTrace, which run history and the inspector already
    read.
    """
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    from workbench_adapters import ZarathustraAdapter
    from workbench_adapters.runtime_resolver import WorkbenchConfigResolver
    from workbench_core import WorkbenchService, WorkbenchStore

    svc = WorkbenchService(WorkbenchStore(tmp_path / "state"))
    svc.register_adapter(ZarathustraAdapter())
    svc.bootstrap()
    svc.bootstrap_rag()
    svc.install_runtime_resolver(WorkbenchConfigResolver(svc.store))

    trace = svc.start_production_run("zarathustra", "Университет и рынок труда.")
    organs = trace["production"]["native_organs"]
    by_organ = {o["organ"]: o for o in organs}

    arg = by_organ["argumentation"]
    assert arg["available"] is True
    assert arg["identity"]["module"] == "californian_id.schemas"
    assert arg["counts"]["claims"] >= 1, arg["counts"]

    fab = by_organ["semantic_fabric"]
    assert fab["identity"] is not None
    # a council run over an already-cut pack legitimately writes no fabric;
    # what matters is that absence is stated, not rendered as an empty success
    if not fab["available"]:
        assert fab["reason"] and fab["value"] is None

    # and it survives the round-trip through the run store the UI reads from
    stored = svc.store.read_run(trace["run_id"])
    assert stored["production"]["native_organs"], "evidence lost on persist"


def test_adapter_layer_makes_no_model_call():
    """No seam may substitute a model for a missing organ."""
    for path in ADAPTER_FILES:
        text = path.read_text(encoding="utf-8")
        for forbidden in ("build_client", "generate(", "role_provider",
                          "ModelClient"):
            assert forbidden not in text, f"{path.name} reaches a model boundary"
