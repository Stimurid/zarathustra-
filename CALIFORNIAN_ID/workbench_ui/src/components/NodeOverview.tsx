import { useState } from 'react';
import type { Json } from '../api';

const KIND_LABEL: Record<string, string> = {
  MODEL_CALL: 'Вызов модели',
  PROMPT: 'Промпт',
  DETERMINISTIC: 'Детерминированный шаг',
  RAG: 'Извлечение',
  ROUTER: 'Маршрутизатор',
  STORE: 'Хранение',
  HUMAN_GATE: 'Человеческий шлюз',
  HYBRID: 'Гибрид',
  OTHER: 'Не определён',
};

const LAYER_NOTE: Record<string, string> = {
  DECLARED_PIPELINE: 'Объявлен в конфигурации, но рантайм его не исполняет.',
  TEST_HARNESS: 'Существует только в тестовом стенде.',
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  if (children === null || children === undefined || children === '') return null;
  return (
    <div className="ov-field">
      <div className="ov-field__label">{label}</div>
      <div className="ov-field__value">{children}</div>
    </div>
  );
}

/**
 * The first thing an operator sees after clicking a node: what it is, in
 * ordinary language. Asset ids, hashes and lifecycle buttons live further
 * down — behind «Технические детали» — because they answer a question nobody
 * asked yet.
 */
