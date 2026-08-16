"""Tinkuy Arena v0.1 — one Match, three participants, one deterministic judge.

Acceptance for L2:

    * three participants (2 Zarathustra sub-configs + 1 baseline single agent)
      each answer the same case;
    * the deterministic judge evaluates each participant only on dimensions
      it can actually observe from that participant's engine;
    * the match persists and reloads round-trip;
    * the runner does NOT compare participants or declare a winner — outcome
      belongs to whoever displays it (Workbench/Academy);
    * the Arena core imports no engine directly (dependency proof).
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from tinkuy_arena import (
    ArenaStore,
    BaselineSingleAgent,
    BenchPack,
    Case,
    DeterministicJudge,
    EvaluationDimension,
    Match,
    MatchProtocol,
    MatchRunner,
    ParticipantConfiguration,
    Turn,
    ZarathustraParticipant,
)
from tinkuy_arena.judges.deterministic import (
    D_ARGUMENT_GRAPH_NON_EMPTY,
    D_COUNCIL_INVOKED,
    D_NO_ERROR,
    D_RESPONDED,
    D_RESPONSE_HAS_CONTENT,
    D_SECURITY_CLEAN,
)

SRC = Path(__file__).resolve().parents[2] / "src"


@pytest.fixture(autouse=True)
def _mock_provider(monkeypatch):
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")


@pytest.fixture()
def bench():
    """One case, six dimensions — enough to prove the shape."""
    return BenchPack(
        bench_id="arena.v01.smoke",
        name="Arena v0.1 smoke",
        version="0.1.0",
        cases=(
            Case(
                case_id="c001",
                text=("Должен ли университет отвечать за трудоустройство "
                      "своих выпускников?"),
                tags=("human_operation_ownership", "authority"),
                expectations={"note": "нормативный вопрос — не имеет "
                                       "единственного ответа"},
                source="test",
            ),
        ),
        dimensions=(
            EvaluationDimension(D_RESPONDED, "участник ответил"),
            EvaluationDimension(D_NO_ERROR, "прогон завершился без ошибок"),
            EvaluationDimension(D_RESPONSE_HAS_CONTENT, "ответ не пустой"),
            EvaluationDimension(D_COUNCIL_INVOKED, "совет запустился",
                                description="только для советных участников"),
            EvaluationDimension(D_ARGUMENT_GRAPH_NON_EMPTY,
                                "накопился граф аргументации"),
            EvaluationDimension(D_SECURITY_CLEAN, "нет security events"),
        ),
    )


@pytest.fixture()
def runner():
    """Two Zarathustra participants + one baseline — the v0.1 acceptance."""
    z_stock = ZarathustraParticipant(participant_id="zarathustra_stock",
                                     workspace_id_default="arena_stock")
    z_variant = ZarathustraParticipant(participant_id="zarathustra_variant",
                                       workspace_id_default="arena_variant")
    baseline = BaselineSingleAgent(participant_id="baseline_single")
    adapters = {p.participant_id: p for p in
                (z_stock, z_variant, baseline)}
    return MatchRunner(adapters=adapters, judges=[DeterministicJudge()])


@pytest.fixture()
def configs():
    return [
        ParticipantConfiguration(
            participant_id="zarathustra_stock",
            display_name="Zarathustra / stock",
            engine_kind="zarathustra_council",
            workspace_id="arena_stock"),
        ParticipantConfiguration(
            participant_id="zarathustra_variant",
            display_name="Zarathustra / variant",
            engine_kind="zarathustra_council",
            workspace_id="arena_variant",
            metadata={"mode": "fast"}),
        ParticipantConfiguration(
            participant_id="baseline_single",
            display_name="Baseline single agent",
            engine_kind="baseline_single_agent"),
    ]


# ---------------- one Match, end-to-end ----------------

def test_match_runs_three_participants_and_persists(runner, configs, bench,
                                                    tmp_path):
    case = bench.cases[0]
    match = runner.run_match(bench.bench_id, case, configs)

    assert match.status == "completed"
    assert match.started_at and match.finished_at
    assert [p.participant_id for p in match.participants] == [
        "zarathustra_stock", "zarathustra_variant", "baseline_single"]
    assert {t.participant_id for t in match.turns} == {
        "zarathustra_stock", "zarathustra_variant", "baseline_single"}
    assert all(isinstance(t, Turn) for t in match.turns)

    # ArenaStore round-trip: what the UI would later read is exactly what
    # the runner produced.
    store = ArenaStore(tmp_path / "arena.sqlite3")
    store.save_match(match)
    reloaded = store.load_match(match.match_id)
    assert reloaded is not None
    assert reloaded.match_id == match.match_id
    assert len(reloaded.turns) == 3
    assert len(reloaded.evaluations) == len(match.evaluations)
    assert reloaded.case.text == case.text

    listing = store.list_matches(bench_id=bench.bench_id)
    assert listing and listing[0]["match_id"] == match.match_id


def test_council_dimensions_evaluated_only_for_council_participants(
        runner, configs, bench):
    match = runner.run_match(bench.bench_id, bench.cases[0], configs)
    matrix = runner.evaluation_matrix(match)

    # Zarathustra participants get real verdicts for council dimensions
    for pid in ("zarathustra_stock", "zarathustra_variant"):
        assert matrix[pid][D_COUNCIL_INVOKED] in {"pass", "fail"}
        assert matrix[pid][D_ARGUMENT_GRAPH_NON_EMPTY] in {"pass", "fail"}
        assert matrix[pid][D_SECURITY_CLEAN] in {"pass", "partial"}

    # Baseline single agent gets `unknown` for council-only signals — not
    # `fail`. Marking it as failing what its engine can't produce would be
    # a category error the judge deliberately avoids.
    assert matrix["baseline_single"][D_COUNCIL_INVOKED] == "unknown"
    assert matrix["baseline_single"][D_ARGUMENT_GRAPH_NON_EMPTY] == "unknown"
    assert matrix["baseline_single"][D_SECURITY_CLEAN] == "unknown"


def test_response_and_no_error_evaluated_for_every_participant(runner, configs,
                                                               bench):
    match = runner.run_match(bench.bench_id, bench.cases[0], configs)
    matrix = runner.evaluation_matrix(match)
    for pid in ("zarathustra_stock", "zarathustra_variant", "baseline_single"):
        assert matrix[pid][D_RESPONDED] in {"pass", "fail"}
        assert matrix[pid][D_NO_ERROR] in {"pass", "fail"}
        assert matrix[pid][D_RESPONSE_HAS_CONTENT] in {"pass", "fail"}


def test_zarathustra_turn_carries_council_evidence(runner, configs, bench):
    match = runner.run_match(bench.bench_id, bench.cases[0], configs)
    z_turn = match.turn_for("zarathustra_stock")
    assert z_turn is not None and not z_turn.failed
    rt = z_turn.runtime_summary
    # These are the exact fields the participant promised — a UI card would
    # read them without knowing anything about Pipeline.run
    assert rt["engine"] == "zarathustra_council"
    assert rt["run_id"]
    assert rt["council_turns"] >= 1
    assert set(rt["argument_map"].keys()) >= {"claims", "attacks", "questions"}
    assert isinstance(rt["personas_called"], list)


def test_runner_declares_no_winner(runner, configs, bench):
    """Explicit inversion: the Arena must not aggregate.

    A caller who wants a winner must produce one; the runner produces facts.
    """
    match = runner.run_match(bench.bench_id, bench.cases[0], configs)
    public = match.to_public()
    for banned in ("winner", "score", "ranking", "best"):
        assert banned not in public


def test_unregistered_participant_produces_an_error_turn(runner, bench):
    """A caller may reference a participant the runner does not know about.

    We produce a turn with an explicit error rather than silently dropping
    the participant — the match's shape is preserved and the failure is
    visible in the evaluation.
    """
    orphan = ParticipantConfiguration(
        participant_id="not_registered", display_name="orphan",
        engine_kind="unknown")
    match = runner.run_match(bench.bench_id, bench.cases[0], [orphan])
    turn = match.turn_for("not_registered")
    assert turn is not None
    assert turn.failed
    assert "no adapter registered" in turn.error
    matrix = runner.evaluation_matrix(match)
    assert matrix["not_registered"][D_RESPONDED] == "fail"


def test_empty_participant_list_refused(runner, bench):
    with pytest.raises(ValueError, match="at least one participant"):
        runner.run_match(bench.bench_id, bench.cases[0], [])


# ---------------- architecture proof ----------------

def test_arena_core_does_not_import_engines():
    """``protocol.py`` and ``match.py`` must not name any engine.

    Engine coupling belongs to ``participants/``. If a future refactor drags
    a californian_id import into the core, this catches it.
    """
    core_files = [SRC / "tinkuy_arena" / "protocol.py",
                  SRC / "tinkuy_arena" / "match.py",
                  SRC / "tinkuy_arena" / "__init__.py",
                  SRC / "tinkuy_arena" / "store.py",
                  SRC / "tinkuy_arena" / "judges" / "deterministic.py"]
    for path in core_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module and not node.level:
                mods = [node.module]
            elif isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            for m in mods:
                head = m.split(".")[0]
                assert head not in {"californian_id", "tinkuy_runtime",
                                    "workbench_adapters"}, \
                    f"{path.name}: leaked engine import {m}"


def test_no_reverse_dependency_from_engine_to_arena():
    """``californian_id`` must not import the arena — the arena is a
    downstream layer, and a reverse import would make the runtime depend
    on how it is evaluated."""
    banned = re.compile(r"\btinkuy_arena\b")
    for path in (SRC / "californian_id").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not banned.search(text), \
            f"{path} imports the arena — dependency direction inverted"
