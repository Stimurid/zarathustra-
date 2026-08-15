import { useEffect, useState } from 'react';
import { api, type Json } from '../api';

type GraphNode = { node_id: string; label: string; kind: string;
  asset_id?: string | null; rag_profile_id?: string | null; doc?: Json };

/**
 * Prompts and retrieval, listed as things rather than as subsystems.
 *
 * These are navigation surfaces: they answer "which prompts exist and where do
 * they act", then hand the operator to the node inspector where the actual work
 * happens. Nothing is edited here — one editor, one place.
 */
export function PromptCatalogue({
  nodes, onOpen,
}: { nodes: GraphNode[]; onOpen: (nodeId: string, tab: string) => void }) {
  const [states, setStates] = useState<Record<string, Json>>({});
  const owned = nodes.filter((n) => n.asset_id);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const acc: Record<string, Json> = {};
      for (const n of owned) {
        try {
          const v = await api.asset(n.asset_id!);
          acc[n.asset_id!] = v;
        } catch { /* asset not registered */ }
      }
      if (!cancelled) setStates(acc);
    })();
    return () => { cancelled = true; };
  }, [nodes.length]);

  if (!owned.length) {
    return (
      <div className="dock-body" data-panel="prompts">
        <h2>Промпты</h2>
        <p className="ov-empty">У этой ветки нет промпт-ассетов.</p>
      </div>
    );
  }

  return (
    <div className="dock-body" data-panel="prompts">
      <h2>Промпты</h2>
      <p className="dim">
        Каждый промпт принадлежит узлу пайплайна. Открытие ведёт в этот узел.
      </p>
      {owned.map((n) => {
        const v = states[n.asset_id!];
        const active = v?.variants?.find(
          (x: Json) => x.variant_id === v.active_variant_id);
        const contract = v?.contract;
        return (
          <button key={n.node_id} className="cat-row" data-prompt-row={n.asset_id}
            onClick={() => onOpen(n.node_id, 'prompt')}>
            <div className="cat-row__title">{n.label}</div>
            <div className="dim mono">{n.asset_id}</div>
            <div className="row" style={{ margin: '4px 0 0' }}>
              {active ? <span className="badge ok">{active.state}</span> : null}
              {v ? <span className="badge">{v.variants.length} вариантов</span> : null}
              {contract && contract.status !== 'OK' && contract.prompt_fields?.length
                ? <span className="badge bad">контракт {contract.summary}</span> : null}
            </div>
          </button>
        );
      })}
    </div>
  );
}

export function RagCatalogue({
  nodes, runId, onOpen,
}: {
  nodes: GraphNode[]; runId: string | null;
  onOpen: (nodeId: string, tab: string) => void;
}) {
  const [profiles, setProfiles] = useState<Record<string, Json>>({});
  const owned = nodes.filter((n) => n.rag_profile_id);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const acc: Record<string, Json> = {};
      for (const n of owned) {
        try { acc[n.rag_profile_id!] = await api.rag(n.rag_profile_id!); }
        catch { /* profile not registered */ }
      }
      if (!cancelled) setProfiles(acc);
    })();
    return () => { cancelled = true; };
  }, [nodes.length]);

  if (!owned.length) {
    return (
      <div className="dock-body" data-panel="rag-catalogue">
        <h2>Извлечение</h2>
        <p className="ov-empty">В этой ветке нет узлов извлечения.</p>
      </div>
    );
  }

  return (
    <div className="dock-body" data-panel="rag-catalogue">
      <h2>Извлечение</h2>
      <p className="dim">
        {runId
          ? 'Показаны настройки; найденные фрагменты — во вкладке узла.'
          : 'Запуск не выбран — показаны только действующие настройки.'}
      </p>
      {owned.map((n) => {
        const p = profiles[n.rag_profile_id!];
        const prof = p?.profile;
        return (
          <button key={n.node_id} className="cat-row" data-rag-row={n.rag_profile_id}
            onClick={() => onOpen(n.node_id, 'rag')}>
            <div className="cat-row__title">{n.label}</div>
            <div className="dim">{n.doc?.purpose || ''}</div>
            <div className="dim mono">{n.rag_profile_id}</div>
            {prof ? (
              <div className="row" style={{ margin: '4px 0 0' }}>
                <span className="badge ok">{prof.state}</span>
                <span className="badge">top_k = {prof.retrieval?.top_k ?? '—'}</span>
                <span className="badge">{prof.scoring?.algorithm || '—'}</span>
              </div>
            ) : <div className="dim">профиль не зарегистрирован</div>}
          </button>
        );
      })}
    </div>
  );
}
