/**
 * Pipeline graph.
 *
 * Donor pattern: quinta/src/components/base/AgentMapView.tsx — ReactFlowProvider +
 * ReactFlow + Background + Controls + MiniMap with custom node types. Layout is
 * deterministic and column-based (Quinta declares "no ELK for first cut"; elkjs
 * is declared there but never used, so nothing to inherit).
 */
import { useMemo } from 'react';
import {
  Background, Controls, Handle, MiniMap, Position, ReactFlow, ReactFlowProvider,
  type Edge, type Node, type NodeProps,
} from '@xyflow/react';

export interface GraphNode {
  node_id: string; label: string; kind: string; implementation: string;
  asset_id: string | null; rag_profile_id: string | null;
  output_contract: string | null; note?: string;
}
export interface GraphEdge { edge_id: string; source: string; target: string; carries: string; }

function WbNode({ data, selected }: NodeProps) {
  const d = data as unknown as GraphNode & { drift?: string; onSelect?: (id: string) => void };
  return (
    <div
      className={`wb-node k-${d.kind} ${selected ? 'selected' : ''}`}
      onPointerDown={() => d.onSelect?.(d.node_id)}
      data-node-id={d.node_id}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div className="kind" style={{ color: 'var(--text-dim)' }}>{d.kind}</div>
      <div className="label">{d.label}</div>
      <div className="meta">
        {d.asset_id ? '✎ prompt asset' : d.rag_profile_id ? '⌕ retrieval' : 'без промпта'}
        {d.drift ? <> · <span className="pill err">{d.drift}</span></> : null}
      </div>
      {(d as any).telemetry ? (
        <div className="tele">
          {(d as any).telemetry.map((t: any, i: number) => (
            <span key={i} className={`tele-item ${t.grade === 'MEASURED' ? 'm' : 'e'}`}
              title={t.grade}>{t.label} {t.value}</span>))}
        </div>) : null}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { wb: WbNode };

const COLUMN_X = [40, 330, 620];

export function PipelineGraph({
  nodes, edges, selectedId, driftByNode, telemetry, edgeLabels, onSelect,
}: {
  nodes: GraphNode[]; edges: GraphEdge[]; selectedId: string | null;
  driftByNode: Record<string, string>;
  telemetry?: Record<string, { label: string; value: string; grade: string }[]>;
  edgeLabels?: Record<string, string>;
  onSelect: (nodeId: string) => void;
}) {
  const rfNodes: Node[] = useMemo(
    () => nodes.map((n, i) => ({
      id: n.node_id,
      type: 'wb',
      position: { x: COLUMN_X[Math.floor(i / 6)] ?? 40, y: 20 + (i % 6) * 96 },
      data: { ...n, drift: driftByNode[n.node_id],
              telemetry: telemetry?.[n.node_id], onSelect },
      selected: n.node_id === selectedId,
    })),
    [nodes, selectedId, driftByNode, telemetry, onSelect],
  );

  const rfEdges: Edge[] = useMemo(
    () => edges.map((e) => ({
      id: e.edge_id, source: e.source, target: e.target,
      label: edgeLabels?.[e.edge_id]
        ?? (e.carries === 'SituationAnalysis' ? e.carries : undefined),
      style: { stroke: '#3a4150' },
      labelStyle: { fill: '#98a0b0', fontSize: 9 },
    })),
    [edges],
  );

  return (
    <ReactFlowProvider>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelect(node.id)}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.3}
      >
        <Background color="#232833" gap={18} />
        <Controls showInteractive={false} />
        <MiniMap pannable zoomable
          nodeColor={() => '#2b313d'} maskColor="rgba(14,16,21,.75)"
          style={{ background: '#1b1e25', border: '1px solid #333944' }} />
      </ReactFlow>
    </ReactFlowProvider>
  );
}
