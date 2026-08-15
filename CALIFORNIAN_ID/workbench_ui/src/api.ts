const BASE = '/api/workbench';

async function call(path: string, init?: RequestInit) {
  const resp = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  const data = await resp.json().catch(() => ({ error: `HTTP ${resp.status}` }));
  if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
  return data;
}

const post = (path: string, body: any = {}) =>
  call(path, { method: 'POST', body: JSON.stringify(body) });

export const api = {
  graph: (branch: string, inputMode: string) =>
    call(`/pipeline/${branch}/graph?input_mode=${encodeURIComponent(inputMode)}`),
  node: (branch: string, nodeId: string, inputMode: string, runId?: string | null) =>
    call(`/node/${branch}/${nodeId}?input_mode=${encodeURIComponent(inputMode)}`
      + (runId ? `&run_id=${encodeURIComponent(runId)}` : '')),
  controls: (branch: string) => call(`/controls/${branch}`),
  asset: (assetId: string) => call(`/asset/${encodeURIComponent(assetId)}`),
  source: (assetId: string, variantId: string) =>
    call(`/asset/${encodeURIComponent(assetId)}/variant/${encodeURIComponent(variantId)}/source`),
  diff: (assetId: string, base: string, candidate: string) =>
    call(`/asset/${encodeURIComponent(assetId)}/diff?base=${encodeURIComponent(base)}&candidate=${encodeURIComponent(candidate)}`),
  clone: (assetId: string, variantId: string) =>
    post(`/asset/${encodeURIComponent(assetId)}/variant/${encodeURIComponent(variantId)}/clone`),
  saveSource: (assetId: string, variantId: string, source_text: string) =>
    post(`/asset/${encodeURIComponent(assetId)}/variant/${encodeURIComponent(variantId)}/source`, { source_text }),
  validate: (assetId: string, variantId: string) =>
    post(`/asset/${encodeURIComponent(assetId)}/variant/${encodeURIComponent(variantId)}/validate`),
  compile: (assetId: string, variantId: string) =>
    post(`/asset/${encodeURIComponent(assetId)}/variant/${encodeURIComponent(variantId)}/compile`),
  smoke: (assetId: string, variantId: string) =>
    post(`/asset/${encodeURIComponent(assetId)}/variant/${encodeURIComponent(variantId)}/smoke`),
  compare: (assetId: string, variantId: string) =>
    post(`/asset/${encodeURIComponent(assetId)}/variant/${encodeURIComponent(variantId)}/compare`),
  accept: (assetId: string, variantId: string) =>
    post(`/asset/${encodeURIComponent(assetId)}/variant/${encodeURIComponent(variantId)}/accept`),
  activate: (assetId: string, variantId: string) =>
    post(`/asset/${encodeURIComponent(assetId)}/variant/${encodeURIComponent(variantId)}/activate`),
  rollback: (assetId: string) =>
    post(`/asset/${encodeURIComponent(assetId)}/rollback`),
  run: (branch: string, assetId: string) =>
    post('/run', { branch, asset_id: assetId }),
  runs: () => call('/runs?limit=10'),

  // ---- Stage 2: RAG ----
  rag: (profileId: string) => call(`/rag/${encodeURIComponent(profileId)}`),
  ragCloneProfile: (profileId: string) => post(`/rag/${encodeURIComponent(profileId)}/clone`),
  ragUpdate: (profileId: string, changes: Record<string, any>) =>
    post(`/rag/${encodeURIComponent(profileId)}/update`, { changes }),
  ragValidate: (profileId: string) => post(`/rag/${encodeURIComponent(profileId)}/validate`),
  ragTest: (profileId: string, fixture_id?: string) =>
    post(`/rag/${encodeURIComponent(profileId)}/test`, { fixture_id }),
  ragCompare: (profileId: string, fixture_id?: string) =>
    post(`/rag/${encodeURIComponent(profileId)}/compare`, { fixture_id }),
  ragAccept: (profileId: string) => post(`/rag/${encodeURIComponent(profileId)}/accept`),
  ragActivate: (profileId: string) => post(`/rag/${encodeURIComponent(profileId)}/activate`),
  ragRollback: (engineId: string) =>
    post(`/rag_engine/${encodeURIComponent(engineId)}/rollback`),
  ragExplain: (profileId: string, runId: string, chunkId: string) =>
    call(`/rag/${encodeURIComponent(profileId)}/explain/${encodeURIComponent(runId)}/${encodeURIComponent(chunkId)}`),
  projection: (branch: string, kind: string, inputMode: string) =>
    call(`/projection/${branch}/${kind}?input_mode=${encodeURIComponent(inputMode)}`),
  retrievalEvents: (runId?: string) =>
    call(`/retrieval_events${runId ? `?run_id=${encodeURIComponent(runId)}` : ''}`),

  // ---- Stage 4A: branches with different runtime maturity ----
  branches: () => call('/branches'),
  branchState: (branch: string) => call(`/branch/${branch}/state`),
  branchInvariants: (branch: string) => call(`/branch/${branch}/invariants`),
  branchContracts: (branch: string) => call(`/branch/${branch}/contracts`),
  branchProfiles: (branch: string) => call(`/branch/${branch}/profiles`),
  branchReadiness: (branch: string) => call(`/branch/${branch}/readiness`),
  branchSnapshot: (branch: string) => call(`/branch/${branch}/snapshot`),
  branchPromptBody: (branch: string, binding: string) =>
    call(`/branch/${branch}/prompt_body/${encodeURIComponent(binding)}`),

  // ---- product surface: run / history / compare ----
  productionRun: (branch: string, text: string, mode: string) =>
    post('/production_run', { branch, text, mode }),
  runIndex: (limit = 30) => call(`/run_index?limit=${limit}`),
  compareRuns: (a: string, b: string) =>
    call(`/compare_runs/${encodeURIComponent(a)}/${encodeURIComponent(b)}`),
  fixtures: (branch: string) => call(`/fixtures/${branch}`),
  runTrace: (runId: string) => call(`/run/${encodeURIComponent(runId)}`),
};

export type Json = Record<string, any>;
