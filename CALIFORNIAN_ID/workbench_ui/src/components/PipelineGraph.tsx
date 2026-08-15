/**
 * Pipeline graph.
 *
 * Donor pattern: quinta/src/components/base/AgentMapView.tsx — ReactFlowProvider +
 * ReactFlow + Background + Controls + MiniMap with custom node types.
 *
 * Layout is rank-based rather than "six per column": the product screen has to
 * show the actual process, and a chunked column grid hid the council loop
 * entirely. Ranks come from the production edges; an edge that points back to an
 * equal-or-earlier rank is a loop edge and is drawn as one. Declared-only nodes
 * are parked in their own lane so a declaration is never mistaken for a step
 * that runs.
 */
import { useMemo } from 'react';
import {
  Background, Controls, Handle, Position, ReactFlow, ReactFlowProvider,
  type Edge, type Node, type NodeProps,
} from '@xyflow/react';

export interface GraphNode {
  node_id: string; label: string; kind: string; implementation: string;
  asset_id: string | null; rag_profile_id: string | null;
  output_contract: string | null; note?: string;
  layer?: string; in_loop?: boolean; doc?: any;
}
export interface GraphEdge {
  edge_id: string; source: string; target: string; carries: string; layer?: string;
}

const KIND_SHORT: Record<string, string> = {
  MODEL_CALL: 'модель',
  PROMPT: 'промпт',
  DETERMINISTIC: 'код',
  RAG: 'извлечение',
  ROUTER: 'маршрут',
  STORE: 'хранение',
  HUMAN_GATE: 'человек',
  HYBRID: 'гибрид',
  OTHER: '—',
};

