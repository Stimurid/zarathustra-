/** Desktop responsiveness: primary actions reachable, no horizontal page scroll. */
import { chromium } from 'playwright';
import { join } from 'node:path';

const OUT = join(process.cwd(), 'qa', 'screenshots');
const sizes = [{ w: 1440, h: 900 }, { w: 1920, h: 1080 }];
const b = await chromium.launch();
let bad = 0;
for (const s of sizes) {
  const p = await b.newPage({ viewport: { width: s.w, height: s.h } });
  await p.goto('http://127.0.0.1:8790', { waitUntil: 'networkidle' });
  await p.waitForSelector('[data-node-id="analyze_situation"]');
  await p.click('[data-node-id="analyze_situation"]');
  await p.waitForSelector('[data-panel="node-overview"]');
  const overflow = await p.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth);
  const cta = await p.$eval('[data-run-cta]', (e) => {
    const r = e.getBoundingClientRect();
    return r.width > 0 && r.right <= window.innerWidth && r.top >= 0;
  });
  const dock = await p.$eval('.right-dock', (e) => e.getBoundingClientRect().width);
  const canvas = await p.$eval('.canvas', (e) => e.getBoundingClientRect().width);
  const ok = overflow <= 0 && cta && dock > 280 && canvas > 500;
  if (!ok) bad += 1;
  console.log(`${s.w}x${s.h}: overflow=${overflow} cta_visible=${cta} dock=${Math.round(dock)} canvas=${Math.round(canvas)} -> ${ok ? 'OK' : 'FAIL'}`);
  await p.screenshot({ path: join(OUT, `responsive_${s.w}x${s.h}.png`) });
  await p.close();
}
await b.close();
process.exitCode = bad ? 1 : 0;
