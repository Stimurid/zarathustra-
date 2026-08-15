import { useCallback, useEffect, useState } from 'react';
import { api, type Json } from './api';
import { PipelineGraph, type GraphEdge, type GraphNode } from './components/PipelineGraph';
import { FieldProjection } from './components/FieldProjection';
import { Inspector } from './components/Inspector';
import { RightDock, type DockTab } from './components/RightDock';

const BRANCH = 'zarathustra';

const TABS: { id: DockTab; label: string; icon: string }[] = [
  { id: 'inspector', label: 'Узел', icon: '◉' },
  { id: 'rag', label: 'RAG', icon: '⌕' },
  { id: 'source', label: 'SOURCE', icon: '✎' },
  { id: 'contract', label: 'Проверки', icon: '⚖' },
  { id: 'compiled', label: 'COMPILED', icon: '⚙' },
  { id: 'effects', label: 'Эффекты', icon: '⇄' },
  { id: 'runs', label: 'Runs', icon: '▶' },
];

export function App() {
  const [inputMode, setInputMode] = useState('raw');
  const [graph, setGraph] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [node, setNode] = useState<Json | null>(null);
  const [drift, setDrift] = useState<Record<string, string>>({});
  const [telemetry, setTelemetry] = useState<Record<string, any[]>>({});
  const [edgeLabels, setEdgeLabels] = useState<Record<string, string>>({});
  const [view, setView] = useState<'graph' | 'radial'>('graph');
  const [field, setField] = useState<Json | null>(null);
  const [tab, setTab] = useState<DockTab>('inspector');
  const [collapsed, setCollapsed] = useState(false);
  const [width, setWidth] = useState(Math.round(window.innerWidth / 3));
  const [mode, setMode] = useState<'pinned' | 'overlay'>('pinned');
  const [err, setErr] = useState('');

  const loadGraph = useCallback(async () => {
    try {
      const g = await api.graph(BRANCH, inputMode);
      setGraph({ nodes: g.nodes, edges: g.edges });
      const badges: Record<string, string> = {};
      for (const n of g.nodes as GraphNode[]) {
        if (!n.asset_id) continue;
        try {
          const view = await api.asset(n.asset_id);
          // A badge only means something when the asset actually declares fields;
          // "0/0/0" for an asset without a declared contract is noise, not drift.
          if (view.contract && view.contract.status !== 'OK'
              && view.contract.prompt_fields.length) {
            badges[n.node_id] = view.contract.summary;
          }
        } catch { /* asset without contract */ }
      }
      setDrift(badges);

      // ---- telemetry overlay from the most recent run (measured only) ----
      const { runs } = await api.runs();
      const last = runs?.[0];
      const tele: Record<string, { label: string; value: string; grade: string }[]> = {};
      const elabels: Record<string, string> = {};
      if (last) {
        for (const rn of last.rag_nodes || []) {
          tele[rn.node_id] = [
            { label: 'chunks', value: `${rn.returned_count}/${rn.considered_count}`, grade: 'MEASURED' },
            { label: 'ctx', value: `${rn.context_tokens}t`, grade: 'ESTIMATED' },
            { label: '', value: `${rn.context_bytes}B`, grade: 'MEASURED' },
            { label: '', value: `${rn.latency_ms}ms`, grade: 'MEASURED' },
            { label: 'v', value: rn.rag_profile_version, grade: 'MEASURED' },
          ];
          elabels[`${rn.node_id}->analyze_situation`] =
            `${rn.returned_count} chunks · ${rn.context_bytes}B · ${rn.context_identity?.slice(0, 12)}`;
        }
        for (const mn of last.nodes || []) {
          tele[mn.node_id] = [
            { label: 'in/out', value: `${mn.tokens_in}/${mn.tokens_out}`, grade: 'MEASURED' },
            { label: '', value: `${mn.latency_ms}ms`, grade: 'MEASURED' },
            { label: '', value: `${mn.provider}`, grade: 'MEASURED' },
            { label: 'hash', value: String(mn.compiled_hash).slice(7, 15), grade: 'MEASURED' },
          ];
        }
      }
      setTelemetry(tele);
      setEdgeLabels(elabels);
    } catch (e: any) { setErr(String(e.message || e)); }
  }, [inputMode]);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  useEffect(() => {
    if (view !== 'radial') return;
    api.projection(BRANCH, 'radial', inputMode).then(setField)
      .catch((e) => setErr(String(e.message || e)));
  }, [view, inputMode]);

  useEffect(() => {
    if (!selected) { setNode(null); return; }
    api.node(BRANCH, selected, inputMode).then(setNode)
      .catch((e) => setErr(String(e.message || e)));
  }, [selected, inputMode]);

  const onSelect = useCallback((nodeId: string) => {
    setSelected(nodeId);
    setTab('inspector');
    setCollapsed(false);
  }, []);

  const third = Math.round(window.innerWidth / 3);
  const twoThirds = Math.round((window.innerWidth * 2) / 3);

  return (
    <div className="app">
      <header className="topbar">
        <h1>Tinkuy Workbench</h1>
        <span className="pill">ветка: {BRANCH}</span>
        <label style={{ fontSize: 11, color: 'var(--text-dim)' }}>
          тип входа{' '}
          <select value={inputMode} onChange={(e) => setInputMode(e.target.value)}>
            <option value="raw">raw</option>
            <option value="raw+fabric">raw+fabric</option>
            <option value="auto-slice">auto-slice</option>
            <option value="semantic-units">semantic-units</option>
          </select>
        </label>
        <span className="pill">узлов: {graph?.nodes.length ?? 0}</span>
        <span style={{ borderLeft: '1px solid var(--border)', paddingLeft: 10 }}>
          <button data-view="graph" className={view === 'graph' ? 'primary' : ''}
            onClick={() => setView('graph')}>граф</button>{' '}
          <button data-view="radial" className={view === 'radial' ? 'primary' : ''}
            onClick={() => setView('radial')}>поле (WhiteCrow)</button>
        </span>
        <div className="spacer" />
        <button onClick={() => setWidth(third)}>⅓</button>
        <button onClick={() => setWidth(twoThirds)}>⅔</button>
        <button onClick={loadGraph}>обновить</button>
      </header>

      {err ? <div className="err-text" style={{ padding: '4px 14px' }}>{err}</div> : null}

      <div className="main">
        <div className="canvas">
          {view === 'radial' ? (
            <FieldProjection projection={field} selectedId={selected}
              onSelect={onSelect} />
          ) : graph ? (
            <PipelineGraph
              nodes={graph.nodes} edges={graph.edges}
              selectedId={selected} driftByNode={drift}
              telemetry={telemetry} edgeLabels={edgeLabels}
              onSelect={onSelect} />
          ) : <div style={{ padding: 20, color: 'var(--text-dim)' }}>Загрузка графа…</div>}
        </div>

        <RightDock
          defaultWidth={third}
          width={width}
          onWidthChange={setWidth}
          minWidth={280}
          maxWidthPercent={70}
          collapsed={collapsed}
          onCollapseChange={setCollapsed}
          mode={mode}
          onModeChange={setMode}
          activeTab={tab}
          onTabChange={setTab}
          tabs={TABS.map((t) => ({ ...t, content: null }))}
        >
          <Inspector branch={BRANCH} node={node} tab={tab}
            onTabChange={setTab} onChanged={loadGraph} />
        </RightDock>
      </div>
    </div>
  );
}
