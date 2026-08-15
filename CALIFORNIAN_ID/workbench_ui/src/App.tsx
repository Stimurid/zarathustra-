import { useCallback, useEffect, useState } from 'react';
import { api, type Json } from './api';
import { PipelineGraph, type GraphEdge, type GraphNode } from './components/PipelineGraph';
import { FieldProjection } from './components/FieldProjection';
import { Inspector } from './components/Inspector';
import { RightDock, type DockTab } from './components/RightDock';
import {
  BranchContracts, BranchInvariants, BranchProfiles, BranchReadiness, StateView,
} from './components/BranchPanels';

const TABS: { id: DockTab; label: string; icon: string }[] = [
  { id: 'inspector', label: 'Узел', icon: '◉' },
  { id: 'rag', label: 'RAG', icon: '⌕' },
  { id: 'source', label: 'SOURCE', icon: '✎' },
  { id: 'contract', label: 'Проверки', icon: '⚖' },
  { id: 'compiled', label: 'COMPILED', icon: '⚙' },
  { id: 'effects', label: 'Эффекты', icon: '⇄' },
  { id: 'runs', label: 'Runs', icon: '▶' },
];

type Branch = {
  branch: string; pipeline_id: string; version: string; nodes: number;
  has_live_runtime: boolean; generation: string | null; owner: string | null;
  capabilities: Record<string, boolean>;
};

export function App() {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [branch, setBranch] = useState('zarathustra');
  const [inputMode, setInputMode] = useState('raw');
  const [graph, setGraph] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
  // WB-021: the selection is owned by a branch. Storing a bare node id let a
  // branch switch fire `/node/<new branch>/<old node id>` before the reset
  // effect committed, producing a 404 against a node that never existed there.
  const [sel, setSel] = useState<{ branch: string; nodeId: string } | null>(null);
  const selected = sel && sel.branch === branch ? sel.nodeId : null;
  const [node, setNode] = useState<Json | null>(null);
  const [drift, setDrift] = useState<Record<string, string>>({});
  const [telemetry, setTelemetry] = useState<Record<string, any[]>>({});
  const [edgeLabels, setEdgeLabels] = useState<Record<string, string>>({});
  const [view, setView] = useState<'graph' | 'radial' | 'state'>('graph');
  const [field, setField] = useState<Json | null>(null);
  const [tab, setTab] = useState<DockTab>('inspector');
  const [collapsed, setCollapsed] = useState(false);
  const [width, setWidth] = useState(Math.round(window.innerWidth / 3));
  const [mode, setMode] = useState<'pinned' | 'overlay'>('pinned');
  const [err, setErr] = useState('');

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

      // A declarative branch has no runs and no drift; asking for them would
      // manufacture emptiness that reads like a measurement.
      const bmeta = (await api.branches()).branches.find((b: Branch) => b.branch === branch);
      if (!bmeta?.has_live_runtime) {
        setDrift({}); setTelemetry({}); setEdgeLabels({});
        return;
      }

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
  }, [branch, inputMode]);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  // Switching branch must not carry the previous branch's selection or
  // projection with it: a projection is a branch capability, not a global mode.
  useEffect(() => {
    setSel(null); setNode(null); setField(null); setView('graph');
  }, [branch]);

  useEffect(() => {
    if (view !== 'radial') return;
    api.projection(branch, 'radial', inputMode).then(setField)
      .catch((e) => setErr(String(e.message || e)));
  }, [view, branch, inputMode]);

  useEffect(() => {
    if (!selected) { setNode(null); return; }
    api.node(branch, selected, inputMode).then(setNode)
      .catch((e) => setErr(String(e.message || e)));
  }, [selected, branch, inputMode]);

  const onSelect = useCallback((nodeId: string) => {
    setSel({ branch, nodeId });
    setTab('inspector');
    setCollapsed(false);
  }, [branch]);

  const third = Math.round(window.innerWidth / 3);
  const twoThirds = Math.round((window.innerWidth * 2) / 3);

  return (
    <div className="app">
      <header className="topbar">
        <h1>Tinkuy Workbench</h1>
        <label style={{ fontSize: 11, color: 'var(--text-dim)' }}>
          ветка{' '}
          <select data-branch-select value={branch}
            onChange={(e) => setBranch(e.target.value)}>
            {branches.map((b) => (
              <option key={b.branch} value={b.branch}>{b.branch}</option>
            ))}
          </select>
        </label>
        {current?.generation ? (
          <span className="pill" data-generation>{current.generation}</span>
        ) : null}
        <span className={`pill ${live ? 'ok' : 'warn'}`} data-live-runtime={String(live)}>
          {live ? 'live runtime' : 'declarative only'}
        </span>
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
            onClick={() => setView('radial')}>поле (WhiteCrow)</button>{' '}
          {caps.state_projection ? (
            <button data-view="state" className={view === 'state' ? 'primary' : ''}
              onClick={() => setView('state')}>состояния</button>
          ) : null}
        </span>
        <div className="spacer" />
        <button onClick={() => setWidth(third)}>⅓</button>
        <button onClick={() => setWidth(twoThirds)}>⅔</button>
        <button onClick={loadGraph}>обновить</button>
      </header>

      {err ? <div className="err-text" style={{ padding: '4px 14px' }}>{err}</div> : null}

      <div className="main">
        <div className="canvas">
          {view === 'state' ? (
            <StateView branch={branch} />
          ) : view === 'radial' ? (
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
          <Inspector branch={branch} node={node} tab={tab}
            onTabChange={setTab} onChanged={loadGraph} />
          {tab === 'inspector' && !live ? (
            <div className="branch-panels" data-branch-panels={branch}>
              <BranchReadiness branch={branch} />
              <BranchProfiles branch={branch} />
              <BranchContracts branch={branch} />
              <BranchInvariants branch={branch} />
            </div>
          ) : null}
        </RightDock>
      </div>
    </div>
  );
}
