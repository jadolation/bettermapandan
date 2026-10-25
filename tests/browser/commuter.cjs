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
const smoke = process.argv.includes('--smoke');
const layoutOnly = process.argv.includes('--layout-only');
const invalidOnly = process.argv.includes('--invalid-only');
const localeIndex = process.argv.indexOf('--locale');
const selectedLocale = localeIndex >= 0 ? process.argv[localeIndex + 1] : null;
assert.ok(!selectedLocale || ['en', 'fil', 'pag'].includes(selectedLocale));
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
    const left = innerWidth >= 900 ? sheet.right : map.left;
    const bottom = innerWidth >= 900 ? map.bottom - 40 : sheet.top;
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
  await sizeSheet(page, 'half');
}
async function sizeSheet(page, state) {
  await page.$eval('.sheet-size-disclosure', el => { el.open = true; });
  await page.click(`.sheet-sizes [data-sheet-state="${state}"]`);
  await page.waitForFunction(state => document.querySelector('#commuter-sheet').dataset.state === state, {}, state);
  await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 230)));
}
async function exploreSheet(page) {
  await page.click('.sheet-explore');
  await openSheet(page);
}
async function dragHandle(page, height) {
  const rect = await page.$eval('.sheet-handle', el => { const r = el.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; });
  const current = await page.$eval('#commuter-sheet', el => el.getBoundingClientRect().height);
  await page.mouse.move(rect.x, rect.y);
  await page.mouse.down();
  await page.mouse.move(rect.x, rect.y + current - height, { steps: 12 });
  await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 130)));
  await page.mouse.up();
}
async function assertHeaderDragging(page) {
  async function gesture(delta, slow, selector = '#commuter-sheet-title') {
    const p = await page.$eval(selector, el => { const r = el.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; });
    await page.mouse.move(p.x, p.y); await page.mouse.down();
    await page.mouse.move(p.x, p.y + delta, { steps: slow ? 12 : 2 });
    if (slow) await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 140)));
    await page.mouse.up();
    await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 230)));
  }
  await sizeSheet(page, 'half');
  await gesture(-40, false);
  assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'expanded', 'fast title fling advances upward');
  await gesture(40, false);
  assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half', 'fast title fling advances downward');
  await gesture(-20, true);
  assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half', 'slow short title drag uses nearest stop');
  await gesture(20, true, '.sheet-handle');
  assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half', 'indicator uses same slow snap');
  const p = await page.$eval('#commuter-sheet-title', el => { const r = el.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; });
  const client = await page.createCDPSession();
  await client.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ ...p, id: 1 }] });
  await client.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: p.x, y: p.y - 45, id: 1 }] });
  await client.send('Input.dispatchTouchEvent', { type: 'touchCancel', touchPoints: [] });
  assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half', 'native touch cancel restores logical stop');
  assert.equal(await page.$eval('#commuter-sheet', el => el.style.height), '');
  await client.detach();
  await page.mouse.move(p.x, p.y); await page.mouse.down(); await page.mouse.move(p.x, p.y - 40);
  await page.$eval('.sheet-toolbar', el => {
    // Native capture was established by the mouse; release exercises lostcapture cleanup.
    for (let id = 1; id < 20; id++) if (el.hasPointerCapture(id)) el.releasePointerCapture(id);
  });
  await page.mouse.up();
  assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half');
  assert.equal(await page.$eval('#commuter-sheet', el => el.style.height), '');
  await page.focus('.sheet-handle'); await page.keyboard.press('End');
  assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'expanded');
  await page.keyboard.press('Home');
  assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'collapsed');
  await page.keyboard.press('ArrowDown');
  assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'collapsed', 'keyboard cannot hide panel');
  await page.keyboard.press('ArrowUp');
}
async function assertZoomGestures(page, mobile) {
  const runtime = await page.evaluate(() => ({ version: L.version, touch: L.Browser.touch, pointer: L.Browser.pointer, safari: L.Browser.safari,
    viewport: document.querySelector('meta[name="viewport"]').content }));
  assert.equal(runtime.version, '1.9.4');
  assert.ok(!/user-scalable\s*=\s*no|maximum-scale/i.test(runtime.viewport));
  console.log('Gesture runtime:', JSON.stringify(runtime));
  const point = await page.$eval('#commuter-map', el => {
    const r = el.getBoundingClientRect();
    const header = document.querySelector('.commuter-hero').getBoundingClientRect();
    const sheet = document.querySelector('#commuter-sheet').getBoundingClientRect();
    return { x: r.right - Math.min(160, r.width / 2), y: innerWidth < 900 ? (header.bottom + sheet.top) / 2 : r.top + r.height * .5 };
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
  if (!mobile) {
    for (const direction of [1, -1]) {
      const before = await page.evaluate(() => window.__commuterMap.getZoom());
      await client.send('Input.dispatchMouseEvent', { type: 'mouseWheel', x: point.x, y: point.y, deltaX: 0, deltaY: -direction * 5 });
      await page.waitForFunction(({ before, direction }) => (window.__commuterMap.getZoom() - before) * direction > 0, {}, { before, direction });
      await page.waitForFunction(() => !window.__commuterMap._animatingZoom);
      const delta = await page.evaluate(before => Math.abs(window.__commuterMap.getZoom() - before), before);
      assert.ok(delta > 0 && delta <= .5, 'gentle fractional wheel keeps quarter-step settling');
    }
  }
  assert.deepEqual(await page.evaluate(() => {
    const options = window.__commuterMap.options;
    return [options.zoomSnap, options.zoomDelta, options.wheelPxPerZoomLevel, options.wheelDebounceTime];
  }), [.25, 1, 60, 40], 'only snap spacing changes; button and wheel tuning retain Leaflet defaults');
  for (const direction of [1, -1]) {
    const before = await page.evaluate(() => window.__commuterMap.getZoom());
    await page.click(direction > 0 ? '.leaflet-control-zoom-in' : '.leaflet-control-zoom-out');
    await page.waitForFunction(target => window.__commuterMap.getZoom() === target, {}, before + direction);
    await page.waitForFunction(() => !window.__commuterMap._animatingZoom);
    assert.equal(await page.evaluate(() => window.__commuterMap.getZoom()), before + direction, 'zoom buttons still move exactly one level');
  }
  const beforePan = await page.evaluate(() => window.__commuterMap.getCenter().lng);
  if (mobile) {
    await client.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ ...point, id: 1 }] });
    for (let step = 1; step <= 8; step++) {
      await client.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: point.x + step * 4, y: point.y, id: 1 }] });
      await page.evaluate(() => new Promise(requestAnimationFrame));
    }
    await client.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  } else {
    await page.mouse.move(point.x, point.y); await page.mouse.down();
    await page.mouse.move(point.x + 40, point.y, { steps: 8 }); await page.mouse.up();
  }
  await page.waitForFunction(lng => Math.abs(window.__commuterMap.getCenter().lng - lng) > .000001, {}, beforePan);
  assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half', 'native map pan works with details half-open');
  await client.detach();
}
async function assertExternalTabs(browser, page) {
  const session = await browser.target().createCDPSession();
  const requests = [];
  session.on('Target.attachedToTarget', async ({ sessionId }) => {
    const child = session.connection().session(sessionId);
    await child.send('Fetch.enable', { patterns: [{ urlPattern: 'https://www.google.com/*' }] });
    child.on('Fetch.requestPaused', async event => {
      if (event.resourceType === 'Document') {
        requests.push(event.request.url);
        assert.ok(!Object.keys(event.request.headers).some(key => key.toLowerCase() === 'referer'), 'noreferrer prevents sharing the source page');
      }
      await child.send('Fetch.fulfillRequest', { requestId: event.requestId, responseCode: 200,
        responseHeaders: [{ name: 'Content-Type', value: 'text/html' }],
        body: Buffer.from('<title>Intercepted Google Maps navigation</title><link rel="icon" href="data:,">').toString('base64') });
    });
    await child.send('Runtime.runIfWaitingForDebugger');
  });
  await session.send('Target.setAutoAttach', { autoAttach: true, waitForDebuggerOnStart: true, flatten: true, filter: [{ type: 'page', exclude: false }] });
  try {
    const before = await page.evaluate(() => ({ route: document.querySelector('#commuter-page').dataset.activeRouteId,
      station: document.querySelector('#commuter-page').dataset.selectionId, zoom: window.__commuterMap.getZoom(),
      bounds: window.__commuterMap.getBounds().toBBoxString(), state: document.querySelector('#commuter-sheet').dataset.state }));
    for (const index of [0, 1]) {
      const href = await page.$$eval('.station-actions a', (els, index) => els[index].href, index);
      const popupReady = browser.waitForTarget(target => target.opener() === page.target() && target.url() === href);
      await page.$$eval('.station-actions a', (els, index) => els[index].click(), index);
      const popup = await (await popupReady).page();
      await popup.waitForFunction(() => document.title === 'Intercepted Google Maps navigation');
      assert.equal(await popup.evaluate(() => window.opener), null);
      assert.equal(requests.at(-1), href);
      await popup.close();
      assert.deepEqual(await page.evaluate(() => ({ route: document.querySelector('#commuter-page').dataset.activeRouteId,
        station: document.querySelector('#commuter-page').dataset.selectionId, zoom: window.__commuterMap.getZoom(),
        bounds: window.__commuterMap.getBounds().toBBoxString(), state: document.querySelector('#commuter-sheet').dataset.state })), before);
    }
    assert.equal(requests.length, 2, 'only explicit anchor clicks navigate to Google; both are intercepted');
  } finally {
    await session.send('Target.setAutoAttach', { autoAttach: false, waitForDebuggerOnStart: false, flatten: true });
    await session.detach();
  }
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
     for (const lang of smoke ? ['en'] : selectedLocale ? [selectedLocale] : ['en', 'fil', 'pag']) {
       for (const width of smoke ? [320, 1440] : [320, 375, 430, 1440]) {
          for (const mode of invalidOnly ? ['invalid-points'] : smoke || layoutOnly ? ['map'] : ['map', 'cdn-failure', 'no-js', 'tile-failure', 'shape-fixture', 'partial-shapes', 'no-shapes', 'invalid-points']) {
           console.log(`Commuter case: ${lang}/${width}/${mode}`);
          const page = await browser.newPage();
          if (lang === 'pag' && width === 430 && mode === 'map') await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
          const errors = [];
          let tileRequests = 0;
           page.on('pageerror', error => errors.push(error.message));
          await page.setViewport({ width, height: 900, isMobile: width < 900, hasTouch: width < 900 });
          if (mode === 'no-js') await page.setJavaScriptEnabled(false);
           await page.setRequestInterception(true);
           let googleRequests = 0;
            page.on('request', async req => {
             if (new URL(req.url()).hostname === 'www.google.com') { googleRequests++; return req.abort(); }
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
              if (['shape-fixture', 'partial-shapes', 'no-shapes', 'invalid-points'].includes(mode) && new URL(req.url()).pathname.endsWith('/commuter/')) {
                const localeRoot = lang === 'en' ? '' : lang;
                let html = fs.readFileSync(path.join(root, localeRoot, 'commuter/index.html'), 'utf8');
                html = html.replace(/(<script id="commuter-data" type="application\/json">)([\s\S]*?)(<\/script>)/, (_, start, raw, end) => {
                   const payload = JSON.parse(raw);
                   if (mode === 'invalid-points') {
                     const geometries = [null, { type: 'LineString', coordinates: [1, 2] }, { type: 'Point', coordinates: [] }, { type: 'Point', coordinates: ['120', 16] }, { type: 'Point', coordinates: [true, 16] }, { type: 'Point', coordinates: [120, 91] }, { type: 'Point', coordinates: [120, 16, 0] }];
                      payload.features.forEach((feature, index) => { feature.geometry = geometries[index]; });
                      payload.features[0].properties.catalog_route_ids = [];
                   }
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
           if (mode === 'invalid-points') {
             await page.waitForSelector('#commuter-page[data-ready="true"]');
             const labels = await page.$eval('#commuter-data', el => JSON.parse(el.textContent).labels);
             for (let index = 0; index < 7; index++) {
               await exploreSheet(page);
               await page.$eval('.commuter-directory', el => { el.open = true; });
               await page.$$eval('.transport-select', (els, index) => els[index].click(), index);
               assert.equal(await page.$$eval('.station-actions a', els => els.length), 0);
               assert.ok((await page.$eval('#commuter-info-body', el => el.textContent)).includes(labels.location_unavailable));
                assert.equal(await page.$$eval('.transport-marker.selected', els => els.length), 0);
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half');
                if (index === 0) {
                  assert.equal(await page.$$eval('[data-associated-route]', els => els.length), 0);
                  assert.ok((await page.$eval('#commuter-info-body', el => el.innerText)).includes(labels.no_routes));
                }
             }
             assert.deepEqual(errors, []);
             assert.equal(googleRequests, 0);
             await page.close();
             continue;
           }
           assert.equal(await page.$$eval('main', els => els.length), 1);
           assert.equal(await page.$$eval('footer, .mobile-action-bar', els => els.length), 0);
          assert.equal(await page.$$eval('.transport-card', els => els.length), 7);
             assert.equal(await page.$$eval('#commuter-lines > button', els => els.length), catalog.length);
             assert.equal(await page.$$eval('#commuter-lines button button, #commuter-lines button details, .sheet-back', els => els.length), 0);
           assert.equal(await page.$$eval('[data-route="manaoag-sm-minibus"]', els => els.length), 0);
           assert.equal(await page.$$eval('[data-route="mapandan-manaoag-sm-multileg"]', els => els.length), 1);
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${lang} ${width} ${mode}: overflow`);
          assert.equal(await page.$eval('#commuter-page', el => /\{C_|\{COMMUTER_/.test(el.textContent)), false);
           if (mode === 'no-js') {
            assert.equal(await page.$eval('#commuter-sheet-body', el => el.hidden), false);
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 0);
            assert.match(await page.$eval('#transport-list', el => el.textContent), /PHP 35-40/);
           } else if (mode === 'cdn-failure') {
             await page.waitForSelector('#commuter-page[data-ready="true"]');
                 await exploreSheet(page);
             await page.click('.route-select');
             assert.equal(await page.$eval('#commuter-page', el => el.dataset.view), 'route');
             assert.match(await page.$eval('#commuter-info-body', el => el.textContent), /PHP/);
             await exploreSheet(page);
             await page.$eval('.commuter-directory', el => { el.open = true; });
             await page.click('.transport-select');
             assert.equal(await page.$eval('#commuter-page', el => el.dataset.view), 'station');
             assert.equal(await page.$$eval('.transport-marker', els => els.length), 0);
           } else {
            await page.waitForSelector('#commuter-page[data-ready="true"]').catch(error => { throw new Error(`${lang}/${width}/${mode}: ${errors.join('; ')} ${error.message}`); });
             assert.equal(await page.evaluate(() => L.version), '1.9.4');
             assert.ok(await page.evaluate(() => Math.abs(document.querySelector('#commuter-page').getBoundingClientRect().bottom - innerHeight) < 2 && parseFloat(getComputedStyle(document.body).paddingBottom) === 0), 'workspace fills viewport without a reserved footer gap');
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
             assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half');
             if (width < 900) assert.ok(await page.evaluate(() => {
               const ratio = document.querySelector('#commuter-sheet').getBoundingClientRect().height / document.querySelector('#commuter-page').getBoundingClientRect().height;
               return ratio > .58 && ratio < .62;
             }), 'initial sheet occupies 60% of workspace');
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
             assert.equal(await page.$$eval('.candidate-toggle', els => els.length), 0, 'multi-select removed explicitly');
             assert.equal(await page.$$eval('.route-select', els => els.length), payload.catalog.length);
             assert.deepEqual(await page.$$eval('[data-sheet-state]', els => els.map(el => el.dataset.sheetState)), ['collapsed', 'half', 'expanded'], 'exactly three stops, no hidden state');
             assert.equal(await page.$$eval('.sheet-reopen', els => els.length), 0);
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
               await sizeSheet(page, state);
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
              const count = route.directions[0].filter(id => shapeIds.has(id)).length;
              if (route.id === 'mapandan-manaoag-sm-multileg') {
                assert.deepEqual(route.directions, [['mini-mapandan-manaoag', 'mini-manaoag-sm']]);
                assert.equal(route.transfer_count, 1);
                if (mode === 'map') assert.equal(count, 2);
              }
                assert.equal(await page.$eval(selector, el => el.tagName), 'BUTTON', 'whole card is one native button');
               await exploreSheet(page);
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
                if (route === payload.catalog[0]) {
                  await page.focus(selector); await page.keyboard.press('Enter');
                } else await page.click(selector);
               await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 250)));
               paths = count;
               assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), paths);
               const expectedMarkers = [...new Set(route.marker_ids)].sort();
               assert.deepEqual(await page.$$eval('.transport-marker', els => els.map(el => el.dataset.id).sort()), expectedMarkers, 'only explicit selected-route source observations');
               assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half', 'route selection opens persistent details');
                assert.equal(await page.$eval('#commuter-page', el => el.dataset.selectionKind), 'route');
                assert.equal(await page.$eval('#commuter-page', el => el.dataset.activeRouteId), route.id, 'another route replaces active context');
               assert.equal(await page.$eval('#commuter-info-title', el => el === document.activeElement), true);
               assert.equal(await page.$eval('#commuter-sheet-title', el => el.textContent), payload.labels[route.id]);
               assert.equal(await page.$$eval('.route-select[aria-pressed="true"]', els => els.length), 1);
               assert.equal(await page.$$eval('.transport-marker.selected', els => els.length), 0);
               await assertCurrentLineFits(page, count);
               assert.ok(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.every(el => el.getAttribute('stroke-dasharray') === '10 7')));
               const compact = await page.$eval('#commuter-info-body', el => Array.from(el.children).filter(el => el.tagName !== 'DETAILS').map(el => el.textContent).join(' '));
               assert.ok(compact.includes(payload.labels.waiting_unknown));
               for (const id of [route.origin_id, route.destination_id]) {
                 if (payload.place_names[id]) assert.ok(compact.includes(payload.labels[id] || payload.place_names[id]), 'existing nonspatial endpoint name is not a fabricated location');
               }
                  assert.equal(await page.$$eval('#commuter-info-body details[open]', els => els.length), 0, 'all directions and sources initially closed');
                 assert.equal(await page.$$eval('.direction-leg', els => els.length), route.legs.length);
                 assert.equal(await page.$$eval('.direction-transfer', els => els.length), route.legs.length - 1);
                 assert.equal(await page.$$eval('.direction-step', els => els.length), route.directions[0].reduce((sum, p) => sum + payload.direction_steps[p].steps.length, 0));
                   assert.equal(await page.$eval('.route-sources', el => el.open), false);
                   assert.ok(await page.$$eval('.route-sources details', els => els.length >= 2), 'restored fare and driving disclosures');
                   const overview = await page.$eval('.journey-summary', el => el.innerText);
                   const summaryLayout = await page.$eval('.journey-summary', el => ({
                     display: getComputedStyle(el).display,
                     width: el.getBoundingClientRect().width,
                     children: Array.from(el.children).map(child => ({ width: child.getBoundingClientRect().width, display: getComputedStyle(child).display, wrap: getComputedStyle(child).overflowWrap, wordBreak: getComputedStyle(child).wordBreak, text: child.innerText }))
                   }));
                   assert.ok(summaryLayout.children.every(child => child.width >= summaryLayout.width * .8), 'summary rows use full width: ' + JSON.stringify(summaryLayout));
                   assert.ok(summaryLayout.children.every(child => child.wrap === 'normal' && child.wordBreak === 'normal'), 'labels wrap at words rather than narrow character columns');
                   assert.ok(await page.$eval('.journey-summary', el => {
                     const rows = Array.from(el.children).map(child => child.getBoundingClientRect());
                     return rows.every((rect, index) => !index || rect.top >= rows[index - 1].bottom);
                   }), 'summary facts stack vertically, never in parallel lanes');
                   assert.ok(await page.$eval('.journey-summary > .summary-fact', el => {
                      const original = el.innerHTML;
                      el.textContent = Array(4).fill(el.textContent).join(' / ');
                     const range = document.createRange(); range.selectNodeContents(el);
                     const lines = Array.from(range.getClientRects()), box = el.getBoundingClientRect();
                     const readable = lines.length > 1 && Math.max(...lines.map(rect => rect.width)) >= box.width * .8 && lines.every(rect => rect.right <= box.right + 1);
                      el.innerHTML = original;
                     return readable;
                   }), 'long localized endpoint names wrap into full-width readable lines');
                   assert.ok(await page.$$eval('.direction-leg', els => els.every(el => el.getBoundingClientRect().width >= el.parentElement.getBoundingClientRect().width * .8)), 'each vehicle leg occupies a full-width section');
                  for (const technical of ['maintainer_', 'unverified', ...route.directions[0]]) assert.ok(!overview.includes(technical), 'summary has no raw source identifiers');
                  await page.focus('.leg-select'); await page.keyboard.press('Enter');
                  assert.equal(await page.$$eval('.route-directions[open]', els => els.length), 1, 'direct keyboard leg selection opens only that leg');
                  assert.equal(await page.$eval('#commuter-page', el => el.dataset.activeRouteId), route.id, 'leg selection retains journey');
                  assert.equal(await page.$eval('#commuter-page', el => el.dataset.selectionId), route.id);
                  if (mode === 'map') {
                    const style = await page.$$eval('#commuter-map path.leaflet-interactive', els => els.map(el => ({ opacity: Number(el.getAttribute('stroke-opacity')), weight: Number(el.getAttribute('stroke-width')) })));
                    if (count) assert.ok(style.some(item => item.opacity === 1 && item.weight === 7) || !payload.shapes.some(shape => shape.properties.pattern_id === route.directions[0][0]));
                    if (count > 1) assert.ok(style.some(item => item.opacity === .25 && item.weight === 3), 'other existing leg geometry is dimmed');
                    assert.equal(style.length, count, 'leg focus retains all journey geometry');
                  }
                  await page.focus('.route-directions summary'); await page.keyboard.press('Enter');
                  assert.equal(await page.$$eval('.route-directions[open]', els => els.length), 0, 'keyboard disclosure closes selected leg');
                  assert.ok(!(await page.$eval('#commuter-info-body', el => el.innerText)).includes('undefined'));
                  for (const pattern of route.directions[0]) {
                    await page.$eval(`.direction-leg[data-pattern="${pattern}"] .route-directions`, el => { el.open = true; });
                    const source = payload.direction_steps[pattern];
                    for (const note of source.notes) assert.ok((await page.$eval(`.direction-leg[data-pattern="${pattern}"] .route-directions`, el => el.innerText)).includes(payload.labels[note]));
                   const point = source.steps.find(step => step.waypoint);
                   if (point) assert.ok(!(await page.$eval('#commuter-info-body', el => el.innerText)).includes(String(point.waypoint[1])), 'raw coordinates stay in collapsed sources');
                 }
                 if (process.argv.includes('--screenshots') && lang === 'en' && mode === 'map' && ['mapandan-calasiao-multileg', 'mapandan-manaoag-sm-multileg'].includes(route.id)) {
                   await page.screenshot({ path: `/tmp/kilo/directions-${width}-${route.id}.png` });
                 }
                 if (mode === 'map') {
                   const routeView = await page.evaluate(() => ({ center: window.__commuterMap.getCenter(), zoom: window.__commuterMap.getZoom() }));
                   for (const pattern of route.directions[0]) {
                     const source = payload.direction_steps[pattern];
                     for (const step of source.steps) {
                       const selector = `.direction-leg[data-pattern="${pattern}"] .direction-step:nth-child(${step.sequence})`;
                       if (!step.waypoint) {
                         assert.equal(await page.$$eval(selector + ' button', els => els.length), 0);
                         assert.ok((await page.$eval(selector, el => el.textContent)).includes(payload.labels.location_not_mapped));
                         continue;
                       }
                       const button = selector + ' button';
                       await page.$eval(button, el => {
                         const panel = document.querySelector('#commuter-sheet-body');
                          const summary = document.querySelector('.journey-summary').getBoundingClientRect();
                          panel.scrollTop += el.getBoundingClientRect().top - panel.getBoundingClientRect().top - Math.max(panel.clientHeight / 2, summary.height + 8);
                       });
                       const before = await page.$eval('#commuter-sheet-body', el => el.scrollTop);
                       const zoom = await page.evaluate(() => window.__commuterMap.getZoom());
                       await page.click(button);
                       assert.equal(await page.$eval('#commuter-sheet-body', el => el.scrollTop), before, 'step focus does not reset panel scroll');
                       assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half');
                       assert.equal(await page.$eval('#commuter-page', el => el.dataset.activeRouteId), route.id);
                       assert.equal(await page.evaluate(() => window.__commuterMap.getZoom()), zoom, 'step click does not refit entire route');
                       assert.equal(await page.$$eval('.direction-waypoint', els => els.length), 1);
                       assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), count, 'no invented connector or segment');
                       assert.ok(await page.$eval('.direction-waypoint', el => {
                         const p = el.getBoundingClientRect(), map = document.querySelector('#commuter-map').getBoundingClientRect();
                         const sheet = document.querySelector('#commuter-sheet').getBoundingClientRect(), header = document.querySelector('.commuter-hero').getBoundingClientRect();
                         return p.left >= (innerWidth >= 900 ? sheet.right : map.left) && p.right <= map.right && p.top >= header.bottom && p.bottom <= (innerWidth >= 900 ? map.bottom : sheet.top);
                       }), 'reported waypoint is visible above/beside panel');
                       if (process.argv.includes('--screenshots') && lang === 'en' && pattern === route.directions[0][0] && step === source.steps.find(s => s.waypoint)) {
                         await page.screenshot({ path: `/tmp/kilo/directions-${width}-${route.id}-timeline.png` });
                       }
                     }
                   }
                   // Return to the pre-step route view for the independent polyline/gesture regressions below.
                   await page.evaluate(view => window.__commuterMap.setView(view.center, view.zoom, { animate: false }), routeView);
                 }
                  await page.$eval('.route-sources', el => { el.open = true; });
                  const breakdown = await page.$eval('.route-sources', el => el.textContent);
                for (const leg of route.legs) assert.ok(breakdown.includes(leg.fare.amount ? `PHP ${leg.fare.amount.min}-${leg.fare.amount.max}` : payload.labels.unknown_fare));
                if (expectedMarkers.length) {
                  await page.focus(`.transport-marker[data-id="${expectedMarkers[0]}"]`);
                  await page.keyboard.press('Enter');
                  assert.equal(await page.$eval('#commuter-page', el => el.dataset.activeRouteId), route.id);
                   assert.equal(await page.$eval('#commuter-page', el => el.dataset.focusedFeature), 'station');
                   assert.equal(await page.$$eval('.direction-step, .ride-cards', els => els.length), 0, 'station view has no journey timeline');
                  assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), count);
                  assert.deepEqual(await page.$$eval('.transport-marker', els => els.map(el => el.dataset.id).sort()), expectedMarkers);
                  const visible = await page.$eval('#commuter-info-body', el => el.innerText);
                  const feature = payload.features.concat(payload.observations).find(f => f.properties.id === expectedMarkers[0]);
                  assert.ok(!visible.includes(String(feature.geometry.coordinates[1])));
                  assert.ok(!visible.includes(feature.properties.source_type));
                  assert.equal(await page.$$eval('#commuter-info-body details[open]', els => els.length), 0);
                  await page.click('#commuter-info-body details summary');
                  assert.ok((await page.$eval('#commuter-info-body', el => el.innerText)).includes(String(feature.geometry.coordinates[1])));
                  await page.click('[data-associated-route="' + route.id + '"]');
                }
               await page.click('.sheet-close');
               assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'collapsed');
               assert.equal(await page.$eval('#commuter-page', el => el.dataset.selectionId), route.id);
               await page.focus('.sheet-handle'); await page.keyboard.press('ArrowUp');
               assert.equal(await page.$eval('#commuter-page', el => el.dataset.view), 'route');
                await page.click('.sheet-explore');
               await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 250)));
                assert.equal(await page.$eval('#commuter-page', el => el.dataset.activeRouteId), route.id, 'Explore preserves route context');
               if (count) {
                  const point = await page.$$eval('#commuter-map path.leaflet-interactive', paths => {
                    for (const el of paths) {
                    for (let d = 0; d < el.getTotalLength(); d += .5) {
                     const p = el.getPointAtLength(d).matrixTransform(el.getScreenCTM());
                      const x = Math.round(p.x), y = Math.round(p.y);
                      if (document.elementFromPoint(x, y) === el) return { x, y };
                    }
                    }
                     throw new Error('Selected route has no reachable painted point: ' + JSON.stringify({ route: document.querySelector('#commuter-page').dataset.activeRouteId, center: window.__commuterMap.getCenter(), zoom: window.__commuterMap.getZoom(), map: document.querySelector('#commuter-map').getBoundingClientRect(), sheet: document.querySelector('#commuter-sheet').getBoundingClientRect(), paths: paths.map(el => el.getBoundingClientRect().toJSON()) }));
                 });
                 await page.mouse.click(point.x, point.y);
                 assert.equal(await page.$eval('#commuter-page', el => el.dataset.view), 'route', 'polyline selection shares transition');
               }
             }
             if (mode === 'map') {
               await openSheet(page);
              await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
              await assertZoomGestures(page, width < 900);
            }
            await openSheet(page);
             for (const state of ['expanded', 'collapsed', 'half']) {
                await sizeSheet(page, state);
                if (state !== 'collapsed') assert.ok(await page.$$eval('.journey-summary > p', els => els.every(el => el.getBoundingClientRect().width >= el.parentElement.getBoundingClientRect().width * .8)), 'summary remains full width at each visible sheet stop');
              await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
              await assertCurrentLineFits(page, paths);
            }
             await exploreSheet(page);
            await page.focus('#commuter-reset');
            await page.keyboard.press('Enter');
             assert.equal(await page.$eval('#commuter-page', el => el.dataset.selectionKind), 'none');
            assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), 0);
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 0);
            await page.focus('#commuter-show-all'); await page.keyboard.press('Space');
             for (const feature of payload.features.concat(payload.observations)) {
              const selector = `.transport-marker[data-id="${feature.properties.id}"]`;
              await page.focus(selector);
              await page.keyboard.press('Enter');
               await page.waitForFunction(name => document.querySelector('#commuter-info-title').textContent.endsWith(name), { timeout: 3000 }, payload.labels[feature.properties.id]);
              assert.notEqual(await page.$eval('#commuter-sheet', el => el.dataset.state), 'collapsed');
               const info = await page.$eval('#commuter-info-body', el => el.textContent);
               const links = await page.$$eval('.station-actions a', els => els.map(el => ({ href: el.href, target: el.target, rel: el.rel, width: el.getBoundingClientRect().width, parentWidth: el.parentElement.getBoundingClientRect().width, height: el.getBoundingClientRect().height, text: el.textContent })));
               const coordinate = [feature.geometry.coordinates[1], feature.geometry.coordinates[0]].join(',');
               assert.deepEqual(links.map(link => link.href), [
                 'https://www.google.com/maps/search/?' + new URLSearchParams({ api: '1', query: coordinate }),
                 'https://www.google.com/maps/dir/?' + new URLSearchParams({ api: '1', destination: coordinate, travelmode: 'walking' })
               ]);
               assert.ok(links.every(link => link.target === '_blank' && link.rel === 'noopener noreferrer' && link.height >= 44 && link.width > 200 && Math.abs(link.width - link.parentWidth) < 1 && link.text.length));
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half');
                assert.equal(await page.$eval('#commuter-sheet-title', el => el.textContent), payload.labels.station_details);
                assert.equal(await page.$eval('#commuter-info-title', el => el.textContent), payload.labels[feature.properties.id]);
                for (const state of mode === 'map' && feature === payload.features[0] ? ['expanded', 'collapsed', 'half'] : []) {
                  await sizeSheet(page, state);
                  assert.equal(await page.evaluate(title => {
                    return ['#commuter-sheet-title', '#commuter-info-title'].filter(selector => {
                      const el = document.querySelector(selector);
                      return el.checkVisibility() && el.textContent === title;
                    }).length;
                  }, payload.labels[feature.properties.id]), 1, 'selected station title is visible exactly once at every stop');
                }
                 assert.equal(await page.$$eval('.station-detail-caveat', els => els.length), 1);
                 assert.ok(await page.$eval('.station-detail-caveat', (el, notice) => el.innerText.trim() === notice, payload.labels.unconfirmed_stops));
                 assert.equal(await page.$$eval('#commuter-info-body details', els => els.length), 1);
                 assert.equal(await page.$eval('.station-source-details', el => el.open), false);
                assert.ok(await page.$eval('#commuter-info-body', (el, props) => {
                  const visible = el.innerText;
                  const title = document.querySelector('#commuter-info-title').textContent;
                  const description = props.location_description || (props.name !== title ? props.name : '');
                  return visible.includes(description) && !visible.includes(props.id) && (!props.notes || !visible.includes(props.notes));
                 }, feature.properties), 'station public description excludes source-only fields: ' + JSON.stringify(await page.$eval('#commuter-info-body', el => el.innerText)));
                 assert.equal(await page.$$eval('.station-route-link', els => els.length), feature.properties.catalog_route_ids.length);
                 assert.ok(await page.$$eval('.station-route-link', els => els.every(el => {
                   const row = el.getBoundingClientRect(), parent = el.parentElement.getBoundingClientRect();
                   return row.width > 200 && Math.abs(row.width - parent.width) < 2 && el.textContent.trim().length > 0;
                 })));
                 await page.$eval('.station-source-details', el => { el.open = true; });
                 assert.ok((await page.$eval('.station-source-details', el => el.innerText)).includes(feature.properties.id));
                 await page.$eval('.station-source-details', el => { el.open = false; });
                assert.equal(googleRequests, 0, 'station selection never requests Google');
               await page.$eval('.station-actions a', el => { el.addEventListener('click', event => event.preventDefault(), { once: true }); el.click(); });
               assert.equal(await page.$eval('#commuter-page', el => el.dataset.selectionId), feature.properties.id, 'explicit external action leaves selection intact');
               for (const fare of feature.properties.fares) assert.ok(info.includes(`PHP ${fare.amount.min}-${fare.amount.max}`));
               assert.equal(await page.$$eval('#commuter-map path.leaflet-interactive', els => els.length), 0, 'station clears route geometry');
               assert.equal(await page.$$eval('.transport-marker.selected', els => els.length), 1);
               assert.deepEqual(await page.$$eval('[data-associated-route]', els => els.map(el => el.dataset.associatedRoute)), feature.properties.catalog_route_ids);
               if (!feature.properties.catalog_route_ids.length) assert.ok(info.includes(payload.labels.no_routes));
               if (feature.properties.observed_only) assert.ok(info.includes(payload.labels.observed_place));
               assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
             }
             await exploreSheet(page);
             await page.$eval('.commuter-directory', el => { el.open = true; });
             await page.click('.transport-select');
             const stationId = await page.$eval('#commuter-page', el => el.dataset.selectionId);
             const associated = await page.$('[data-associated-route]');
             assert.ok(associated);
             await associated.click();
             assert.equal(await page.$eval('#commuter-page', el => el.dataset.selectionKind), 'route');
              await page.focus(`.transport-marker[data-id="${stationId}"]`); await page.keyboard.press('Enter');
             assert.equal(await page.$eval('#commuter-page', el => el.dataset.view), 'station');
              assert.ok(await page.$eval('#commuter-page', el => !!el.dataset.activeRouteId));
             assert.equal(await page.$$eval('.transport-marker.selected', els => els.length), 1);
             await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 250)));
             const stationPoint = await page.$eval('.transport-marker.selected', el => {
               const r = el.getBoundingClientRect(), sheet = document.querySelector('#commuter-sheet').getBoundingClientRect();
               const hero = document.querySelector('.commuter-hero').getBoundingClientRect();
               return { x: r.x + r.width / 2, y: r.y + r.height / 2, visible: r.top >= hero.bottom && (innerWidth >= 900 ? r.left >= sheet.right : r.bottom <= sheet.top) };
             });
             assert.ok(stationPoint.visible, 'selected station fits unobscured map strip');
              await page.mouse.click(stationPoint.x, stationPoint.y);
              assert.equal(await page.$eval('#commuter-page', el => el.dataset.view), 'station', 'native marker click uses same station transition');
              if (process.argv.includes('--screenshots') && mode === 'map') await page.screenshot({ path: `/tmp/kilo/station-${lang}-${width}.png` });
              if (mode === 'map') await assertExternalTabs(browser, page);
              await exploreSheet(page);
              await page.click('#commuter-reset');
              await page.click('#commuter-show-all');
              await page.focus(`.transport-marker[data-id="${stationId}"]`); await page.keyboard.press('Enter');
              await exploreSheet(page);
             await page.select('#commuter-type', 'tricycle');
             assert.equal(await page.$$eval('.transport-marker', els => els.length), payload.features.concat(payload.observations).filter(f => f.properties.transport_type === 'tricycle').length);
            assert.equal(await page.$$eval('.transport-card:not([hidden])', els => els.length), 3);
            await page.focus('#commuter-search'); await page.type('#commuter-search', 'zzzzzz');
             assert.equal(await page.$$eval('.transport-marker', els => els.length), 0, 'chooser clears station focus and filters unselected markers');
            await page.focus('#commuter-reset'); await page.keyboard.press('Enter');
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 0);
            await page.$eval('.commuter-directory', el => { el.open = true; });
            await page.focus('.transport-select'); await page.keyboard.press('Enter');
             assert.equal(await page.$eval('#commuter-info-title', el => el === document.activeElement), true);
            assert.equal(await page.$$eval('.transport-marker', els => els.length), 1, 'directory selection works with no route or show-all');
             await sizeSheet(page, 'collapsed');
            assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'collapsed');
            assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
            if (mode === 'tile-failure') assert.equal(await page.$eval('#commuter-map-status', el => el.textContent), payload.labels.tiles_failed);
            if (mode === 'map') {
               if (width < 900) {
                 await assertHeaderDragging(page);
                 await exploreSheet(page);
                const height = await page.$eval('#commuter-page', el => el.clientHeight);
                await dragHandle(page, height);
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'expanded');
                const scroll = await page.$eval('#commuter-sheet-body', el => { el.scrollTop = 0; return { x: el.getBoundingClientRect().x + 30, y: el.getBoundingClientRect().y + 100 }; });
                await page.mouse.move(scroll.x, scroll.y); await page.mouse.wheel({ deltaY: 250 });
                await page.waitForFunction(() => document.querySelector('#commuter-sheet-body').scrollTop > 0);
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'expanded', 'content scrolling never drags sheet');
                 await dragHandle(page, height * .5);
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half');
                 await dragHandle(page, 96);
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'collapsed');
                 await dragHandle(page, 0);
                 assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'collapsed', 'cannot drag to hidden state');
                 await page.focus('.sheet-handle'); await page.keyboard.press('ArrowUp');
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half');
                await page.focus('.sheet-handle'); await page.keyboard.press('ArrowUp');
                assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'expanded');
                await page.keyboard.press('Home');
                 assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'collapsed');
                const mapRect = await page.$eval('#commuter-map', el => { const r = el.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; });
                assert.equal(await page.$eval('#commuter-map', el => getComputedStyle(el).touchAction), 'none');
                assert.notEqual(await page.$eval('body', el => getComputedStyle(el).touchAction), 'none', 'gestures outside map are not blocked');
                const client = await page.createCDPSession();
                const zoom = await page.evaluate(() => window.__commuterMap.getZoom());
                await client.send('Input.synthesizePinchGesture', { x: mapRect.x, y: mapRect.y, scaleFactor: 2, relativeSpeed: 400, gestureSourceType: 'touch' });
                 await page.waitForFunction(zoom => window.__commuterMap.getZoom() > zoom, { timeout: 3000 }, zoom);
                 await page.waitForFunction(() => !window.__commuterMap._animatingZoom && !window.__commuterMap.touchZoom._zooming);
                 await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 150)));
                const center = await page.evaluate(() => window.__commuterMap.getCenter().lng);
                await client.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: mapRect.x, y: mapRect.y, id: 1 }] });
                for (let step = 1; step <= 10; step++) {
                  await client.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: mapRect.x - step * 7, y: mapRect.y, id: 1 }] });
                  await page.evaluate(() => new Promise(requestAnimationFrame));
                }
                await client.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
                await page.waitForFunction(lng => Math.abs(window.__commuterMap.getCenter().lng - lng) > .00001, { timeout: 3000 }, center).catch(async error => { throw new Error(`${lang}/${width}: touch drag; ${JSON.stringify(await page.evaluate(() => ({ touch: L.Browser.touch, pointer: L.Browser.pointer, dragging: window.__commuterMap.dragging.enabled(), center: window.__commuterMap.getCenter() })))} ${error.message}`); });
                await client.detach();
                 await openSheet(page);
              }
               await page.setViewport({ width, height: 600, isMobile: width < 900, hasTouch: width < 900 });
              await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
              assert.ok(await page.evaluate(() => document.querySelector('#commuter-page').getBoundingClientRect().bottom <= visualViewport.height + 1), 'dynamic viewport resize remains within available viewport');
               await sizeSheet(page, 'expanded');
              await page.evaluate(() => new Promise(requestAnimationFrame));
               assert.ok(await page.evaluate(() => {
                const p = document.querySelector('#commuter-sheet').getBoundingClientRect();
                return p.bottom <= innerHeight + 1 && p.height > 44;
               }));
               const selected = await page.$eval('#commuter-page', el => [el.dataset.selectionKind, el.dataset.selectionId]);
               const zoom = await page.evaluate(() => window.__commuterMap.getZoom());
               await page.setViewport({ width: width < 900 ? 600 : width, height: 360, isMobile: width < 900, hasTouch: width < 900 });
               await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 240)));
               assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'expanded', 'logical stop survives short landscape/keyboard-like viewport');
               assert.deepEqual(await page.$eval('#commuter-page', el => [el.dataset.selectionKind, el.dataset.selectionId]), selected);
               assert.equal(await page.evaluate(() => window.__commuterMap.getZoom()), zoom, 'short viewport does not refit zoom');
               assert.ok(await page.$eval('.sheet-toolbar', el => { const r = el.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight + 1; }), 'header remains accessible in short viewport');
            }
          }
          assert.deepEqual(errors, [], `${lang}/${width}/${mode}`);
          await page.close();
        }
      }
    }
     console.log(`Commuter exact-artifact: ${smoke ? '2 desktop/mobile smoke cases' : (selectedLocale || '3 locales') + ' x 4 widths x ' + (layoutOnly || invalidOnly ? '1 mode' : '8 modes')} passed (actual Leaflet; active route with station focus, persistent three-stop sheet, Explore/Close/reopen, source markers, native pinch/pan, geometry/fare fixtures, partial/missing geometry).`);
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
