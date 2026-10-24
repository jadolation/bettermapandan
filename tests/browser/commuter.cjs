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
const originalMarkers = ['terminals.geojson', 'tricycle_stands.geojson'].flatMap(name =>
  JSON.parse(fs.readFileSync(path.join(__dirname, '../../src/data/transport', name), 'utf8')).features
).map(feature => [feature.id, feature.geometry.coordinates]);
const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, '../../src/data/transport/routes.json'), 'utf8')).routes;
const newDistances = { 'mini-mapandan-manaoag': 6784, 'mini-manaoag-mapandan': 6928.5, 'tri-guam-mapandan': 7733.8, 'tri-mapandan-guam': 7633, 'jeep-tuliao-calasiao': 5536.1, 'tri-tuliao-sta-barbara': 767.2, 'mini-manaoag-sm': 13773 };
const generatedShapes = JSON.parse(fs.readFileSync(path.join(__dirname, '../../src/data/transport/route_shapes.geojson'), 'utf8')).features;
async function assertCurrentLineFits(page, count) {
  assert.ok(await page.evaluate(count => {
    const map = document.querySelector('#commuter-map').getBoundingClientRect();
    const sheet = document.querySelector('#commuter-sheet').getBoundingClientRect();
    const header = document.querySelector('.commuter-hero').getBoundingClientRect();
    const left = innerWidth >= 900 && document.querySelector('#commuter-sheet').dataset.state !== 'collapsed' ? sheet.right : map.left;
    const bottom = innerWidth >= 900 ? map.bottom : sheet.top;
    return Array.from(document.querySelectorAll('#commuter-map path.leaflet-interactive')).every(path => {
      const rect = path.getBoundingClientRect();
      return rect.left >= left - 2 && rect.right <= map.right + 2 && rect.top >= header.bottom - 2 && rect.bottom <= bottom + 2;
    });
  }, count), 'the selected actual direction fits the map');
}
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
      for (const width of [320, 375, 430, 1440]) {
        for (const mode of ['map', 'cdn-failure', 'no-js', 'tile-failure', 'shape-fixture', 'partial-shapes', 'no-shapes']) {
          const page = await browser.newPage();
          if (lang === 'pag' && width === 430 && mode === 'map') await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
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
              if (['shape-fixture', 'partial-shapes', 'no-shapes'].includes(mode) && new URL(req.url()).pathname.endsWith('/commuter/')) {
                const localeRoot = lang === 'en' ? '' : lang;
                let html = fs.readFileSync(path.join(root, localeRoot, 'commuter/index.html'), 'utf8');
                html = html.replace(/(<script id="commuter-data" type="application\/json">)([\s\S]*?)(<\/script>)/, (_, start, raw, end) => {
                  const payload = JSON.parse(raw);
                  if (mode === 'shape-fixture') payload.shapes = payload.patterns.map(pattern => {
                    const capture = JSON.parse(fs.readFileSync(path.join(__dirname, '../fixtures/transport-osrm', pattern.id + '.json'), 'utf8'));
                    return { type: 'Feature', geometry: capture.routes[0].geometry, properties: {
                      pattern_id: pattern.id, distance_m: capture.routes[0].distance, endpoint: 'https://fixture.invalid', profile: 'driving', retrieved_at: 'captured test fixture only', snap_offsets_m: capture.waypoints.map(w => w.distance)
                    }};
                  });
                  if (mode === 'partial-shapes') payload.shapes = payload.shapes.filter(shape => ['mini-mapandan-dagupan-outbound', 'shared-mapandan-border-arch'].includes(shape.properties.pattern_id));
                  if (mode === 'no-shapes') payload.shapes = [];
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
           assert.equal(await page.$$eval('#commuter-lines fieldset', els => els.length), catalog.length);
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${lang} ${width} ${mode}: overflow`);
          assert.equal(await page.$eval('#commuter-page', el => /\{C_|\{COMMUTER_/.test(el.textContent)), false);
          if (mode === 'no-js' || mode === 'cdn-failure') {
            assert.equal(await page.$eval('#commuter-sheet-body', el => el.hidden), false);
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 0);
            assert.match(await page.$eval('#transport-list', el => el.textContent), /PHP 35-40/);
          } else {
            await page.waitForSelector('#commuter-page[data-ready="true"]').catch(error => { throw new Error(`${lang}/${width}/${mode}: ${errors.join('; ')} ${error.message}`); });
            assert.equal(await page.evaluate(() => L.version), '1.9.4');
            const markerCount = await page.$eval('#commuter-data', el => { const d = JSON.parse(el.textContent); return d.features.length + d.observations.length; });
            assert.equal(await page.$$eval('.transport-marker', els => els.length), markerCount, `${lang}/${width}/${mode}: ${await page.$eval('#commuter-map-status', el => el.textContent)}`);
            assert.ok(tileRequests > 0);
            assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'collapsed');
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
            assert.deepEqual(payload.features.map(feature => [feature.id, feature.geometry.coordinates]), originalMarkers);
            if (mode === 'map' || mode === 'tile-failure') {
              for (const [id, distance] of Object.entries(newDistances)) {
                const shape = payload.shapes.find(shape => shape.properties.pattern_id === id);
                assert.ok(shape, `${id}: actual generated candidate is public`);
                assert.equal(shape.properties.distance_m, distance);
                assert.equal(shape.properties.routing_eligible, false);
                assert.equal(shape.properties.verification_status, 'unverified');
                assert.deepEqual(shape.geometry, generatedShapes.find(feature => feature.id === id).geometry, 'actual generated geometry, not substituted overview');
              }
              assert.ok(payload.labels.candidate_warning.length < 100, 'compact localized provisional warning');
              assert.ok(await page.$eval('#commuter-page', (el, text) => el.textContent.includes(text), payload.labels.candidate_warning));
            }
            assert.equal(payload.catalog.length, catalog.length);
            assert.equal(payload.patterns.length, generatedShapes.filter(f => f.properties.classification === 'passenger_candidate').length);
            assert.equal(JSON.stringify(payload).includes('mini-dagupan-turnaround'), false);
            assert.equal(await page.$$eval('.candidate-toggle', els => els.length), payload.catalog.length);
            assert.equal(await page.$$eval('.candidate-toggle:checked', els => els.length), 0);
            assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), 0);
            assert.equal(await page.$$eval('.operational-geometry', els => els.length), 0);
            assert.equal(await page.$$eval('.transport-marker svg', els => els.length), markerCount);
            assert.ok(await page.$$eval('.transport-marker', els => els.every(el => el.getAttribute('aria-label') && el.clientWidth >= 40)));
            assert.equal(await page.$$eval('#commuter-lines details[open]', els => els.length), 0);
            for (const state of ['half', 'expanded', 'collapsed', 'half']) {
              await page.click(`[data-sheet-state="${state}"]`);
              await page.waitForFunction(state => document.querySelector('#commuter-sheet').dataset.state === state, {}, state);
              await page.evaluate(() => new Promise(requestAnimationFrame));
              assert.equal(await page.$eval(`[data-sheet-state="${state}"]`, el => el.getAttribute('aria-pressed')), 'true');
              if (process.argv.includes('--screenshots') && lang === 'en' && mode === 'map' && ['half', 'collapsed'].includes(state)) {
                await page.screenshot({ path: `/tmp/kilo/commuter-${width}-${state}.png` });
              }
            }
            assert.ok(await page.evaluate(() => {
              const map = document.querySelector('#commuter-map').getBoundingClientRect();
              const panel = document.querySelector('#commuter-sheet').getBoundingClientRect();
              return panel.bottom <= map.bottom + 1 && panel.left >= map.left && panel.right <= map.right;
            }), 'panel overlays map, not a separate stacked map area');
            let paths = 0;
            const shapeIds = new Set(payload.shapes.map(shape => shape.properties.pattern_id));
            for (const [index, route] of payload.catalog.entries()) {
              const selector = `[data-route="${route.id}"]`;
              const id = route.directions[0].join('+');
              const count = route.directions[0].filter(id => shapeIds.has(id)).length;
              const swappable = route.directions.filter(ids => ids.some(id => shapeIds.has(id))).length > 1;
              assert.equal(await page.$eval(`${selector} input`, el => el.disabled), count === 0);
              assert.equal(await page.$eval(`${selector} button`, el => el.hidden), !swappable);
              if (route.vehicle_type === 'multileg') {
                assert.ok(route.legs.length >= 2);
                assert.equal(route.transfer_count, route.legs.length - 1);
                assert.equal(route.directions.length, 1);
                const summary = await page.$eval(`${selector} .fare-summary`, el => el.textContent);
                if (route.id === 'mapandan-sta-barbara-multileg') {
                  assert.equal(route.fare_summary.complete, false);
                  assert.equal(route.fare_summary.amount, null);
                  assert.ok(summary.includes('PHP 65-100') && summary.includes(payload.labels.unknown_fare));
                } else {
                  assert.equal(route.fare_summary.complete, true);
                  assert.ok(summary.includes(route.id === 'mapandan-calasiao-multileg' ? 'PHP 80-120' : 'PHP 45-60'));
                }
              }
              await page.focus(`${selector} details summary`);
              await page.keyboard.press('Enter');
              assert.equal(await page.$eval(`${selector} details`, el => el.open), true);
              const breakdown = await page.$eval(`${selector} details`, el => el.textContent);
              assert.ok(breakdown.includes(payload.labels.waiting_unknown));
              assert.ok(breakdown.includes(payload.labels.fare_caveat));
              for (const leg of route.legs) {
                assert.ok(breakdown.includes(payload.labels[leg.label_key]));
                assert.ok(breakdown.includes(leg.fare.amount ? `PHP ${leg.fare.amount.min}-${leg.fare.amount.max}` : payload.labels.unknown_fare));
              }
              await page.keyboard.press('Enter');
              if (!count) continue;
              await page.focus(`${selector} input`);
              await page.keyboard.press('Space');
              paths += count;
              assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), paths);
              assert.equal(await page.$$eval('.transport-marker', els => els.length), markerCount);
              await assertCurrentLineFits(page, count);
              assert.ok(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.every(el => el.getAttribute('stroke-dasharray') === '10 7')));
              if (!swappable) continue;
              const before = await page.$$eval('#commuter-map path.leaflet-interactive', els => els.map(el => el.getAttribute('d')));
              const swap = `${selector} input`;
              await page.$eval(swap, el => el.closest('fieldset').querySelector('button').focus());
              await page.keyboard.press('Enter');
              const changed = await page.$eval(`#commuter-lines fieldset:nth-child(${index + 1}) input`, el => el.dataset.pattern);
              assert.notEqual(changed, id);
              assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), paths);
              const after = await page.$$eval('#commuter-map path.leaflet-interactive', els => els.map(el => el.getAttribute('d')));
              assert.notDeepEqual(after, before, 'swap selects independently captured direction geometry');
              await assertCurrentLineFits(page, count);
              assert.equal(await page.$eval('#commuter-info-body', el => /snap|OSRM|routing.openstreetmap/i.test(el.textContent)), false);
              await page.keyboard.press('Enter');
              assert.equal(await page.$eval(swap, el => el.dataset.pattern), id);
            }
            for (const state of ['expanded', 'collapsed', 'half']) {
              await page.click(`[data-sheet-state="${state}"]`);
              await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
              await assertCurrentLineFits(page, paths);
            }
            const enabled = await page.$$eval('.candidate-toggle:not(:disabled)', els => els.map(el => el.dataset.pattern));
            if (enabled.length) {
              await page.focus(`.candidate-toggle[data-pattern="${enabled[0]}"]`);
              await page.keyboard.press('Space');
              assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), paths - enabled[0].split('+').filter(id => shapeIds.has(id)).length);
            }
            await page.focus('#commuter-reset');
            await page.keyboard.press('Enter');
            assert.equal(await page.$$eval('.candidate-toggle:checked', els => els.length), 0);
            assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), 0);
            for (const feature of payload.features.concat(payload.observations)) {
              const selector = `.transport-marker[data-id="${feature.properties.id}"]`;
              await page.focus(selector);
              await page.keyboard.press('Enter');
              await page.waitForFunction(name => document.querySelector('#commuter-info-title').textContent === name, { timeout: 3000 }, payload.labels[feature.properties.id]).catch(async error => { throw new Error(JSON.stringify({lang, width, mode, id: feature.properties.id, errors, active: await page.evaluate(() => document.activeElement.outerHTML)}) + error.message); });
              assert.equal(await page.$eval('#commuter-info-title', el => el.textContent), payload.labels[feature.properties.id]);
              assert.notEqual(await page.$eval('#commuter-sheet', el => el.dataset.state), 'collapsed');
              const info = await page.$eval('#commuter-info-body', el => el.textContent);
              for (const fare of feature.properties.fares) assert.ok(info.includes(`PHP ${fare.amount.min}-${fare.amount.max}`));
              assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
            }
            await page.select('#commuter-type', 'tricycle');
            assert.equal(await page.$$eval('.transport-marker', els => els.length), payload.features.concat(payload.observations).filter(f => f.properties.transport_type === 'tricycle').length);
            assert.equal(await page.$$eval('.transport-card:not([hidden])', els => els.length), 3);
            await page.focus('#commuter-search'); await page.type('#commuter-search', 'zzzzzz');
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 0);
            await page.focus('#commuter-reset'); await page.keyboard.press('Enter');
            assert.equal(await page.$$eval('.transport-marker', els => els.length), markerCount);
            await page.$eval('.commuter-directory', el => { el.open = true; });
            await page.focus('.transport-select'); await page.keyboard.press('Enter');
            assert.equal(await page.$eval('#commuter-info', el => el === document.activeElement), true);
            await page.focus('[data-sheet-state="collapsed"]'); await page.keyboard.press('Enter');
            assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'collapsed');
            assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
            if (mode === 'tile-failure') assert.equal(await page.$eval('#commuter-map-status', el => el.textContent), payload.labels.tiles_failed);
            if (mode === 'map') {
              await page.setViewport({ width, height: 600 });
              await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
              assert.ok(await page.evaluate(() => document.querySelector('#commuter-page').getBoundingClientRect().bottom <= visualViewport.height + 1), 'dynamic viewport resize remains within available viewport');
              await page.click('[data-sheet-state="expanded"]');
              await page.evaluate(() => new Promise(requestAnimationFrame));
              assert.ok(await page.evaluate(() => {
                const p = document.querySelector('#commuter-sheet').getBoundingClientRect();
                return p.bottom <= innerHeight + 1 && p.height > 44;
              }));
            }
          }
          assert.deepEqual(errors, [], `${lang}/${width}/${mode}`);
          await page.close();
        }
      }
    }
    console.log('Commuter exact-artifact: 3 locales x 4 widths x 7 modes passed (actual Leaflet; dynamic catalog, overlay states/padding, accessible symbols, scoped fares, independent directions, partial/missing geometry, captured fixtures).');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
