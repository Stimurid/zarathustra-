import { useCallback, useEffect, useMemo, useState } from 'react';
import { api, type Json } from './api';
import { PipelineGraph, type GraphEdge, type GraphNode } from './components/PipelineGraph';
import { FieldProjection } from './components/FieldProjection';
import { Inspector } from './components/Inspector';
import { RightDock, type DockTab } from './components/RightDock';
import { RunPanel } from './components/RunPanel';
import { RunHistory } from './components/RunHistory';
import { PromptCatalogue, RagCatalogue } from './components/Catalogue';
import {
  BranchContracts, BranchInvariants, BranchProfiles, BranchReadiness, StateView,
} from './components/BranchPanels';

/** What the operator is doing, not which subsystem owns the screen. */
type Section = 'pipeline' | 'run' | 'prompts' | 'rag' | 'runs';
type View = 'graph' | 'field' | 'state';

const SECTIONS: { id: Section; label: string }[] = [
  { id: 'pipeline', label: 'Пайплайн' },
  { id: 'run', label: 'Запуск' },
  { id: 'prompts', label: 'Промпты' },
  { id: 'rag', label: 'Извлечение' },
  { id: 'runs', label: 'Запуски' },
];

type Branch = {
  branch: string; pipeline_id: string; version: string; status: string; nodes: number;
  has_live_runtime: boolean; generation: string | null; owner: string | null;
  capabilities: Record<string, boolean>;
};

/** Subject tabs, filtered by what the node actually has. A tab that cannot do
 *  anything for this node is not shown — an empty tab is a broken promise. */
function tabsFor(node: Json | null): { id: DockTab; label: string; icon: string }[] {
  const n = node?.node;
  const tabs: { id: DockTab; label: string; icon: string }[] = [
    { id: 'overview', label: 'Обзор', icon: '◉' },
    { id: 'io', label: 'Вход / выход', icon: '⇄' },
  ];
  if (n?.asset_id) tabs.push({ id: 'prompt', label: 'Промпт', icon: '✎' });
  if (n?.rag_profile_id) tabs.push({ id: 'rag', label: 'Извлечение', icon: '⌕' });
  if (n?.params?.length || node?.effects?.length)
    tabs.push({ id: 'settings', label: 'Настройки', icon: '⚙' });
  if (n?.asset_id || n?.output_contract || n?.contract_refs?.length)
    tabs.push({ id: 'contracts', label: 'Контракты', icon: '⚖' });
  if (n?.asset_id) tabs.push({ id: 'run', label: 'Прогон', icon: '▶' });
  return tabs;
}

