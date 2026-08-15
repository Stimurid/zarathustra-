import { useState } from 'react';
import { api, type Json } from '../api';

const ASK = [
  { id: 'explain', label: 'Объясни промпт' },
  { id: 'explain_selection', label: 'Что делает выделение?', needsSel: true },
  { id: 'find_problem', label: 'Найди проблему' },
  { id: 'propose_change', label: 'Предложи изменение' },
];
const REWRITE = [
  { id: 'rewrite_stricter', label: 'жёстче' },
  { id: 'rewrite_softer', label: 'мягче' },
  { id: 'rewrite_sharper', label: 'точнее' },
];

/**
 * The prompt companion.
 *
 * Two rules it does not bend: it never edits the prompt itself — the operator
 * inserts what they choose — and when no model is configured it says so rather
 * than composing a plausible-looking answer locally.
 */
export function PromptCopilot({
  branch, sourceText, selection, readOnly, onInsertAll, onInsertSelection,
}: {
  branch: string;
  sourceText: string;
  selection: string;
  readOnly: boolean;
  onInsertAll: (text: string) => void;
  onInsertSelection: (text: string) => void;
}) {
  const [busy, setBusy] = useState('');
  const [res, setRes] = useState<Json | null>(null);
  const [draft, setDraft] = useState('');
  const [err, setErr] = useState('');

  const ask = async (action: string) => {
    setBusy(action); setErr(''); setRes(null);
    try {
      const r = await api.copilot(branch, action, sourceText, selection);
      setRes(r.copilot);
      if (r.copilot?.available && r.copilot.kind === 'proposal')
        setDraft(r.copilot.text);
    } catch (e: any) {
      setErr(String(e.message || e));
    } finally { setBusy(''); }
  };

  return (
    <div className="copilot" data-panel="copilot">
      <h3>Помощник</h3>
      <div className="row" data-copilot-ask>
        {ASK.map((a) => (
          <button key={a.id} data-copilot={a.id}
            disabled={!!busy || (a.needsSel && !selection.trim())}
            title={a.needsSel && !selection.trim()
              ? 'выделите фрагмент в тексте промпта' : ''}
            onClick={() => ask(a.id)}>
            {busy === a.id ? '…' : a.label}
          </button>
        ))}
      </div>
      <div className="row" data-copilot-rewrite>
        <span className="dim">переписать выделение:</span>
        {REWRITE.map((a) => (
          <button key={a.id} data-copilot={a.id}
            disabled={!!busy || !selection.trim()}
            onClick={() => ask(a.id)}>{busy === a.id ? '…' : a.label}</button>
        ))}
      </div>

      {err ? <div className="card err-text" data-copilot-error>{err}</div> : null}

      {res && !res.available ? (
        <p className="ov-empty" data-copilot-unavailable>
          {res.reason}. Ответ не показан — вместо него ничего, а не выдумка.
        </p>
      ) : null}

      {res?.available ? (
        <div data-copilot-result={res.kind}>
          <div className="row">
            <span className="badge warn" data-copilot-grade>
              {res.kind === 'proposal' ? 'предложение модели' : 'объяснение модели'}
              {' · '}{res.evidence_grade}
            </span>
            <span className="dim">{res.provider}{res.model ? ` · ${res.model}` : ''}</span>
          </div>
          {res.provider === 'mock' ? (
            <p className="ov-warn" data-copilot-mock>
              Отвечает mock-провайдер: это не объяснение модели, а заглушка
              рантайма. Настройте провайдера, чтобы получать настоящие ответы.
            </p>
          ) : null}
          <pre className="block" data-copilot-text>{res.text}</pre>
          <p className="dim">
            Ничего не применено автоматически — вставьте то, что считаете нужным.
          </p>
        </div>
      ) : null}

      <div className="ov-field__label">Черновик для вставки</div>
      <textarea className="draft" value={draft} spellCheck={false}
        data-copilot-draft
        placeholder="Сюда попадают предложения модели; можно править перед вставкой."
        onChange={(e) => setDraft(e.target.value)} />
      <div className="row">
        <button data-action="insert-all" disabled={readOnly || !draft}
          onClick={() => onInsertAll(draft)}>Вставить всё</button>
        <button data-action="insert-selection" disabled={readOnly || !draft}
          onClick={() => onInsertSelection(draft)}>Вставить в выделение</button>
        <button onClick={() => navigator.clipboard?.writeText(draft)}>копировать</button>
      </div>
    </div>
  );
}