export function NodeOverview({
  node, run, onOpenTab,
}: {
  node: Json;
  run: Json | null;
  onOpenTab: (tab: any) => void;
}) {
  const [tech, setTech] = useState(false);
  const n = node.node;
  const doc = n.doc || {};
  const exec: Json[] = node.executions || [];

  return (
    <div data-panel="node-overview">
      <h2 data-node-title>{n.label}</h2>
      <div className="row">
        <span className="badge" data-node-kind={n.kind}>
          {KIND_LABEL[n.kind] || n.kind}
        </span>
        {n.in_loop ? <span className="badge warn">в цикле совета</span> : null}
        {n.optional ? <span className="badge warn">условный</span> : null}
        {n.layer !== 'ACTUAL_RUNTIME'
          ? <span className="badge bad" data-node-layer={n.layer}>{n.layer}</span>
          : null}
      </div>

      {LAYER_NOTE[n.layer] ? (
        <p className="ov-warn" data-layer-note>{LAYER_NOTE[n.layer]}</p>
      ) : null}

      <Field label="Назначение">
        {doc.purpose || <span className="dim">описание не задано для этого узла</span>}
      </Field>
      <Field label="Когда выполняется">{doc.when}</Field>
      <Field label="Получает">{doc.receives || n.input_contract}</Field>
      <Field label="Выдаёт">{doc.produces || n.output_contract}</Field>
      <Field label="Куда идёт результат">{doc.consumers}</Field>

      {(doc.controlled_by || []).length ? (
        <Field label="Управляется">
          <ul className="ov-list" data-controlled-by>
            {doc.controlled_by.map((c: string) => <li key={c}>{c}</li>)}
          </ul>
        </Field>
      ) : null}

      <div className="row">
        {n.asset_id ? (
          <button data-goto="prompt" onClick={() => onOpenTab('prompt')}>
            Открыть промпт
          </button>
        ) : null}
        {n.rag_profile_id ? (
          <button data-goto="rag" onClick={() => onOpenTab('rag')}>
            Открыть извлечение
          </button>
        ) : null}
        <button data-goto="io" onClick={() => onOpenTab('io')}>Вход / выход</button>
      </div>

      {node.known_issues?.length ? (
        <Field label="Известные проблемы">
          <ul className="ov-list ov-list--bad" data-known-issues>
            {node.known_issues.map((k: string, i: number) => <li key={i}>{k}</li>)}
          </ul>
        </Field>
      ) : null}

      {/* ---- runtime section: definition above, evidence below, never mixed ---- */}
      <div className="ov-runtime" data-runtime-section>
        <h3>{run ? 'Этот запуск' : 'Последнее исполнение'}</h3>
        {!run ? (
          <p className="ov-empty" data-runtime-empty>
            Запуск не выбран — показано только устройство узла.
          </p>
        ) : !exec.length ? (
          <p className="ov-empty" data-runtime-empty>
            В выбранном запуске этот узел не наблюдался.
          </p>
        ) : (
          exec.map((e, i) => (
            <div className="card" key={i} data-execution={e.node_id}>
              <div className="row" style={{ margin: 0 }}>
                <span className="badge ok">выполнен</span>
                {e.turn_index !== undefined && e.turn_index !== null
                  ? <span className="badge">ход {e.turn_index}</span> : null}
                {e.persona_id ? <span className="badge">{e.persona_id}</span> : null}
                {e.operation ? <span className="badge">{e.operation}</span> : null}
              </div>
              <table className="kvt"><tbody>
                <tr><td>получил</td><td><code>{(e.input_object_ids || []).join(', ') || '—'}</code></td></tr>
                <tr><td>выдал</td><td><code>{(e.output_object_ids || []).filter(Boolean).join(', ') || '—'}</code></td></tr>
                {e.retrieved_chunks !== undefined && e.retrieved_chunks !== null ? (
                  <tr><td>найдено фрагментов</td><td>{e.retrieved_chunks}</td></tr>) : null}
                {e.effective_top_k !== undefined && e.effective_top_k !== null ? (
                  <tr><td>действовавший top_k</td><td>{e.effective_top_k}</td></tr>) : null}
                <tr>
                  <td>модель</td>
                  <td>{e.model_binding?.provider
                    ? <code>{e.model_binding.provider}</code>
                    : <span className="dim">не применимо</span>}</td>
                </tr>
                <tr>
                  <td>токены</td>
                  <td>{e.input_tokens != null || e.output_tokens != null
                    ? `${e.input_tokens ?? '—'} → ${e.output_tokens ?? '—'}`
                    : <span className="dim" data-not-measured>не измерялось</span>}</td>
                </tr>
                <tr>
                  <td>стоимость</td>
                  <td><span className="dim">{e.cost?.note || 'неизвестна'}</span></td>
                </tr>
                <tr><td>свидетельство</td><td><code>{e.evidence}</code></td></tr>
              </tbody></table>
            </div>
          ))
        )}
      </div>

      {/* ---- level 4: identities and hashes, folded away by default ---- */}
      <button className="ov-tech-toggle" data-tech-toggle
        onClick={() => setTech((t) => !t)}>
        Технические детали {tech ? '▴' : '▾'}
      </button>
      {tech ? (
        <table className="kvt" data-tech-details><tbody>
          <tr><td>node_id</td><td><code>{n.node_id}</code></td></tr>
          <tr><td>реализация</td><td><code>{n.implementation}</code></td></tr>
          <tr><td>источник</td><td><code>{n.source_ref || '—'}</code></td></tr>
          <tr><td>слой топологии</td><td><code>{n.layer}</code></td></tr>
          <tr><td>статус топологии</td><td><code>{n.topology_status}</code></td></tr>
          <tr><td>asset_id</td><td><code>{n.asset_id || '—'}</code></td></tr>
          <tr><td>rag_profile_id</td><td><code>{n.rag_profile_id || '—'}</code></td></tr>
          <tr><td>контракт входа</td><td><code>{n.input_contract || '—'}</code></td></tr>
          <tr><td>контракт выхода</td><td><code>{n.output_contract || '—'}</code></td></tr>
          {n.declared_predecessors?.length ? (
            <tr><td>объявленные предшественники</td>
              <td><code>{n.declared_predecessors.join(', ')}</code></td></tr>) : null}
          {n.actual_callers?.length ? (
            <tr><td>реальные вызывающие</td>
              <td><code>{n.actual_callers.join(', ')}</code></td></tr>) : null}
          {n.note ? <tr><td>примечание</td><td>{n.note}</td></tr> : null}
        </tbody></table>
      ) : null}
    </div>
  );
}
