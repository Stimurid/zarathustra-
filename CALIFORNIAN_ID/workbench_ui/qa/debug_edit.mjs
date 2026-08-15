import { chromium } from 'playwright';

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1600, height: 950 } });
p.on('console', (m) => { if (m.type() === 'error') console.log('CONSOLE', m.text()); });
await p.goto('http://127.0.0.1:8790', { waitUntil: 'networkidle' });
await p.click('[data-node-id="analyze_situation"]');
await p.waitForSelector('.dock-body');
await p.click('.right-dock__tab:has-text("SOURCE")');
await p.click('button[data-step="clone"]');
await p.waitForSelector('.cm-content');
await p.waitForTimeout(800);

await p.click('button:has-text("signal_definitions")');
await p.waitForTimeout(400);
await p.keyboard.press('ArrowDown');
await p.keyboard.press('End');
await p.keyboard.type(' Уточнено.');
await p.waitForTimeout(400);

const state = async (tag) => {
  const o = await p.evaluate(() => ({
    err: document.querySelector('.err-text')?.textContent || null,
    hasDiff: !!document.querySelector('pre.diff'),
    variantState: document.querySelector('.dock-body .pill')?.textContent || null,
    saveDisabled: document.querySelector('button.primary')?.disabled ?? null,
    steps: [...document.querySelectorAll('.step')].map(s => s.className).join('|'),
  }));
  console.log(tag, JSON.stringify(o));
};
await state('BEFORE_SAVE');
await p.click('button[data-step="edit"]');
await p.waitForTimeout(1500);
await state('AFTER_SAVE');
await p.click('button[data-step="diff"]');
await p.waitForTimeout(1800);
await state('AFTER_DIFF');
await b.close();
