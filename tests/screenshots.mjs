// Screenshots of every page at phone and desktop width, for a visual check after a frontend change.
//
//   cd tests && npm install && npx playwright install chromium      # once (Chromium, ~120 MB)
//   node screenshots.mjs [base-url] [out-dir]                         # default http://localhost, ../logs/screenshots/<date>
//
// Writes <page>-<width>.png (full page) and a report.txt with the HTTP status, the page errors and the
// console errors of each page. A non-zero exit means a page did not answer or threw an error; the
// pictures are for the human (or the assistant) to look at. Run against the local stack
// (./shell/local-test.sh --frontend) rather than production.
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const baseURL = (process.argv[2] || 'http://localhost').replace(/\/$/, '');
const stamp = new Date().toISOString().slice(0, 16).replace(/[T:]/g, '-');
const outDir = process.argv[3] || join('..', 'logs', 'screenshots', stamp);
// the pages of the site (SpExo-FrontEnd/app/(SharedContext)/*/page.js*), see tests/smoke.py PAGES
const pages = ['/', '/ExploreData', '/Tutorials', '/DataInfo', '/DevTeam', '/Contact', '/Login', '/Register',
               '/ResetPasswordRequest'];
const widths = [1280, 390];

mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
const report = [`screenshots of ${baseURL} at ${new Date().toISOString()}`, ''];
let failures = 0;
for (const width of widths) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1 });
    for (const path of pages) {
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', (e) => errors.push(`page error: ${e.message}`));
        page.on('console', (m) => { if (m.type() === 'error' && !/compute-pressure/.test(m.text())) errors.push(`console error: ${m.text()}`); });
        const name = (path === '/' ? 'home' : path.slice(1).toLowerCase()) + `-${width}.png`;
        let status = 'no response';
        try {
            const response = await page.goto(baseURL + path, { waitUntil: 'networkidle', timeout: 60000 });
            status = response ? String(response.status()) : status;
            // the explore page draws its plot after the data arrives
            await page.waitForTimeout(1500);
            await page.screenshot({ path: join(outDir, name), fullPage: true });
        } catch (e) {
            errors.push(`screenshot failed: ${e.message.split('\n')[0]}`);
        }
        const ok = status === '200' && errors.length === 0;
        if (!ok) failures += 1;
        report.push(`${ok ? 'PASS' : 'FAIL'} ${path} at ${width}px: HTTP ${status}, ${errors.length} error(s) -> ${name}`);
        for (const e of errors) report.push(`      ${e}`);
        await page.close();
    }
    await context.close();
}
await browser.close();
report.push('', `${pages.length * widths.length} screenshots, ${failures} with problems, in ${outDir}`);
writeFileSync(join(outDir, 'report.txt'), report.join('\n') + '\n');
console.log(report.join('\n'));
process.exit(failures ? 1 : 0);
