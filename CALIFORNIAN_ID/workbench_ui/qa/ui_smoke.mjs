/**
 * C5 — headless UI acceptance.
 *
 * Selector-based only: no coordinate clicks. Produces screenshots plus a
 * machine-readable report so visual QA can be judged independently of whether
 * the interactive Browser pane composites frames.
 *
 *   node qa/ui_smoke.mjs [baseUrl]
 */
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const BASE = process.argv[2] || 'http://127.0.0.1:8790';
const OUT = join(process.cwd(), 'qa', 'screenshots');
mkdirSync(OUT, { recursive: true });

const steps = [];
const shot = async (page, name, note) => {
  const file = join(OUT, `${String(steps.length + 1).padStart(2, '0')}_${name}.png`);
  await page.screenshot({ path: file, fullPage: false });
  steps.push({ step: name, note, screenshot: file, ok: true });
  console.log(`  ✓ ${name} -> ${file}`);
};
const fail = (name, err) => {
  steps.push({ step: name, ok: false, error: String(err) });
  console.log(`  ✗ ${name}: ${err}`);
};

const run = async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
  const consoleErrors = [];
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  const netFailures = [];
  page.on('response', (r) => { if (r.status() >= 400) netFailures.push(`${r.status()} ${r.url()}`); });

  try {
    // 1. pipeline graph
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await page.waitForSelector('[data-node-id="analyze_situation"]');
    await shot(page, 'pipeline_graph', 'граф пайплайна с типами узлов и бейджем дрейфа');

    // 2. prompt node inspector
    await page.click('[data-node-id="analyze_situation"]');
    await page.waitForSelector('.dock-body');
    await page.waitForFunction(() =>
      document.querySelector('.dock-body')?.innerText.includes('17/9/7'));
    await shot(page, 'inspector_prompt_node', 'MODEL_CALL, контракт 17/9/7, редактор доступен');

    // 3. SOURCE + clone + edit
    await page.click('.right-dock__tab:has-text("SOURCE")');
    await page.click('button[data-step="clone"]');
    await page.waitForSelector('.cm-content');
    await page.waitForFunction(() =>
      !document.querySelector('.cm-editor')?.classList.contains('cm-readonly'));
    await shot(page, 'source_editor', 'CodeMirror с подсветкой protected/editable областей');

    // Edit strictly inside the editable region. Appending at end-of-document
    // would land in the protected `prohibitions` region and the server would
    // (correctly) refuse it — that path is covered by the C2 negative tests.
    // CodeMirror virtualises lines, so navigate via the region button (which
    // scrolls the region into view and places the cursor) rather than by text.
    await page.click('button:has-text("signal_definitions")');
    await page.waitForTimeout(300);
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('End');
    await page.keyboard.type(' Уточнено для говорящего.');
    await page.click('button[data-step="edit"]');
    await page.waitForTimeout(900);
    await page.click('button[data-step="diff"]');
    await page.waitForFunction(() =>
      !!document.querySelector('pre.diff'), null, { timeout: 15000 });
    await shot(page, 'diff', 'unified diff кандидата против baseline');

    // 4. validate + compile + provenance
    await page.click('button[data-step="validate"]');
    await page.waitForFunction(() =>
      /KNOWN_BASELINE_DRIFT|NEW_CANDIDATE_DRIFT|NONE/.test(
        document.querySelector('.dock-body')?.innerText || ''));
    await shot(page, 'validation', 'вердикт + класс дрейфа');

    await page.click('button[data-step="compile"]');
    await page.waitForFunction(() =>
      document.querySelector('.dock-body')?.innerText.includes('provenance 100%'));
    await shot(page, 'compiled_provenance', 'COMPILED + карта провенанса 100%');

    // 5. deterministic node — no prompt editor
    await page.click('[data-node-id="assess_turn"]');
    await page.waitForFunction(() =>
      document.querySelector('.dock-body')?.innerText.includes('DETERMINISTIC'));
    const hasEditorBtn = await page.$('button[data-step="clone"]');
    steps.push({ step: 'deterministic_has_no_editor', ok: hasEditorBtn === null,
                 note: 'кнопка клонирования отсутствует в DOM' });
    await shot(page, 'inspector_deterministic', 'DETERMINISTIC без редактора промпта');

    // 6. hybrid effects (V054)
    await page.click('.right-dock__tab:has-text("Эффекты")');
    await page.waitForFunction(() =>
      document.querySelector('.dock-body')?.innerText.includes('DETERMINISTIC_ALGORITHM'));
    await shot(page, 'effects_v054', 'один контрол — оба класса эффектов');

    // 7. RAG inspector
    await page.click('[data-node-id="cultural_context"]');
    await page.click('.right-dock__tab:has-text("RAG")');
    // NB: h3 headings are uppercased by CSS text-transform and innerText
    // returns the transformed text, so every text assertion is case-folded.
    await page.waitForFunction(() =>
      (document.querySelector('.dock-body')?.innerText || '')
        .toLowerCase().includes('эффективные параметры'));
    await shot(page, 'rag_inspector', 'RAG-профиль, эффективные параметры, NOT_IMPLEMENTED');

    // 8. retrieval test + why this chunk
    await page.click('button[data-rag="test"]');
    await page.waitForFunction(() =>
      document.querySelector('.dock-body')?.innerText.includes('RETRIEVAL FACTS'));
    await shot(page, 'rag_retrieval_facts', 'ранжированные чанки с score/locator/hash');

    const why = await page.$('button[data-rag="explain"]');
    if (why) {
      await why.click();
      await page.waitForFunction(() =>
        document.querySelector('.dock-body')?.innerText.includes('LLM INTERPRETATION'));
      await shot(page, 'rag_why_this_chunk', 'факты и интерпретация разделены');
    }

    // 9. clone profile, change top_k, compare
    await page.click('button[data-rag="clone"]');
    await page.waitForTimeout(500);
    const topk = await page.$('input[type="number"]');
    if (topk) { await topk.fill('5'); }
    await page.click('button[data-rag="apply"]');
    await page.waitForTimeout(400);
    await page.click('button[data-rag="validate"]');
    await page.waitForTimeout(400);
    await page.click('button[data-rag="compare"]');
    await page.waitForFunction(() =>
      (document.querySelector('.dock-body')?.innerText || '')
        .toLowerCase().includes('baseline ↔ candidate'), null, { timeout: 20000 });
    await shot(page, 'rag_comparison', 'baseline vs candidate: overlap, entered, Δ context');

    // 10. telemetry overlay
    await page.click('[data-node-id="analyze_situation"]');
    await page.click('.right-dock__tab:has-text("Runs")');
    const runBtn = await page.$('.dock-body button.primary');
    if (runBtn) {
      await runBtn.click();
      await page.waitForFunction(() =>
        document.querySelector('.dock-body')?.innerText.includes('activation_revision'));
      await shot(page, 'run_trace', 'RunTrace: variant/source/compiled/snapshot');
    }
    await page.click('header button:has-text("обновить")');
    await page.waitForTimeout(1200);
    await shot(page, 'telemetry_overlay', 'measured/estimated метрики на узлах графа');
  } catch (err) {
    fail('run', err);
  }

  const report = {
    base: BASE, at: new Date().toISOString(),
    steps, console_errors: consoleErrors, http_failures: netFailures,
    passed: steps.filter((s) => s.ok).length, total: steps.length,
  };
  writeFileSync(join(OUT, 'report.json'), JSON.stringify(report, null, 2));
  console.log(`\n${report.passed}/${report.total} steps ok; ` +
              `${consoleErrors.length} console errors; ${netFailures.length} http>=400`);
  await browser.close();
  process.exit(steps.every((s) => s.ok) ? 0 : 1);
};

run();
