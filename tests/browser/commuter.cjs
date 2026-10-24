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
const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, '../../src/data/transport/routes.json'), 'utf8')).routes.filter(route => route.public_catalog !== false);
const newDistances = { 'mini-mapandan-manaoag': 6784, 'mini-manaoag-mapandan': 6928.5, 'tri-guam-mapandan': 7733.8, 'tri-mapandan-guam': 7633, 'jeep-tuliao-calasiao': 5536.1, 'tri-tuliao-sta-barbara': 767.2, 'mini-manaoag-sm': 13773 };
const generatedShapes = JSON.parse(fs.readFileSync(path.join(__dirname, '../../src/data/transport/route_shapes.geojson'), 'utf8')).features;
async function assertCurrentLineFits(page, count) {
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  if (await page.$eval('#commuter-sheet', el => el.dataset.state === 'expanded' && innerWidth < 900)) return;
  assert.ok(await page.evaluate(count => {
    const map = document.querySelector('#commuter-map').getBoundingClientRect();
    const sheet = document.querySelector('#commuter-sheet').getBoundingClientRect();
    const header = document.querySelector('.commuter-hero').getBoundingClientRect();
    const hidden = document.querySelector('#commuter-sheet').dataset.state === 'hidden';
    const left = innerWidth >= 900 && !hidden ? sheet.right : map.left;
    const bottom = innerWidth >= 900 || hidden ? map.bottom - 52 : sheet.top;
    return Array.from(document.querySelectorAll('#commuter-map path.leaflet-interactive')).every(path => {
      const rect = path.getBoundingClientRect();
      return rect.left >= left - 2 && rect.right <= map.right + 2 && rect.top >= header.bottom - 2 && rect.bottom <= bottom + 2;
    });
  }, count), 'the selected actual direction fits the map: ' + JSON.stringify(await page.evaluate(() => ({
    width: innerWidth, zoom: window.__commuterMap.getZoom(),
    map: document.querySelector('#commuter-map').getBoundingClientRect().toJSON(),
    sheet: document.querySelector('#commuter-sheet').getBoundingClientRect().toJSON(),
    paths: Array.from(document.querySelectorAll('#commuter-map path.leaflet-interactive')).map(el => el.getBoundingClientRect().toJSON())
  }))));
}
async function openSheet(page) {
  if (await page.$eval('#commuter-sheet', el => el.dataset.state === 'hidden')) await page.click('.sheet-reopen');
  await page.click('.sheet-sizes [data-sheet-state="half"]');
}
async function dragHandle(page, height) {
  const rect = await page.$eval('.sheet-handle', el => { const r = el.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; });
  const current = await page.$eval('#commuter-sheet', el => el.getBoundingClientRect().height);
  await page.mouse.move(rect.x, rect.y);
  await page.mouse.down();
  await page.mouse.move(rect.x, rect.y + current - height, { steps: 12 });
  await page.mouse.up();
}
async function assertZoomGestures(page, mobile) {
  const runtime = await page.evaluate(() => ({ version: L.version, touch: L.Browser.touch, pointer: L.Browser.pointer, safari: L.Browser.safari,
    viewport: document.querySelector('meta[name="viewport"]').content }));
  assert.equal(runtime.version, '1.9.4');
  assert.ok(!/user-scalable\s*=\s*no|maximum-scale/i.test(runtime.viewport));
  console.log('Gesture runtime:', JSON.stringify(runtime));
  const point = await page.$eval('#commuter-map', el => {
    const r = el.getBoundingClientRect();
    return { x: r.right - Math.min(160, r.width / 2), y: r.top + r.height * .5 };
  });
  assert.ok(await page.evaluate(({ x, y }) => document.elementFromPoint(x, y).closest('#commuter-map') !== null, point), 'gesture reaches map, not overlay');
  const client = await page.createCDPSession();
  async function pinch(start, end) {
    const touches = distance => [-1, 1].map((sign, id) => ({ x: point.x + sign * distance, y: point.y, id: id + 1 }));
    await client.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: touches(start) });
    for (let step = 1; step <= 12; step++) {
      await client.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: touches(start + (end - start) * step / 12) });
      await page.evaluate(() => new Promise(requestAnimationFrame));
    }
    await client.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await page.waitForFunction(() => !window.__commuterMap._animatingZoom && !window.__commuterMap.touchZoom._zooming);
  }
  if (mobile) {
    const original = await page.evaluate(() => ({ center: window.__commuterMap.getCenter(), zoom: window.__commuterMap.getZoom() }));
    for (const edge of [null, 'min', 'max']) {
      for (const direction of [1, -1]) {
        const before = await page.evaluate(({ edge, center }) => {
          const map = window.__commuterMap;
          map.setView(center, edge === 'min' ? map.getMinZoom() : edge === 'max' ? map.getMaxZoom() : 12, { animate: false });
          return map.getZoom();
        }, { edge, center: original.center });
        await pinch(50, direction > 0 ? 55 : 50 / 1.1);
        const settled = await page.evaluate(() => {
          const map = window.__commuterMap;
          return { zoom: map.getZoom(), min: map.getMinZoom(), max: map.getMaxZoom(), bounds: map.getBounds().toBBoxString() };
        });
        const delta = (settled.zoom - before) * direction;
        assert.ok(delta >= 0 && delta <= .5, `small native pinch ${edge}/${direction}: ${delta}`);
        if (!edge) assert.equal(delta, .25, '10% pinch settles to a quarter level in either direction');
        assert.ok(settled.zoom >= settled.min && settled.zoom <= settled.max, 'pinch release respects zoom limits');
        await page.evaluate(() => {
          window.dispatchEvent(new Event('resize'));
          if (visualViewport) { visualViewport.dispatchEvent(new Event('resize')); visualViewport.dispatchEvent(new Event('scroll')); }
        });
        await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 250)));
        assert.deepEqual(await page.evaluate(() => ({ zoom: window.__commuterMap.getZoom(), bounds: window.__commuterMap.getBounds().toBBoxString() })),
          { zoom: settled.zoom, bounds: settled.bounds }, 'small pinch zoom and geographic bounds remain stable after release');
      }
    }
    await page.evaluate(({ center, zoom }) => window.__commuterMap.setView(center, zoom, { animate: false }), original);
  }
  for (const ctrl of mobile ? [null] : [false, true]) {
    for (const direction of [1, -1]) {
      const before = await page.evaluate(() => window.__commuterMap.getZoom());
      if (mobile) {
        await pinch(direction > 0 ? 25 : 70, direction > 0 ? 70 : 25);
      } else {
        await client.send('Input.dispatchMouseEvent', { type: 'mouseWheel', x: point.x, y: point.y, deltaX: 0, deltaY: -direction * 160, modifiers: ctrl ? 2 : 0 });
      }
      await page.waitForFunction(({ before, direction }) => (window.__commuterMap.getZoom() - before) * direction > .5, { timeout: 3000 }, { before, direction });
      await page.waitForFunction(() => !window.__commuterMap._animatingZoom && !window.__commuterMap.touchZoom._zooming);
      const after = await page.evaluate(() => window.__commuterMap.getZoom());
      await page.evaluate(() => {
        window.dispatchEvent(new Event('resize'));
        if (visualViewport) { visualViewport.dispatchEvent(new Event('resize')); visualViewport.dispatchEvent(new Event('scroll')); }
      });
      await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 250)));
      assert.equal(await page.evaluate(() => window.__commuterMap.getZoom()), after, 'completed zoom survives viewport events');
    }
  }
  assert.deepEqual(await page.evaluate(() => {
    const options = window.__commuterMap.options;
    return [options.zoomSnap, options.zoomDelta, options.wheelPxPerZoomLevel, options.wheelDebounceTime];
  }), [.25, 1, 60, 40], 'only snap spacing changes; button and wheel tuning retain Leaflet defaults');
  for (const direction of [1, -1]) {
    const before = await page.evaluate(() => window.__commuterMap.getZoom());
    await page.click(direction > 0 ? '.leaflet-control-zoom-in' : '.leaflet-control-zoom-out');
    await page.waitForFunction(() => !window.__commuterMap._animatingZoom);
    assert.equal(await page.evaluate(() => window.__commuterMap.getZoom()), before + direction, 'zoom buttons still move exactly one level');
  }
  await client.detach();
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
          await page.setViewport({ width, height: 900, isMobile: width < 900, hasTouch: width < 900 });
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
              if (new URL(req.url()).pathname.endsWith('/assets/commuter-map.min.js')) {
                return req.respond({ contentType: 'text/javascript', body: 'if (window.L) L.Map.addInitHook(function () { window.__commuterMap = this; });\n' + fs.readFileSync(path.join(root, 'assets/commuter-map.min.js'), 'utf8') });
              }
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
           assert.equal(await page.$$eval('[data-route="manaoag-sm-minibus"]', els => els.length), 0);
           assert.equal(await page.$$eval('[data-route="mapandan-manaoag-sm-multileg"]', els => els.length), 1);
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
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 0, `${lang}/${width}/${mode}: starts without crowded markers`);
             assert.equal(await page.$eval('#commuter-show-all', el => el.checked), false);
            await page.waitForSelector('.leaflet-commuter-boundaries-pane path').catch(async error => { throw new Error(`${lang}/${width}/${mode}: boundary ${await page.$eval('#commuter-map', el => el.dataset.boundaryUrl)}; ${errors.join('; ')}; ${error.message}`); });
            assert.ok(await page.evaluate(() => {
              const pane = document.querySelector('.leaflet-commuter-boundaries-pane');
              const map = window.__commuterMap;
              return getComputedStyle(pane).pointerEvents === 'none' && +pane.style.zIndex < +getComputedStyle(map.getPane('overlayPane')).zIndex &&
                Array.from(pane.querySelectorAll('path')).every(el => !el.classList.contains('leaflet-interactive')) &&
                Object.values(map._layers).filter(layer => layer instanceof L.Path && layer.options.pane === 'commuter-boundaries').every(layer => layer.options.interactive === false && layer.options.bubblingMouseEvents === false && !layer.getPopup() && !layer.getTooltip());
            }), 'local indicative boundaries are visual only below routes');
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
            await openSheet(page);
            await page.focus('#commuter-show-all'); await page.keyboard.press('Space');
            assert.equal(await page.$$eval('.transport-marker svg', els => els.length), markerCount);
            assert.ok(await page.$$eval('.transport-marker', els => els.every(el => {
              const marker = el.getBoundingClientRect(), svg = el.querySelector('svg').getBoundingClientRect();
              return marker.width === 44 && marker.height === 44 && svg.width <= 20 && svg.height <= 20 &&
                Math.abs(marker.x + marker.width / 2 - svg.x - svg.width / 2) < 1 && Math.abs(marker.y + marker.height / 2 - svg.y - svg.height / 2) < 1 && getComputedStyle(el.querySelector('svg')).marginTop === '0px';
            })), 'actual Leaflet SVG boxes centered in 44px marker hit targets: ' + JSON.stringify(await page.$eval('.transport-marker', el => {
              const svg = el.querySelector('svg'); const style = getComputedStyle(svg);
              return { marker: el.getBoundingClientRect().toJSON(), svg: svg.getBoundingClientRect().toJSON(), margin: style.margin, display: style.display, parentDisplay: getComputedStyle(el).display };
            })));
            await page.keyboard.press('Space');
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 0);
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
            for (const route of payload.catalog) {
              const selector = `[data-route="${route.id}"]`;
              const id = route.directions[0].join('+');
              const count = route.directions[0].filter(id => shapeIds.has(id)).length;
              if (route.id === 'mapandan-manaoag-sm-multileg') {
                assert.deepEqual(route.directions, [['mini-mapandan-manaoag', 'mini-manaoag-sm']]);
                assert.equal(route.transfer_count, 1);
                assert.equal(await page.$eval(`${selector} .route-subtitle`, el => el.textContent), payload.labels.via_manaoag);
                if (mode === 'map') assert.equal(count, 2);
              }
              assert.equal(await page.$eval(`${selector} input`, el => el.disabled), count === 0);
              assert.equal(await page.$$eval(`${selector} button`, els => els.length), 0, 'no direction interchange control');
              await openSheet(page);
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
              const expectedMarkers = await page.$$eval('.candidate-toggle:checked', (els, routes) => [...new Set(els.flatMap(el => routes.find(route => route.id === el.closest('fieldset').dataset.route).marker_ids))].sort(), payload.catalog);
              assert.deepEqual(await page.$$eval('.transport-marker', els => els.map(el => el.dataset.id).sort()), expectedMarkers, 'only explicit selected-route source observations');
              if (width < 900) {
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'hidden', 'route selection immediately reveals the map');
                assert.equal(await page.$eval('.sheet-reopen', el => el === document.activeElement), true);
              }
              await assertCurrentLineFits(page, count);
              assert.ok(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.every(el => el.getAttribute('stroke-dasharray') === '10 7')));
              assert.equal(await page.$eval(`${selector} input`, el => el.dataset.pattern), id, 'catalog primary sourced direction, not reversed geometry');
              assert.equal(await page.$eval('#commuter-info-body', el => /snap|OSRM|routing.openstreetmap/i.test(el.textContent)), false);
            }
            if (mode === 'map') {
              if (await page.$eval('#commuter-sheet', el => el.dataset.state !== 'hidden')) await page.click('[data-sheet-state="hidden"]');
              await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
              await assertZoomGestures(page, width < 900);
            }
            await openSheet(page);
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
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 0);
            await page.focus('#commuter-show-all'); await page.keyboard.press('Space');
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
            const lastFeature = payload.features.concat(payload.observations).at(-1);
            assert.equal(await page.$$eval('.transport-marker', els => els.length), payload.features.concat(payload.observations).filter(f => f.properties.transport_type === 'tricycle' || f.properties.id === lastFeature.properties.id).length);
            assert.equal(await page.$$eval('.transport-card:not([hidden])', els => els.length), 3);
            await page.focus('#commuter-search'); await page.type('#commuter-search', 'zzzzzz');
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 1, 'explicit selection remains visible independently of filters');
            await page.focus('#commuter-reset'); await page.keyboard.press('Enter');
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 0);
            await page.$eval('.commuter-directory', el => { el.open = true; });
            await page.focus('.transport-select'); await page.keyboard.press('Enter');
            assert.equal(await page.$eval('#commuter-info', el => el === document.activeElement), true);
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 1, 'directory selection works with no route or show-all');
            await page.focus('[data-sheet-state="collapsed"]'); await page.keyboard.press('Enter');
            assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'collapsed');
            assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
            if (mode === 'tile-failure') assert.equal(await page.$eval('#commuter-map-status', el => el.textContent), payload.labels.tiles_failed);
            if (mode === 'map') {
              if (width < 900) {
                await openSheet(page);
                const height = await page.$eval('#commuter-page', el => el.clientHeight);
                await dragHandle(page, height);
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'expanded');
                const scroll = await page.$eval('#commuter-sheet-body', el => { el.scrollTop = 0; return { x: el.getBoundingClientRect().x + 30, y: el.getBoundingClientRect().y + 100 }; });
                await page.mouse.move(scroll.x, scroll.y); await page.mouse.wheel({ deltaY: 250 });
                await page.waitForFunction(() => document.querySelector('#commuter-sheet-body').scrollTop > 0);
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'expanded', 'content scrolling never drags sheet');
                await dragHandle(page, height * .52);
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half');
                await dragHandle(page, 58);
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'collapsed');
                await dragHandle(page, 0);
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'hidden');
                await page.focus('.sheet-reopen'); await page.keyboard.press('Enter');
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half');
                await page.focus('.sheet-handle'); await page.keyboard.press('ArrowUp');
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'expanded');
                await page.keyboard.press('Home');
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'hidden');
                const mapRect = await page.$eval('#commuter-map', el => { const r = el.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; });
                assert.equal(await page.$eval('#commuter-map', el => getComputedStyle(el).touchAction), 'none');
                assert.notEqual(await page.$eval('body', el => getComputedStyle(el).touchAction), 'none', 'gestures outside map are not blocked');
                const client = await page.createCDPSession();
                const zoom = await page.evaluate(() => window.__commuterMap.getZoom());
                await client.send('Input.synthesizePinchGesture', { x: mapRect.x, y: mapRect.y, scaleFactor: 2, relativeSpeed: 400, gestureSourceType: 'touch' });
                await page.waitForFunction(zoom => window.__commuterMap.getZoom() > zoom, { timeout: 3000 }, zoom);
                const center = await page.evaluate(() => window.__commuterMap.getCenter().lng);
                await client.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: mapRect.x, y: mapRect.y, id: 1 }] });
                for (let step = 1; step <= 10; step++) {
                  await client.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: mapRect.x - step * 7, y: mapRect.y, id: 1 }] });
                  await page.evaluate(() => new Promise(requestAnimationFrame));
                }
                await client.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
                await page.waitForFunction(lng => Math.abs(window.__commuterMap.getCenter().lng - lng) > .00001, { timeout: 3000 }, center).catch(async error => { throw new Error(`${lang}/${width}: touch drag; ${JSON.stringify(await page.evaluate(() => ({ touch: L.Browser.touch, pointer: L.Browser.pointer, dragging: window.__commuterMap.dragging.enabled(), center: window.__commuterMap.getCenter() })))} ${error.message}`); });
                await client.detach();
                await page.click('.sheet-reopen');
              }
              await page.setViewport({ width, height: 600, isMobile: width < 900, hasTouch: width < 900 });
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
    console.log('Commuter exact-artifact: 3 locales x 4 widths x 7 modes passed (actual Leaflet; source marker subsets, show-all/reset, centered 44px targets, handle drag/scroll/keyboard, hidden/reopen, native CDP touch pinch/drag, visual local boundaries, route fit, fares, primary sourced directions, partial/missing geometry).');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
