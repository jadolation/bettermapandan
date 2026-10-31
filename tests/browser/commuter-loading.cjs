"use strict";
// Exact artifact and actual local Leaflet; route delivery is explicitly gated.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const zlib = require('node:zlib');
const assert = require('node:assert/strict');
const puppeteer = require('puppeteer-core');
const root = path.resolve(process.argv[process.argv.indexOf('--root') + 1]);
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'assets/commuter/manifest.json')));
// Measured production output: max HTML 63,609 raw / 15,053 gzip;
// six initial CSS/JS assets total 321,668 raw / 83,411 gzip. Modest headroom,
// independent of CDN availability, tile counts and wall-clock scheduling.
for (const locale of ['', 'fil', 'pag']) {
  const bytes = fs.readFileSync(path.join(root, locale, 'commuter/index.html'));
  assert.ok(bytes.length <= 72000 && zlib.gzipSync(bytes).length <= 17000, 'initial HTML byte budget');
  assert.ok(!/chart\.umd|barangay-data|lucide|https:\/\/unpkg.com\/leaflet/.test(bytes.toString()), 'commuter omits unrelated/CDN runtime assets');
}
const initialAssets = ['style.min.css','commuter-map.min.js','script.min.js','font-loader.min.js','vendor/leaflet-1.9.4/leaflet.js','vendor/leaflet-1.9.4/leaflet.css'].map(name => fs.readFileSync(path.join(root, 'assets', name)));
assert.ok(initialAssets.reduce((sum, bytes) => sum + bytes.length, 0) <= 345000);
assert.ok(initialAssets.reduce((sum, bytes) => sum + zlib.gzipSync(bytes).length, 0) <= 90000);
assert.ok(initialAssets[1].length < fs.statSync(path.join(root, 'assets/commuter-map.js')).size * .8, 'CI artifact is actually minified, not offline copy fallback');
const pixel = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNQK7j0HwAEkAJo39+DWAAAAABJRU5ErkJggg==', 'base64');
let hold = true, libraryHold = false, boundaryFailure = false, pending = [], requests = [], fault = null, faultKind = 'geometry', replacement = null;
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost').pathname;
  requests.push(url);
  if (boundaryFailure && url.endsWith('barangay-boundaries.geojson')) return res.writeHead(503).end();
  let file = path.resolve(root, '.' + url);
  if (replacement && replacement.url === url) file = path.join(root, replacement.originalUrl);
  if (!file.startsWith(root + path.sep)) return res.writeHead(403).end();
  try {
    if (fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
    const send = () => {
      if (fault && url.includes('/' + faultKind + '-')) {
        const current = fault; fault = null;
        if (current === 'http') return res.writeHead(503).end();
        if (current === 'timeout') return;
        res.setHeader('Content-Type', 'application/json');
        return res.end(current === 'json' ? '{' : JSON.stringify({ schema_version: 999 }));
      }
      let bytes = replacement && replacement.url === url ? replacement.bytes : fs.readFileSync(file);
      if (file.endsWith('index.html') && replacement) bytes = bytes.toString().replace(/(<script id="commuter-data" type="application\/json">)([\s\S]*?)(<\/script>)/, (_, a, raw, b) => {
        const data = JSON.parse(raw); data.resources[replacement.pattern].geometry = {url: replacement.url, sha256: replacement.hash};
        return a + JSON.stringify(data) + b;
      });
      if (url.endsWith('/leaflet.js')) bytes += '\nL.Map.addInitHook(function () { window.__commuterMap = this; });';
      res.setHeader('Content-Type', ({'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.geojson':'application/json','.png':'image/png'})[path.extname(file)] || 'application/octet-stream');
      res.end(bytes);
    };
    if (libraryHold && url.endsWith('/leaflet.js') || hold && /\/assets\/commuter\/(geometry|detail)-/.test(url)) pending.push({ url, send });
    else send();
  } catch { res.writeHead(404).end(); }
});
function release(test = () => true) {
  const ready = pending.filter(item => test(item.url)); pending = pending.filter(item => !test(item.url)); ready.forEach(item => item.send());
}
async function route(page, id) { await page.$eval(`[data-route="${id}"]`, el => el.click()); }
async function station(page, id = 'term-mini-mapandan') { await page.$eval(`.transport-card[data-id="${id}"] button`, el => el.click()); }
async function settle(page) { await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 280))); }
async function waitLines(page, count) { await page.waitForFunction(count => document.querySelectorAll('#commuter-map path.leaflet-interactive').length === count, {}, count); }
async function reset(page) { await page.$eval('#commuter-reset', el => el.click()); }
async function fresh(browser, origin, locale, width, waitForMap = true) {
  const page = await browser.newPage();
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  page.errors = errors;
  await page.setViewport({width,height:900,isMobile:width<900,hasTouch:width<900});
  await page.setRequestInterception(true);
  page.on('request', req => {
    if (req.url().startsWith(origin)) return req.continue();
    if (req.url().includes('tile.openstreetmap.org')) return req.respond({contentType:'image/png',body:pixel});
    return req.abort();
  });
  requests = []; pending = []; hold = true;
  await page.goto(origin + (locale === 'en' ? '/' : '/' + locale + '/') + 'commuter/', {waitUntil:'domcontentloaded'});
  await page.waitForSelector('#commuter-page[data-ready="true"]');
  if (waitForMap) await page.waitForFunction(() => !!window.__commuterMap);
  return page;
}
async function delayedLibrary(browser, origin) {
  libraryHold = true;
  const page = await fresh(browser, origin, 'en', 375, false);
  assert.equal(await page.evaluate(() => !!window.L), false);
  await page.type('#commuter-search', 'Dagupan');
  await station(page); assert.equal(await page.$$eval('.station-actions a', els => els.length), 2);
  await reset(page); await route(page, 'mapandan-manaoag-sm-multileg');
  hold = false; release(url => /\/(geometry|detail)-/.test(url));
  await page.waitForFunction(() => document.querySelector('#commuter-route-status').textContent === '');
  await station(page);
  const text = await page.$eval('#commuter-info-body', el => el.textContent);
  libraryHold = false; release(url => url.endsWith('/leaflet.js'));
  await page.waitForFunction(() => !!window.__commuterMap); await waitLines(page, 2);
  assert.equal(await page.$eval('#commuter-info-body', el => el.textContent), text);
  assert.equal(await page.$eval('#commuter-page', el => el.dataset.view), 'station');
  assert.deepEqual(page.errors, []); await page.close();
  console.log('Delayed local Leaflet: text/search/stations ready before library; late enhancement preserves selection');
}
async function progressive(page) {
  assert.ok(requests.filter(url => !url.endsWith('.geojson')).length <= 12, 'initial same-origin request budget: ' + JSON.stringify(requests));
  assert.equal(requests.filter(url => /\/(geometry|detail)-/.test(url)).length, 0, 'no speculative resources');
  await page.type('#commuter-search', 'Dagupan');
  assert.ok(await page.$$eval('.route-select', els => els.some(el => el.hidden) && els.some(el => !el.hidden)), 'search works before route delivery');
  await station(page);
  assert.equal(await page.$$eval('.station-actions a', els => els.length), 2);
  assert.equal(requests.filter(url => /\/(geometry|detail)-/.test(url)).length, 0, 'station needs no geometry');
  await reset(page);
  const a = 'mapandan-calasiao-multileg', b = 'mapandan-sta-barbara-multileg';
  await route(page, a);
  await page.waitForFunction(() => document.querySelector('#commuter-route-status').textContent.length > 0);
  assert.ok((await page.$eval('#commuter-info-body', el => el.textContent)).includes('PHP 80-120'), 'immediate complete fare');
  await route(page, b);
  const bPatterns = manifest.catalog.find(route => route.id === b).directions[0];
  await station(page);
  const stationText = await page.$eval('#commuter-info-body', el => el.textContent);
  await page.evaluate(() => new Promise(resolve => setTimeout(resolve, 1500)));
  assert.equal(requests.filter(url => url.endsWith('barangay-boundaries.geojson')).length, 0, 'optional boundaries wait behind selected network work, not tiles');
  hold = false; release();
  await waitLines(page, 3); await settle(page);
  assert.equal(await page.$eval('#commuter-info-body', el => el.textContent), stationText, 'late route never replaces station');
  assert.equal(await page.$eval('#commuter-sheet', el => el.dataset.state), 'half', 'loading never changes sheet state');
  assert.equal(await page.$eval('#commuter-page', el => el.dataset.activeRouteId), b);
  assert.deepEqual(await page.evaluate(() => Object.values(window.__commuterMap._layers).filter(layer => layer.feature && layer.feature.geometry.type !== 'Point' && layer.options.pane !== 'commuter-boundaries').map(layer => layer.feature.properties.pattern_id).sort()), [...bPatterns].sort(), 'late A cannot add its line');
  const geometryRequests = requests.filter(url => /\/geometry-/.test(url));
  assert.equal(new Set(geometryRequests).size, 4); assert.equal(geometryRequests.length, 4, 'shared legs in flight fetched once');
  await route(page, b); await settle(page);
  assert.equal(requests.filter(url => /\/geometry-/.test(url)).length, 4, 'successful responses cached');
  assert.equal(requests.filter(url => /\/detail-/.test(url)).length, 0, 'closed details remain lazy');
  await page.$eval('.route-directions', el => {el.open = true;});
  await page.waitForSelector('.direction-timeline');
  assert.equal(requests.filter(url => /\/detail-/.test(url)).length, 1);
  await page.$eval('.route-sources', el => {el.open = true;});
  await page.waitForSelector('.route-sources pre');
  assert.equal(requests.filter(url => /\/detail-/.test(url)).length, 3, 'source and timeline share detail cache');
  assert.ok((await page.$eval('.route-sources', el => el.textContent)).includes('original_source'));
  await reset(page);
  hold = true;
  await route(page, 'mapandan-manaoag-sm-multileg');
  await reset(page);
  const before = await page.evaluate(() => ({center:window.__commuterMap.getCenter(),zoom:window.__commuterMap.getZoom()}));
  hold = false; release(); await settle(page);
  await waitLines(page, 0);
  assert.equal(await page.$eval('#commuter-page', el => el.dataset.activeRouteId), '');
  assert.deepEqual(await page.evaluate(() => ({center:window.__commuterMap.getCenter(),zoom:window.__commuterMap.getZoom()})), before, 'reset suppresses obsolete fit');
  hold = true; await route(page, 'mapandan-dagupan-minibus');
  await page.evaluate(() => {
    const container = window.__commuterMap.getContainer();
    container.dispatchEvent(new PointerEvent('pointerdown', {bubbles:true}));
    window.__commuterMap.panBy([50,20], {animate:false});
  });
  const panned = await page.evaluate(() => ({center:window.__commuterMap.getCenter(),zoom:window.__commuterMap.getZoom()}));
  hold = false; release(); await waitLines(page, 1); await settle(page);
  assert.deepEqual(await page.evaluate(() => ({center:window.__commuterMap.getCenter(),zoom:window.__commuterMap.getZoom()})), panned, 'late geometry respects user pan');
  assert.deepEqual(page.errors, []);
}
async function failures(browser, origin) {
  for (const mode of ['http','json','hash','timeout']) {
    const page = await fresh(browser, origin, 'en', 375);
    fault = mode; hold = false;
    await route(page, 'mapandan-manaoag-sm-multileg');
    await page.waitForSelector('#commuter-route-status button');
    const requested = requests.filter(url => /\/geometry-/.test(url)).length;
    await settle(page);
    assert.equal(requests.filter(url => /\/geometry-/.test(url)).length, requested, 'no automatic retry loop');
    await page.click('#commuter-route-status button'); await waitLines(page, 2);
    assert.equal(requests.filter(url => /\/geometry-/.test(url)).length, requested + 1, 'only failed shared resource retried');
    assert.equal(await page.$$eval('#commuter-route-status button', els => els.length), 0);
    await page.close(); console.log('Loading failure/retry:', mode);
  }
  const pattern = 'mini-mapandan-manaoag';
  for (const change of [value => {value.schema_version = 999;}, value => {value.pattern_id = 'wrong-pattern';}, value => {value.data.coordinates[0][0] = null;}, value => {value.data = {type:'Point',coordinates:[120,16]};}, value => {value.data.coordinates[0][0] = '__nonfinite__';}, () => '{']) {
    const value = JSON.parse(fs.readFileSync(path.join(root, manifest.resources[pattern].geometry.url)));
    const override = change(value);
    const bytes = typeof override === 'string' ? override : JSON.stringify(value).replace('"__nonfinite__"', '1e400');
    const hash = crypto.createHash('sha256').update(bytes).digest('hex');
    // Reuse an existing safe path so the server's filesystem boundary is exercised.
    replacement = {pattern,bytes,hash,url:'/assets/commuter/geometry-' + hash + '.json',originalUrl:manifest.resources[pattern].geometry.url};
    const page = await fresh(browser, origin, 'en', 375); hold = false;
    await route(page, 'mapandan-manaoag-minibus');
    await page.waitForSelector('#commuter-route-status button'); await waitLines(page, 0);
    assert.deepEqual(page.errors, []); await page.close(); replacement = null;
  }
  const page = await fresh(browser, origin, 'en', 375); hold = false;
  await route(page, 'mapandan-manaoag-minibus'); await waitLines(page, 1);
  fault = 'http'; faultKind = 'detail';
  await page.$eval('.route-directions', el => {el.open = true;});
  await page.waitForSelector('.route-directions button');
  await page.click('.route-directions button'); await page.waitForSelector('.direction-timeline');
  assert.deepEqual(page.errors, []); await page.close(); faultKind = 'geometry';
  boundaryFailure = true;
  const noBoundary = await fresh(browser, origin, 'en', 375); hold = false;
  await noBoundary.evaluate(() => new Promise(resolve => setTimeout(resolve, 1500)));
  assert.equal(requests.filter(url => url.endsWith('barangay-boundaries.geojson')).length, 1);
  await route(noBoundary, 'mapandan-manaoag-sm-multileg'); await waitLines(noBoundary, 2);
  assert.deepEqual(noBoundary.errors, []); await noBoundary.close(); boundaryFailure = false;
  console.log('Correct-hash schema/nonfinite/JSON rejection, detail retry and optional boundary failure passed');
}
(async () => {
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  const origin = 'http://127.0.0.1:' + server.address().port;
  const browser = await puppeteer.launch({executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
  try {
    await delayedLibrary(browser, origin);
    for (const locale of ['en','fil','pag']) for (const width of [320,375,430,1440]) {
      const page = await fresh(browser,origin,locale,width); await progressive(page); await page.close(); console.log('Progressive case:',locale,width);
    }
    await failures(browser,origin);
  } finally { await browser.close(); server.close(); }
})().catch(error => {console.error(error);process.exitCode=1;server.close();});