function WbNode({ data, selected }: NodeProps) {
  const d = data as unknown as GraphNode & {
    drift?: string; onSelect?: (id: string) => void;
    telemetry?: { label: string; value: string; grade: string }[];
    executed?: boolean; runMode?: boolean;
  };
  const declaredOnly = d.layer === 'DECLARED_PIPELINE';
  return (
    <div
      className={`wb-node k-${d.kind}${selected ? ' selected' : ''}`
        + (declaredOnly ? ' declared-only' : '')
        + (d.runMode ? (d.executed ? ' executed' : ' not-executed') : '')}
      onPointerDown={() => d.onSelect?.(d.node_id)}
      data-node-id={d.node_id}
      data-executed={d.runMode ? String(!!d.executed) : undefined}
      title={d.node_id}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div className="label">{d.label}</div>
      <div className="kind">{KIND_SHORT[d.kind] || d.kind}</div>
      {declaredOnly ? <div className="meta">только объявление</div> : null}
      {d.runMode && !declaredOnly ? (
        <div className={`meta ${d.executed ? 'ok' : ''}`}>
          {d.executed ? '✓ выполнен' : 'не наблюдался'}
        </div>
      ) : null}
      {d.telemetry?.length ? (
        <div className="tele">
          {d.telemetry.map((t, i) => (
            <span key={i} className={`tele-item ${t.grade === 'MEASURED' ? 'm' : 'e'}`}
              title={t.grade}>{t.label} {t.value}</span>))}
        </div>) : null}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}

/** A labelled band behind the ranks that form a cycle. Purely explanatory:
 *  without it the loop is just an edge that happens to point upwards. */
function BandNode({ data }: NodeProps) {
  const d = data as any;
  return (
    <div className="wb-band" style={{ width: d.w, height: d.h }} data-band={d.band_id}>
      <span className="wb-band__label">{d.label}</span>
    </div>
  );
}

const nodeTypes = { wb: WbNode, band: BandNode };

const ROW_H = 76;
const COL_W = 230;
const NODE_W = 190;

/** Rank every production node by longest path from a source, and report which
 *  edges close a cycle. Pure structure — no branch knowledge. */
function layout(nodes: GraphNode[], edges: GraphEdge[]) {
  const live = nodes.filter((n) => n.layer !== 'DECLARED_PIPELINE');
  const liveIds = new Set(live.map((n) => n.node_id));
  const prod = edges.filter(
    (e) => e.layer !== 'DECLARED_PIPELINE' && liveIds.has(e.source) && liveIds.has(e.target));

  const indeg = new Map<string, number>();
  live.forEach((n) => indeg.set(n.node_id, 0));
  prod.forEach((e) => indeg.set(e.target, (indeg.get(e.target) || 0) + 1));

  // Kahn with cycle tolerance: when nothing has indegree 0 the remaining edges
  // are the back edges, and the earliest remaining node opens the next rank.
  const rank = new Map<string, number>();
  const remaining = new Set(liveIds);
  const deg = new Map(indeg);
  let r = 0;
  while (remaining.size) {
    let ready = [...remaining].filter((id) => (deg.get(id) || 0) <= 0);
    if (!ready.length) ready = [[...remaining][0]];   // cycle entry point
    ready.forEach((id) => rank.set(id, r));
    ready.forEach((id) => {
      remaining.delete(id);
      prod.filter((e) => e.source === id).forEach((e) => {
        if (remaining.has(e.target)) deg.set(e.target, (deg.get(e.target) || 0) - 1);
      });
    });
    r += 1;
  }

  const backEdges = new Set(
    prod.filter((e) => (rank.get(e.target) ?? 0) <= (rank.get(e.source) ?? 0))
      .map((e) => e.edge_id));

  const byRank = new Map<number, string[]>();
  live.forEach((n) => {
    const k = rank.get(n.node_id) ?? 0;
    byRank.set(k, [...(byRank.get(k) || []), n.node_id]);
  });

  const widest = Math.max(1, ...[...byRank.values()].map((v) => v.length));
  const centre = 40 + ((widest - 1) * COL_W) / 2;

  const pos = new Map<string, { x: number; y: number }>();
  byRank.forEach((ids, k) => {
    const offset = -((ids.length - 1) * COL_W) / 2;
    ids.forEach((id, i) => pos.set(id, { x: centre + offset + i * COL_W, y: 20 + k * ROW_H }));
  });
  // Declared-but-not-executed steps get their own lane to the right of the
  // widest rank — visibly adjacent to the process, visibly not part of it.
  const laneX = centre + ((widest - 1) * COL_W) / 2 + COL_W + 40;
  nodes.filter((n) => n.layer === 'DECLARED_PIPELINE').forEach((n, i) => {
    pos.set(n.node_id, { x: laneX, y: 20 + i * ROW_H });
  });

  // The span of ranks a back edge closes over is the cycle.
  let band: { x: number; y: number; w: number; h: number } | null = null;
  const backs = prod.filter((e) => backEdges.has(e.edge_id));
  if (backs.length) {
    const lo = Math.min(...backs.map((e) => rank.get(e.target) ?? 0));
    const hi = Math.max(...backs.map((e) => rank.get(e.source) ?? 0));
    const members = [...rank.entries()].filter(([, k]) => k >= lo && k <= hi);
    const xs = members.map(([id]) => pos.get(id)!.x);
    band = {
      x: Math.min(...xs) - 26,
      y: 20 + lo * ROW_H - 22,
      w: Math.max(...xs) - Math.min(...xs) + NODE_W + 52,
      h: (hi - lo) * ROW_H + 92,
    };
  }
  return { pos, backEdges, band };
}

export function PipelineGraph({
  nodes, edges, selectedId, driftByNode, telemetry, edgeLabels,
  executed, runMode, onSelect,
}: {
  nodes: GraphNode[]; edges: GraphEdge[]; selectedId: string | null;
  driftByNode: Record<string, string>;
  telemetry?: Record<string, { label: string; value: string; grade: string }[]>;
  edgeLabels?: Record<string, string>;
  executed?: Set<string>;
  runMode?: boolean;
  onSelect: (nodeId: string) => void;
}) {
  const { pos, backEdges, band } = useMemo(() => layout(nodes, edges), [nodes, edges]);

  const rfNodes: Node[] = useMemo(() => {
    const list: Node[] = [];
    if (band) {
      list.push({
        id: '__loop_band__', type: 'band', draggable: false, selectable: false,
        position: { x: band.x, y: band.y }, zIndex: -1,
        data: { w: band.w, h: band.h, band_id: 'council_loop',
                label: 'Цикл совета — повторяется, пока не решено остановиться' },
      });
    }
    nodes.forEach((n) => list.push({
      id: n.node_id,
      type: 'wb',
      position: pos.get(n.node_id) || { x: 40, y: 20 },
      data: {
        ...n, drift: driftByNode[n.node_id], telemetry: telemetry?.[n.node_id],
        executed: executed?.has(n.node_id), runMode, onSelect,
      },
      selected: n.node_id === selectedId,
    }));
    return list;
  }, [nodes, pos, band, selectedId, driftByNode, telemetry, executed, runMode, onSelect]);

  const rfEdges: Edge[] = useMemo(
    () => edges.map((e) => {
      const declared = e.layer === 'DECLARED_PIPELINE';
      const back = backEdges.has(e.edge_id);
      return {
        id: e.edge_id, source: e.source, target: e.target,
        label: edgeLabels?.[e.edge_id] ?? (back ? 'цикл совета' : undefined),
        animated: back,
        style: {
          stroke: back ? '#e0a83c' : declared ? '#4a4152' : '#3a4150',
          strokeWidth: back ? 2 : 1,
          strokeDasharray: declared ? '4 3' : undefined,
        },
        labelStyle: { fill: back ? '#e0a83c' : '#98a0b0', fontSize: 10 },
        labelBgStyle: { fill: '#1b1e25' },
        data: { back },
      } as Edge;
    }),
    [edges, backEdges, edgeLabels],
  );

  return (
    <ReactFlowProvider>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelect(node.id)}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.2}
      >
        <Background color="#232833" gap={18} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </ReactFlowProvider>
  );
}
