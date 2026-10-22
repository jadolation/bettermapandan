"use strict";
// Uses genuine Leaflet, including its CSS loaded after site CSS. Never mutates --root.
// GIS_LEAFLET_JS_PATH / GIS_LEAFLET_CSS_PATH must point to cached Leaflet 1.9.4.
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const assert = require("node:assert/strict");
const root = path.resolve(process.argv[process.argv.indexOf("--root") + 1] || "_site");
const puppeteer = require(process.env.PUPPETEER_CORE_PATH || "puppeteer-core");
const leafletJs = fs.readFileSync(process.env.GIS_LEAFLET_JS_PATH, "utf8");
const leafletCss = fs.readFileSync(process.env.GIS_LEAFLET_CSS_PATH, "utf8");
async function residentChecks(page, locale, width) {
  const lang = locale ? locale.slice(0, -1) : 'en';
  const labels = JSON.parse(fs.readFileSync(path.join(__dirname, `../../locales/${lang}.json`))).gis.resident;
  await page.evaluate(() => document.querySelector('#gis-explore-tab').click());
  const members = await page.evaluate(() => [
    ...window.GIS_FACILITIES.features.filter(f => f.geometry).map(f => f.properties)
  ].filter(p => p.evacuation_id).map(p => ({ id: p.id, listing: p.evacuation_id })));
  assert.equal(members.length, 9);
  assert.equal(await page.$('#gis-layer-filter'), null);
  assert.equal(await page.$$eval('.gis-result', rows => rows.filter(r => r.gisFeature.properties.evacuation_id).length), 9);
  assert.ok(await page.$eval('#gis-legend', el => el.textContent.includes(window.GIS_RESIDENTS.labels.listedEvacuation)));
  for (const member of members) {
    await page.evaluate(id => {
      const input = document.querySelector('#gis-search'); input.value = id; input.dispatchEvent(new Event('input'));
      const button = [...document.querySelectorAll('.gis-result')].find(b => b.gisFeature.properties.id === id);
      if (!button) throw Error('Missing source listing ' + id);
      button.focus();
    }, member.id);
    const svg = await page.$eval('.gis-result svg', el => ({ color: el.getAttribute('stroke'), path: el.innerHTML }));
    assert.equal(svg.color, '#b66b08');
    await page.keyboard.press('Enter');
    const details = await page.$eval('#gis-detail-content', el => ({
      content: el.textContent,
      technical: [...el.querySelectorAll('details')].map(d => ({ summary: d.querySelector('summary').textContent, open: d.open })),
      phones: [...el.querySelectorAll('a[href^="tel:"]')].map(a => a.getAttribute('href')),
      terms: [...el.querySelectorAll('dt')].map(dt => dt.textContent)
    }));
    assert.ok(details.content.includes(labels.listedEvacuation));
    assert.ok(details.content.includes(labels.availabilityUnknown));
    assert.ok(details.content.includes(labels.capacityUnknown));
    assert.ok(details.technical.some(d => d.summary === labels.sourceMap && !d.open));
    assert.ok(details.content.includes(labels.officials));
    assert.ok(details.phones.includes('tel:0756002564'));
    assert.ok(!details.terms.includes('barangay gid') && !details.terms.includes('coordinate method'));
    if (member.listing === 'evac-006' || member.listing === 'evac-010') assert.ok(details.content.includes(labels.operationUnknown));
    if (member.listing === 'evac-001' && width === 390 && !locale && process.env.GIS_MARKER_SCREENSHOT_DIR) {
      await page.screenshot({ path: path.join(process.env.GIS_MARKER_SCREENSHOT_DIR, 'gis-resident-details-mobile.png'), fullPage: true });
    }
    await page.keyboard.press('Escape');
    assert.ok(await page.evaluate(id => document.activeElement.gisFeature.properties.id === id, member.id));
  }
  // Load all optional vector record types, then inspect citizen-first details.
  for (const id of ['roads', 'barangay-boundaries']) {
    await page.evaluate(id => { const input = document.querySelector(`[data-layer-id="${id}"] input`); if (!input.checked) input.click(); }, id);
    await page.waitForFunction(id => document.querySelector(`[data-layer-id="${id}"]`).textContent.includes(document.querySelector('#gis-page').dataset.loaded), {}, id);
  }
  for (const [layer, query] of [['roads',''], ['barangay-labels','Poblacion'], ['dpwh-projects','']]) {
    await page.evaluate(([layer, query]) => {
      const search = document.querySelector('#gis-search'); search.value = query;
       search.dispatchEvent(new Event('input'));
       const manifest = window.GIS_LAYERS.layers.find(l => l.id === layer);
       const button = [...document.querySelectorAll('.gis-result')].find(b => manifest.data_key === 'GIS_BARANGAYS' ? b.gisFeature.properties.gid : b.querySelector('small').textContent.includes(typeof manifest.title === 'string' ? manifest.title : manifest.title[document.documentElement.lang]));
       if (!button) throw Error('Missing mapped layer item ' + layer);
       button.focus();
    }, [layer, query]);
    await page.keyboard.press('Enter');
    assert.ok(await page.$eval('#gis-detail-content', (el, label) => [...el.querySelectorAll('details')].some(d => d.querySelector('summary').textContent === label && !d.open), labels.sourceMap));
    await page.keyboard.press('Escape');
  }
  await page.evaluate(() => {
    document.querySelector('#gis-search').value = '';
     document.querySelector('#gis-search').dispatchEvent(new Event('input'));
  });
  const payload = await page.evaluate(() => JSON.stringify([window.GIS_FACILITIES, window.GIS_RECORDS, window.GIS_RESIDENTS]));
  assert.doesNotMatch(payload, /Mapandan Town Center|coordinate_history|review_notes|junjrburguillos@gmail/);
  assert.equal(await page.$$eval('.gis-result', rows => rows.filter(r => r.gisFeature.properties.evacuation_id).length), 9);
  console.log(JSON.stringify({ locale: lang, width, residentListingsChecked: 9, recordTypesChecked: 4 }));
}
const server = http.createServer((req, res) => {
  const file = path.resolve(root, "." + decodeURIComponent(new URL("http://localhost" + req.url).pathname).replace(/\/+/g, "/"));
  if (!file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
  try {
    const target = fs.statSync(file).isDirectory() ? path.join(file, "index.html") : file;
    res.setHeader("Content-Type", ({ ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".geojson": "application/json" })[path.extname(target)] || "application/octet-stream");
    res.end(fs.readFileSync(target));
  } catch { res.writeHead(404).end(); }
});
(async () => {
  let browser;
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  try {
    browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || "/opt/google/chrome/chrome", headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
    for (const locale of ["", "fil/", "pag/"]) for (const width of [320, 390, 1440]) {
      const page = await browser.newPage();
      await page.setViewport({ width, height: 1000 });
      await page.setRequestInterception(true);
      page.on("request", request => {
        const url = request.url();
        if (/leaflet[^/]*\.js(?:\?|$)/.test(url)) return request.respond({ headers: { "Access-Control-Allow-Origin": "*" }, contentType: "text/javascript", body: leafletJs });
        if (/leaflet[^/]*\.css(?:\?|$)/.test(url)) return request.respond({ headers: { "Access-Control-Allow-Origin": "*" }, contentType: "text/css", body: leafletCss });
        if (!url.startsWith(`http://127.0.0.1:${server.address().port}/`)) return request.abort();
        return request.continue();
      });
      await page.goto(`http://127.0.0.1:${server.address().port}/${locale}gis/`, { waitUntil: "networkidle0" });
      await page.waitForSelector(".leaflet-marker-icon.gis-icon-marker > svg");
      await page.evaluate(css => {
        // Deliberately reproduce the production ordering, even if loading changes.
        const style = document.createElement("style"); style.textContent = css; document.head.append(style);
        const layer = window.GIS_LAYERS.layers.find(l => l.semantic_role === "dpwh_project");
        const input = document.querySelector(`[data-layer-id="${layer.id}"] input`);
        if (!input.checked) input.click();
      }, leafletCss);
      await page.waitForFunction(() => [...document.querySelectorAll(".gis-icon-marker svg")].some(svg => ["#287943", "#b66b08"].includes(svg.getAttribute("stroke"))));
      const measurements = await page.evaluate(() => {
        const output = [];
        for (const marker of document.querySelectorAll(".leaflet-marker-icon.gis-icon-marker")) {
          for (const selected of [false, true]) {
            marker.classList.toggle("gis-marker-selected", selected);
            const a = marker.getBoundingClientRect(), b = marker.querySelector("svg").getBoundingClientRect();
            output.push({ dx: (b.left + b.right - a.left - a.right) / 2, dy: (b.top + b.bottom - a.top - a.bottom) / 2, display: getComputedStyle(marker).display, width: a.width, height: a.height, selected, badge: !!marker.querySelector(".gis-marker-count") });
          }
          marker.classList.remove("gis-marker-selected");
        }
        return output;
      });
      for (const m of measurements) {
        assert.equal(m.display, "grid", JSON.stringify(m));
        assert.equal(m.width, 36); assert.equal(m.height, 36);
        assert.ok(Math.abs(m.dx) <= 0.5 && Math.abs(m.dy) <= 0.5, JSON.stringify(m));
      }
      if (width !== 320) await residentChecks(page, locale, width);
      if (process.env.GIS_MARKER_SCREENSHOT_DIR && locale === "" && width !== 320) await page.screenshot({ path: path.join(process.env.GIS_MARKER_SCREENSHOT_DIR, `gis-centered-markers-${width}.png`), fullPage: true });
      console.log(JSON.stringify({ root, locale: locale || "en", width, markers: measurements.length / 2, maxOffset: Math.max(...measurements.map(m => Math.max(Math.abs(m.dx), Math.abs(m.dy)))), badges: measurements.filter(m => m.badge).length / 2 }));
      await page.close();
    }
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
