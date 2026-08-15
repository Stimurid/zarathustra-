import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type Json } from '../api';
import type { DockTab } from './RightDock';
import { PromptEditor, type EditorHandle, type Marker } from './PromptEditor';
import { RagPanel } from './RagPanel';
import { PromptBody, ReadinessBadge } from './BranchPanels';
import { NodeOverview } from './NodeOverview';
import { PromptCopilot } from './PromptCopilot';

const STEPS = [
  ['clone', 'клонировать'], ['edit', 'сохранить'], ['diff', 'diff'],
  ['validate', 'валидация'], ['compile', 'компиляция'], ['smoke', 'смок'],
  ['compare', 'сравнение'], ['accept', 'принять'], ['activate', 'активировать'],
] as const;

function Pill({ text, tone }: { text: string; tone?: 'ok' | 'warn' | 'err' }) {
  return <span className={`pill ${tone ?? ''}`}>{text}</span>;
}

function stateTone(s: string): 'ok' | 'warn' | 'err' | undefined {
  if (s === 'ACTIVE' || s === 'ACCEPTED' || s === 'SMOKE_TESTED') return 'ok';
  if (s === 'INCOMPATIBLE' || s === 'REJECTED') return 'err';
  if (s === 'CANDIDATE_UNCHECKED') return 'warn';
  return undefined;
}

