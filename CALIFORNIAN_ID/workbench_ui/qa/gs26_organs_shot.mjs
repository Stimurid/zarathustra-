/** Durable frame: native organ evidence inside the ordinary run result. */
import { chromium } from 'playwright';
import { join } from 'node:path';

const OUT = join(process.cwd(), 'qa', 'screenshots');
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
const errs = [];
p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });

await p.goto('http://127.0.0.1:8790', { waitUntil: 'networkidle' });
await p.click('[data-run-cta]');
await p.waitForSelector('[data-panel="run"]');
await p.click('[data-fixture]');
await p.click('[data-run-start]');
await p.waitForSelector('[data-run-result]', { timeout: 180000 });
await p.waitForSelector('[data-native-organs]');

const organs = await p.$$eval('[data-organ]', (rows) => rows.map((r) => ({
  organ: r.getAttribute('data-organ'),
  text: r.innerText.replace(/\s+/g, ' ').trim(),
})));
console.log(JSON.stringify(organs, null, 2));
const impls = await p.$$eval('[data-organ-impl]', (n) => n.map((x) => x.textContent.trim()));
console.log('implementation identities on screen:', impls);

await p.locator('[data-native-organs]').scrollIntoViewIfNeeded();
await p.screenshot({ path: join(OUT, 'gs26_native_organs.png') });
console.log('console errors:', errs.length ? errs : 'none');
await b.close();
