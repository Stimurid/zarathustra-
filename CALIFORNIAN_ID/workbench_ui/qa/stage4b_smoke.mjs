/** Stage 4B visual proof: same objects, two projections, one inspector. */
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const BASE = process.argv[2] || 'http://127.0.0.1:8790';
const OUT = join(process.cwd(), 'qa', 'screenshots');
mkdirSync(OUT, { recursive: true });
const steps = [];
const shot = async (p, name, note) => {
  const file = join(OUT, `s4b_${name}.png`);
  await p.screenshot({ path: file });
  steps.push({ step: name, note, screenshot: file, ok: true });
  console.log(`  ✓ ${name}`);
};

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1600, height: 950 } });
const errs = [];
p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
p.on('response', (r) => { if (r.status() >= 400) errs.push(`${r.status()} ${r.url()}`); });

try {
  await p.goto(BASE, { waitUntil: 'networkidle' });
  await p.waitForSelector('[data-node-id="analyze_situation"]');

  // 1. graph projection with the corrected topology
  await shot(p, '01_graph_real_topology', 'реальный порядок + слои DECLARED/ACTUAL');

  // 2. switch to the WhiteCrow radial field
  await p.click('button[data-view="radial"]');
  await p.waitForSelector('[data-testid="field-radial"]');
  await shot(p, '02_radial_field', 'радиальная полевая проекция тех же объектов');

  // 3. click a field item -> the SAME inspector opens
  await p.click('[data-field-item="analyze_situation"]');
  await p.waitForFunction(() =>
    (document.querySelector('.dock-body')?.innerText || '').includes('17/9/7'));
  await shot(p, '03_inspector_from_field', 'инспектор из поля: тот же ассет и контракт');

  // 4. a RAG item from the field keeps RAG semantics
  await p.click('[data-field-item="cultural_context"]');
  await p.click('.right-dock__tab:has-text("RAG")');
  await p.waitForFunction(() =>
    (document.querySelector('.dock-body')?.innerText || '')
      .toLowerCase().includes('эффективные параметры'));
  await shot(p, '04_rag_from_field', 'RAG-инспектор открыт из полевой проекции');

  // 5. back to graph — selection survives the projection switch
  await p.click('button[data-view="graph"]');
  await p.waitForSelector('[data-node-id="cultural_context"]');
  await shot(p, '05_back_to_graph', 'возврат в граф, тот же выбранный узел');
} catch (e) {
  steps.push({ step: 'run', ok: false, error: String(e) });
  console.log('  ✗', e);
}

writeFileSync(join(OUT, 'stage4b_report.json'),
  JSON.stringify({ base: BASE, at: new Date().toISOString(), steps, errors: errs }, null, 2));
console.log(`\n${steps.filter(s => s.ok).length}/${steps.length} ok; ${errs.length} errors`);
await b.close();
process.exit(steps.every(s => s.ok) ? 0 : 1);
