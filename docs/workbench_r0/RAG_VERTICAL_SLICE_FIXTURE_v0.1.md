# RAG_VERTICAL_SLICE_FIXTURE v0.1

---

## 1. Выбор узла — и почему их два

Задание называет `retrieve_initial_context`. Он инвентаризирован и выведен в интерфейс полностью, но **сравнение baseline↔candidate на нём вырождено**: ни у одной из семи персон нет каталога `corpus/`, поэтому `LexicalPersonaRetriever.retrieve` возвращает `[]` при любом `top_k`. Это факт данных поставки, а не поломка, и он показан в UI как `корпус присутствует: нет — узел вернёт 0 чанков`.

Поэтому срез идёт на **втором существующем RAG-узле того же рантайма** — `cultural_context` (`CulturalIndex.retrieve_cards`, вызывается в `pipeline.py:555,630,1230`, корпус из 37 карт присутствует). Оба узла реальны; искусственного RAG-демо не создавалось.

| Узел | Движок | Корпус | Роль в срезе |
|---|---|---|---|
| `retrieve_initial_context` | `tinkuy.persona_lexical_bm25` | пуст | наблюдаемость и честная отчётность о нуле |
| `cultural_context` | `zarathustra.cultural_cards_bm25` | 37 карт | рабочий срез со сравнением |

## 2. Фикстуры

Подобраны зондированием корпуса, а не выдуманы: запрос, на который движок отвечает нулём, сделал бы сравнение бессодержательным.

| fixture_id | запрос | ожидание |
|---|---|---|
| `fx_rag_cards_001` | «сцена спор истина» | ≥5 карт с ненулевым BM25 — рабочая фикстура |
| `fx_rag_cards_002` | «полифония голос диалог» | другой профиль ранжирования |
| `fx_rag_cards_003` | «ответственность университета за трудоустройство» | **0 хитов** — негативная фикстура |
| `fx_rag_persona_001` | «ответственность и последствия решения» | 0 чанков, корпус пуст |

## 3. Изменённый параметр

`retrieval.top_k`: **2 → 5**. Выбран потому, что он единственный одновременно реальный, `runtime_mutable`, версионируемый и с расхождением дефолта (3) и эффективного значения (2).

## 4. Результат сравнения

```
BASELINE  (top_k=2)   1 CARD_GREAT_INQUISITOR_DOSTOEVSKY      3.99
                      2 CARD_OVERMAN_INVOCATION_NIETZSCHE     3.93

CANDIDATE (top_k=5)   1 CARD_GREAT_INQUISITOR_DOSTOEVSKY      3.99
                      2 CARD_OVERMAN_INVOCATION_NIETZSCHE     3.93
                      3 CARD_STOP_FUTILE_DISPUTE_POVARNIN     3.25
                      4 CARD_THESIS_HOLDING_POVARNIN          2.48
                      5 CARD_DETERRITORIALIZATION_DELEUZE_GUATTARI 2.37
```

| метрика | значение |
|---|---|
| `result_count` | 2 → 5 |
| `overlap_count` / `overlap_ratio` | 2 / 1.0 |
| `entered_chunks` | STOP_FUTILE_DISPUTE_POVARNIN, THESIS_HOLDING_POVARNIN, DETERRITORIALIZATION_DELEUZE_GUATTARI |
| `dropped_chunks` | — |
| `rank_changes` | 0 |
| `source_count` | 2 → 5 |
| `context_tokens` | 46 → 100 (Δ +54) · **ESTIMATED** |
| `context_bytes` | 250 → 519 (Δ +269) · **MEASURED** |
| `retrieval_latency_ms` | 70 → 64 · MEASURED |
| `relevance_labels_available` | **false** |
| **вердикт** | **`NO_REGRESSION_ON_DECLARED_FIXTURE`** |

Вердикт не называется улучшением: разметки релевантности нет, поэтому допустимы только `IDENTICAL`, `NO_REGRESSION_ON_DECLARED_FIXTURE` (baseline ⊆ candidate) и `DIFFERENT`.

## 5. Активация и снимок прогона

```
accept → activate  (rag.cultural_cards.74a80d24, v0.1.1)
start_run wbrun_ad3f7b589fe1
  rag_snapshot[zarathustra.cultural_cards_bm25] =
      {profile_id: rag.cultural_cards.74a80d24,
       version: 0.1.1,
       source_hash: edd2f0d8245e10cb…}
  context_identity = ctx:0c7dd7c57b16686dce0d2e85
  chunks 5 · tokens 100
```

Уже начатый прогон сохраняет свой RAG-снимок при активации другого профиля посередине — тот же инвариант, что и для `PromptVariant` (тест `test_08_09_activation_affects_only_new_runs`). Откат влияет только на следующий прогон (`test_10_rollback_affects_next_run`).

## 6. Условия отката профиля

Кандидат откатывается, если на объявленной фикстуре: пропал хотя бы один baseline-чанк (`dropped_chunks` непусто при неизменной семантике запроса); `overlap_ratio < 1.0` без явного обоснования; снят защищённый контракт; изменена `contract_version`; `context_bytes` вырос более чем вдвое без соответствующего решения; параметр вне объявленного диапазона.

## 7. Downstream

В том же прогоне под тем же снимком исполняется промпт-узел `analyze_situation`. `context_identity` пересчитывается из событий извлечения и сверяется с трассой — тест `test_17_downstream_receives_exactly_the_recorded_context`. Утверждений о семантическом превосходстве расширенного контекста не делается: без разметки релевантности это было бы домыслом.
