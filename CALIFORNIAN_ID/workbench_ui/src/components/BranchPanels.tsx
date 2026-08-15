import { useEffect, useState } from 'react';
import { api, type Json } from '../api';

/** Readiness is presentation, never a claim: a declarative branch says what it
 *  has and what it is waiting for, and offers no control it cannot honour. */
export function ReadinessBadge({ readiness }: { readiness?: Json | null }) {
  if (!readiness) return null;
  const level = String(readiness.level || 'UNKNOWN');
  const cls = level === 'LIVE_VALIDATED' ? 'ok'
    : level === 'NOT_READY' ? 'bad' : 'warn';
  return (
    <span className={`badge ${cls}`} data-readiness={level} title={readiness.evidence || ''}>
      {level}
      {readiness.expected_in ? ` · ждёт ${readiness.expected_in}` : ''}
    </span>
  );
}

/** A materialised prompt body: readable so the operator can explain it,
 *  with no editing affordance, because nothing executes it and we do not own it. */
export function PromptBody({ branch, binding }: { branch: string; binding: string }) {
  const [body, setBody] = useState<Json | null>(null);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    setBody(null);
    api.branchPromptBody(branch, binding).then(setBody).catch(() => setBody(null));
  }, [branch, binding]);
  const b = body?.prompt_body;
  if (!b?.text) return null;
  return (
    <div data-prompt-body={binding}>
      <div className="row">
        <button data-prompt-body-toggle onClick={() => setOpen((o) => !o)}>
          {open ? 'скрыть тело промпта' : 'показать тело промпта'}
        </button>
        <span className="badge warn" data-prompt-body-readonly>
          только чтение — {b.body_fidelity}
        </span>
      </div>
      <div className="dim" data-prompt-body-reason>{b.reason}</div>
      {open ? (
        <pre className="prompt-body" data-prompt-body-text>{b.text}</pre>
      ) : null}
      <div className="dim">{b.source_ref}</div>
    </div>
  );
}

