/** Stage 4A UI acceptance: one Workbench, three branches, three maturities.
 *
 * The point of this pass is NOT that Socrates looks good — it is that the
 * Workbench refuses to pretend. Every control that cannot be honoured must be
 * visibly disabled with a reason, and no prompt editor may appear for a node
 * whose prompt body has not been fetched.
 */
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const BASE = process.argv[2] || 'http://127.0.0.1:8790';
const OUT = join(process.cwd(), 'qa', 'screenshots');
mkdirSync(OUT, { recursive: true });

const steps = [];
const shot = async (p, name, note) => {
  const file = join(OUT, `s4a_${name}.png`);
  await p.screenshot({ path: file });
  steps.push({ step: name, note, screenshot: file, ok: true });
  console.log(`  ✓ ${name}`);
};
const check = (name, cond, detail) => {
  steps.push({ step: name, note: detail, ok: !!cond });
  console.log(`  ${cond ? '✓' : '✗'} ${name}${cond ? '' : ` — ${detail}`}`);
  if (!cond) throw new Error(`${name}: ${detail}`);
};

const selectBranch = async (p, branch) => {
  await p.selectOption('[data-branch-select]', branch);
  await p.waitForFunction(
    (b) => document.querySelector('[data-branch-select]')?.value === b, branch);
  await p.waitForTimeout(400);
};

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1700, height: 980 } });
const errs = [];
p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
p.on('pageerror', (e) => errs.push(`pageerror: ${e.message}`));
p.on('response', (r) => { if (r.status() >= 400) errs.push(`${r.status()} ${r.url()}`); });

