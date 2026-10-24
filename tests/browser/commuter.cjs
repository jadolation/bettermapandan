"use strict";
// Exact staged HTML, actual pinned Leaflet, deterministic CDN and tile responses.
// No live tile availability or geographic/service accuracy is asserted.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');
const puppeteer = require('puppeteer-core');
const rootIndex = process.argv.indexOf('--root');
assert.ok(rootIndex >= 0 && process.argv[rootIndex + 1], 'Pass --root _site');
const root = path.resolve(process.argv[rootIndex + 1]);
async function main() {
  const library = {};
  for (const ext of ['js', 'css']) {
    const response = await fetch(`https://unpkg.com/leaflet@1.9.4/dist/leaflet.${ext}`, { signal: AbortSignal.timeout(30000) });
    assert.ok(response.ok, 'actual Leaflet must be available, not a mock');
    library[ext] = await response.text();
  }
  const server = http.createServer((req, res) => {
    let file = path.resolve(root, '.' + new URL(req.url.replace(/^\/+/, '/'), 'http://localhost').pathname);
    if (!file.startsWith(root + path.sep)) return res.writeHead(403).end();
    try {
      if (fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
      res.setHeader('Content-Type', ({ '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml' })[path.extname(file)] || 'application/octet-stream');
      res.end(fs.readFileSync(file));
    } catch { res.writeHead(404).end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  let browser;
  try {
    browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] });
    for (const lang of ['en', 'fil', 'pag']) {
      for (const width of [320, 375, 1440]) {
        for (const mode of ['map', 'cdn-failure', 'no-js', 'tile-failure', 'shape-fixture']) {
          const page = await browser.newPage();
          const errors = [];
          let tileRequests = 0;
          page.on('pageerror', error => errors.push(error.message));
          await page.setViewport({ width, height: 900 });
          await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
          if (mode === 'no-js') await page.setJavaScriptEnabled(false);
          await page.setRequestInterception(true);
          page.on('request', async req => {
            if (req.url().includes('leaflet@1.9.4')) {
              if (mode === 'cdn-failure') return req.abort();
              const ext = req.url().endsWith('.css') ? 'css' : 'js';
              return req.respond({ contentType: ext === 'css' ? 'text/css' : 'text/javascript', headers: { 'access-control-allow-origin': '*' }, body: library[ext] });
            }
            if (req.url().includes('tile.openstreetmap.org')) {
              tileRequests++;
              if (mode === 'tile-failure') return req.abort();
              return req.respond({ contentType: 'image/png', body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNQK7j0HwAEkAJo39+DWAAAAABJRU5ErkJggg==', 'base64') });
            }
            if (req.url().startsWith(origin)) {
              if (mode === 'shape-fixture' && new URL(req.url()).pathname.endsWith('/commuter/')) {
                const localeRoot = lang === 'en' ? '' : lang;
                let html = fs.readFileSync(path.join(root, localeRoot, 'commuter/index.html'), 'utf8');
                html = html.replace(/(<script id="commuter-data" type="application\/json">)([\s\S]*?)(<\/script>)/, (_, start, raw, end) => {
                  const payload = JSON.parse(raw);
                  payload.shapes = payload.patterns.map(pattern => {
                    const capture = JSON.parse(fs.readFileSync(path.join(__dirname, '../fixtures/transport-osrm', pattern.id + '.json'), 'utf8'));
                    return { type: 'Feature', geometry: capture.routes[0].geometry, properties: {
                      pattern_id: pattern.id, distance_m: capture.routes[0].distance, endpoint: 'https://fixture.invalid', profile: 'driving', retrieved_at: 'captured test fixture only', snap_offsets_m: capture.waypoints.map(w => w.distance)
                    }};
                  });
                  return start + JSON.stringify(payload) + end;
                });
                return req.respond({contentType: 'text/html', body: html});
              }
              return req.continue();
            }
            return req.abort();
          });
          await page.goto(`${origin}/${lang === 'en' ? '' : lang + '/'}commuter/`, { waitUntil: 'networkidle0' });
          assert.equal(await page.$$eval('main', els => els.length), 1);
          assert.equal(await page.$$eval('.transport-card', els => els.length), 7);
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${lang} ${width} ${mode}: overflow`);
          assert.equal(await page.$eval('#commuter-page', el => /\{C_|\{COMMUTER_/.test(el.textContent)), false);
          if (mode === 'no-js' || mode === 'cdn-failure') {
            assert.equal(await page.$eval('#commuter-sheet', el => el.open), true);
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 0);
            assert.match(await page.$eval('#transport-list', el => el.textContent), /PHP 35-40/);
          } else {
            await page.waitForSelector('#commuter-page[data-ready="true"]').catch(error => { throw new Error(`${lang}/${width}/${mode}: ${errors.join('; ')} ${error.message}`); });
            assert.equal(await page.evaluate(() => L.version), '1.9.4');
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 7, `${lang}/${width}/${mode}: ${await page.$eval('#commuter-map-status', el => el.textContent)}`);
            assert.ok(tileRequests > 0);
            assert.equal(await page.$eval('#commuter-sheet', el => el.open), width >= 720);
            assert.ok(await page.$eval('#commuter-map', el => el.clientHeight >= 280));
            // All seven initial marker centers, including Dagupan, are in map bounds.
            assert.ok(await page.evaluate(() => {
              const bounds = document.querySelector('#commuter-map').getBoundingClientRect();
              return Array.from(document.querySelectorAll('.transport-marker')).every(el => {
                const r = el.getBoundingClientRect();
                return r.left >= bounds.left && r.right <= bounds.right && r.top >= bounds.top && r.bottom <= bounds.bottom;
              });
            }));
            const payload = await page.$eval('#commuter-data', el => JSON.parse(el.textContent));
            assert.equal(payload.patterns.length, 4);
            assert.equal(JSON.stringify(payload).includes('mini-dagupan-turnaround'), false);
            assert.equal(payload.shapes.length, 4);
            assert.equal(await page.$$eval('#commuter-lines fieldset', els => els.length), 2);
            assert.equal(await page.$$eval('.candidate-toggle', els => els.length), 2);
            assert.equal(await page.$$eval('.candidate-toggle:checked', els => els.length), 0);
            assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), 0);
            assert.equal(await page.$$eval('.operational-geometry', els => els.length), 0);
            const enabled = await page.$$eval('.candidate-toggle:not(:disabled)', els => els.map(el => el.dataset.pattern));
            assert.equal(enabled.length, 2);
            for (const [index, id] of enabled.entries()) {
              await page.focus(`.candidate-toggle[data-pattern="${id}"]`);
              await page.keyboard.press('Space');
              assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), index + 1);
              assert.equal(await page.$$eval('.transport-marker', els => els.length), 7);
              const before = await page.$$eval('#commuter-map path.leaflet-interactive', els => els.map(el => el.getAttribute('d')));
              const swap = `.candidate-toggle[data-pattern="${id}"]`;
              await page.$eval(swap, el => el.closest('fieldset').querySelector('button').focus());
              await page.keyboard.press('Enter');
              const changed = await page.$eval(`#commuter-lines fieldset:nth-child(${index + 1}) input`, el => el.dataset.pattern);
              assert.notEqual(changed, id);
              assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), index + 1);
              const after = await page.$$eval('#commuter-map path.leaflet-interactive', els => els.map(el => el.getAttribute('d')));
              assert.notDeepEqual(after, before, 'swap selects independently captured direction geometry');
              assert.equal(await page.$eval('#commuter-info-body', el => /snap|OSRM|routing.openstreetmap/i.test(el.textContent)), false);
              await page.keyboard.press('Enter');
              assert.equal(await page.$eval(swap, el => el.dataset.pattern), id);
            }
            const view = await page.$eval('.leaflet-map-pane', el => el.style.transform);
            if (enabled.length) {
              await page.focus(`.candidate-toggle[data-pattern="${enabled[0]}"]`);
              await page.keyboard.press('Space');
              assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), enabled.length - 1);
              assert.equal(await page.$eval('.leaflet-map-pane', el => el.style.transform), view);
            }
            await page.focus('#commuter-reset');
            await page.keyboard.press('Enter');
            assert.equal(await page.$$eval('.candidate-toggle:checked', els => els.length), 0);
            assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), 0);
            for (const feature of payload.features) {
              const selector = `.transport-marker[title="${payload.labels[feature.properties.id]}"]`;
              await page.focus(selector);
              await page.keyboard.press('Enter');
              await page.waitForFunction(name => document.querySelector('#commuter-info-title').textContent === name, { timeout: 3000 }, payload.labels[feature.properties.id]).catch(async error => { throw new Error(JSON.stringify({lang, width, mode, id: feature.properties.id, errors, active: await page.evaluate(() => document.activeElement.outerHTML)}) + error.message); });
              assert.equal(await page.$eval('#commuter-info-title', el => el.textContent), payload.labels[feature.properties.id]);
              assert.equal(await page.$eval('#commuter-sheet', el => el.open), true);
              const info = await page.$eval('#commuter-info-body', el => el.textContent);
              for (const fare of feature.properties.fares) assert.ok(info.includes(`PHP ${fare.amount.min}-${fare.amount.max}`));
              assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
            }
            await page.select('#commuter-type', 'tricycle');
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 3);
            assert.equal(await page.$$eval('.transport-card:not([hidden])', els => els.length), 3);
            await page.focus('#commuter-search'); await page.type('#commuter-search', 'zzzzzz');
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 0);
            await page.focus('#commuter-reset'); await page.keyboard.press('Enter');
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 7);
            await page.focus('.transport-select'); await page.keyboard.press('Enter');
            assert.equal(await page.$eval('#commuter-info', el => el === document.activeElement), true);
            await page.focus('#commuter-sheet summary'); await page.keyboard.press('Enter');
            assert.equal(await page.$eval('#commuter-sheet', el => el.open), false);
            assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
            if (mode === 'tile-failure') assert.equal(await page.$eval('#commuter-map-status', el => el.textContent), payload.labels.tiles_failed);
          }
          assert.deepEqual(errors, [], `${lang}/${width}/${mode}`);
          await page.close();
        }
      }
    }
    console.log('Commuter exact-artifact: 3 locales x 3 widths x 5 modes passed (actual Leaflet; captured road fixtures, fixture tiles).');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
