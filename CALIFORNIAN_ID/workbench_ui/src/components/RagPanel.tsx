/**
 * RAG inspector — retrieval as a first-class managed object.
 *
 * Two hard UI rules, mirroring the core:
 *  - RETRIEVAL FACTS and LLM INTERPRETATION are visually separated and never
 *    merged; the companion may narrate the facts, never invent causality.
 *  - a capability the runtime does not have is rendered as NOT_IMPLEMENTED,
 *    never as a knob with a default.
 */
import { useCallback, useEffect, useState } from 'react';
import { api, type Json } from '../api';

function Pill({ text, tone }: { text: string; tone?: 'ok' | 'warn' | 'err' }) {
  return <span className={`pill ${tone ?? ''}`}>{text}</span>;
}

const gradeTone = (g: string) =>
  g === 'MEASURED' ? 'ok' : g === 'UNKNOWN' ? 'err' : 'warn';

export function RagPanel({ profileId, onChanged }: {
  profileId: string; onChanged: () => void;
}) {
  const [view, setView] = useState<Json | null>(null);
  const [workingId, setWorkingId] = useState(profileId);
  const [test, setTest] = useState<Json | null>(null);
  const [cmp, setCmp] = useState<Json | null>(null);
  const [explain, setExplain] = useState<Json | null>(null);
  const [validation, setValidation] = useState<Json | null>(null);
  const [topK, setTopK] = useState<number>(2);
  const [fixture, setFixture] = useState<string>('');
  const [busy, setBusy] = useState('');
  const [err, setErr] = useState('');

  const load = useCallback(async (pid: string) => {
    const v = await api.rag(pid);
    setView(v);
    setWorkingId(pid);
    setTopK(Number(v.profile.retrieval?.top_k ?? 2));
    if (!fixture && v.fixtures?.length) setFixture(v.fixtures[0].fixture_id);
  }, [fixture]);

  useEffect(() => { setTest(null); setCmp(null); setExplain(null); setValidation(null);
    load(profileId).catch((e) => setErr(String(e.message || e))); }, [profileId]);

  const guard = async (k: string, fn: () => Promise<void>) => {
    setBusy(k); setErr('');
    try { await fn(); } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(''); }
  };

  if (!view) return <div className="dock-body"><p style={{ color: 'var(--text-dim)' }}>
    Загрузка RAG-профиля…</p></div>;

  const p = view.profile;
  const isBaseline = p.state === 'BASELINE' || p.state === 'ACTIVE';
  const params: Json[] = view.parameters || [];
  const missing: Json[] = view.missing_capabilities || [];

  return (
    <>
      {err ? <div className="card err-text">{err}</div> : null}
      <h2>RAG-профиль</h2>
      <div className="row">
        <Pill text={p.state} tone={p.state === 'ACTIVE' ? 'ok'
          : p.state === 'INCOMPATIBLE' ? 'err' : undefined} />
        {workingId === view.active_profile_id ? <Pill text="активен" tone="ok" /> : null}
        <span className="mono">{p.profile_id}</span>
      </div>
      <div className="kv">
        <div className="k">engine</div><div className="v mono">{p.engine_id}</div>
        <div className="k">версия</div><div className="v mono">{p.version}
          {p.parent_version ? ` ← ${p.parent_version}` : ''}</div>
        <div className="k">source_hash</div><div className="v mono">{p.source_hash.slice(0, 24)}</div>
        <div className="k">узел</div><div className="v mono">{p.runtime_binding?.node_id}</div>
        <div className="k">точка вызова</div><div className="v mono">{p.runtime_binding?.call_site}</div>
        <div className="k">корпус присутствует</div>
        <div className="v">{p.source_bindings?.corpora_present
          ? <Pill text="да" tone="ok" />
          : <Pill text="нет — узел вернёт 0 чанков" tone="warn" />}</div>
        <div className="k">contract_version</div><div className="v mono">{p.contract_version}</div>
        <div className="k">защищённые контракты</div>
        <div className="v mono">{(p.protected_contracts || []).join(', ')}</div>
      </div>

      <h3>Профили ({(view.profiles || []).length})</h3>
      {(view.profiles || []).map((x: Json) => (
        <div key={x.profile_id} className="card" style={{
          borderColor: x.profile_id === workingId ? 'var(--accent)' : undefined }}>
          <div className="row" style={{ margin: 0 }}>
            <Pill text={x.state} tone={x.state === 'ACTIVE' ? 'ok' : undefined} />
            <span className="mono">{x.profile_id}</span>
            <span style={{ flex: 1 }} />
            <button onClick={() => load(x.profile_id)}>выбрать</button>
          </div>
        </div>))}

      <h3>Эффективные параметры ({params.length})</h3>
      {params.map((q) => (
        <div key={q.parameter_id} className="card">
          <div className="row" style={{ margin: 0 }}>
            <b style={{ fontSize: 11 }}>{q.label}</b>
            {q.default_differs_from_effective
              ? <Pill text="дефолт ≠ эффективное" tone="warn" /> : null}
            {q.runtime_mutable ? <Pill text="изменяем" tone="ok" />
              : <Pill text="фиксирован" />}
          </div>
          <div className="kv">
            <div className="k">parameter_id</div><div className="v mono">{q.parameter_id}</div>
            <div className="k">в коде</div><div className="v mono">{JSON.stringify(q.current_default)}</div>
            <div className="k">эффективно</div><div className="v mono">{JSON.stringify(q.effective_value)}</div>
            <div className="k">источник</div><div className="v mono">{q.source_path}</div>
            <div className="k">потребитель</div><div className="v mono">{q.consumer}</div>
          </div>
          {q.note ? <div style={{ fontSize: 10, color: 'var(--warn)' }}>{q.note}</div> : null}
        </div>))}

      <h3>Отсутствующие возможности</h3>
      <div className="row">
        {missing.map((m) => (
          <span key={m.capability_id} title={m.note}>
            <Pill text={`${m.label}: ${m.status}`} tone="err" /></span>))}
      </div>

      <h3>Жизненный цикл профиля</h3>
      <div className="row">
        <button data-rag="clone" disabled={!!busy}
          onClick={() => guard('clone', async () => {
            const r = await api.ragCloneProfile(workingId);
            await load(r.profile.profile_id);
          })}>клонировать</button>
        <label style={{ fontSize: 11 }}>top_k{' '}
          <input type="number" min={1} max={20} value={topK} style={{ width: '4em' }}
            disabled={isBaseline}
            onChange={(e) => setTopK(Number(e.target.value))} /></label>
        <button data-rag="apply" disabled={!!busy || isBaseline}
          onClick={() => guard('apply', async () => {
            await api.ragUpdate(workingId, { 'retrieval.top_k': topK });
            await load(workingId);
          })}>применить</button>
        <button data-rag="validate" disabled={!!busy || isBaseline}
          onClick={() => guard('validate', async () => {
            setValidation(await api.ragValidate(workingId));
            await load(workingId);
          })}>валидация</button>
      </div>
      <div className="row">
        <select value={fixture} onChange={(e) => setFixture(e.target.value)}>
          {(view.fixtures || []).map((f: Json) => (
            <option key={f.fixture_id} value={f.fixture_id}>{f.fixture_id}</option>))}
        </select>
        <button data-rag="test" disabled={!!busy}
          onClick={() => guard('test', async () => {
            setTest(await api.ragTest(workingId, fixture)); })}>retrieval test</button>
        <button data-rag="compare" disabled={!!busy || isBaseline}
          onClick={() => guard('compare', async () => {
            setCmp(await api.ragCompare(workingId, fixture)); })}>сравнить</button>
        <button data-rag="accept" disabled={!!busy || isBaseline}
          onClick={() => guard('accept', async () => {
            await api.ragAccept(workingId); await load(workingId); })}>принять</button>
        <button data-rag="activate" disabled={!!busy || isBaseline}
          onClick={() => guard('activate', async () => {
            await api.ragActivate(workingId); await load(workingId); onChanged();
          })}>активировать</button>
        <button data-rag="rollback" disabled={!!busy}
          onClick={() => guard('rollback', async () => {
            await api.ragRollback(p.engine_id); await load(p.engine_id === p.engine_id
              ? (view.profiles.find((x: Json) => x.state === 'BASELINE')?.profile_id
                 || workingId) : workingId);
            onChanged();
          })}>откат</button>
      </div>

      {validation ? (
        <div className="card">
          <Pill text={validation.verdict} tone={validation.verdict === 'pass' ? 'ok' : 'err'} />
          {(validation.issues || []).map((i: Json, k: number) => (
            <div key={k} style={{ fontSize: 11 }}>· {i.message}</div>))}
        </div>) : null}

      {test ? (<>
        <h3>RETRIEVAL FACTS</h3>
        <div className="row">
          <Pill text={`вернул ${test.event.returned_count} из ${test.event.considered_count}`} />
          <Pill text={`${test.event.latency_ms} ms`} tone="ok" />
          <Pill text={test.event.cache_state} />
          <Pill text={`profile ${test.event.rag_profile_version}`} />
        </div>
        <div className="mono" style={{ color: 'var(--text-dim)', fontSize: 10 }}>
          query: {test.event.query_text}</div>
        {test.event.candidates.length === 0
          ? <div className="card">0 чанков. Это факт движка, а не ошибка интерфейса.</div>
          : test.event.candidates.map((c: Json) => (
            <div key={c.chunk_id} className="card">
              <div className="row" style={{ margin: 0 }}>
                <Pill text={`#${c.rank}`} />
                <b style={{ fontSize: 11 }}>{c.chunk_id}</b>
                <Pill text={`${c.score_kind} ${c.score.toFixed(2)}`} tone="ok" />
                <span style={{ flex: 1 }} />
                <button data-rag="explain"
                  onClick={() => guard('explain', async () => {
                    setExplain(await api.ragExplain(
                      workingId, test.event.run_id, c.chunk_id)); })}>
                  почему этот чанк?</button>
              </div>
              <div className="kv">
                <div className="k">locator</div><div className="v mono">{c.locator}</div>
                <div className="k">chunk_hash</div><div className="v mono">{c.chunk_hash}</div>
                <div className="k">source</div><div className="v mono">{c.source_id}</div>
                <div className="k">в контексте</div>
                <div className="v">{c.included_in_context ? `да, #${c.context_order}` : 'нет'}</div>
                <div className="k">токены / байты</div>
                <div className="v">{c.token_count} <Pill text="ESTIMATED" tone="warn" />
                  {' / '}{c.byte_count} <Pill text="MEASURED" tone="ok" /></div>
                <div className="k">совпавшие термы</div>
                <div className="v mono">{(c.matched_terms || []).join(', ') || '—'}</div>
                <div className="k">фильтры</div>
                <div className="v mono">{(c.filters_applied || []).join('; ')}</div>
              </div>
            </div>))}
      </>) : null}

      {explain ? (<>
        <h3>Почему этот чанк — факты</h3>
        <div className="card">
          {(explain.retrieval_facts || []).map((f: Json, i: number) => (
            <div key={i} className="span-row">
              <Pill text={f.grade} tone={gradeTone(f.grade) as any} />
              <span className="mono">{f.fact}</span>
              <span className="mono" style={{ color: 'var(--text-dim)' }}>
                {JSON.stringify(f.value)}</span>
            </div>))}
        </div>
        <h3>LLM INTERPRETATION</h3>
        <div className="card" style={{ borderStyle: 'dashed' }}>
          {explain.llm_interpretation
            ? explain.llm_interpretation
            : <span style={{ color: 'var(--text-dim)', fontSize: 11 }}>
                Интерпретация не запрашивалась. {explain.disclaimer}</span>}
        </div>
      </>) : null}

      {cmp ? (<>
        <h3>Baseline ↔ Candidate</h3>
        <div className="kv">
          <div className="k">результатов</div>
          <div className="v">{cmp.delta.result_count.baseline} → {cmp.delta.result_count.candidate}</div>
          <div className="k">пересечение</div>
          <div className="v">{cmp.delta.overlap_count} (ratio {cmp.delta.overlap_ratio})</div>
          <div className="k">вошли</div><div className="v mono">{cmp.delta.entered_chunks.join(', ') || '—'}</div>
          <div className="k">выпали</div><div className="v mono">{cmp.delta.dropped_chunks.join(', ') || '—'}</div>
          <div className="k">смена рангов</div><div className="v">{cmp.delta.rank_changes.length}</div>
          <div className="k">источников</div>
          <div className="v">{cmp.delta.source_count.baseline} → {cmp.delta.source_count.candidate}</div>
          <div className="k">контекст, токены</div>
          <div className="v">{cmp.delta.context_tokens.baseline} → {cmp.delta.context_tokens.candidate}
            {' '}(Δ{cmp.delta.context_tokens.delta}) <Pill text="ESTIMATED" tone="warn" /></div>
          <div className="k">контекст, байты</div>
          <div className="v">{cmp.delta.context_bytes.baseline} → {cmp.delta.context_bytes.candidate}
            {' '}<Pill text="MEASURED" tone="ok" /></div>
          <div className="k">латентность</div>
          <div className="v">{cmp.delta.retrieval_latency_ms.baseline} → {cmp.delta.retrieval_latency_ms.candidate} ms</div>
          <div className="k">вердикты</div>
          <div className="v">{(cmp.delta.verdicts || []).map((v: string) => (
            <span key={v}><Pill text={v}
              tone={v.startsWith('QUALITY_UNKNOWN') ? 'warn'
                : v === 'DOWNSTREAM_CONTRACT_FAIL' ? 'err' : 'ok'} />{' '}</span>))}</div>
          <div className="k">разметка релевантности</div>
          <div className="v">{cmp.delta.relevance_labels_available
            ? 'есть' : <Pill text="отсутствует — QUALITY_* недоступен" tone="warn" />}</div>
        </div>
        <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>{cmp.delta.note}</div>
      </>) : null}
    </>
  );
}
