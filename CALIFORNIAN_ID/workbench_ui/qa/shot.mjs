/** Ad-hoc visual check: open a state, screenshot it, print console errors.
 *  Usage: node qa/shot.mjs <name> [<script-name>] */
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';

const BASE = 'http://127.0.0.1:8790';
const name = process.argv[2] || 'look';
const what = process.argv[3] || 'landing';
const OUT = join(process.cwd(), 'qa', 'screenshots');
mkdirSync(OUT, { recursive: true });

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
const errs = [];
p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
p.on('pageerror', (e) => errs.push(`pageerror: ${e.message}`));

await p.goto(BASE, { waitUntil: 'networkidle' });
await p.waitForSelector('[data-mainnav]');

if (what === 'node') {
  await p.click('[data-node-id="analyze_situation"]');
  await p.waitForSelector('[data-panel="node-overview"]');
} else if (what === 'prompt') {
  await p.click('[data-node-id="analyze_situation"]');
  await p.waitForSelector('[data-panel="node-overview"]');
  await p.click('[data-goto="prompt"]');
  await p.waitForSelector('[data-prompt-head]');
} else if (what === 'run') {
  await p.click('[data-run-cta]');
  await p.waitForSelector('[data-panel="run"]');
} else if (what === 'runs') {
  await p.click('[data-section="runs"]');
  await p.waitForSelector('[data-panel="runs"]');
} else if (what === 'overlay') {
  await p.click('[data-section="runs"]');
  await p.waitForSelector('[data-panel="runs"]');
  const first = await p.$('[data-run-open]');
  if (first) { await first.click(); await p.waitForTimeout(900); }
} else if (what === 'rag') {
  await p.click('[data-section="rag"]');
  await p.waitForSelector('[data-panel="rag-catalogue"]');
} else if (what === 'field') {
  await p.click('[data-view="field"]');
  await p.waitForTimeout(700);
}
await p.waitForTimeout(500);
await p.screenshot({ path: join(OUT, `look_${name}.png`) });
console.log('console errors:', errs.length ? errs : 'none');
await b.close();
