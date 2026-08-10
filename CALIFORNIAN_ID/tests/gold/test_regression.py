"""Пик 9.6 — Gold test corpus + regression suite.

Фиксированные inputs → фиксированные ожидания на mock provider. Regression:
если Pipeline/Zarathustra что-то ломают в дефолтной траектории, тесты
падают. Не проверяют качество ответа — проверяют структурные инварианты.
"""
from __future__ import annotations

import pytest

from californian_id.pipeline import Pipeline


GOLD_INPUTS = [
    {
        "name": "material_autonomy",
        "text": "Является ли материальное автономным в отношении сознания?",
        "min_turns": 3,
    },
    {
        "name": "freedom_vs_optimization",
        "text": "Стоит ли выбирать оптимальное решение, если оно навязано регуляцией?",
        "min_turns": 3,
    },
    {
        "name": "act_under_paralysis",
        "text": "Что делать, если любой выбор имеет моральную цену и нет чистого пути?",
        "min_turns": 3,
    },
]


@pytest.mark.parametrize("case", GOLD_INPUTS, ids=lambda c: c["name"])
def test_gold_run_structural_invariants(case):
    """Regression: полный совет на mock должен возвращать корректную структуру."""
    pipe = Pipeline()
    result = pipe.run(text=case["text"], mode="fast")
    state = result.run_state

    # 1. Run завершился успешно
    assert state.status == "COMPLETED", f"status={state.status} errors={state.errors}"

    # 2. Есть валидная форма завершения
    assert state.completion is not None
    valid_forms = {"synthesis", "aporia", "decision_with_dissent", "world_fork",
                   "polyphony", "delegation", "alliance", "refusal_to_close",
                   "transformed_question", "unresolvable_conflict"}
    assert state.completion.form in valid_forms, f"unknown form {state.completion.form}"

    # 3. Совет отработал не меньше N ходов
    assert len(state.turns) >= case["min_turns"], \
        f"only {len(state.turns)} turns, expected >= {case['min_turns']}"

    # 4. Каждый ход имеет валидную персону + операцию + утверждение
    for turn in state.turns:
        assert turn.persona_id, f"turn {turn.turn_index}: empty persona_id"
        assert turn.operation, f"turn {turn.turn_index}: empty operation"
        assert turn.utterance and len(turn.utterance) > 5, \
            f"turn {turn.turn_index}: empty/tiny utterance"

    # 5. Argument map накоплен
    assert len(state.argument_map.claims) > 0, "no claims recorded"

    # 6. Voices не повторяются подряд более 2 раз (rotation invariant)
    prev = None; run_count = 1
    for turn in state.turns:
        if turn.persona_id == prev:
            run_count += 1
            assert run_count <= 2, \
                f"{turn.persona_id} spoke {run_count} times in a row"
        else:
            run_count = 1
        prev = turn.persona_id


def test_gold_run_deterministic_on_mock():
    """На mock provider вторая прогонка того же input даёт ту же форму."""
    pipe = Pipeline()
    text = "Может ли молчание быть валидным ответом на закрытую систему аргументации?"
    r1 = pipe.run(text=text, mode="fast")
    r2 = pipe.run(text=text, mode="fast")
    # На mock топология сцены детерминирована → одинаковая cast + form.
    assert r1.run_state.selected_personas == r2.run_state.selected_personas, \
        "cast diverges between runs on mock — non-deterministic regression"
    assert r1.run_state.completion.form == r2.run_state.completion.form, \
        f"form diverges: {r1.run_state.completion.form} vs {r2.run_state.completion.form}"


def test_gold_run_produces_conflict_map_when_multiple_voices():
    """Если ≥3 голоса заговорили — conflict_map не пустая."""
    pipe = Pipeline()
    result = pipe.run(
        text="Свобода индивида против общего блага в условиях катастрофы.",
        mode="fast",
    )
    voices = {t.persona_id for t in result.run_state.turns}
    if len(voices) >= 3:
        assert result.run_state.completion.conflict_map, \
            "3+ voices but empty conflict_map — regression in completion assembly"


def test_gold_narrative_note_written_after_run(tmp_path, monkeypatch):
    """9.1 hook: после run пишется observation-note в narrative store."""
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    from californian_id.narrative_memory import NarrativeStore
    pipe = Pipeline(workspace_id="gold-test")
    result = pipe.run(text="Что такое доверие?", mode="fast")
    assert result.run_state.status == "COMPLETED"
    store = NarrativeStore.for_workspace("gold-test")
    try:
        notes = store.list(kind="observation")
    finally:
        store.close()
    assert len(notes) >= 1, "no observation note written after run"
    # note должна ссылаться на этот run
    note = notes[0]
    assert result.run_state.run_id in note.related_run_ids
