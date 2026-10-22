"use strict";
// Real Leaflet smoke test; weather responses are deterministic fixtures.
// CHROME_PATH is required. Downloads the pinned Leaflet runtime, never weather.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');
const puppeteer = require('puppeteer-core');
const rootArg = process.argv.indexOf('--root');
assert.ok(rootArg >= 0 && process.argv[rootArg + 1], 'Usage: node tests/browser/gis-weather.cjs --root _site');
const root = path.resolve(process.argv[rootArg + 1]);
const fields = ['temperature_2m', 'apparent_temperature', 'wind_speed_10m', 'wind_direction_10m', 'precipitation'];
const units = ['°C', '°C', 'km/h', '°', 'mm'];
const start = Math.floor(Date.now() / 3600000) * 3600;
const fixture = { hourly: { time: Array.from({ length: 48 }, (_, i) => start + i * 3600) }, hourly_units: { time: 'unixtime' } };
fields.forEach((field, i) => { fixture.hourly[field] = Array.from({ length: 48 }, (_, n) => [29 + n % 3, 34 + n % 3, 12, 45, n % 3 * 0.8][i]); fixture.hourly_units[field] = units[i]; });
async function main() {
  const leaflet = await fetch('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js', { signal: AbortSignal.timeout(15000) }).then(r => { assert.ok(r.ok); return r.text(); });
  const css = await fetch('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css', { signal: AbortSignal.timeout(15000) }).then(r => { assert.ok(r.ok); return r.text(); });
  const server = http.createServer((req, res) => {
    let file = path.resolve(root, '.' + new URL(req.url.replace(/^\/+/, '/'), 'http://localhost').pathname);
    if (!file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
    try {
      if (fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
      res.setHeader('Content-Type', ({ '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.geojson': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml', '.webp': 'image/webp' })[path.extname(file)] || 'application/octet-stream');
      res.end(fs.readFileSync(file));
    } catch { res.writeHead(404).end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  let browser;
  try {
    browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH, headless: true, args: ['--no-sandbox'] });
    for (const [lang, width] of [['en', 1440], ['en', 390], ['fil', 1440], ['pag', 390]]) {
      const page = await browser.newPage();
      async function activate(selector) { await page.focus(selector); await page.keyboard.press(selector === '#gis-weather-enabled' ? 'Space' : 'Enter'); }
      const errors = []; let radarRequests = 0, tileRequests = 0; let requests = 0, failure = false, delay = false;
      page.on('pageerror', error => errors.push(error.stack || error.message));
      await page.setViewport({ width, height: 1000 });
      await page.setCacheEnabled(false);
      await page.setRequestInterception(true);
      page.on('request', async req => {
        try {
          if (req.url().includes('api.rainviewer.com')) {
            radarRequests++;
            if (process.env.WEATHER_LIVE_RADAR) { await req.continue(); return; }
            await req.respond({ contentType: 'application/json', headers: { 'access-control-allow-origin': '*' }, body: JSON.stringify({host:'https://tilecache.rainviewer.com',radar:{past:[{time:start-600,path:'/v2/radar/'+(start-600)},{time:start,path:'/v2/radar/'+start}]}}) });
          } else if (req.url().includes('tilecache.rainviewer.com')) {
            tileRequests++;
            assert.ok(Number(new URL(req.url()).pathname.split('/')[5]) <= 7, 'radar respects native zoom limit');
            if (process.env.WEATHER_LIVE_RADAR) { await req.continue(); return; }
            await req.respond({contentType:'image/png',headers:{'access-control-allow-origin':'*'},body:Buffer.from(req.url().includes('/radar/'+(start-600)+'/') ? 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABpfZFQAAAAABJRU5ErkJggg==' : 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNQK7j0HwAEkAJo39+DWAAAAABJRU5ErkJggg==','base64')});
          } else if (req.url().includes('api.open-meteo.com')) {
            requests++;
            if (delay) await new Promise(resolve => setTimeout(resolve, 500));
            await req.respond({ status: failure ? 429 : 200, contentType: 'application/json', headers: { 'access-control-allow-origin': '*', 'retry-after': '120' }, body: JSON.stringify(failure ? { error: true } : fixture) });
          } else if (req.url().includes('leaflet@1.9.4/dist/leaflet.js')) await req.respond({ contentType: 'text/javascript', headers: { 'access-control-allow-origin': '*' }, body: leaflet });
          else if (req.url().includes('leaflet@1.9.4/dist/leaflet.css')) await req.respond({ contentType: 'text/css', headers: { 'access-control-allow-origin': '*' }, body: css });
          else if (req.url().startsWith(origin) || (process.env.WEATHER_VISUAL && /^https:\/\/(tile.openstreetmap.org|fonts.googleapis.com|fonts.gstatic.com)\//.test(req.url()))) await req.continue();
          else await req.abort();
        } catch (error) { if (!page.isClosed() && !/handled|closed|Invalid InterceptionId/.test(error.message)) errors.push(error.stack || error.message); }
      });
      await page.goto(`${origin}/${lang === 'en' ? '' : lang + '/'}gis/`, { waitUntil: 'networkidle2' });
      await page.waitForSelector('#gis-workspace[data-ready="true"]');
      assert.equal(requests, 0, 'weather stays opt-in');
      assert.equal(radarRequests, 0);
      assert.ok(await page.$eval('#gis-map', el => el.getBoundingClientRect().height >= 280), 'styled map has usable height');
      assert.equal(await page.$eval('#gis-weather-summary', el => getComputedStyle(el).position), 'absolute');
      assert.ok(await page.$('.leaflet-map-pane'), JSON.stringify(await page.evaluate(() => ({ leaflet: typeof L, status: document.querySelector('#gis-map-status').textContent }))));
      await activate('#gis-layers-tab');
      const before = await page.$eval('.leaflet-map-pane', el => el.style.transform);
      const markers = await page.$$eval('.gis-icon-marker', els => els.length);
      await activate('#gis-weather-enabled');
      await page.waitForSelector('#gis-weather-summary:not([hidden])');
      assert.equal(requests, 1);
      await page.waitForSelector('.leaflet-gis-radar-pane img');
      await page.waitForFunction(() => document.querySelector('#gis-radar-status').textContent !== document.querySelector('#gis-weather').dataset.loading);
      assert.ok(await page.evaluate(() => { const p = document.querySelector('#gis-weather').dataset; return [p.radarReady, p.radarEmpty].includes(document.querySelector('#gis-radar-status').textContent); }));
      assert.equal(radarRequests, 1);
      assert.ok(tileRequests > 0);
      const radarTimes = await page.$$eval('#gis-radar-time option', els => els.map(el => el.value));
      const latestTile = await page.$eval('.leaflet-gis-radar-pane img', el => el.src);
      await page.select('#gis-radar-time', radarTimes[0]);
      assert.notEqual(await page.$eval('.leaflet-gis-radar-pane img', el => el.src), latestTile, 'frame selection changes tile URL');
      await page.waitForFunction(() => document.querySelector('#gis-radar-status').textContent !== document.querySelector('#gis-weather').dataset.loading);
      if (!process.env.WEATHER_LIVE_RADAR) assert.equal(await page.$eval('#gis-radar-status', el => el.textContent), await page.$eval('#gis-weather', el => el.dataset.radarEmpty), 'transparent tiles show an explicit empty state');
      await page.select('#gis-radar-time', radarTimes[radarTimes.length - 1]);
      await page.waitForFunction(() => document.querySelector('#gis-radar-status').textContent !== document.querySelector('#gis-weather').dataset.loading);
      if (!process.env.WEATHER_LIVE_RADAR) assert.equal(await page.$eval('#gis-radar-status', el => el.textContent), await page.$eval('#gis-weather', el => el.dataset.radarReady), 'visible tile pixels restore the ready state');
      if (!process.env.WEATHER_LIVE_RADAR) {
        const latestTime = await page.$eval('#gis-radar-time', el => el.value);
        await activate('#gis-radar-play');
        await page.waitForFunction(time => document.querySelector('#gis-radar-time').value !== time, {}, latestTime);
        await page.waitForFunction(time => document.querySelector('#gis-radar-time').value === time, {}, latestTime);
        await activate('#gis-radar-play');
        assert.equal(await page.$eval('#gis-radar-play', el => el.getAttribute('aria-pressed')), 'false');
        await activate('#gis-radar-play');
        await page.select('#gis-radar-time', radarTimes[0]);
        assert.equal(await page.$eval('#gis-radar-play', el => el.getAttribute('aria-pressed')), 'false', 'manual selection pauses playback');
        await page.select('#gis-radar-time', latestTime);
      }
      assert.match(await page.$eval('#gis-radar-time option', el => el.textContent), /AM|PM/);
      assert.match(await page.$eval('#gis-weather-time option', el => el.textContent), /AM|PM/);
      await page.$eval('#gis-radar-opacity', el => {el.value = '25'; el.dispatchEvent(new Event('input'));});
      assert.equal(await page.$eval('#gis-radar-opacity-value', el => el.textContent), '25%');
      assert.equal(await page.$eval('.leaflet-gis-radar-pane .leaflet-layer', el => el.style.opacity), '0.25');
      await page.$eval('#gis-radar-opacity', el => {el.value = '65'; el.dispatchEvent(new Event('input'));});
      assert.equal(await page.$$eval('#gis-weather-time option', els => els.length), 48);
      for (const mode of ['feels', 'wind', 'rain', 'temperature']) {
        await activate(`[data-weather-mode="${mode}"]`);
        assert.equal(await page.$$eval('.gis-weather-marker', els => els.length), 0, 'forecast uses the side summary only');
      }
      assert.equal(requests, 1, 'modes reuse one response');
      await page.select('#gis-weather-time', String((start + 3600) * 1000));
      assert.match(await page.$eval('.gis-weather-reading', el => el.textContent), /30/);
      assert.equal(await page.$eval('.leaflet-map-pane', el => el.style.transform), before);
      assert.equal(await page.$$eval('.gis-icon-marker', els => els.length), markers);
      assert.equal(await page.$eval('.leaflet-gis-radar-pane', el => getComputedStyle(el).pointerEvents), 'none');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal overflow');
      if (process.env.WEATHER_SCREENSHOTS) {
        await page.evaluate(() => { document.activeElement.blur(); document.querySelector('#gis-layers-panel').scrollTop = 0; window.scrollTo({ top: 0, behavior: "instant" }); });
        await new Promise(resolve => setTimeout(resolve, 200));
        fs.mkdirSync(process.env.WEATHER_SCREENSHOTS, { recursive: true });
        await page.screenshot({ path: path.join(process.env.WEATHER_SCREENSHOTS, `weather-fixture-${lang}-${width}.png`), fullPage: true });
      }
      if (process.env.WEATHER_LIVE_RADAR && lang === 'en' && width === 1440) {
        for (let i = 0; i < 10; i++) {
          await page.$eval('.leaflet-control-zoom-out', el => el.click());
          await new Promise(resolve => setTimeout(resolve, 400));
        }
        await page.waitForFunction(() => document.querySelector('#gis-radar-status').textContent === document.querySelector('#gis-weather').dataset.radarReady).catch(async error => { console.log(await page.evaluate(() => ({status:document.querySelector('#gis-radar-status').textContent, tiles:Array.from(document.querySelectorAll('.leaflet-gis-radar-pane img')).map(el=>({url:el.src,loaded:el.className,width:el.naturalWidth}))}))); if(process.env.WEATHER_SCREENSHOTS) await page.screenshot({path:path.join(process.env.WEATHER_SCREENSHOTS,'weather-regional-failure.png'),fullPage:true}); throw error; });
        assert.ok(await page.$eval('.leaflet-gis-radar-pane', el => el.querySelectorAll('.leaflet-tile-loaded').length > 0));
        if (process.env.WEATHER_SCREENSHOTS) await page.screenshot({path:path.join(process.env.WEATHER_SCREENSHOTS,'weather-live-regional.png'),fullPage:true});
        console.log('Live regional radar has visible pixels in the map viewport');
      }
      if (!process.env.WEATHER_LIVE_RADAR) await activate('#gis-radar-play');
      await activate('#gis-weather-enabled');
      assert.equal(await page.$eval('#gis-radar-play', el => el.getAttribute('aria-pressed')), 'false', 'disabling weather pauses playback');
      assert.equal(await page.$$eval('.gis-weather-marker', els => els.length), 0);
      assert.equal(await page.$$eval('.leaflet-gis-radar-pane img', els => els.length), 0);
      assert.equal(await page.$eval('#gis-weather-summary', el => el.hidden), true);
      // Removed layers must detach Leaflet's map listeners before clearing events.
      await page.$eval('.leaflet-control-zoom-out', el => el.click());
      await new Promise(resolve => setTimeout(resolve, 400));
      await page.$eval('.leaflet-control-zoom-in', el => el.click());
      await new Promise(resolve => setTimeout(resolve, 400));
      await activate('#gis-weather-enabled');
      assert.equal(requests, 1, 're-enable uses fresh cache');
      assert.equal(await page.$eval('#gis-radar-play', el => el.getAttribute('aria-pressed')), 'false');
      assert.equal(radarRequests, 1, 'radar metadata uses fresh cache');
      failure = true; delay = true;
      await page.evaluate(() => { const realNow = Date.now; Date.now = () => realNow() + 61 * 60000; document.dispatchEvent(new Event('visibilitychange')); });
      await page.waitForFunction(() => document.querySelector('.gis-weather-stale'));
      await page.waitForFunction(() => document.querySelector('#gis-weather-status').textContent === document.querySelector('#gis-weather').dataset.limited);
      assert.equal(requests, 2);
      assert.equal(await page.$eval('#gis-weather-refresh', el => el.disabled), true);
      await activate('#gis-weather-enabled');
      failure = false;
      await page.evaluate(() => { const realNow = Date.now; Date.now = () => realNow() + 6 * 60000; });
      await activate('#gis-weather-enabled');
      await activate('#gis-weather-enabled');
      await new Promise(resolve => setTimeout(resolve, 700));
      assert.equal(await page.$eval('#gis-weather-summary', el => el.hidden), true, 'late response cannot revive disabled overlay');
      assert.equal(await page.$$eval('.gis-weather-marker', els => els.length), 0);
      assert.deepEqual(errors, []);
      await page.close();
      console.log(`Weather modes/cache/layout passed: ${lang}, ${width}px`);
    }
  } finally { if (browser) await browser.close(); await new Promise(resolve => server.close(resolve)); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