export function App() {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [branch, setBranch] = useState('zarathustra');
  const [section, setSection] = useState<Section>('pipeline');
  const [view, setView] = useState<View>('graph');
  const [inputMode, setInputMode] = useState('raw');
  const [graph, setGraph] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
  const [sel, setSel] = useState<{ branch: string; nodeId: string } | null>(null);
  const [node, setNode] = useState<Json | null>(null);
  const [field, setField] = useState<Json | null>(null);
  const [tab, setTab] = useState<DockTab>('overview');
  const [collapsed, setCollapsed] = useState(false);
  const [width, setWidth] = useState(Math.round(window.innerWidth / 3));
  const [mode, setMode] = useState<'pinned' | 'overlay'>('pinned');
  const [err, setErr] = useState('');

  // ---- the product invariant: a pipeline definition is not a run ----
  const [runId, setRunId] = useState<string | null>(null);
  const [runTrace, setRunTrace] = useState<Json | null>(null);
  const [running, setRunning] = useState(false);
  const [showMetrics, setShowMetrics] = useState(false);

  const selected = sel && sel.branch === branch ? sel.nodeId : null;
  const current = branches.find((b) => b.branch === branch) || null;
  const caps = current?.capabilities || {};
  const live = current ? current.has_live_runtime : true;

  useEffect(() => {
    api.branches().then((d) => setBranches(d.branches || []))
      .catch((e) => setErr(String(e.message || e)));
  }, []);

  const loadGraph = useCallback(async () => {
    try {
      const g = await api.graph(branch, inputMode);
      setGraph({ nodes: g.nodes, edges: g.edges });
    } catch (e: any) { setErr(String(e.message || e)); }
  }, [branch, inputMode]);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  // Switching branch carries neither selection nor projection.
  useEffect(() => {
    setSel(null); setNode(null); setField(null); setView('graph');
    setRunId(null); setRunTrace(null);
  }, [branch]);

  useEffect(() => {
    if (view !== 'field') return;
    api.projection(branch, 'radial', inputMode).then(setField)
      .catch((e) => setErr(String(e.message || e)));
  }, [view, branch, inputMode]);

  // Clearing first matters: without it the previous node stayed on screen —
  // with the previous node's tab set — until the fetch resolved, so for a beat
  // the inspector offered a Prompt tab for a node that has no prompt.
  useEffect(() => {
    if (!selected) { setNode(null); return; }
    let stale = false;
    setNode(null);
    api.node(branch, selected, inputMode, runId)
      .then((d) => { if (!stale) setNode(d); })
      .catch((e) => { if (!stale) setErr(String(e.message || e)); });
    return () => { stale = true; };
  }, [selected, branch, inputMode, runId]);

  // A run is loaded only when one is explicitly selected. No "last run" default:
  // that is how a definition screen silently turns into a stale run screen.
  useEffect(() => {
    if (!runId) { setRunTrace(null); return; }
    api.runTrace(runId).then(setRunTrace).catch(() => setRunTrace(null));
  }, [runId]);

  const onSelect = useCallback((nodeId: string) => {
    setSel({ branch, nodeId });
    setSection('pipeline');
    setTab('overview');
    setCollapsed(false);
  }, [branch]);

  const openNodeTab = useCallback((nodeId: string, t: string) => {
    setSel({ branch, nodeId });
    setSection('pipeline');
    setTab(t as DockTab);
    setCollapsed(false);
  }, [branch]);

  // ---- telemetry overlay: derived from the SELECTED run, never from "latest" --
  // Aggregated per node, not per execution: a node that ran five times used to
  // stack fifteen chips on one card and became unreadable.
  const telemetry = useMemo(() => {
    const out: Record<string, { label: string; value: string; grade: string }[]> = {};
    if (!runTrace || !showMetrics) return out;
    const byNode = new Map<string, Json[]>();
    for (const e of (runTrace.node_executions || []) as Json[]) {
      byNode.set(e.node_id, [...(byNode.get(e.node_id) || []), e]);
    }
    byNode.forEach((execs, nid) => {
      const rows: { label: string; value: string; grade: string }[] = [];
      if (execs.length > 1) rows.push({ label: '', value: `${execs.length}×`, grade: 'MEASURED' });
      const chunks = execs.map((e) => e.retrieved_chunks).filter((c) => c != null);
      if (chunks.length) {
        const total = chunks.reduce((a: number, b: number) => a + b, 0);
        rows.push({ label: '', value: `${total} фр.`, grade: 'MEASURED' });
      }
      const topK = [...new Set(execs.map((e) => e.effective_top_k).filter((v) => v != null))];
      if (topK.length) rows.push({ label: 'top_k', value: topK.join('/'), grade: 'MEASURED' });
      const providers = [...new Set(execs.map((e) => e.model_binding?.provider).filter(Boolean))];
      if (providers.length) rows.push({ label: '', value: providers.join('/'), grade: 'MEASURED' });
      out[nid] = rows;
    });
    if (runTrace.duration_ms != null && !out['persist_trace'])
      out['persist_trace'] = [{ label: 'прогон', value: `${runTrace.duration_ms} ms`,
                               grade: 'MEASURED' }];
    return out;
  }, [runTrace, showMetrics]);

  const executedNodes = useMemo(() => {
    const s = new Set<string>();
    for (const e of (runTrace?.node_executions || []) as Json[]) s.add(e.node_id);
    return s;
  }, [runTrace]);

  const third = Math.round(window.innerWidth / 3);
  const twoThirds = Math.round((window.innerWidth * 2) / 3);
  // No node selected means no node tabs: an inspector tab bar over an empty
  // inspector promises a subject that is not there.
  const dockTabs = section === 'pipeline' && node ? tabsFor(node) : [];

  // Fall back to Обзор only once the loaded node IS the selected one. Judging
  // by a stale node threw away a tab the caller had just asked for (opening a
  // retrieval node from the catalogue landed on Обзор instead of Извлечение).
  useEffect(() => {
    if (section !== 'pipeline') return;
    if (node?.node?.node_id !== selected) return;
    if (dockTabs.length && !dockTabs.some((t) => t.id === tab)) setTab('overview');
  }, [node, section, selected]);

  return (
    <div className="app">
      {/* ---------- level 1: what am I looking at ---------- */}
      <header className="topbar">
        <h1>Tinkuy Workbench</h1>
        <div className="topbar__ident">
          <label className="topbar__branch">
            ветка{' '}
            <select data-branch-select value={branch}
              onChange={(e) => setBranch(e.target.value)}>
              {branches.map((b) => (
                <option key={b.branch} value={b.branch}>{b.branch}</option>
              ))}
            </select>
          </label>
          <span className="dim" data-pipeline-ident>
            {current ? `${current.pipeline_id} · v${current.version}` : '…'}
          </span>
        </div>
        <span className={`badge ${live ? 'ok' : 'warn'}`} data-live-runtime={String(live)}>
          {live ? 'можно запускать' : 'только определение'}
        </span>
        {current?.generation
          ? <span className="badge" data-generation>{current.generation}</span> : null}
        <div className="spacer" />
        {live ? (
          <button className="primary" data-run-cta onClick={() => setSection('run')}>
            ▶ Запустить
          </button>
        ) : null}
      </header>

      {/* ---------- main navigation: user tasks ---------- */}
      <nav className="mainnav" data-mainnav>
        {SECTIONS.map((s) => (
          <button key={s.id} data-section={s.id}
            className={section === s.id ? 'sel' : ''}
            onClick={() => setSection(s.id)}>{s.label}</button>
        ))}
        <div className="spacer" />
        <span className="viewsel">
          представление
          <button data-view="graph" className={view === 'graph' ? 'sel' : ''}
            onClick={() => setView('graph')}>Пайплайн</button>
          <button data-view="field" className={view === 'field' ? 'sel' : ''}
            onClick={() => setView('field')}>Поле</button>
          {caps.state_projection ? (
            <button data-view="state" className={view === 'state' ? 'sel' : ''}
              onClick={() => setView('state')}>Состояния</button>
          ) : null}
        </span>
        <label className="metric-toggle">
          <input type="checkbox" data-metrics-toggle checked={showMetrics}
            disabled={!runId}
            onChange={(e) => setShowMetrics(e.target.checked)} />
          показать метрики
        </label>
      </nav>

      {/* ---------- the epistemic mode strip: definition vs a specific run ------ */}
      <div className={`modebar ${runId ? 'modebar--run' : ''}`} data-modebar>
        {runId ? (
          <>
            <b data-mode="run">ЗАПУСК</b>
            <span className="mono">{runId}</span>
            <span className="dim">
              {runTrace?.started_at?.replace('T', ' ').slice(0, 19) || ''}
              {runTrace?.duration_ms != null ? ` · ${runTrace.duration_ms} ms` : ''}
            </span>
            <span className="dim">показаны данные этого прогона</span>
            <div className="spacer" />
            <button data-back-to-definition onClick={() => setRunId(null)}>
              Вернуться к определению
            </button>
          </>
        ) : (
          <>
            <b data-mode="definition">ОПРЕДЕЛЕНИЕ</b>
            <span className="dim">
              как система устроена · прогон не выбран, поэтому измерений нет
            </span>
            <div className="spacer" />
            {running ? <span className="badge warn">идёт прогон…</span> : null}
          </>
        )}
      </div>

      {err ? <div className="err-text" style={{ padding: '4px 14px' }}>{err}</div> : null}

      <div className="main">
        <div className="canvas">
          {view === 'state' ? (
            <StateView branch={branch} />
          ) : view === 'field' ? (
            <FieldProjection projection={field} selectedId={selected}
              onSelect={onSelect} />
          ) : graph ? (
            <PipelineGraph
              nodes={graph.nodes} edges={graph.edges}
              selectedId={selected} driftByNode={{}}
              telemetry={telemetry} edgeLabels={{}}
              executed={executedNodes} runMode={!!runId}
              onSelect={onSelect} />
          ) : <div style={{ padding: 20, color: 'var(--text-dim)' }}>Загрузка пайплайна…</div>}
        </div>

        <RightDock
          defaultWidth={third}
          width={width}
          onWidthChange={setWidth}
          minWidth={300}
          maxWidthPercent={70}
          collapsed={collapsed}
          onCollapseChange={setCollapsed}
          mode={mode}
          onModeChange={setMode}
          activeTab={tab}
          onTabChange={setTab}
          tabs={dockTabs.map((t) => ({ ...t, content: null }))}
        >
          {section === 'pipeline' ? (
            node ? (
              <Inspector branch={branch} node={node} tab={tab} runId={runId}
                onTabChange={setTab} onChanged={loadGraph} />
            ) : (
              <div className="dock-body" data-panel="no-selection">
                <h2>Пайплайн</h2>
                <p>
                  Слева — фактический порядок работы ветки <b>{branch}</b>.
                  Пунктирная рамка выделяет цикл совета: он повторяется, пока
                  чекпойнт не решит остановиться.
                </p>
                <table className="kvt" data-pipeline-summary><tbody>
                  <tr><td>узлов</td><td>{graph?.nodes.length ?? 0}</td></tr>
                  <tr><td>связей</td><td>{graph?.edges.length ?? 0}</td></tr>
                  <tr><td>с промптом</td>
                    <td>{(graph?.nodes || []).filter((n: any) => n.asset_id).length}</td></tr>
                  <tr><td>с извлечением</td>
                    <td>{(graph?.nodes || []).filter((n: any) => n.rag_profile_id).length}</td></tr>
                  <tr><td>только объявлены</td>
                    <td>{(graph?.nodes || []).filter(
                      (n: any) => n.layer === 'DECLARED_PIPELINE').length}</td></tr>
                </tbody></table>
                <h3>Что можно сделать прямо сейчас</h3>
                <ul className="ov-list">
                  <li>Кликнуть узел — прочитать, что он делает и чем управляется.</li>
                  <li>«Промпты» — какие промпты существуют и где действуют.</li>
                  <li>«Извлечение» — как ищется контекст и с какими параметрами.</li>
                  {live ? <li>«Запустить» — прогнать реальный вход через пайплайн.</li> : null}
                </ul>
                {live ? (
                  <>
                    <h3>Как проверить, что изменение подействовало</h3>
                    <ol className="ov-list" data-verify-loop>
                      <li>Запустить пайплайн на выбранном входе.</li>
                      <li>Изменить промпт или параметры извлечения и активировать
                        новую версию.</li>
                      <li>Запустить ещё раз на <b>том же входе</b>.</li>
                      <li>«Запуски» → отметить два прогона как A и B → сравнить.</li>
                    </ol>
                  </>
                ) : null}
                <h3>Рантайм</h3>
                <p className="ov-empty" data-runtime-empty>
                  Прогон не выбран — измерений нет.
                </p>
                {!live ? (
                  <div className="branch-panels" data-branch-panels={branch}>
                    <BranchReadiness branch={branch} />
                    <BranchProfiles branch={branch} />
                    <BranchContracts branch={branch} />
                    <BranchInvariants branch={branch} />
                  </div>
                ) : null}
              </div>
            )
          ) : null}

          {section === 'run' ? (
            <>
              <RunPanel branch={branch} live={live} onActive={setRunning}
                onFinished={(id) => { setRunId(id); setShowMetrics(true); }} />
              {/* A branch that cannot run still owes the operator an account of
                  itself: what it declares, what it is waiting for, and which
                  controls are therefore disabled. */}
              {!live ? (
                <div className="branch-panels" data-branch-panels={branch}>
                  <BranchReadiness branch={branch} />
                  <BranchProfiles branch={branch} />
                  <BranchContracts branch={branch} />
                  <BranchInvariants branch={branch} />
                </div>
              ) : null}
            </>
          ) : null}

          {section === 'prompts' ? (
            <PromptCatalogue nodes={(graph?.nodes || []) as any} onOpen={openNodeTab} />
          ) : null}

          {section === 'rag' ? (
            <RagCatalogue nodes={(graph?.nodes || []) as any} runId={runId}
              onOpen={openNodeTab} />
          ) : null}

          {section === 'runs' ? (
            <RunHistory selected={runId} onSelect={(id) => {
              setRunId(id); if (id) setShowMetrics(true);
            }} />
          ) : null}
        </RightDock>
      </div>

      <footer className="statusbar">
        <span className="dim">
          вход{' '}
          <select value={inputMode} onChange={(e) => setInputMode(e.target.value)}>
            <option value="raw">raw</option>
            <option value="raw+fabric">raw+fabric</option>
            <option value="auto-slice">auto-slice</option>
            <option value="semantic-units">semantic-units</option>
          </select>
        </span>
        <span className="dim">узлов: {graph?.nodes.length ?? 0}</span>
        <div className="spacer" />
        <button onClick={() => setWidth(third)}>⅓</button>
        <button onClick={() => setWidth(twoThirds)}>⅔</button>
        <button onClick={loadGraph}>обновить</button>
      </footer>
    </div>
  );
}