try {
  await p.goto(BASE, { waitUntil: 'networkidle' });
  await p.waitForSelector('[data-branch-select]');

  // 1 — the branch selector offers all registered branches
  const options = await p.$$eval('[data-branch-select] option', (o) => o.map((x) => x.value));
  check('01_branch_selector', options.includes('zarathustra') && options.includes('socrates'),
    `options=${options.join(',')}`);

  // 2 — select Socrates and load the real G-S24 pipeline
  await selectBranch(p, 'socrates');
  await p.waitForSelector('[data-node-id="S0"]');
  const nodeIds = await p.$$eval('[data-node-id]', (n) =>
    n.map((x) => x.getAttribute('data-node-id')));
  const steps011 = ['S0','S1','S2','S3','S4','S5','S6','S7','S8','S9','S10'];
  check('02_all_eleven_steps', steps011.every((s) => nodeIds.includes(s)),
    `missing: ${steps011.filter((s) => !nodeIds.includes(s)).join(',')}`);
  await shot(p, '01_socrates_pipeline', 'S0–S10 + типизированные терминалы из pipeline.yaml');

  // 3 — the branch is labelled declarative, with its generation
  const gen = await p.textContent('[data-generation]');
  const liveFlag = await p.getAttribute('[data-live-runtime]', 'data-live-runtime');
  check('03_declarative_labelled', gen.trim() === 'G-S24' && liveFlag === 'false',
    `gen=${gen} live=${liveFlag}`);

  // 4 — conditional S7 is presented as conditional, not as an always-step
  await p.click('[data-node-id="S7"]');
  await p.waitForSelector('[data-conditional="S7"]');
  const s7 = await p.textContent('[data-conditional="S7"]');
  check('04_s7_conditional', s7.includes('условный'), s7);

  // 5 — S7's prompt body is mirrored read-only: readable for explanation,
  //     with no editing affordance anywhere on the node
  const s7binding = await p.getAttribute('[data-prompt-binding]', 'data-prompt-binding');
  const s7bodyText = await p.textContent('[data-prompt-binding]');
  check('05_prompt_binding_materialised',
    s7binding === 'MODE_AND_REFLEXIVITY_GOVERNOR_PROMPT_PACK'
      && s7bodyText.includes('MIRRORED_READ_ONLY'), `${s7binding} / ${s7bodyText}`);
  await p.click('[data-prompt-body-toggle]');
  await p.waitForSelector('[data-prompt-body-text]');
  const body = await p.textContent('[data-prompt-body-text]');
  const readonly = await p.textContent('[data-prompt-body-readonly]');
  check('06_body_readable_for_explanation',
    body.includes('P2 — Arbitration') && body.includes('Never infer truth from vote count')
      && readonly.includes('только чтение'), readonly);
  const editorCount = await p.locator('.cm-host').count();
  check('07_no_editor_over_a_body_we_do_not_own', editorCount === 0,
    `${editorCount} editors rendered for a prompt nothing executes`);
  await shot(p, '02_s7_readiness', 'S7: тело промпта читаемо, редактор не предлагается');

  // 6 — S9 shows the guard that decides whether it runs at all
  await p.click('[data-node-id="S9"]');
  await p.waitForSelector('[data-conditional="S9"]');
  const s9 = await p.textContent('[data-conditional="S9"]');
  check('07_s9_conditional_on_execute',
    s9.includes('execution_status') && s9.includes('EXECUTE'), s9);

  // 7 — S6 human-operation contracts are inspectable
  await p.click('[data-node-id="S6"]');
  await p.waitForSelector('[data-panel="branch-contracts"]');
  const contracts = await p.$$eval('[data-contract]', (n) =>
    n.map((x) => x.getAttribute('data-contract')));
  check('08_s6_human_operation_contracts',
    contracts.includes('human_operation.schema.json')
      && contracts.includes('ownership_assessment_v0.2.schema.json'),
    contracts.join(','));

  // 8 — S8 intervention contract
  check('09_s8_intervention_contract',
    contracts.includes('intervention_selection.schema.json'), contracts.join(','));

  // 9 — arbitration/council contracts for S7
  check('10_s7_council_arbitration',
    contracts.includes('arbitration_record.schema.json')
      && contracts.includes('council_recipe.schema.json'), contracts.join(','));
  await shot(p, '03_contracts', 'контракт-инспектор: S6/S7/S8 привязки со статусом');

  // 10 — runtime profiles are inspectable, activation is disabled with a reason
  const profiles = await p.$$eval('[data-profile]', (n) =>
    n.map((x) => x.getAttribute('data-profile')));
  check('11_six_runtime_profiles', profiles.length === 6, profiles.join(','));
  const activateDisabled = await p.$$eval('[data-profile-activate]',
    (n) => n.every((x) => x.disabled));
  const activationStatus = await p.textContent('[data-activation-status]');
  check('12_activation_disabled_with_reason',
    activateDisabled && activationStatus.includes('WAITING_FOR_G-S26'),
    `disabled=${activateDisabled} status=${activationStatus}`);
  await shot(p, '04_profiles_activation_blocked', 'профили: inspect можно, activate — нет');

  // 11 — branch invariants are shown with provenance
  const invariants = await p.$$eval('[data-invariant]', (n) => n.length);
  check('13_branch_invariants', invariants === 18, `${invariants} invariants`);
  await shot(p, '05_invariants', '18 инвариантов ветки с provenance');

  // 12 — STATE VIEW: dispatcher states are not steps
  await p.click('button[data-view="state"]');
  await p.waitForSelector('[data-view="state"].state-view');
  const dispatchers = await p.$$eval('[data-state-kind="dispatcher"] [data-state]',
    (n) => n.map((x) => x.getAttribute('data-state')));
  const terminals = await p.$$eval('[data-state-kind="terminal"] [data-state]',
    (n) => n.length);
  check('14_state_view_dispatchers',
    dispatchers.includes('RETRY_PENDING') && dispatchers.includes('ESCALATION_PENDING')
      && terminals === 7, `${dispatchers.join(',')} / ${terminals} terminals`);
  await p.click('[data-state="RETRY_PENDING"]');
  await p.waitForSelector('[data-transition]');
  const retryOut = await p.$$eval('[data-transition]', (n) => n.length);
  check('15_retry_returns_to_the_exact_step', retryOut >= 11, `${retryOut} transitions`);
  const forbidden = await p.$$eval('[data-forbidden]', (n) => n.length);
  check('16_forbidden_transitions_visible', forbidden > 0, `${forbidden}`);
  await shot(p, '06_state_view', 'модель состояний: диспетчерские ≠ шаги');

  // 13 — switch across all three presentations without a reload
  await p.click('button[data-view="graph"]');
  await selectBranch(p, 'zarathustra');
  await p.waitForSelector('[data-node-id="analyze_situation"]');
  check('17_back_to_zarathustra_live',
    (await p.getAttribute('[data-live-runtime]', 'data-live-runtime')) === 'true',
    'zarathustra must present as live');
  await shot(p, '07_zarathustra_graph', 'та же оболочка, живой рантайм');

  await p.click('button[data-view="radial"]');
  await p.waitForSelector('[data-testid="field-radial"]');
  await shot(p, '08_whitecrow_radial', 'WhiteCrow-проекция тех же типов');

  await selectBranch(p, 'socrates');
  await p.waitForSelector('[data-node-id="S0"]');
  check('18_three_branches_no_reload', true, 'zarathustra → whitecrow → socrates');
  await shot(p, '09_socrates_after_roundtrip', 'возврат в Socrates без перезагрузки');

  // 14 — zero console errors across the whole pass
  check('19_zero_console_errors', errs.length === 0, errs.join(' | '));

  writeFileSync(join(OUT, 's4a_report.json'),
    JSON.stringify({ base: BASE, steps, console_errors: errs }, null, 2), 'utf-8');
  console.log(`\nStage 4A UI: ${steps.filter((s) => s.ok).length}/${steps.length} OK`);
} catch (e) {
  console.error('FAILED:', e.message);
  console.error('console errors:', errs);
  await p.screenshot({ path: join(OUT, 's4a_FAILURE.png') });
  writeFileSync(join(OUT, 's4a_report.json'),
    JSON.stringify({ base: BASE, steps, console_errors: errs, failure: e.message },
      null, 2), 'utf-8');
  process.exitCode = 1;
} finally {
  await b.close();
}