export function BranchReadiness({ branch }: { branch: string }) {
  const [data, setData] = useState<Json | null>(null);
  useEffect(() => { api.branchReadiness(branch).then((d) => setData(d.readiness)).catch(() => setData(null)); }, [branch]);
  if (!data) return null;
  return (
    <section data-panel="branch-readiness">
      <h3>Готовность ветки</h3>
      <p className="dim">
        поколение <b>{data.generation}</b> · владелец <b>{data.owner}</b> ·
        {data.canonical_claim ? ' объявлена канонической' : ' каноничность не заявлена'}
      </p>
      <table className="kvt">
        <tbody>
          {Object.entries(data.matrix || {}).map(([k, v]) => (
            <tr key={k} data-readiness-row={k}>
              <td>{k}</td><td><code>{String(v)}</code></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="err-text" data-live-status>{data.live_runtime_status}</p>
    </section>
  );
}

export function BranchInvariants({ branch }: { branch: string }) {
  const [items, setItems] = useState<Json[]>([]);
  useEffect(() => { api.branchInvariants(branch).then((d) => setItems(d.invariants || [])).catch(() => setItems([])); }, [branch]);
  if (!items.length) return null;
  return (
    <section data-panel="branch-invariants">
      <h3>Инварианты ветки ({items.length})</h3>
      <ul className="inv-list">
        {items.map((i) => (
          <li key={i.invariant_id} data-invariant={i.invariant_id}>
            <b>{i.invariant_id}</b> — {i.text}
            <div className="dim">{i.source_ref}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function BranchContracts({ branch }: { branch: string }) {
  const [items, setItems] = useState<Json[]>([]);
  useEffect(() => { api.branchContracts(branch).then((d) => setItems(d.contracts || [])).catch(() => setItems([])); }, [branch]);
  if (!items.length) return null;
  return (
    <section data-panel="branch-contracts">
      <h3>Контракты ({items.length})</h3>
      <table className="kvt">
        <tbody>
          {items.map((c, idx) => (
            <tr key={`${c.contract_id}:${idx}`} data-contract={c.contract_id}>
              <td>{c.contract_id}</td>
              <td>
                <code>{(c.used_by || []).join(', ') || '—'}</code>{' '}
                <span className={c.in_owner_manifest === false ? 'badge bad' : 'badge'}>
                  {c.readiness}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function BranchProfiles({ branch }: { branch: string }) {
  const [items, setItems] = useState<Json[]>([]);
  useEffect(() => { api.branchProfiles(branch).then((d) => setItems(d.profiles || [])).catch(() => setItems([])); }, [branch]);
  if (!items.length) return null;
  return (
    <section data-panel="branch-profiles">
      <h3>Runtime-профили ({items.length})</h3>
      {items.map((p) => (
        <div key={p.profile_id} className="profile-row" data-profile={p.profile_id}>
          <div>
            <b>{p.profile_id}</b>{p.is_default ? ' · default' : ''}
            <div className="dim">{p.note}</div>
          </div>
          <div>
            {(p.available_actions || []).map((a: string) => (
              <button key={a} data-profile-action={a}>{a}</button>
            ))}
            <button
              data-profile-activate={p.profile_id}
              disabled={!p.activate_in_live_runtime?.enabled}
              title={p.activate_in_live_runtime?.status || ''}
            >
              activate
            </button>
          </div>
        </div>
      ))}
      <p className="dim" data-activation-status>
        {items[0]?.activate_in_live_runtime?.status}
      </p>
    </section>
  );
}

/** The state machine is its own projection — dispatcher states are not steps. */
export function StateView({ branch }: { branch: string }) {
  const [sp, setSp] = useState<Json | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  useEffect(() => { api.branchState(branch).then((d) => setSp(d.state)).catch(() => setSp(null)); }, [branch]);
  if (!sp) return <div style={{ padding: 20, color: 'var(--text-dim)' }}>нет модели состояний</div>;

  const groups: [string, string][] = [
    ['active', 'рабочие'], ['dispatcher', 'диспетчерские'], ['terminal', 'терминальные'],
  ];
  const outgoing = (sp.transitions || []).filter((t: Json) => t.source === sel);

  return (
    <div className="state-view" data-view="state">
      <div className="state-cols">
        {groups.map(([kind, label]) => (
          <div key={kind} className="state-col" data-state-kind={kind}>
            <h4>{label}</h4>
            {(sp.states || []).filter((s: Json) => s.kind === kind).map((s: Json) => (
              <button
                key={s.state_id}
                className={`state-chip${sel === s.state_id ? ' sel' : ''}`}
                data-state={s.state_id}
                onClick={() => setSel(s.state_id)}
              >
                {s.state_id}
              </button>
            ))}
          </div>
        ))}
      </div>
      <div className="state-detail">
        <h4>переходы {sel ? `из ${sel}` : ''} ({sel ? outgoing.length : sp.transitions?.length || 0})</h4>
        {sel ? (
          <ul>
            {outgoing.map((t: Json, i: number) => (
              <li key={i} data-transition={`${t.source}->${t.target}`}>
                → <b>{t.target}</b> {t.guarded ? <span className="badge warn">guard</span> : null}
                <div className="dim">{t.when}</div>
              </li>
            ))}
          </ul>
        ) : <p className="dim">выберите состояние</p>}
        <h4>бюджет повторов</h4>
        <table className="kvt"><tbody>
          {Object.entries(sp.retry_budget || {}).map(([k, v]) => (
            <tr key={k} data-retry={k}><td>{k}</td><td><code>{String(v)}</code></td></tr>
          ))}
        </tbody></table>
        <h4>запрещённые переходы ({(sp.forbidden_transitions || []).length})</h4>
        <ul className="inv-list">
          {(sp.forbidden_transitions || []).map((f: string, i: number) => (
            <li key={i} data-forbidden={i}>{f}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
