import { useCallback, useEffect, useState } from 'react';
import { api, type Json } from '../api';

function when(iso?: string) {
  if (!iso) return '—';
  return iso.replace('T', ' ').replace(/\..*$/, '').slice(0, 19);
}

function Row({ label, a, b, changed }: {
  label: string; a: any; b: any; changed: boolean;
}) {
  return (
    <tr data-diff-row={label} className={changed ? 'diff-changed' : ''}>
      <td>{label}</td>
      <td><code>{a ?? '—'}</code></td>
      <td><code>{b ?? '—'}</code></td>
    </tr>
  );
}

/** Run history and comparison. States differences; ranks nothing. */
export function RunHistory({
  selected, onSelect,
}: {
  selected: string | null;
  onSelect: (runId: string | null) => void;
}) {
  // `null` = not loaded yet. Starting from `[]` made the panel assert "прогонов
  // ещё не было" during every fetch — a claim it had no grounds for.
  const [runs, setRuns] = useState<Json[] | null>(null);
  const [a, setA] = useState<string | null>(null);
  const [b, setB] = useState<string | null>(null);
  const [cmp, setCmp] = useState<Json | null>(null);
  const [err, setErr] = useState('');

  const load = useCallback(() => {
    api.runIndex().then((d) => setRuns(d.runs || []))
      .catch((e) => setErr(String(e.message || e)));
  }, []);
  useEffect(() => { load(); }, [load]);

  const doCompare = async () => {
    if (!a || !b) return;
    setErr('');
    try {
      setCmp(await api.compareRuns(a, b));
      // The comparison renders above a list the operator has just scrolled
      // through; without this it appears off-screen and looks like nothing
      // happened.
      // the dock body IS the scroll container, so scrollIntoView on it is a
      // no-op — reset its own scrollTop instead
      const panel = document.querySelector('[data-panel="runs"]');
      if (panel) panel.scrollTop = 0;
    } catch (e: any) { setErr(String(e.message || e)); }
  };

  return (
    <div className="dock-body" data-panel="runs">
      <h2>Запуски</h2>
      {err ? <div className="card err-text">{err}</div> : null}

      {cmp ? (
        <div data-compare-result>
          <div className="row">
            <h3 style={{ margin: 0, flex: 1 }}>Сравнение</h3>
            <button data-close-compare onClick={() => setCmp(null)}>закрыть</button>
          </div>
          <table className="kvt cmp"><tbody>
            <tr><td /><td><b>A</b></td><td><b>B</b></td></tr>
            <Row label="время" a={when(cmp.a.started_at)} b={when(cmp.b.started_at)}
              changed={false} />
            <Row label="длительность" a={`${cmp.a.duration_ms} ms`}
              b={`${cmp.b.duration_ms} ms`} changed={cmp.a.duration_ms !== cmp.b.duration_ms} />
            <Row label="снимок" a={cmp.a.snapshot_id?.slice(0, 12)}
              b={cmp.b.snapshot_id?.slice(0, 12)}
              changed={cmp.a.snapshot_id !== cmp.b.snapshot_id} />
          </tbody></table>

          <h4>Вход</h4>
          <p data-input-same className={cmp.same_input ? 'dim' : 'ov-warn'}>
            {cmp.same_input
              ? 'Вход одинаковый — различия относятся к конфигурации или рантайму.'
              : 'Вход разный — различия результата нельзя приписать только конфигурации.'}
          </p>

          <h4>Промпты</h4>
          <table className="kvt cmp" data-prompt-diff><tbody>
            {cmp.prompt_diff.map((d: Json) => (
              <Row key={d.id} label={d.id} a={d.a} b={d.b} changed={d.changed} />
            ))}
          </tbody></table>

          <h4>Извлечение</h4>
          <table className="kvt cmp" data-rag-diff><tbody>
            {cmp.rag_diff.map((d: Json) => (
              <Row key={d.id} label={d.id} a={d.a} b={d.b} changed={d.changed} />
            ))}
          </tbody></table>

          <h4>Настройки</h4>
          <table className="kvt cmp" data-control-diff><tbody>
            {cmp.control_diff.map((d: Json) => (
              <Row key={d.id} label={d.id} a={d.a} b={d.b} changed={d.changed} />
            ))}
            {cmp.model_diff.map((d: Json) => (
              <Row key={d.id} label={`модель · ${d.id}`} a={d.a} b={d.b}
                changed={d.changed} />
            ))}
          </tbody></table>

          <h4>Узлы в рантайме</h4>
          <table className="kvt cmp" data-node-runtime-diff><tbody>
            <tr><td /><td><b>A</b></td><td><b>B</b></td></tr>
            {cmp.node_runtime.map((d: Json) => (
              <Row key={d.node_id} label={d.node_id}
                a={`${d.a_executions ?? '—'}×${d.a_chunks != null ? ` / ${d.a_chunks} фр.` : ''}`}
                b={`${d.b_executions ?? '—'}×${d.b_chunks != null ? ` / ${d.b_chunks} фр.` : ''}`}
                changed={d.changed} />
            ))}
          </tbody></table>

          <h4>Итог</h4>
          <table className="kvt cmp" data-outcome-diff><tbody>
            <Row label="статус" a={cmp.outcome_a.status} b={cmp.outcome_b.status}
              changed={cmp.outcome_a.status !== cmp.outcome_b.status} />
            <Row label="тема" a={cmp.outcome_a.topic} b={cmp.outcome_b.topic}
              changed={cmp.outcome_a.topic !== cmp.outcome_b.topic} />
            <Row label="ходов" a={cmp.outcome_a.turns} b={cmp.outcome_b.turns}
              changed={cmp.outcome_a.turns !== cmp.outcome_b.turns} />
          </tbody></table>

          <p className="ov-empty" data-no-verdict>
            {cmp.quality_verdict.reason}.
          </p>
        </div>
      ) : null}


      {runs === null ? (
        <p className="ov-empty" data-runs-loading>Загрузка истории…</p>
      ) : !runs.length ? (
        <p className="ov-empty" data-runs-empty>
          Прогонов ещё не было. Пайплайн можно изучать и без запуска —
          вкладка «Пайплайн» показывает его устройство.
        </p>
      ) : (
        <>
          <div className="row">
            <button data-clear-run onClick={() => onSelect(null)}
              disabled={!selected}>Вернуться к определению</button>
            <button onClick={load}>обновить</button>
          </div>
          <div className="run-list">
            {runs.map((r) => (
              <div key={r.run_id}
                className={`run-row${selected === r.run_id ? ' sel' : ''}`}
                data-run-row={r.run_id}>
                <button className="run-row__main" data-run-open={r.run_id}
                  onClick={() => onSelect(r.run_id)}>
                  <div className="run-row__top">
                    <span className={`badge ${String(r.status).toUpperCase() === 'COMPLETED' ? 'ok' : 'bad'}`}>
                      {r.status}
                    </span>
                    <span className="dim">{when(r.started_at)}</span>
                    <span className="dim">{r.duration_ms != null
                      ? `${r.duration_ms} ms` : 'длительность не записана'}</span>
                  </div>
                  <div className="run-row__label">{r.input_label || '(без входа)'}</div>
                  <div className="dim">
                    режим {r.mode || '—'} · ходов {r.turns} · снимок{' '}
                    <code>{r.snapshot_id?.slice(0, 12)}</code>
                  </div>
                </button>
                <div className="run-row__cmp">
                  <button className={a === r.run_id ? 'primary' : ''}
                    data-pick-a={r.run_id} onClick={() => setA(r.run_id)}>A</button>
                  <button className={b === r.run_id ? 'primary' : ''}
                    data-pick-b={r.run_id} onClick={() => setB(r.run_id)}>B</button>
                </div>
              </div>
            ))}
          </div>

          <div className="row">
            <button className="primary" data-compare-run
              disabled={!a || !b || a === b} onClick={doCompare}>
              Сравнить A и B
            </button>
          </div>
        </>
      )}

    </div>
  );
}
