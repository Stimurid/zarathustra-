"""LOCAL_GS26_RUNTIME_BLOCKER_TEST — executable proof, not documentation.

Answers one question per organ, from running code:

    did a NATIVE Tinkuy organ execute here, and can we name the file that did it?

Deliberately NOT a single artificial scenario. The three organs do not naturally
meet in one call in this architecture, so each is exercised the way the runtime
actually uses it:

    argumentation   — inside a real ``Pipeline.run`` council loop
    semantic fabric — over a real ``FabricStore`` database, read back by query
    Working Memory  — propose → reject → propose → commit → readback

Writes evidence to docs/socrates_gs26/LOCAL_GS26_RUNTIME_PROOF.json.

Run:  python scripts/gs26_native_runtime_proof.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from californian_id.fabric import (  # noqa: E402
    FabricBlock, FabricRelation, FabricSceneState, FabricSnapshot,
    FabricSourceSpan, FabricStore, FabricThread, FabricUnit,
)
from tinkuy_runtime import argumentation, fabric, working_memory  # noqa: E402
from tinkuy_runtime.working_memory import WriteAuthority  # noqa: E402

OUT = ROOT.parent / "docs" / "socrates_gs26" / "LOCAL_GS26_RUNTIME_PROOF.json"
WORKSPACE = "gs26-proof"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ident(res) -> dict:
    i = res.identity
    return {"module": i.module, "qualname": i.qualname,
            "source_path": i.source_path, "source_sha256": i.source_sha256,
            "lineno": i.lineno, "execution_kind": i.execution_kind}


# ------------------------------------------------------------ fabric

def prove_fabric(tmp: Path) -> dict:
    """Real store, real snapshot, real typed read-back."""
    db = tmp / "fabric_proof.sqlite3"
    snap = FabricSnapshot(
        snapshot_id="snap_proof", source_id="src_proof", source_version="v1",
        parser_run_id="gs26_proof",
        units=[
            FabricUnit(unit_id="u001", intention="claim",
                       text="Университет отвечает за мышление, а не за вакансию.",
                       evidence_span_ids=["sp1"], speaker_ref="Декан"),
            FabricUnit(unit_id="u002", intention="assumption",
                       text="Образование измеряется способностью различать.",
                       evidence_span_ids=["sp1"]),
            FabricUnit(unit_id="u003", intention="counterexample",
                       text="Родители платят за трудоустройство.",
                       evidence_span_ids=["sp1"], speaker_ref="Работодатель"),
        ],
        blocks=[FabricBlock(block_id="b001", block_type="argument",
                            title="Ответственность университета",
                            unit_ids=["u001", "u002", "u003"])],
        relations=[FabricRelation(relation_id="r001", relation_type="contradicts",
                                  source_id="u001", target_id="u003")],
        threads=[FabricThread(thread_id="t001", thread_type="tension",
                              label="результат против мышления")],
        spans=[FabricSourceSpan(span_id="sp1", source_id="src_proof", version="v1",
                                char_start=0, char_end=48, locator="§1")],
        evidence=[],
        scene=FabricSceneState(scene_id="sc1",
                               question="За что отвечает университет?",
                               open_loops=["чей это вопрос — рынка или факультета?"]),
        stats={"n_units": 3})

    store = FabricStore(db)
    try:
        store.register_source("src_proof", "G-S26 proof", "note",
                              "Университет и рынок труда.")
        store.save_snapshot(snap)
    finally:
        store.close()

    res = fabric.query(db, fabric.FabricQuery(source_id="src_proof",
                                              include_evidence=True))
    if not res.available:
        return {"verdict": "FAIL", "reason": res.reason}

    q = res.value
    typed = {type(x).__name__ for x in (q.units + q.blocks + q.relations + q.threads)}
    unavailable = fabric.query(tmp / "absent.sqlite3", fabric.FabricQuery())

    return {
        "verdict": "PASS",
        "call": res.call,
        "implementation": _ident(res),
        "db_path": str(db),
        "typed_objects_returned": sorted(typed),
        "counts": q.counts(),
        "open_loops": q.open_loops,
        "scene_question": getattr(q.scene, "question", ""),
        "explicit_unavailability": {
            "available": unavailable.available,
            "value_is_none": unavailable.value is None,
            "reason": unavailable.reason,
        },
        "model_involved": False,
    }


# ------------------------------------------------------ argumentation

def prove_argumentation(tmp: Path) -> dict:
    """Two halves: the live graph from a real run, and the fabric projector."""
    os.environ.setdefault("CALIFORNIAN_ID_PROVIDER", "mock")
    from californian_id.pipeline import Pipeline

    pipe = Pipeline(workspace_id=WORKSPACE)
    result = pipe.run(
        text="Должен ли университет отвечать за трудоустройство выпускников?",
        mode="fast")
    state = result.run_state

    live = argumentation.map_of(state.argument_map)
    if not live.available:
        return {"verdict": "FAIL", "reason": live.reason}

    # the projector, on a real fabric snapshot
    snap = FabricSnapshot(
        snapshot_id="snap_arg", source_id="src_arg", source_version="v1",
        units=[
            FabricUnit(unit_id="u001", intention="claim",
                       text="Университет отвечает за мышление, а не за вакансию."),
            FabricUnit(unit_id="u002", intention="assumption",
                       text="Образование измеряется способностью различать."),
            FabricUnit(unit_id="u003", intention="counterexample",
                       text="Родители платят за трудоустройство."),
        ],
        blocks=[FabricBlock(block_id="b001", block_type="argument",
                            unit_ids=["u001", "u002", "u003"])],
        relations=[FabricRelation(relation_id="r001", relation_type="contradicts",
                                  source_id="u001", target_id="u003")],
        threads=[], spans=[], evidence=[], scene=None, stats={})
    proj = argumentation.project(snap)
    empty = argumentation.project(
        FabricSnapshot(snapshot_id="s0", source_id="x", source_version="v1"))

    first = proj.value.arguments[0] if proj.available and proj.value.arguments else None
    return {
        "verdict": "PASS" if (live.available and proj.available) else "FAIL",
        "live_graph": {
            "call": live.call,
            "implementation": _ident(live),
            "run_id": state.run_id,
            "status": state.status,
            "turns": len(state.turns),
            "counts": live.provenance,
            "typed_object": type(state.argument_map).__name__,
            "trace_dir": str(result.trace_dir),
        },
        "projection": {
            "call": proj.call,
            "implementation": _ident(proj),
            "counts": proj.value.counts() if proj.available else None,
            "first_argument": None if first is None else {
                "claim": first.claim, "warrant": first.warrant,
                "rebuttal": first.rebuttal, "toulmin_complete": first.complete,
            },
        },
        "explicit_unavailability": {
            "available": empty.available, "value_is_none": empty.value is None,
            "reason": empty.reason,
        },
        "model_involved_in_projection": False,
    }


# ------------------------------------------------------ working memory

def prove_working_memory(tmp: Path) -> dict:
    """READ → PROPOSE → REJECT → PROPOSE → COMMIT → READBACK."""
    import sqlite3

    db = tmp / "narrative_proof.sqlite3"
    steps: list[dict] = []

    before = working_memory.read(WORKSPACE, db_path=db)
    steps.append({"step": "READ", "available": before.available,
                  "count": len(before.value or []),
                  "implementation": _ident(before)})

    refused = working_memory.propose_write(
        WORKSPACE, "hypothesis", "Гипотеза, которую отклонят.")
    rej = working_memory.reject_write(refused.value, "не подтверждено свидетельством")
    after_reject = working_memory.read(WORKSPACE, db_path=db)
    steps.append({"step": "PROPOSE_THEN_REJECT",
                  "proposal_id": refused.value.proposal_id,
                  "persisted_by_proposal": refused.provenance["persisted"],
                  "state": rej.value.state,
                  "store_rows_after": len(after_reject.value or [])})

    ungated = working_memory.propose_write(
        WORKSPACE, "observation", "Попытка записи без полномочия.")
    denied = working_memory.commit_if_authorized(
        ungated.value, WriteAuthority.denied("шлюз G-S18 не выдал полномочие"),
        db_path=db)
    after_denied = working_memory.read(WORKSPACE, db_path=db)
    steps.append({"step": "COMMIT_WITHOUT_AUTHORITY",
                  "available": denied.available, "reason": denied.reason,
                  "persisted": denied.provenance["persisted"],
                  "store_rows_after": len(after_denied.value or []),
                  "invariant": denied.provenance["invariant"]})

    proposal = working_memory.propose_write(
        WORKSPACE, "distinction",
        "Ответственность за мышление ≠ ответственность за трудоустройство.",
        related_run_ids=["gs26_proof"]).value
    committed = working_memory.commit_if_authorized(
        proposal,
        WriteAuthority(granted=True, granted_by="operator",
                       basis="подтверждено человеком в сцене",
                       authority_kind="HUMAN"),
        db_path=db)
    steps.append({"step": "COMMIT_WITH_AUTHORITY",
                  "available": committed.available,
                  "persisted": committed.provenance.get("persisted"),
                  "note_id": committed.provenance.get("note_id"),
                  "implementation": _ident(committed)})

    back = working_memory.read_one(proposal.committed_note_id, WORKSPACE, db_path=db)
    rows = sqlite3.connect(db).execute(
        "SELECT note_id, kind, text FROM narrative_note").fetchall()
    steps.append({"step": "READBACK",
                  "available": back.available,
                  "text": getattr(back.value, "text", None),
                  "rows_in_database": len(rows),
                  "row_kinds": [r[1] for r in rows]})

    ok = (steps[1]["store_rows_after"] == 0
          and steps[2]["persisted"] is False
          and steps[2]["store_rows_after"] == 0
          and steps[3]["persisted"] is True
          and steps[4]["available"] is True
          and steps[4]["rows_in_database"] == 1)
    return {"verdict": "PASS" if ok else "FAIL", "db_path": str(db), "steps": steps}


def main() -> int:
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="gs26_proof_"))
    report = {
        "test": "LOCAL_GS26_RUNTIME_BLOCKER_TEST",
        "generated_at": _now(),
        "scope": "local executable repository only — no Drive access, no "
                 "authority over Socrates generation state",
        "semantic_fabric": prove_fabric(tmp),
        "argumentation": prove_argumentation(tmp),
        "working_memory": prove_working_memory(tmp),
    }
    report["verdicts"] = {
        "FABRIC_NATIVE_BINDING": report["semantic_fabric"]["verdict"],
        "ARGUMENTATION_NATIVE_BINDING": report["argumentation"]["verdict"],
        "WORKING_MEMORY_NATIVE_BINDING": report["working_memory"]["verdict"],
    }
    all_pass = set(report["verdicts"].values()) == {"PASS"}
    report["D-S26-001_LOCAL_REPOSITORY_SIDE"] = "RESOLVED" if all_pass else "PARTIAL"
    report["not_claimed"] = [
        "G-S26 CLOSED — вне наших полномочий: авторитетное состояние Socrates "
        "живёт в Drive, которого у нас нет",
        "полная интеграция Socrates — здесь доказан рантайм-носитель, не импорт",
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for organ, verdict in report["verdicts"].items():
        print(f"{organ:32} {verdict}")
    print(f"{'D-S26-001_LOCAL_REPOSITORY_SIDE':32} "
          f"{report['D-S26-001_LOCAL_REPOSITORY_SIDE']}")
    # ASCII on purpose: this script is run from cp1251 consoles.
    print(f"\nevidence -> {OUT}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
