/**
 * Product acceptance for the live-Zarathustra Workbench: P1–P8.
 *
 * These are not selector-existence checks. Each scenario asserts the product
 * claim behind it — most importantly that a pipeline with no run is useful and
 * that an absent measurement is never rendered as a zero.
 */
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const BASE = process.argv[2] || 'http://127.0.0.1:8790';
const OUT = join(process.cwd(), 'qa', 'screenshots');
mkdirSync(OUT, { recursive: true });

const steps = [];
let failed = 0;
const check = (name, cond, detail = '') => {
  steps.push({ step: name, ok: !!cond, detail });
  console.log(`  ${cond ? '✓' : '✗'} ${name}${cond ? '' : ` — ${detail}`}`);
  if (!cond) { failed += 1; throw new Error(`${name}: ${detail}`); }
};
const shot = async (p, file, note) => {
  await p.screenshot({ path: join(OUT, file) });
  steps.push({ step: file, ok: true, detail: note });
  console.log(`  ▣ ${file}`);
};

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
const errs = [];
p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
p.on('pageerror', (e) => errs.push(`pageerror: ${e.message}`));
p.on('response', (r) => { if (r.status() >= 400) errs.push(`${r.status()} ${r.url()}`); });

try {
  // ================= P1 — explore without a run =================
  console.log('\nP1 — изучение пайплайна без запуска');
  await p.goto(BASE, { waitUntil: 'networkidle' });
  await p.waitForSelector('[data-mainnav]');

  check('P1.1 стартовый экран — пайплайн',
    await p.$eval('[data-section="pipeline"]', (e) => e.className.includes('sel')),
    'pipeline must be the landing section');

  check('P1.2 режим — определение',
    (await p.textContent('[data-mode="definition"]')) === 'ОПРЕДЕЛЕНИЕ');

  const nodeIds = await p.$$eval('[data-node-id]', (n) =>
    n.map((x) => x.getAttribute('data-node-id')));
  const spine = ['intake', 'analyze_situation', 'select_initial_voice', 'route_next',
    'evidence_retrieval', 'cultural_context', 'persona_turn', 'assess_turn',
    'checkpoint', 'synthesize', 'validate_output', 'persist_trace'];
  check('P1.3 фактический рантайм-порядок целиком',
    spine.every((s) => nodeIds.includes(s)),
    `missing: ${spine.filter((s) => !nodeIds.includes(s))}`);

  check('P1.4 цикл совета виден как цикл',
    !!(await p.$('[data-band="council_loop"]')), 'no loop band rendered');

  check('P1.5 входной текст не требуется',
    !(await p.$('[data-run-input]')), 'run input must not block exploration');

  // no zeros anywhere on a never-run pipeline
  const canvasText = await p.$eval('.canvas', (e) => e.innerText);
  check('P1.6 ноль не выдаётся за измерение',
    !/\b0\s*(ms|мс|tokens|токен|chunks|фрагм)/i.test(canvasText),
    canvasText.slice(0, 200));
  await shot(p, '01_pipeline_definition.png', 'пайплайн без прогона — полезен сам по себе');

  await p.click('[data-node-id="analyze_situation"]');
  await p.waitForSelector('[data-panel="node-overview"]');
  // textContent returns the source case; the uppercase look is CSS
  // text-transform, so assertions must fold case (defect WB-011).
  const ov = (await p.textContent('[data-panel="node-overview"]')).toLowerCase();
  check('P1.7 узел объяснён по-человечески',
    ov.includes('назначение') && ov.includes('первичное чтение ситуации')
      && ov.includes('когда выполняется') && ov.includes('куда идёт результат'),
    ov.slice(0, 160));
  check('P1.8 видно, чем узел управляется',
    (await p.textContent('[data-controlled-by]')).includes('Чтение сцены'));
  check('P1.9 рантайм честно пуст',
    (await p.textContent('[data-runtime-empty]')).includes('Запуск не выбран'));
  check('P1.10 идентификаторы убраны под раскрытие',
    !(await p.$('[data-tech-details]')) && !!(await p.$('[data-tech-toggle]')));
  await shot(p, '02_node_overview.png', 'human-first обзор узла');

  // ================= P2 — different node kinds =================
  console.log('\nP2 — разные типы узлов показывают только релевантное');
  const tabsOf = async () =>
    (await p.$$eval('.right-dock__tab', (n) => n.map((x) => x.textContent.trim())))
      .join('|');
  // The inspector clears while a node loads; waiting on the title avoids
  // reading the previous node's tab set.
  const openNode = async (id, title) => {
    await p.click(`[data-node-id="${id}"]`);
    await p.waitForFunction(
      (t) => document.querySelector('[data-node-title]')?.textContent?.includes(t),
      title, { timeout: 15000 });
  };

  const promptTabs = await tabsOf();
  check('P2.1 промпт-узел: есть Промпт, нет Извлечения',
    /Промпт/.test(promptTabs) && !/Извлечение/.test(promptTabs), promptTabs);

  await openNode('cultural_context', 'Культурный контекст');
  const ragTabs = await tabsOf();
  check('P2.2 RAG-узел: есть Извлечение, нет Промпта',
    /Извлечение/.test(ragTabs) && !/Промпт/.test(ragTabs), ragTabs);

  await openNode('assess_turn', 'Оценка хода');
  const detTabs = await tabsOf();
  check('P2.3 детерминированный узел: ни промпта, ни извлечения',
    !/Промпт/.test(detTabs) && !/Извлечение/.test(detTabs), detTabs);

  await openNode('select_initial_voice', 'Первичный кастинг');
  check('P2.4 гибрид назван гибридом',
    (await p.getAttribute('[data-node-kind]', 'data-node-kind')) === 'HYBRID');

  await openNode('retrieve_initial_context', 'Извлечение контекста');
  await p.waitForSelector('[data-layer-note]');
  check('P2.5 мёртвое объявление названо объявлением',
    (await p.textContent('[data-layer-note]')).includes('не исполняет'));

  // ================= P3 — run =================
  console.log('\nP3 — запуск');
  await p.click('[data-run-cta]');
  await p.waitForSelector('[data-panel="run"]');
  await p.click('[data-fixture]');
  const typed = await p.inputValue('[data-run-input]');
  check('P3.1 готовый вход подставляется', typed.length > 40, `${typed.length} chars`);
  await p.click('[data-run-start]');
  await p.waitForSelector('[data-run-result]', { timeout: 180000 });
  const status = await p.textContent('[data-run-status]');
  check('P3.2 реальный прогон завершился', status.toUpperCase().includes('COMPLETED'), status);
  check('P3.3 пайплайн остался на экране во время запуска',
    !!(await p.$('[data-node-id="persona_turn"]')));
  check('P3.4 режим переключился на запуск',
    (await p.textContent('[data-mode="run"]')) === 'ЗАПУСК');
  await shot(p, '05_run_active_or_completed.png', 'прогон выполнен через настоящий Pipeline.run');

  // ================= P4 — inspect a run =================
  console.log('\nP4 — разбор прогона');
  const executed = await p.$$eval('[data-executed="true"]', (n) => n.length);
  check('P4.1 выполненные узлы отмечены', executed >= 4, `${executed}`);
  const notExecuted = await p.$$eval('[data-executed="false"]', (n) => n.length);
  check('P4.2 невыполненные отличимы', notExecuted >= 1, `${notExecuted}`);

  await p.click('[data-section="pipeline"]');
  await openNode('persona_turn', 'Ход персоны');
  await p.waitForSelector('[data-execution]');
  const runSec = await p.textContent('[data-runtime-section]');
  check('P4.3 определение и свидетельство разделены',
    runSec.includes('Этот запуск')
      && (await p.textContent('[data-panel="node-overview"]')).toLowerCase()
         .includes('назначение'));
  check('P4.4 неизмеренное названо неизмеренным, а не нулём',
    (await p.$$eval('[data-not-measured]', (n) => n.length)) >= 1);
  await shot(p, '06_run_overlay.png', 'узел в контексте конкретного прогона');

  await openNode('cultural_context', 'Культурный контекст');
  await p.click('.right-dock__tab:has-text("Извлечение")');
  await p.waitForSelector('[data-rag-observed], [data-rag-not-observed]');
  check('P4.5 извлечение показывает факт прогона',
    !!(await p.$('[data-rag-observed]')) || !!(await p.$('[data-rag-not-observed]')));
  await shot(p, '04_rag_inspector.png', 'извлечение: конфигурация + факт прогона');

  // metrics overlay only on demand, only when measured
  // off -> nothing on the canvas; on -> only measured values
  await p.setChecked('[data-metrics-toggle]', false);
  await p.waitForTimeout(300);
  check('P4.6 метрики выключены — на схеме их нет',
    (await p.$$eval('.tele-item', (n) => n.length)) === 0);
  await p.setChecked('[data-metrics-toggle]', true);
  await p.waitForTimeout(400);
  const tele = await p.$$eval('.tele-item', (n) => n.map((x) => x.textContent.trim()));
  check('P4.7 метрики включены — только измеренное, без выдуманных нулей',
    tele.length > 0 && !tele.some((t) => /(^|\s)0\s*(ms|мс|фр|токен)/i.test(t)),
    tele.join(' | '));

  // ================= P5 — prompt change =================
  console.log('\nP5 — правка промпта');
  await openNode('analyze_situation', 'Чтение сцены');
  await p.click('[data-goto="prompt"]');
  await p.waitForSelector('[data-prompt-head]');
  check('P5.1 стартовое состояние — активный вариант, а не пустота',
    !!(await p.textContent('[data-active-variant]')));
  await p.click('[data-prompt-edit-copy]');
  await p.waitForSelector('[data-prompt-check]');
  check('P5.2 после клонирования — редакторские действия',
    !!(await p.$('[data-prompt-test]')) && !!(await p.$('[data-prompt-activate]')));
  await shot(p, '03_prompt_editor.png', 'редакторский цикл вместо CI-лестницы');

  await p.click('[data-prompt-check]');
  await p.waitForSelector('[data-prompt-verdict]');
  check('P5.3 проверка даёт вердикт',
    (await p.textContent('[data-prompt-verdict]')).includes('проверка'));
  check('P5.4 полный жизненный цикл доступен, но убран',
    !!(await p.$('[data-lifecycle-toggle]')) && !(await p.$('[data-lifecycle]')));

  // ================= P6 — retrieval change =================
  console.log('\nP6 — правка извлечения');
  await p.click('[data-section="rag"]');
  await p.waitForSelector('[data-panel="rag-catalogue"]');
  const ragRows = await p.$$eval('[data-rag-row]', (n) => n.length);
  check('P6.1 профили извлечения перечислены по-человечески', ragRows >= 2, `${ragRows}`);
  await p.click('[data-rag-row] >> nth=0');
  await p.waitForSelector('[data-rag-runtime]');
  check('P6.2 конфигурация видна вместе с фактом прогона',
    !!(await p.$('[data-rag-runtime]')));

  // ================= P7 — compare runs =================
  console.log('\nP7 — сравнение прогонов');
  await p.click('[data-section="run"]');
  await p.waitForSelector('[data-panel="run"]');
  await p.click('[data-fixture] >> nth=0');
  await p.click('[data-run-start]');
  await p.waitForSelector('[data-run-result]', { timeout: 180000 });

  await p.click('[data-section="runs"]');
  await p.waitForSelector('[data-panel="runs"]');
  await p.waitForSelector('[data-run-row], [data-runs-empty]');
  const rows = await p.$$eval('[data-run-row]', (n) => n.length);
  check('P7.1 история содержит оба прогона', rows >= 2, `${rows}`);
  await p.click('[data-pick-a] >> nth=0');
  await p.click('[data-pick-b] >> nth=1');
  await p.click('[data-compare-run]');
  await p.waitForSelector('[data-compare-result]');
  const cmpText = await p.textContent('[data-compare-result]');
  check('P7.2 сравнение показывает конфигурацию и рантайм',
    cmpText.includes('Промпты') && cmpText.includes('Извлечение')
      && cmpText.includes('Узлы в рантайме'));
  check('P7.3 качество не объявляется',
    (await p.textContent('[data-no-verdict]')).includes('нет модели оценки'));
  await shot(p, '07_run_compare.png', 'сравнение: различия названы, победитель не назначен');

  // ================= back to definition =================
  await p.click('[data-back-to-definition]');
  await p.waitForSelector('[data-mode="definition"]');
  check('P7.4 возврат к определению чистый',
    (await p.$$eval('[data-executed]', (n) => n.length)) === 0);

  // ================= P8 — field view =================
  console.log('\nP8 — поле (WhiteCrow)');
  await p.click('[data-view="field"]');
  await p.waitForSelector('[data-testid="field-radial"]');
  await p.click('[data-field-item="analyze_situation"]');
  await p.waitForSelector('[data-panel="node-overview"]');
  check('P8.1 поле открывает тот же инспектор',
    (await p.textContent('[data-node-title]')).includes('Чтение сцены'));
  await shot(p, '08_field_view.png', 'та же система, другая проекция');
  await p.click('[data-view="graph"]');
  await p.waitForSelector('[data-node-id="analyze_situation"]');
  check('P8.2 возврат без потери выбора',
    (await p.textContent('[data-node-title]')).includes('Чтение сцены'));

  check('P9 ноль ошибок консоли', errs.length === 0, errs.join(' | '));
  console.log(`\nPRODUCT ACCEPTANCE: ${steps.filter((s) => s.ok).length}/${steps.length} OK`);
} catch (e) {
  console.error('FAILED:', e.message);
  console.error('console errors:', errs);
  await p.screenshot({ path: join(OUT, 'product_FAILURE.png') });
  process.exitCode = 1;
} finally {
  writeFileSync(join(OUT, 'product_report.json'),
    JSON.stringify({ base: BASE, steps, console_errors: errs, failed }, null, 2), 'utf-8');
  await b.close();
}
