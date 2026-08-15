import { useEffect, useState } from 'react';
import { api, type Json } from '../api';

const MODES = [
  { id: 'fast', label: 'Быстрый', note: 'короткий совет, минимум ходов' },
  { id: 'deep', label: 'Глубокий', note: 'больше ходов, дороже' },
];

/**
 * The run surface. Input first, one primary action, everything technical
 * folded away — the operator should not have to choose an input mode to press
 * RUN.
 */
export function RunPanel({
  branch, live, onFinished, onActive,
}: {
  branch: string;
  live: boolean;
  onFinished: (runId: string) => void;
  onActive: (running: boolean) => void;
}) {
  const [fixtures, setFixtures] = useState<Json[]>([]);
  const [text, setText] = useState('');
  const [mode, setMode] = useState('fast');
  const [advanced, setAdvanced] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Json | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    setResult(null); setErr('');
    api.fixtures(branch).then((d) => setFixtures(d.fixtures || []))
      .catch(() => setFixtures([]));
  }, [branch]);

  if (!live) {
    return (
      <div className="dock-body" data-panel="run">
        <h2>Запуск</h2>
        <p className="ov-empty" data-run-unavailable>
          У этой ветки нет исполняемого рантайма — запускать нечего.
          Доступен разбор устройства пайплайна.
        </p>
      </div>
    );
  }

  const doRun = async () => {
    setBusy(true); setErr(''); setResult(null); onActive(true);
    try {
      const r = await api.productionRun(branch, text, mode);
      setResult(r);
      onFinished(r.run_id);
    } catch (e: any) {
      setErr(String(e.message || e));
    } finally {
      setBusy(false); onActive(false);
    }
  };

  const prod = result?.production;

  return (
    <div className="dock-body" data-panel="run">
      <h2>Запуск</h2>

      <div className="ov-field__label">Вход</div>
      <textarea
        className="run-input" data-run-input spellCheck={false}
        placeholder="Вставьте текст, вопрос или фрагмент разговора…"
        value={text} onChange={(e) => setText(e.target.value)} />

      {fixtures.length ? (
        <>
          <div className="ov-field__label">Или готовый вход</div>
          <div className="fixture-list">
            {fixtures.map((f) => (
              <button key={f.id} className="fixture" data-fixture={f.id}
                title={f.text} onClick={() => setText(f.text)}>
                <b>{f.description || f.id}</b>
                <span className="dim">
                  {f.origin === 'previous_run' ? 'из прошлого запуска' : 'готовый пример'}
                </span>
              </button>
            ))}
          </div>
        </>
      ) : null}

      <div className="ov-field__label">Режим прогона</div>
      <div className="row" data-run-profiles>
        {MODES.map((m) => (
          <button key={m.id} data-mode={m.id} title={m.note}
            className={mode === m.id ? 'primary' : ''}
            onClick={() => setMode(m.id)}>{m.label}</button>
        ))}
      </div>

      <div className="run-cta">
        <button className="primary big" data-run-start
          disabled={busy || !text.trim()} onClick={doRun}>
          {busy ? 'Идёт прогон…' : '▶ Запустить'}
        </button>
        {!text.trim() ? (
          <span className="dim">сначала выберите или вставьте вход</span>
        ) : null}
      </div>

      <button className="ov-tech-toggle" data-advanced-toggle
        onClick={() => setAdvanced((a) => !a)}>
        Дополнительно {advanced ? '▴' : '▾'}
      </button>
      {advanced ? (
        <div data-advanced>
          <p className="dim">
            Прогон идёт через настоящую точку входа <code>Pipeline.run</code>.
            Промпты и параметры извлечения берутся из активных версий и
            замораживаются в снимке конфигурации на всё время прогона.
          </p>
        </div>
      ) : null}

      {err ? <div className="card err-text" data-run-error>{err}</div> : null}

      {result ? (
        <div data-run-result>
          <h3>Результат</h3>
          <div className="row">
            <span className={`badge ${String(prod?.status).toUpperCase() === 'COMPLETED' ? 'ok' : 'bad'}`}
              data-run-status>{prod?.status || 'нет статуса'}</span>
            <span className="badge">{result.duration_ms} ms</span>
            <span className="badge">{prod?.turns?.length ?? 0} ходов</span>
          </div>
          {result.failure ? (
            <div className="card err-text" data-run-failure>{result.failure}</div>
          ) : null}
          <table className="kvt"><tbody>
            <tr><td>run_id</td><td><code>{result.run_id}</code></td></tr>
            <tr><td>тема</td><td>{prod?.topic || <span className="dim">—</span>}</td></tr>
            <tr><td>жанр</td><td>{prod?.genre || <span className="dim">—</span>}</td></tr>
            <tr><td>персоны</td>
              <td><code>{(prod?.selected_personas || []).join(', ') || '—'}</code></td></tr>
            <tr><td>снимок конфигурации</td>
              <td><code>{result.run_configuration_snapshot?.snapshot_id}</code></td></tr>
          </tbody></table>
          {(prod?.errors || []).length ? (
            <div className="card err-text">{(prod.errors as string[]).join('\n')}</div>
          ) : null}

          {/* G-S26: which native Tinkuy organs this run actually touched, and
              which file did the work. Absence is stated, never shown as an
              empty success. */}
          {(prod?.native_organs || []).length ? (
            <>
              <h3>Нативные органы Тинкуя</h3>
              <table className="kvt" data-native-organs><tbody>
                {(prod.native_organs as Json[]).map((o, i) => (
                  <tr key={i} data-organ={o.organ}>
                    <td>
                      {o.organ}
                      <div className="dim mono">{o.call}</div>
                    </td>
                    <td>
                      <span className={`badge ${o.available ? 'ok' : 'warn'}`}>
                        {o.available ? 'вызван' : 'не затронут'}
                      </span>
                      {o.identity ? (
                        <div className="dim mono" data-organ-impl>
                          {o.identity.source_path}:{o.identity.lineno}
                          {' · '}{o.identity.source_sha256?.slice(0, 12)}
                        </div>
                      ) : null}
                      {o.available && o.counts
                        ? <div className="dim">{Object.entries(o.counts)
                            .filter(([, v]) => (v as number) > 0)
                            .map(([k, v]) => `${k}: ${v}`).join(' · ') || '—'}</div>
                        : null}
                      {!o.available ? <div className="dim">{o.reason}</div> : null}
                    </td>
                  </tr>
                ))}
              </tbody></table>
            </>
          ) : null}
          <p className="dim">
            Прогон выбран как контекст — узлы пайплайна показывают его данные.
          </p>
        </div>
      ) : null}
    </div>
  );
}