export function Inspector({
  branch, node, tab, runId, onTabChange, onChanged,
}: {
  branch: string; node: Json | null; tab: DockTab; runId: string | null;
  onTabChange: (t: DockTab) => void; onChanged: () => void;
}) {
  const [lifecycle, setLifecycle] = useState(false);
  const [assetView, setAssetView] = useState<Json | null>(null);
  const [workingId, setWorkingId] = useState<string | null>(null);
  const [source, setSource] = useState('');
  const [regions, setRegions] = useState<Json[]>([]);
  const [dirty, setDirty] = useState(false);
  const [validation, setValidation] = useState<Json | null>(null);
  const [compiled, setCompiled] = useState<Json | null>(null);
  const [smoke, setSmoke] = useState<Json | null>(null);
  const [cmp, setCmp] = useState<Json | null>(null);
  const [diff, setDiff] = useState<Json | null>(null);
  const [run, setRun] = useState<Json | null>(null);
  const [effects, setEffects] = useState<Json[]>([]);
  const [busy, setBusy] = useState('');
  const [err, setErr] = useState('');
  const [done, setDone] = useState<Set<string>>(new Set());
  const editor = useRef<EditorHandle>(null);
  const [sel, setSel] = useState({ from: 0, to: 0, text: '' });

  const assetId: string | undefined = node?.node?.asset_id ?? undefined;
  const editorAvailable: boolean = !!node?.editor_available;

  const mark = (k: string) => setDone((d) => new Set(d).add(k));
  const guard = async (k: string, fn: () => Promise<void>) => {
    setBusy(k); setErr('');
    try { await fn(); mark(k); } catch (e: any) { setErr(String(e.message || e)); }
    finally { setBusy(''); }
  };

  // Defect WB-002: the preferred variant must be passed explicitly. Deriving it
  // from `workingId` inside the callback captured a stale value, so a freshly
  // cloned candidate was silently replaced by the active baseline.
  const loadAsset = useCallback(async (aid: string, preferId?: string | null) => {
    const view = await api.asset(aid);
    setAssetView(view);
    const known = (id?: string | null) =>
      !!id && view.variants.some((v: Json) => v.variant_id === id);
    const target = known(preferId) ? preferId! : view.active_variant_id;
    setWorkingId(target);
    if (target) {
      const src = await api.source(aid, target);
      setSource(src.variant.source_text);
      setRegions(src.regions);
      setDirty(false);
    }
  }, []);

  useEffect(() => {
    setValidation(null); setCompiled(null); setSmoke(null);
    setCmp(null); setDiff(null); setRun(null); setErr(''); setDone(new Set());
    if (!assetId) { setAssetView(null); setWorkingId(null); setSource(''); return; }
    loadAsset(assetId).catch((e) => setErr(String(e.message || e)));
  }, [assetId, loadAsset]);

  useEffect(() => {
    api.controls(branch).then((r) => setEffects(r.controls)).catch(() => {});
  }, [branch]);

  // WB-021 (same class as the App-level fix): during a branch switch the new
  // branch arrives before the old node payload is cleared. Rendering that node
  // issued requests for `<new branch>/<old branch's object>` and 404'd.
  if (!node || (node.branch && node.branch !== branch)) {
    return <div className="dock-body"><p style={{ color: 'var(--text-dim)' }}>
      Выберите узел графа.</p></div>;
  }

  const n = node.node;
  const contract = assetView?.contract;
  const variants: Json[] = assetView?.variants ?? [];
  const working = variants.find((v) => v.variant_id === workingId);
  const isBaseline = working?.state === 'BASELINE';

  // Validation issues become editor markers wherever they name a locatable region.
  const validationMarkers: Marker[] = (validation?.issues ?? [])
    .map((i: Json) => {
      const rname = i.detail?.region;
      const r = rname ? regions.find((x) => x.name === rname) : undefined;
      if (!r || r.start == null || r.end == null) return null;
      return { from: r.start, to: r.end, severity: i.severity, message: i.message };
    })
    .filter(Boolean) as Marker[];

  // ---------------- actions ----------------
  const doClone = () => guard('clone', async () => {
    const r = await api.clone(assetId!, workingId!);
    await loadAsset(assetId!, r.variant.variant_id);
    onTabChange('prompt');
  });
  const doSave = () => guard('edit', async () => {
    await api.saveSource(assetId!, workingId!, source);
    setValidation(null); setCompiled(null); setSmoke(null); setCmp(null);
    await loadAsset(assetId!, workingId);
  });
  const doDiff = () => guard('diff', async () => {
    const base = variants.find((v) => v.state === 'BASELINE' && v.origin === 'baseline_file')
      ?? variants.find((v) => v.state === 'BASELINE');
    setDiff(await api.diff(assetId!, base!.variant_id, workingId!));
    onTabChange('prompt');
  });
  const doValidate = () => guard('validate', async () => {
    setValidation(await api.validate(assetId!, workingId!));
    await loadAsset(assetId!, workingId);
    onTabChange('prompt');
  });
  const doCompile = () => guard('compile', async () => {
    setCompiled(await api.compile(assetId!, workingId!));
    await loadAsset(assetId!, workingId);
    onTabChange('prompt');
  });
  const doSmoke = () => guard('smoke', async () => {
    setSmoke(await api.smoke(assetId!, workingId!));
    await loadAsset(assetId!, workingId);
    onTabChange('prompt');
  });
  const doCompare = () => guard('compare', async () => {
    setCmp(await api.compare(assetId!, workingId!));
    await loadAsset(assetId!, workingId);
    onTabChange('prompt');
  });
  const doAccept = () => guard('accept', async () => {
    await api.accept(assetId!, workingId!);
    await loadAsset(assetId!, workingId);
  });
  const doActivate = () => guard('activate', async () => {
    await api.activate(assetId!, workingId!);
    await loadAsset(assetId!, workingId);
    onChanged();
  });
  const doRun = () => guard('run', async () => {
    setRun(await api.run(branch, assetId!));
    onTabChange('run');
  });
  const doRollback = () => guard('rollback', async () => {
    await api.rollback(assetId!);
    await loadAsset(assetId!);
    onChanged();
  });

  const ACTIONS: Record<string, () => void> = {
    clone: doClone, edit: doSave, diff: doDiff, validate: doValidate,
    compile: doCompile, smoke: doSmoke, compare: doCompare,
    accept: doAccept, activate: doActivate,
  };

  // ---------------- panels ----------------
  // Declarative-branch detail. It rides under the human overview rather than
  // competing with it: readiness and a prompt binding without a body are things
  // to know about a node, not the first thing to say about one.
  const branchDetail = (
    <>
      {n.readiness ? (<>
        <h3>Готовность</h3>
        <div className="row">
          <ReadinessBadge readiness={n.readiness} />
        </div>
        <div className="kv">
          <div className="k">почему</div>
          <div className="v" data-readiness-reason>{n.readiness.reason || '—'}</div>
          <div className="k">свидетельство</div>
          <div className="v mono">{n.readiness.evidence || '—'}</div>
        </div>
      </>) : null}
      {n.optional || n.conditional_on ? (
        <div className="card" data-conditional={n.node_id} style={{ fontSize: 11 }}>
          {n.optional ? <b>условный шаг — не выполняется всегда. </b> : null}
          {n.conditional_on ? <span className="mono">{n.conditional_on}</span> : null}
        </div>) : null}
      {n.prompt_binding ? (<>
        <h3>Привязка промпта</h3>
        <div className="kv" data-prompt-binding={n.prompt_binding.binding}>
          <div className="k">binding</div>
          <div className="v mono">{n.prompt_binding.binding}</div>
          <div className="k">тело промпта</div>
          <div className="v"><Pill text={n.prompt_binding.body_status}
            tone={n.prompt_binding.body_status === 'MIRRORED_READ_ONLY'
              ? 'ok' : 'warn'} /></div>
        </div>
        {n.prompt_binding.body_status === 'MIRRORED_READ_ONLY' ? (
          <PromptBody branch={branch} binding={n.prompt_binding.binding} />
        ) : null}
      </>) : null}
      {n.contract_refs?.filter(Boolean).length ? (<>
        <h3>Контракты узла</h3>
        <ul className="inv-list">
          {n.contract_refs.filter(Boolean).map((c: string) => (
            <li key={c} className="mono" data-node-contract={c}>{c}</li>
          ))}
        </ul>
      </>) : null}
    </>
  );

  const variantsPanel = assetView ? (
    <>
      <h3>Варианты ({variants.length})</h3>
      {variants.map((v) => (
        <div key={v.variant_id} className="card" data-variant={v.variant_id} style={{
          borderColor: v.variant_id === workingId ? 'var(--accent)' : undefined }}>
          <div className="row" style={{ margin: 0 }}>
            <Pill text={v.state} tone={stateTone(v.state)} />
            {v.variant_id === assetView.active_variant_id
              ? <Pill text="активен" tone="ok" /> : null}
            <span className="mono">{v.variant_id}</span>
            <span style={{ flex: 1 }} />
            <button onClick={() => loadAsset(assetId!, v.variant_id)}>выбрать</button>
          </div>
          <div className="mono" style={{ color: 'var(--text-dim)' }}>
            {v.origin} · {v.source_hash?.slice(0, 12)}</div>
        </div>))}
    </>
  ) : null;

  const sourcePanel = !editorAvailable ? (
    <div className="card">Узел не промпт-управляемый. Редактор недоступен.</div>
  ) : (
    <>
      <h3>Текст промпта</h3>
      <div className="row" style={{ gap: 4 }}>
        <span className="dim">области:</span>
        {regions.map((r) => (
          <button key={r.name} title={r.reason}
            onClick={() => editor.current?.gotoRegion(r.name)}>
            {r.kind === 'protected' ? '🔒' : '✎'} {r.name}</button>))}
      </div>

      <PromptEditor
        ref={editor}
        value={source}
        readOnly={isBaseline}
        regions={regions as any}
        spans={compiled?.source_map}
        markers={validationMarkers}
        onChange={(t) => { setSource(t); setDirty(true); }}
        onSelectionChange={setSel}
      />

      <div className="row">
        <button onClick={() => editor.current?.undo()} title="Ctrl+Z">↶ undo</button>
        <button onClick={() => editor.current?.redo()} title="Ctrl+Shift+Z">↷ redo</button>
        <span className="mono" style={{ color: 'var(--text-dim)' }}>
          cursor {sel.from}{sel.to !== sel.from ? `–${sel.to}` : ''}
          {sel.text ? ` · выделено ${sel.text.length}` : ''}</span>
        <span style={{ flex: 1 }} />
        {isBaseline
          ? <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
              BASELINE только для чтения — клонируйте для правки</span>
          : <button className="primary" disabled={!dirty || !!busy} onClick={doSave}>
              Сохранить</button>}
      </div>

      <PromptCopilot
        branch={branch}
        sourceText={source}
        selection={sel.text}
        readOnly={isBaseline}
        onInsertAll={(t) => editor.current?.insertAll(t)}
        onInsertSelection={(t) => editor.current?.insertSelection(t)}
      />
      {diff ? (
        <div className="row">
          <button data-action="apply-diff" disabled={isBaseline}
            onClick={() => {
              const add = (diff?.unified || []).find((l: string) =>
                l.startsWith('+') && !l.startsWith('+++'));
              const del = (diff?.unified || []).find((l: string) =>
                l.startsWith('-') && !l.startsWith('---'));
              if (!add || !del) { setErr('нет применимого ханка'); return; }
              const ok = editor.current?.applyDiff(del.slice(1), add.slice(1));
              if (!ok) setErr('ханк не найден в тексте');
            }}>Применить ханк из diff</button>
        </div>
      ) : null}
      {diff ? (<>
        <h3>Diff с baseline</h3>
        <div className="row">
          <Pill text={`+${diff.added}`} tone="ok" /><Pill text={`−${diff.removed}`} tone="err" />
          {diff.identical ? <Pill text="идентичны" tone="warn" /> : null}
        </div>
        <pre className="block diff">{diff.unified.map((l: string, i: number) => (
          <div key={i} className={l.startsWith('+') && !l.startsWith('+++') ? 'add'
            : l.startsWith('-') && !l.startsWith('---') ? 'del' : ''}>{l}</div>))}</pre>
      </>) : null}
    </>
  );

  const contractPanel = (
    <>
      <h2>Проверки</h2>
      {!validation ? <p style={{ color: 'var(--text-dim)' }}>Валидация ещё не запускалась.</p> : (<>
        <div className="row">
          <Pill text={validation.verdict}
            tone={validation.verdict === 'pass' ? 'ok'
              : validation.verdict === 'warn' ? 'warn' : 'err'} />
          <Pill text={validation.drift_class}
            tone={validation.drift_class === 'NEW_CANDIDATE_DRIFT' ? 'err'
              : validation.drift_class === 'KNOWN_BASELINE_DRIFT' ? 'warn' : 'ok'} />
        </div>
        {validation.issues.map((i: Json, k: number) => (
          <div key={k} className="card">
            <div className="row" style={{ margin: 0 }}>
              <Pill text={i.severity}
                tone={i.severity === 'error' ? 'err'
                  : i.severity === 'warning' ? 'warn' : undefined} />
              <span className="mono">{i.code}</span>
            </div>
            <div style={{ fontSize: 11, marginTop: 4 }}>{i.message}</div>
            {Object.keys(i.detail || {}).length ? (
              <pre className="block" style={{ maxHeight: 130 }}>
                {JSON.stringify(i.detail, null, 1)}</pre>) : null}
          </div>))}
      </>)}
      {smoke ? (<>
        <h3>Смок</h3>
        <div className="row">
          <Pill text={smoke.ok ? 'pass' : 'fail'} tone={smoke.ok ? 'ok' : 'err'} />
          <Pill text={smoke.fixture_id} />
          <Pill text={`${smoke.provider}/${smoke.model}`} />
          <Pill text={`in ${smoke.tokens_in} / out ${smoke.tokens_out}`} />
        </div>
        <pre className="block">{smoke.raw_text}</pre>
      </>) : null}
      {cmp ? (<>
        <h3>Baseline ↔ Candidate</h3>
        <div className="kv">
          <div className="k">tokens_out</div>
          <div className="v">{cmp.delta.tokens_out.baseline} → {cmp.delta.tokens_out.candidate}
            {' '}(×{cmp.delta.tokens_out.ratio})</div>
          <div className="k">поля +</div>
          <div className="v mono">{cmp.delta.fields_added.join(', ') || '—'}</div>
          <div className="k">поля −</div>
          <div className="v mono">{cmp.delta.fields_removed.join(', ') || '—'}</div>
          <div className="k">выход идентичен</div>
          <div className="v">{String(cmp.delta.identical_output)}</div>
          <div className="k">триггеры отката</div>
          <div className="v">{cmp.delta.rollback_triggers.length
            ? <Pill text={cmp.delta.rollback_triggers.join(', ')} tone="err" />
            : <Pill text="нет" tone="ok" />}</div>
        </div>
      </>) : null}
    </>
  );

  const compiledPanel = (
    <>
      <h2>COMPILED</h2>
      {!compiled ? <p style={{ color: 'var(--text-dim)' }}>Компиляция ещё не запускалась.</p> : (<>
        <div className="row">
          <Pill text={`provenance ${compiled.provenance_coverage}`}
            tone={compiled.provenance_coverage === '100%' ? 'ok' : 'err'} />
          <Pill text={`${compiled.token_count.total} токенов (оценка)`} />
          {compiled.cache_hit ? <Pill text="cache hit" tone="ok" /> : <Pill text="compiled" />}
        </div>
        <div className="kv">
          <div className="k">compiled_hash</div><div className="v mono">{compiled.compiled_hash}</div>
          <div className="k">profile</div><div className="v mono">{compiled.profile_id}</div>
          <div className="k">cache_key</div><div className="v mono">{compiled.cache_key}</div>
        </div>
        <h3>system</h3>
        <pre className="block">{compiled.system_text}</pre>
        <h3>user</h3>
        <pre className="block">{compiled.user_template}</pre>
        <h3>Provenance map ({compiled.source_map.length})</h3>
        {compiled.source_map.map((s: Json, i: number) => (
          <div key={i} className="span-row">
            <span className={s.kind === 'source_module' ? 'src' : 'gen'}>
              {s.kind === 'source_module' ? '▣' : '⚙'}</span>
            <span className="mono">{s.target} {s.span_start}–{s.span_end}</span>
            <span className="mono" style={{ color: 'var(--text-dim)' }}>
              {s.kind === 'source_module'
                ? `${s.region_name} (${s.region_kind})`
                : `rule=${s.rule_id}`}</span>
          </div>))}
      </>)}
    </>
  );

  const effectsPanel = (
    <>
      <h2>Гибриды и эффекты</h2>
      <p style={{ fontSize: 11, color: 'var(--text-dim)' }}>
        Семантический контрол не расщепляется: один контрол — несколько эффектов.
      </p>
      {effects.map((c: Json) => (
        <div key={c.control.id} className="card">
          <div className="row" style={{ margin: 0 }}>
            <b style={{ fontSize: 12 }}>{c.control.label}</b>
            <Pill text={c.control.subject} />
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', margin: '4px 0' }}>
            {c.control.semantics}</div>
          {c.effects.map((e: Json, i: number) => (
            <div key={i} className="effect">
              <div className={`cls ${e.class}`}>{e.class}</div>
              <div className="mono">{e.target}</div>
              <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>
                потребители: {e.consumers.join(', ')}</div>
              <div className="mono" style={{ color: 'var(--text-dim)' }}>{e.source_ref}</div>
              {e.value_map ? <pre className="block" style={{ maxHeight: 90 }}>
                {JSON.stringify(e.value_map, null, 1)}</pre> : null}
            </div>))}
        </div>))}
    </>
  );

  const runsPanel = (
    <>
      <h2>RunTrace</h2>
      <div className="row">
        <button className="primary" disabled={!assetId || !!busy} onClick={doRun}>
          ▶ Запустить run</button>
        <button disabled={!assetId || !!busy} onClick={doRollback}>↩ Откатить</button>
      </div>
      {!run ? <p style={{ color: 'var(--text-dim)' }}>Прогонов ещё не было.</p> : (<>
        <div className="kv">
          <div className="k">run_id</div><div className="v mono">{run.run_id}</div>
          <div className="k">snapshot_id</div>
          <div className="v mono">{run.activation_snapshot.snapshot_id}</div>
          <div className="k">activation_revision</div>
          <div className="v mono">{run.activation_snapshot.activation_revision}</div>
        </div>
        {run.nodes.map((rn: Json, i: number) => (
          <div key={i} className="card">
            <div className="kv">
              <div className="k">asset_id</div><div className="v mono">{rn.asset_id}</div>
              <div className="k">variant_id</div><div className="v mono">{rn.variant_id}</div>
              <div className="k">source_hash</div><div className="v mono">{rn.source_hash}</div>
              <div className="k">compiled_hash</div><div className="v mono">{rn.compiled_hash}</div>
              <div className="k">profile_id</div><div className="v mono">{rn.profile_id}</div>
              <div className="k">fixture</div><div className="v mono">{rn.fixture_id}</div>
              <div className="k">провайдер</div>
              <div className="v mono">{rn.provider}/{rn.model}</div>
              <div className="k">токены</div>
              <div className="v">in {rn.tokens_in} / out {rn.tokens_out}</div>
              <div className="k">выход валиден</div>
              <div className="v">{rn.output_valid
                ? <Pill text="да" tone="ok" /> : <Pill text="нет" tone="err" />}</div>
            </div>
            <pre className="block">{rn.output_text}</pre>
          </div>))}
      </>)}
    </>
  );

  // ---------------- ВХОД / ВЫХОД — typed contract in human order -----------
  const ioPanel = (
    <>
      <h2>Вход и выход</h2>
      <div className="ov-field">
        <div className="ov-field__label">Получает</div>
        <div className="ov-field__value" data-io-in>
          {n.doc?.receives || n.input_contract
            || <span className="dim">вход не типизирован</span>}
        </div>
      </div>
      <div className="ov-field">
        <div className="ov-field__label">Выдаёт</div>
        <div className="ov-field__value" data-io-out>
          {n.doc?.produces || n.output_contract
            || <span className="dim">выход не типизирован</span>}
        </div>
      </div>
      <div className="ov-field">
        <div className="ov-field__label">Куда идёт результат</div>
        <div className="ov-field__value">
          {n.doc?.consumers || <span className="dim">потребители не описаны</span>}
        </div>
      </div>
      {node.executions?.length ? (
        <>
          <h3>В выбранном запуске</h3>
          {node.executions.map((e: Json, i: number) => (
            <div key={i} className="card">
              <table className="kvt"><tbody>
                <tr><td>получил</td>
                  <td><code>{(e.input_object_ids || []).join(', ') || '—'}</code></td></tr>
                <tr><td>выдал</td>
                  <td><code>{(e.output_object_ids || []).filter(Boolean).join(', ') || '—'}</code></td></tr>
              </tbody></table>
            </div>
          ))}
        </>
      ) : (
        <p className="ov-empty">
          Фактические объекты появятся, когда будет выбран запуск.
        </p>
      )}
    </>
  );

  // ---------------- ПРОМПТ — editorial workflow, CI ladder folded away -----
  const promptPanel = !editorAvailable ? (
    <div className="card">Узел не промпт-управляемый — редактор не открывается.</div>
  ) : (
    <>
      <h2>Промпт</h2>
      <div className="prompt-head" data-prompt-head>
        <table className="kvt"><tbody>
          <tr><td>активный вариант</td>
            <td><code data-active-variant>{assetView?.active_variant_id}</code></td></tr>
          <tr><td>вы правите</td><td>
            <code>{workingId}</code>{' '}
            <span className={`badge ${isBaseline ? 'warn' : 'ok'}`}>
              {working?.state}</span></td></tr>
          <tr><td>профиль компиляции</td>
            <td><code>{assetView?.compiler_profile?.profile_id}</code></td></tr>
        </tbody></table>
        {isBaseline ? (
          <div className="row">
            <button className="primary" data-prompt-edit-copy
              disabled={!!busy} onClick={doClone}>Редактировать копию</button>
            <button data-prompt-diff onClick={doDiff}>Сравнить варианты</button>
          </div>
        ) : (
          <div className="row">
            <button className="primary" data-prompt-check
              disabled={!!busy} onClick={doValidate}>Проверить</button>
            <button data-prompt-test disabled={!!busy} onClick={doSmoke}>
              Протестировать</button>
            <button data-prompt-diff onClick={doDiff}>Сравнить с активным</button>
            <button data-prompt-activate disabled={!!busy} onClick={doActivate}>
              Активировать</button>
            <button data-prompt-rollback disabled={!!busy} onClick={doRollback}>
              Откатить</button>
          </div>
        )}
        {validation ? (
          <div className="row" data-prompt-verdict>
            <span className={`badge ${validation.verdict === 'pass' ? 'ok'
              : validation.verdict === 'warn' ? 'warn' : 'bad'}`}>
              проверка: {validation.verdict}</span>
            <span className="badge">{validation.drift_class}</span>
            <button onClick={() => onTabChange('contracts')}>подробности</button>
          </div>
        ) : null}
        {!isBaseline ? (
          <p className="dim" data-verify-hint>
            Чтобы увидеть эффект: активируйте версию, запустите пайплайн на том
            же входе и сравните два прогона во вкладке «Запуски».
          </p>
        ) : null}
        {smoke ? (
          <div className="row" data-prompt-smoke>
            <span className={`badge ${smoke.passed ? 'ok' : 'bad'}`}>
              тест: {smoke.passed ? 'пройден' : 'не пройден'}</span>
            <span className="badge">{smoke.level}</span>
          </div>
        ) : null}
      </div>

      {sourcePanel}
      {variantsPanel}

      <button className="ov-tech-toggle" data-lifecycle-toggle
        onClick={() => setLifecycle((l) => !l)}>
        Полный жизненный цикл {lifecycle ? '▴' : '▾'}
      </button>
      {lifecycle ? (
        <div className="card" data-lifecycle>
          <p className="dim">
            Внутренние стадии. Кнопки выше проходят их за вас; здесь они
            доступны по отдельности.
          </p>
          <div className="steps">
            {STEPS.map(([k, label]) => (
              <div key={k} className={`step ${done.has(k) ? 'done' : ''}`}>
                <span className="n">{done.has(k) ? '✓' : ''}</span>
                <span style={{ flex: 1 }}>{label}</span>
                <button data-step={k}
                  disabled={!!busy || !workingId ||
                    (isBaseline && k !== 'clone' && k !== 'diff')}
                  onClick={ACTIONS[k]}>{busy === k ? '…' : '▸'}</button>
              </div>))}
          </div>
          {compiledPanel}
        </div>
      ) : null}
    </>
  );

  return (
    <div className="dock-body">
      {err ? <div className="card err-text">{err}</div> : null}

      {tab === 'overview' && (
        <>
          <NodeOverview node={node} run={runId ? { run_id: runId } : null}
            onOpenTab={onTabChange} />
          {branchDetail}
        </>
      )}
      {tab === 'io' && ioPanel}
      {tab === 'prompt' && promptPanel}
      {tab === 'rag' && (n.rag_profile_id
        ? <RagPanel profileId={n.rag_profile_id} onChanged={onChanged}
            executions={node.executions} runId={runId} />
        : <div className="card">Узел не является узлом извлечения.</div>)}
      {tab === 'settings' && effectsPanel}
      {tab === 'contracts' && contractPanel}
      {tab === 'run' && runsPanel}
    </div>
  );
}
