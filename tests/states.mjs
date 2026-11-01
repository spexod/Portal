// Interaction states of the explore page (and the forms), screenshotted at desktop and phone width:
// the menus open, a spectrum staged, the table scrolled, the help dialog, the forms submitted empty.
//   cd tests && npm install && npx playwright install chromium      # once, see screenshots.mjs
//   node states.mjs [base-url] [out-dir]                             # default http://localhost, ../logs/screenshots/states
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const baseURL = (process.argv[2] || 'http://localhost').replace(/\/$/, '');
const outDir = process.argv[3] || join('..', 'logs', 'screenshots', 'states');
mkdirSync(outDir, { recursive: true });
const widths = [1280, 390];
const report = [];

// each state: a name and a function that drives the page before the screenshot
const states = [
    ['explore-columns-menu', async (p) => { await p.click('button#AddColumn'); await p.waitForTimeout(600); }],
    ['explore-sample-menu', async (p) => { await p.hover('.SampleSelect'); await p.waitForTimeout(400); }],
    ['explore-hitran-menu', async (p) => { await p.click('button:has-text("Hitran Line Menu")'); await p.waitForTimeout(600); }],
    ['explore-downloads-empty', async (p) => {
        const t = p.locator('.header-downloads-toggle');
        if (await t.getAttribute('aria-expanded') !== 'true') await t.click();
        await p.waitForTimeout(400);
    }],
    ['explore-staged', async (p) => {
        // hover a cell with a spectrum count: the tooltip offers "Mark for download"
        const arrow = p.locator('img[alt="ArrowIcon"]').first();
        await arrow.hover();
        await p.waitForTimeout(500);
        const add = p.locator('img[title^="Click add"]').first();
        await add.click({ force: true });
        await p.waitForTimeout(1200);
    }],
    ['explore-star', async (p) => {
        await p.locator('.spexo-datacell-link').first().click();
        await p.waitForLoadState('networkidle');
        await p.waitForTimeout(2500);
    }],
    ['explore-scrolled', async (p) => { await p.evaluate(() => window.scrollBy(0, 1400)); await p.waitForTimeout(400); }],
    ['explore-table-scrolled', async (p) => { await p.evaluate(() => { const r = document.querySelector('.SpexoSearchScroller'); if (r) r.scrollTop = 1400; }); await p.waitForTimeout(400); }],
    ['explore-help', async (p) => { await p.click('.instructionsButton'); await p.waitForTimeout(500); }],
    ['login-submitted', async (p) => { await p.goto(baseURL + '/Login', { waitUntil: 'networkidle' }); await p.click('button[type="submit"], input[type="submit"]').catch(() => {}); await p.waitForTimeout(800); }],
    ['register-submitted', async (p) => { await p.goto(baseURL + '/Register', { waitUntil: 'networkidle' }); await p.click('button[type="submit"], input[type="submit"]').catch(() => {}); await p.waitForTimeout(800); }],
];

const browser = await chromium.launch();
for (const width of widths) {
    for (const [name, drive] of states) {
        const context = await browser.newContext({ viewport: { width, height: 900 } });
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', (e) => errors.push(`page error: ${e.message}`));
        page.on('console', (m) => { if (m.type() === 'error' && !/compute-pressure/.test(m.text())) errors.push(`console error: ${m.text()}`); });
        const file = `${name}-${width}.png`;
        try {
            await page.goto(baseURL + '/ExploreData', { waitUntil: 'networkidle', timeout: 60000 });
            await page.waitForTimeout(1500);
            // close the first-visit downloads panel so it does not cover the state under test
            const toggle = page.locator('.header-downloads-toggle');
            if (!name.includes('downloads') && await toggle.count() && await toggle.getAttribute('aria-expanded') === 'true') await toggle.click();
            await drive(page);
            await page.screenshot({ path: join(outDir, file), fullPage: false });
            report.push(`${errors.length ? 'FAIL' : 'PASS'} ${name} at ${width}px -> ${file}` + (errors.length ? `\n      ${errors.join('\n      ')}` : ''));
        } catch (e) {
            report.push(`FAIL ${name} at ${width}px: ${e.message.split('\n')[0]}`);
        }
        await context.close();
    }
}
await browser.close();
writeFileSync(join(outDir, 'report.txt'), report.join('\n') + '\n');
console.log(report.join('\n'));
process.exit(report.some((line) => line.startsWith('FAIL')) ? 1 : 0);
