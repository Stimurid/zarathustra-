/**
 * Stage 4B — WhiteCrow radial field projection.
 *
 * Geometry ported verbatim from the real WhiteCrow implementation
 * (`conceptarticle/mvp/FIELD_KERNEL_v6_3_1.html::getFPERadial`): W=300, H=240,
 * R=95, angle = i/min(8,n)·2π − π/2, node r 10 / active 14, centre hub r=16.
 *
 * It is fed by the SAME typed objects as the graph, and clicking an item calls
 * the same `onSelect(node_id)` — so the inspector, contracts and telemetry are
 * identical whichever projection you came from.
 */
import { useMemo } from 'react';
import type { Json } from '../api';

export interface FieldItemT {
  item_id: string; label: string; node_id: string; role: string;
  kind: string; asset_id: string | null; rag_profile_id: string | null;
  level: string; weight: number; tags: string[]; note: string;
}

export function FieldProjection({
  projection, selectedId, onSelect,
}: {
  projection: Json | null; selectedId: string | null;
  onSelect: (nodeId: string) => void;
}) {
  const g = projection?.geometry;
  const items: FieldItemT[] = projection?.items ?? [];

  const placed = useMemo(() => {
    if (!g) return [];
    const n = Math.min(g.max_items, items.length) || 1;
    return items.slice(0, g.max_items).map((it, i) => {
      const a = (i / n) * 2 * Math.PI - Math.PI / 2;
      return { it, x: g.cx + g.R * Math.cos(a), y: g.cy + g.R * Math.sin(a) };
    });
  }, [items, g]);

  if (!projection || !g) {
    return <div style={{ padding: 20, color: 'var(--text-dim)' }}>
      Загрузка проекции…</div>;
  }

  return (
    <div className="field-proj">
      <div className="field-proj__hd">
        <b>{projection.title}</b>
        <span className="pill">{projection.kind}</span>
        <span className="pill">{items.length} объектов</span>
        <span className="mono" style={{ color: 'var(--text-dim)', fontSize: 10 }}>
          {projection.source_ref}</span>
      </div>
      {/* Scales with the canvas column so every item stays clickable when the
          dock is open — the ported geometry stays 300×240 in viewBox units. */}
      <svg viewBox={`0 0 ${g.W} ${g.H}`}
           className="field-proj__svg" preserveAspectRatio="xMidYMid meet"
           xmlns="http://www.w3.org/2000/svg" data-testid="field-radial">
        {/* decorative ring — must never swallow clicks meant for an item */}
        <circle cx={g.cx} cy={g.cy} r={g.R} pointerEvents="none"
                fill="rgba(255,255,255,.02)" stroke="#333944" strokeWidth={0.6} />
        {placed.map(({ it, x, y }) => {
          const active = it.node_id === selectedId;
          // The hit target is the node circle itself: on the <g> the bounding
          // box centre lands on empty canvas and the click is swallowed by the
          // svg background.
          return (
            <g key={it.item_id} style={{ cursor: 'pointer' }}
               onClick={() => onSelect(it.node_id)}>
              <line x1={g.cx} y1={g.cy} x2={x} y2={y} pointerEvents="none"
                    stroke={active ? '#7c8cf8' : '#333944'} strokeWidth={active ? 1 : 0.5} />
              <circle cx={x} cy={y} r={active ? g.active_r : g.node_r}
                      data-field-item={it.node_id}
                      fill={active ? '#7c8cf8' : '#1b1e25'}
                      stroke={active ? '#7c8cf8' : '#4a5262'}
                      strokeWidth={active ? 2 : 1}>
                <title>{`${it.role} · ${it.kind} · ${it.node_id}`}</title>
              </circle>
              <text x={x} y={y + 2.5} textAnchor="middle" fontSize={5} pointerEvents="none"
                    fontFamily="monospace" fill={active ? '#10121a' : '#98a0b0'}>
                {it.kind.slice(0, 6)}
              </text>
              <text x={x} y={y + (y > g.cy ? 22 : -16)} textAnchor="middle"
                    pointerEvents="none" fontSize={6} fill="#98a0b0">{it.role}</text>
              <text x={x} y={y + (y > g.cy ? 29 : -9)} textAnchor="middle"
                    pointerEvents="none" fontSize={5.5} fill="#6c7484">{it.label}</text>
            </g>
          );
        })}
        <circle cx={g.cx} cy={g.cy} r={g.hub_r} fill="#7c8cf8" opacity={0.15}
                pointerEvents="none" />
        <text x={g.cx} y={g.cy + 3} textAnchor="middle" fontSize={7} pointerEvents="none"
              fontFamily="monospace" fill="#7c8cf8">{projection.center_label}</text>
      </svg>
      <div className="field-proj__note">{projection.note}</div>
    </div>
  );
}
