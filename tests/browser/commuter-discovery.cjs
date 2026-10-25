"use strict";
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const http = require('node:http');
const puppeteer = require('puppeteer-core');
const root = path.resolve(process.argv[process.argv.indexOf('--root') + 1] || '_site');
const server = http.createServer((req, res) => {
  const file = path.join(root, decodeURIComponent(req.url.split('?')[0]), req.url.split('?')[0].endsWith('/') ? 'index.html' : '');
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file)) { res.writeHead(404).end(); return; }
  const ext = path.extname(file);
  res.setHeader('Content-Type', ({'.html':'text/html', '.css':'text/css', '.js':'text/javascript', '.json':'application/json'})[ext] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
});
(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  let browser;
  try {
    browser = await puppeteer.launch({executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome', headless:true, args:['--no-sandbox']});
    const page = await browser.newPage();
    await page.setRequestInterception(true);
    page.on('request', req => req.url().startsWith(origin) ? req.continue() : req.abort());
    let cases = 0;
    for (const locale of ['', 'fil/', 'pag/']) {
      for (const surface of ['', 'services/', 'gis/']) {
        for (const width of [320, 375, 430, 1440]) {
          await page.setViewport({width, height:900});
          const response = await page.goto(`${origin}/${locale}${surface}`, {waitUntil:'networkidle0'});
          assert.equal(response.status(), 200);
           assert.ok(await page.$eval('html', el => el.scrollWidth <= innerWidth + 1), `${locale}${surface} ${width}: page overflow`);
           if (surface === 'gis/') {
             assert.equal(await page.$$eval('a[href$="/commuter/"], .commuter-discovery-shortcut, #gis-commuter-title', els => els.length), 0);
             assert.equal(await page.$$eval('footer', els => els.length), 0);
             assert.ok(await page.$$eval('.site-header .nav a[href$="/gis/"]', els => els.length >= 1));
             assert.equal(await page.$$eval('header a[href$="/commuter/"]', els => els.length), 0);
             cases++;
             continue;
           }
           if (surface === '') {
             assert.ok(await page.$eval('#dpwh-map', el => el.closest('section').nextElementSibling.matches('.commuter-discovery')));
             assert.ok(await page.$eval('.commuter-discovery', el => Boolean(el.compareDocumentPosition(document.querySelector('.map-container')) & Node.DOCUMENT_POSITION_FOLLOWING)));
           }
           const selector = surface === 'services/' ? '[data-entry-type="digital-tool"] .service-link' : '.commuter-discovery-card a';
          assert.deepEqual(await page.$eval(selector, el => ({href:el.getAttribute('href'), target:el.target})), {href:`/${locale}commuter/`, target:''});
          assert.ok(fs.existsSync(path.join(root, locale, 'commuter/index.html')));
          assert.ok(await page.$eval(selector, el => { const r=el.getBoundingClientRect(); return r.height>=44 && r.width>=44 && r.left>=0 && r.right<=innerWidth; }), `${locale}${surface} ${width}: ${JSON.stringify(await page.$eval(selector, el => el.getBoundingClientRect().toJSON()))}`);
          await page.$eval(selector, el => el.focus());
          assert.ok(await page.$eval(selector, el => document.activeElement === el));
          assert.equal(await page.$$eval('a a', els => els.length), 0);
          assert.equal(await page.$$eval('header a[href$="/commuter/"]', els => els.length), 0);
           assert.equal(await page.$$eval('footer a[href$="/gis/"]', els => els.length), 1);
           assert.equal(await page.$$eval('footer a[href$="/commuter/"]', els => els.length), 1);
          assert.ok(await page.$$eval('.site-header .nav a[href$="/gis/"]', els => els.length >= 1));
          assert.ok(await page.$eval(selector, el => {
             const card = el.closest('.commuter-discovery-card, .service-category-card');
            const r = card.getBoundingClientRect();
            return r.left >= 0 && r.right <= innerWidth && card.scrollWidth <= card.clientWidth + 1;
          }), 'discovery card has no horizontal overflow');
          assert.equal(await page.$$eval('script[src*="commuter"]', els => els.length), 0);
          assert.equal(await page.$$eval('[href]', els => els.filter(el => /\/(fil|pag)\/\1\//.test(el.getAttribute('href'))).length), 0);
          assert.ok(!await page.$eval('body', el => /\{\{?DISCOVERY_/.test(el.innerHTML)));
           if (surface === 'services/') {
            await page.$eval('#service-filter-input', el => {el.value='commuter'; el.dispatchEvent(new Event('input'));});
            assert.equal(await page.$$eval('.service-category-card', els => els.filter(el => getComputedStyle(el).display !== 'none').length), 1);
            assert.ok(await page.$eval(selector, el => getComputedStyle(el).display !== 'none'));
            await page.$eval('#service-filter-input', el => {el.value='zz-no-match'; el.dispatchEvent(new Event('input'));});
             assert.ok(await page.$eval('#service-no-results', el => getComputedStyle(el).display !== 'none'));
           }
           await page.$eval(selector, el => el.click());
           await page.waitForFunction(expected => location.pathname === expected, {}, `/${locale}commuter/`);
           cases++;
        }
      }
      await page.goto(`${origin}/${locale}commuter/`, {waitUntil:'networkidle0'});
      assert.equal(await page.$$eval('footer', els => els.length), 0);
      assert.equal(await page.$$eval('#primary-nav a[href$="/commuter/"]', els => els.length), 0);
    }
    console.log(`Commuter discovery: ${cases} exact-artifact locale/surface/viewport cases passed (external requests blocked).`);
  } finally { if (browser) await browser.close(); await new Promise(resolve => server.close(resolve)); }
})().catch(error => {console.error(error); process.exitCode=1;});
