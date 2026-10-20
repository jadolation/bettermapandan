"use strict";
/* Offline Chrome checks. External Leaflet is replaced by a controlled mock, not
   claimed as live CDN/Leaflet visual validation. Never builds or mutates --root.
   node tests/browser/gis-explorer.cjs --fixtures
   node tests/browser/gis-explorer.cjs --root /absolute/_site
   CHROME_PATH and PUPPETEER_CORE_PATH may reference existing local installations. */
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const assert = require("node:assert/strict");
const { createRequire } = require("node:module");
const repo = path.resolve(__dirname, "../..");
const args = process.argv.slice(2);
function arg(key) { const i = args.indexOf(key); return i < 0 ? null : args[i + 1]; }
const root = arg("--root");
const fixtures = args.includes("--fixtures");
if (fixtures === !!root || args.some(a => a.startsWith("--") && !["--fixtures", "--root"].includes(a))) {
  throw Error("Usage: --fixtures OR --root <artifact>");
}
const esc = v => String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const inline = v => JSON.stringify(v).replace(/</g, "\\u003c").replace(/>/g, "\\u003e").replace(/&/g, "\\u0026");
const fc = features => ({ type: "FeatureCollection", features });
const feature = (name, geometry = null, extra = {}) => ({ type: "Feature", geometry, properties: { name, ...extra } });
const malicious = '<img src=x onerror="window.__injected=1">';
const bounds = { west: 120.44, south: 16.01, east: 120.46, north: 16.04 };
async function click(page, selector) {
  // Puppeteer's nearest-edge scrolling can leave controls under fixed site bars.
  await page.$eval(selector, el => el.scrollIntoView({ block: "center", behavior: "instant" }));
  await page.click(selector);
}
function fixture(lang, scenario = "normal") {
  const locale = JSON.parse(fs.readFileSync(path.join(repo, `locales/${lang}.json`))).gis;
  let html = fs.readFileSync(path.join(repo, "src/pages/gis.html"), "utf8").replace(/^---[\s\S]*?---/, "");
  html = html.replace(/\{\{GIS_([A-Z_]+)\}\}/g, (_, key) => esc(locale[key.toLowerCase()]));
  html = html.replace(/\{\{ASSET_BASE\}\}/g, "/");
  const layer = (id, type, extra = {}) => ({ id, title: { en: id, fil: id, pag: id }, group: "References",
    type, enabled: true, available: true, visible_by_default: false, legend: [], ...extra });
  const layers = [layer("barangays", "reference", { data_key: "GIS_BARANGAYS" }),
    layer("facilities", "inline-geojson", { data_key: "GIS_FACILITIES", visible_by_default: true }),
    layer("roads", "geojson", { url: "assets/gis/roads.geojson" }),
    layer("places", "geojson", { url: "assets/gis/places.geojson" }),
    layer("anchors", "geojson", { url: "assets/gis/anchors.geojson", semantic_role: "label_anchor" }),
    layer("raster", "raster-image-overlay", { images: [{ url: "assets/gis/map.png", bounds }], source_date: "2012-12-15", attribution: malicious,
      limitations: [malicious], legend: [{ color: "#c80", label: { en: "Class A", fil: "Klase A", pag: "Klase A" } }] }),
    layer("broken", "geojson", { url: "assets/gis/broken.geojson" }),
    layer("broken-image", "raster-image-overlay", { images: [{ url: "assets/gis/missing.png", bounds }] }),
    layer("unsupported", "wms"),
    layer("disabled", "geojson", { enabled: false, visible_by_default: true, url: "assets/gis/disabled.geojson" }),
    layer("unavailable", "geojson", { available: false, visible_by_default: true, url: "assets/gis/unavailable.geojson" }),
    layer("records", "reference", { data_key: "GIS_RECORDS" }),
    layer("hostile", "geojson", { visible_by_default: true, url: "assets/private/forbidden.geojson" })];
  const values = {
    GIS_LAYERS_DATA: { schema_version: 1, metadata: { asset_base: "/" }, layers },
    GIS_FACILITIES_DATA: fc(scenario === "empty" ? [] : Array.from({ length: 16 }, (_, i) =>
      feature(i === 0 ? malicious + "</script><script>window.__injected=1</script>" : `Facility ${i}`, { type: "Point", coordinates: i < 2 ? [120.45, 16.03] : [120.45 + i / 10000, 16.03] }, { id: `fac-${i}` }))),
    GIS_BARANGAYS_DATA: fc(Array.from({ length: 15 }, (_, i) => feature(`Barangay ${i}`, null, { gid: `PSGC${i}` }))),
    GIS_RECORDS_DATA: [ { name: "Project reference", project_id: "canonical-1", confidence: "explicit", evidence: "Source record test" } ],
  };
  html = html.replace(/\{(GIS_\w+_DATA)\}/g, (_, key) => inline(values[key]));
  const replacements = {
    GIS_RECORD_DIRECTORY: '<section id="gis-record-directory">Project reference</section>',
    GIS_BARANGAY_COUNT: "15", GIS_FACILITY_COUNT: String(values.GIS_FACILITIES_DATA.features.length),
    GIS_BARANGAY_DIRECTORY: `<ul class="gis-directory">${Array.from({ length: 15 }, (_, i) => `<li>Barangay ${i}</li>`).join("")}</ul>`,
    GIS_FACILITY_DIRECTORY: `<ul class="gis-directory">${values.GIS_FACILITIES_DATA.features.map(f => `<li>${esc(f.properties.name)}</li>`).join("")}</ul>`,
  };
  html = html.replace(/\{(GIS_\w+)\}/g, (_, key) => replacements[key] == null ? `{${key}}` : replacements[key]);
  assert.doesNotMatch(html, /\{GIS_|\{\{GIS_/);
  if (scenario === "missing") html = html.replace(/window\.GIS_(FACILITIES|BARANGAYS|RECORDS) = [^\n]*;/g, "");
  return `<!doctype html><html lang="${lang}"><head><meta name="viewport" content="width=device-width"><link rel="stylesheet" href="/assets/css/tokens.css"><link rel="stylesheet" href="/assets/css/map.css"></head><body>${html}<div class="mobile-action-bar" style="position:fixed;bottom:0;height:72px;left:0;right:0;background:white">Site actions</div></body></html>`;
}

function leafletMock() {
  const stats = window.__gisTest = { markers: [], images: [], fits: 0, pans: 0, views: 0, vectors: 0, resizes: 0 };
  const bounds = () => ({ isValid: () => true, extend() { return this; } });
  function layer(buttonClass) {
    const item = { handlers: {}, children: [], on(event, fn) { this.handlers[event] = fn; return this; },
      addTo(target) { target.addLayer(this); return this; },
      addLayer(child) { this.children.push(child); if (this.container) child.mount(this.container); return this; },
      mount(container) { this.container = container; if (this.button) container.appendChild(this.button);
        this.children.forEach(child => child.mount(container)); },
      remove() { if (this.button) this.button.remove(); this.children.forEach(child => child.remove()); },
      getBounds: bounds, bindTooltip(value) { this.tooltip = value; return this; } };
    if (buttonClass) {
      item.button = document.createElement("button"); item.button.type = "button"; item.button.className = buttonClass;
      item.button.textContent = "Map feature"; item.button.onclick = () => item.handlers.click && item.handlers.click();
    }
    return item;
  }
  window.L = {
    map(id) {
      const container = document.getElementById(id);
      for (const cls of ["leaflet-control-zoom-in", "leaflet-control-zoom-out"]) {
        const b = document.createElement("button"); b.className = cls; container.appendChild(b);
      }
      return { setView() { stats.views++; return this; }, addLayer(item) { item.mount(container); return this; },
        removeLayer(item) { item.remove(); }, panTo() { stats.pans++; }, fitBounds() { stats.fits++; },
        invalidateSize() { stats.resizes++; }, getContainer() { return container; } };
    },
    tileLayer() { const item = layer(); setTimeout(() => { if (item.handlers.tileerror) item.handlers.tileerror(); }, 20); return item; },
    featureGroup: () => layer(), latLngBounds: bounds,
    circleMarker(coords) { const item = layer("gis-test-marker"); stats.markers.push(coords); return item; },
    geoJSON(payload, options = {}) { const item = layer(); for (const f of payload.features || [payload]) {
      stats.vectors++; const child = layer("gis-test-shape"); if (options.onEachFeature) options.onEachFeature(f, child); item.addLayer(child);
    } return item; },
    imageOverlay(url) { const item = layer(); stats.images.push(url); const image = new Image();
      image.onload = () => item.handlers.load && item.handlers.load(); image.onerror = () => item.handlers.error && item.handlers.error();
      image.src = url; return item; },
    control: { scale: () => ({ addTo() {} }) },
  };
}

async function main() {
  let puppeteer;
  if (process.env.PUPPETEER_CORE_PATH) puppeteer = require(process.env.PUPPETEER_CORE_PATH);
  else {
    try { puppeteer = createRequire(path.join(repo, "package.json"))("puppeteer-core"); }
    catch { throw Error("Existing puppeteer-core not found. Set PUPPETEER_CORE_PATH; this test never installs dependencies."); }
  }
  const chrome = process.env.CHROME_PATH || ["/opt/google/chrome/chrome", "/usr/bin/google-chrome", "/usr/bin/chromium",
    "/home/jeydi/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome",
    "/home/jeydi/.cache/puppeteer/chrome/linux-145.0.7632.77/chrome-linux64/chrome"].find(p => fs.existsSync(p));
  assert.ok(chrome, "Set CHROME_PATH to an installed Chrome");
  const baseRoot = path.resolve(root || repo);
  if (!fixtures) assert.ok(fs.existsSync(path.join(baseRoot, "gis/index.html")), "Artifact must contain gis/index.html");
  const server = http.createServer((req, res) => {
    const pathname = decodeURIComponent(new URL("http://localhost" + req.url).pathname).replace(/\/{2,}/g, "/");
    if (fixtures) {
      if (/^\/(?:fil\/|pag\/)?transparency\/projects\/$/.test(pathname)) {
        res.setHeader("content-type", "text/html");
        res.end('<!doctype html><html><body><input id="explorer-search"><select id="explorer-barangay"><option value=""></option></select><select id="explorer-year"><option value=""></option></select><select id="explorer-type"><option value=""></option></select><select id="explorer-coverage"><option value=""></option></select><select id="explorer-match"><option value=""></option></select><p id="explorer-count"></p><div id="explorer-results"></div><script>window.__CONFIG__={assetBase:""};</script><script src="/assets/js/project-explorer.min.js"></script></body></html>'); return;
      }
      if (pathname === "/assets/js/project-explorer.min.js") {
        res.setHeader("content-type", "text/javascript"); res.end(fs.readFileSync(path.join(repo, "assets/js/project-explorer.js"))); return;
      }
      if (pathname.startsWith("/assets/data/")) {
        res.setHeader("content-type", "application/json");
        const payload = pathname.endsWith("project-index.json") ? [
          { id: "canonical-1", name: "Exact canonical record", sources: { dilg: true }, barangay: [], type: "lgu_development" },
          { id: "canonical-1-other", name: "Not a relationship", sources: {}, barangay: [] },
        ] : pathname.endsWith("entity-projects.json") ? [{ project_id: "canonical-1", provenance: [] }] : [];
        setTimeout(() => res.end(JSON.stringify(payload)), 25); return;
      }
      const match = pathname.match(/^\/fixtures\/(en|fil|pag)\/gis\/$/);
      if (match) { res.setHeader("content-type", "text/html"); res.end(fixture(match[1], new URL("http://localhost" + req.url).searchParams.get("data") || "normal")); return; }
      if (pathname === "/assets/gis-map.min.js") { res.setHeader("content-type", "text/javascript"); res.end(fs.readFileSync(path.join(repo, "assets/gis-map.js"))); return; }
      if (pathname === "/assets/gis/map.png") {
        res.setHeader("content-type", "image/png"); res.end(Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5wAAAABJRU5ErkJggg==", "base64")); return;
      }
      const geometries = {
        roads: { type: "LineString", coordinates: [[120.44, 16.02], [120.46, 16.04]] },
        places: { type: "Polygon", coordinates: [[[120.44, 16.02], [120.46, 16.02], [120.46, 16.04], [120.44, 16.02]]] },
        anchors: { type: "Point", coordinates: [120.45, 16.03] },
      };
      const key = pathname.match(/^\/assets\/gis\/(roads|places|anchors)\.geojson$/);
      if (key) { res.setHeader("content-type", "application/json"); setTimeout(() => res.end(JSON.stringify(fc([feature(key[1], geometries[key[1]])]))), 150); return; }
    }
    let file = path.resolve(baseRoot, "." + pathname);
    if (!file.startsWith(baseRoot + path.sep)) { res.writeHead(403); res.end(); return; }
    try {
      if (fs.statSync(file).isDirectory()) file = path.join(file, "index.html");
      const ext = path.extname(file);
      res.setHeader("content-type", ({ ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".geojson": "application/json", ".png": "image/png" })[ext] || "application/octet-stream");
      res.end(fs.readFileSync(file));
    } catch { res.writeHead(404); res.end(); }
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  let browser, checks = 0;
  try {
    browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
    for (const lang of ["en", "fil", "pag"]) {
      const url = fixtures ? `${origin}/fixtures/${lang}/gis/` : `${origin}${lang === "en" ? "" : "/" + lang}/gis/`;
      const locale = JSON.parse(fs.readFileSync(path.join(repo, `locales/${lang}.json`))).gis;
      for (const mobile of [false, true]) {
        const page = await browser.newPage(), errors = [], requests = [];
        await page.setViewport({ width: mobile ? 390 : 1440, height: mobile ? 844 : 1000 });
        await page.evaluateOnNewDocument(leafletMock);
        await page.setRequestInterception(true);
        page.on("request", request => { requests.push(request.url()); request.url().startsWith(origin) ? request.continue() : request.abort(); });
        page.on("pageerror", error => errors.push(error.message));
        await page.goto(url, { waitUntil: "domcontentloaded" });
        await page.waitForSelector('#gis-workspace[data-ready="true"]');
        await page.waitForFunction(() => document.getElementById("gis-map-status").textContent === document.getElementById("gis-page").dataset.tileError);
        assert.equal(await page.evaluate(() => "GIS_MODE" in window), false);
        assert.equal(await page.$eval("#gis-barangay-list", el => el.querySelectorAll("li").length), 15);
        assert.equal(await page.$eval("#gis-map-fallback", el => !el.hidden), true);
        assert.equal(await page.$eval("#gis-map-status", el => el.textContent), locale.tile_error);
        assert.equal(await page.$eval("#gis-search", el => !!el.labels.length), true);
        assert.equal(await page.$$eval("#gis-page h1", els => els.length), 1);
        assert.equal(await page.$eval("#gis-page h1", el => el.textContent), locale.title);
        assert.equal(await page.$eval("#gis-explore-tab", el => el.getAttribute("aria-selected")), "true");
        await page.$eval("#gis-search", el => { el.value = "Facility"; el.dispatchEvent(new Event("input")); });
        await page.focus("#gis-explore-tab"); await page.keyboard.press("ArrowRight");
        assert.equal(await page.evaluate(() => document.activeElement.id), "gis-layers-tab");
        assert.equal(await page.$eval("#gis-explore-panel", el => el.hidden), true);
        assert.equal(await page.$eval("#gis-layers-panel", el => el.hidden), false);
        assert.equal(await page.$eval("#gis-layers-panel", el => getComputedStyle(el).overflowY), "auto");
        const filter = await page.$eval("#gis-layer-filter", el => el.options[1] && el.options[1].value);
        if (filter) await page.select("#gis-layer-filter", filter);
        await page.keyboard.press("Home");
        assert.equal(await page.$eval("#gis-search", el => el.value), "Facility");
        assert.equal(await page.evaluate(() => document.activeElement.id), "gis-explore-tab");
        if (filter) {
          assert.equal(await page.$eval("#gis-layer-filter", el => el.value), filter);
          await page.select("#gis-layer-filter", "");
        }
        await page.focus("#gis-explore-tab"); await page.keyboard.press("End");
        assert.equal(await page.evaluate(() => document.activeElement.id), "gis-layers-tab");
        await page.keyboard.press("ArrowLeft");
        assert.equal(await page.evaluate(() => document.activeElement.id), "gis-explore-tab");
        await page.$eval("#gis-search", el => { el.value = ""; el.dispatchEvent(new Event("input")); });
        const resizes = await page.evaluate(() => window.__gisTest.resizes);
        await page.$eval("#gis-map", el => { el.style.height = "340px"; });
        await page.waitForFunction(previous => window.__gisTest.resizes > previous, {}, resizes);
        await page.$eval("#gis-map", el => { el.style.height = ""; });
        assert.equal(await page.$eval("#gis-results", el => getComputedStyle(el).overflowY), "auto");
        assert.equal(await page.evaluate(() => Number(document.getElementById("gis-facility-count").textContent) === window.GIS_FACILITIES.features.length), true, "Facility count matches emitted points");
        assert.equal(await page.evaluate(() => document.getElementById("gis-facility-list").querySelectorAll("li").length === window.GIS_FACILITIES.features.length), true, "Static directory matches supplied facilities");
        if (fixtures) {
          await page.select("#gis-layer-filter", "barangays");
          assert.equal(await page.$eval("#gis-results", el => el.children.length), 15);
          const before = await page.evaluate(() => [window.__gisTest.pans, window.__gisTest.fits]);
          await click(page, ".gis-result");
          assert.deepEqual(await page.evaluate(() => [window.__gisTest.pans, window.__gisTest.fits]), before, "Null barangays never navigate");
          assert.equal(await page.$eval("#gis-detail-content", el => el.textContent.includes(document.getElementById("gis-page").dataset.precisionLabel)), false, "Missing precision is not repeated as an unknown warning");
          await page.keyboard.press("Escape");
          await page.select("#gis-layer-filter", "facilities");
          assert.equal(await page.$eval("#gis-results", el => el.children.length), 16);
          await page.select("#gis-layer-filter", "");
        }
        assert.equal(await page.$("#gis-status-filter"), null);
        if (!fixtures) {
          await click(page, "#gis-layers-tab");
          const before = await page.evaluate(() => [window.__gisTest.fits, window.__gisTest.views]);
          await page.$$eval('#gis-layer-list input:not(:disabled)', inputs => inputs.forEach(input => { if (!input.checked) input.click(); }));
          await page.waitForFunction(() => [...document.querySelectorAll(".gis-layer small")].every(el => el.textContent !== document.getElementById("gis-page").dataset.loading));
          assert.equal(await page.$$eval(".gis-layer small", els => els.filter(el => el.textContent === document.getElementById("gis-page").dataset.layerError).length), 0, "Every generated available layer must load");
          assert.deepEqual(await page.evaluate(() => [window.__gisTest.fits, window.__gisTest.views]), before);
          assert.equal(page.url(), url, "Layer toggles must not navigate away from the map");
          await click(page, "#gis-explore-tab");
        }
        await page.focus("#gis-search"); await page.keyboard.type("NO_SUCH_RECORD_123");
        assert.equal(await page.$eval("#gis-results", el => el.children.length), 0);
        assert.equal(await page.$eval("#gis-no-results", el => !el.hidden), true);
        await page.$eval("#gis-search", el => { el.value = ""; el.dispatchEvent(new Event("input")); });
        const result = await page.$(".gis-result");
        if (result) {
          await result.focus(); await page.keyboard.press("Enter");
          assert.equal(await page.$eval("#gis-details", el => !el.hidden), true);
          assert.equal(await page.evaluate(() => document.activeElement.id), "gis-close");
          if (mobile) {
            assert.equal(await page.$eval("#gis-details", el => getComputedStyle(el).position), "fixed");
            assert.equal(await page.evaluate(() => {
              const sheet = document.getElementById("gis-details").getBoundingClientRect();
              const bar = document.querySelector(".mobile-action-bar");
              return !bar || !bar.getClientRects().length || sheet.bottom <= bar.getBoundingClientRect().top;
            }), true, "Details clear the global sticky action bar");
          }
          await page.keyboard.press("Escape");
          assert.equal(await page.$eval("#gis-details", el => el.hidden), true);
          assert.equal(await page.evaluate(() => document.activeElement.className), "gis-result");
        }
        if (fixtures) {
          assert.equal(await page.evaluate(() => window.GIS_FACILITIES.features.length), 16);
          assert.equal(await page.evaluate(() => window.__gisTest.markers.length), 15);
          assert.deepEqual(await page.evaluate(() => window.__gisTest.markers[0]), [16.03, 120.45]);
          assert.equal(await page.$eval("#gis-facility-list", el => el.querySelectorAll("li").length), 16);
          assert.ok(!requests.some(url => /\/(disabled|unavailable|forbidden)\.geojson/.test(url)), "Disabled and unsafe URLs never fetch");
          await page.$eval("#gis-search", el => { el.value = "<img"; el.dispatchEvent(new Event("input")); });
          await click(page, ".gis-result");
          assert.equal(await page.$eval(".gis-result", el => el.getAttribute("aria-pressed")), "true");
          assert.ok((await page.$eval("#gis-detail-content", el => el.textContent)).includes(malicious));
          assert.ok((await page.$eval("#gis-detail-content", el => el.textContent)).includes(locale.shared));
          assert.equal(await page.$("#gis-detail-content img"), null);
          await page.keyboard.press("Escape");
          await page.$eval("#gis-search", el => { el.value = ""; el.dispatchEvent(new Event("input")); });
          const initial = await page.evaluate(() => [window.__gisTest.fits, window.__gisTest.views]);
          await click(page, "#gis-layers-tab");
          for (const id of ["roads", "places", "anchors", "raster", "broken", "broken-image"]) {
            const checkbox = await page.evaluateHandle(id => {
              const rows = [...document.querySelectorAll(".gis-layer")]; return rows.find(row => row.querySelector("label span").textContent === id).querySelector("input");
            }, id);
            await checkbox.asElement().evaluate(el => el.scrollIntoView({ block: "center", behavior: "instant" }));
            await checkbox.asElement().click();
            if (id === "roads") assert.equal(await page.evaluate(() => [...document.querySelectorAll(".gis-layer")].find(row => row.querySelector("label span").textContent === "roads").querySelector("small").textContent), locale.loading);
          }
          await page.waitForFunction(() => [...document.querySelectorAll(".gis-layer small")].filter(el => el.textContent === document.getElementById("gis-page").dataset.layerError).length >= 3);
          await page.waitForFunction(() => window.__gisTest.vectors >= 2 && [...document.querySelectorAll(".gis-layer")].find(row => row.querySelector("label span").textContent === "anchors").querySelector("small").textContent === document.getElementById("gis-page").dataset.loaded);
          assert.deepEqual(await page.evaluate(() => [window.__gisTest.fits, window.__gisTest.views]), initial);
          assert.equal(await page.$eval("#gis-legend", el => !el.hidden), true);
          assert.ok(await page.evaluate(() => window.__gisTest.vectors >= 2));
          await click(page, "#gis-explore-tab");
          await page.$eval("#gis-search", el => { el.value = "anchors"; el.dispatchEvent(new Event("input")); });
          const before = await page.evaluate(() => window.__gisTest.pans);
          await click(page, ".gis-result");
          assert.equal(await page.evaluate(() => window.__gisTest.pans), before, "Label anchors never navigate");
          await page.keyboard.press("Escape");
          assert.equal(await page.evaluate(() => window.__injected), undefined);
          assert.equal(await page.$("#gis-detail-content img"), null);
          await page.$eval("#gis-search", el => { el.value = "Project reference"; el.dispatchEvent(new Event("input")); });
          const navigation = await page.evaluate(() => [window.__gisTest.pans, window.__gisTest.fits]);
          await click(page, ".gis-result");
          assert.deepEqual(await page.evaluate(() => [window.__gisTest.pans, window.__gisTest.fits]), navigation, "Null projects never navigate");
          assert.match(await page.$eval("#gis-detail-content a", el => el.getAttribute("href")), /\/transparency\/projects\/\?project=canonical-1$/);
        }
        assert.deepEqual(errors, [], `Browser errors: ${errors}`);
        if (mobile) {
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2), true, "No horizontal overflow");
          await page.setViewport({ width: 320, height: 740 });
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2), true, "No narrow-mobile overflow");
          await page.keyboard.press("Escape");
          await page.click("#gis-layers-tab");
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2), true, "Layer panel has no narrow-mobile overflow");
          await click(page, ".gis-layer button");
          await page.keyboard.press("Escape");
          assert.equal(await page.evaluate(() => document.activeElement.closest("#gis-layers-panel") !== null), true, "Layer details restore focus to the layer panel");
        }
        checks++; await page.close();
      }
      const nojs = await browser.newPage(); await nojs.setJavaScriptEnabled(false);
      await nojs.setRequestInterception(true); nojs.on("request", r => r.url().startsWith(origin) ? r.continue() : r.abort());
      await nojs.goto(url, { waitUntil: "domcontentloaded" });
      assert.equal(await nojs.$eval("#gis-barangay-list", el => el.querySelectorAll("li").length), 15);
      assert.equal(await nojs.$eval("#gis-map-fallback", el => getComputedStyle(el).display !== "none"), true);
       assert.equal(await nojs.$eval("#gis-workspace", el => el.hidden), true);
       assert.equal(await nojs.$eval("#gis-page h1", el => el.textContent), locale.title);
      checks++; await nojs.close();
      const missing = await browser.newPage();
      await missing.setRequestInterception(true); missing.on("request", r => r.url().startsWith(origin) ? r.continue() : r.abort());
      await missing.goto(url, { waitUntil: "domcontentloaded" });
      await missing.waitForSelector('#gis-workspace[data-ready="true"]');
      assert.equal(await missing.$eval("#gis-map", el => el.hidden), true);
      assert.equal(await missing.$eval("#gis-map-status", el => el.textContent), locale.library_error);
      assert.equal(await missing.$eval("#gis-barangay-list", el => el.querySelectorAll("li").length), 15);
      checks++; await missing.close();
    }
    if (fixtures) {
      for (const lang of ["en", "fil", "pag"]) for (const scenario of ["empty", "missing"]) {
        const page = await browser.newPage(), errors = [];
        await page.evaluateOnNewDocument(leafletMock);
        await page.setRequestInterception(true);
        page.on("request", r => r.url().startsWith(origin) ? r.continue() : r.abort());
        page.on("pageerror", e => errors.push(e.message));
        await page.goto(`${origin}/fixtures/${lang}/gis/?data=${scenario}`, { waitUntil: "domcontentloaded" });
        await page.waitForSelector('#gis-workspace[data-ready="true"]');
        await page.select("#gis-layer-filter", "facilities");
        assert.equal(await page.$eval("#gis-results", el => el.children.length), 0);
        assert.equal(await page.evaluate(() => window.__gisTest.markers.length), 0);
        if (scenario === "empty") {
          assert.equal(await page.$eval("#gis-facility-empty", el => !el.hidden), true);
          assert.equal(await page.$eval("#gis-marker-count", el => el.textContent), "0");
        } else {
          assert.equal(await page.$$eval(".gis-layer small", els => els.filter(el => el.textContent === document.getElementById("gis-page").dataset.layerError).length), 4);
        }
        assert.deepEqual(errors, []);
        checks++; await page.close();
      }
      for (const lang of ["en", "fil", "pag"]) for (const id of ["canonical-1", "absent-id"]) {
        const page = await browser.newPage();
        await page.goto(`${origin}${lang === "en" ? "" : "/" + lang}/transparency/projects/?project=${id}`, { waitUntil: "domcontentloaded" });
        await page.waitForFunction(() => document.querySelector('[aria-expanded="true"], #explorer-results [role="status"]'));
        if (id === "canonical-1") {
          assert.equal(await page.$eval('[data-id="canonical-1"] [data-expand]', el => el.getAttribute("aria-expanded")), "true");
          assert.equal(await page.$eval('[data-id="canonical-1-other"] [data-expand]', el => el.getAttribute("aria-expanded")), "false");
        } else {
          assert.match(await page.$eval('#explorer-results [role="status"]', el => el.textContent), /No project with this canonical ID/);
          assert.equal(await page.$$eval('[aria-expanded="true"]', els => els.length), 0);
        }
        checks++; await page.close();
      }
    }
    console.log(`GIS browser checks passed: ${checks} locale/viewport/no-JS/deep-link cases (${fixtures ? "source fixtures" : "exact built/minified artifact"}).`);
    console.log("External Leaflet/CDN and tiles were controlled, not live-renderer or geographic-accuracy validation.");
  } finally { if (browser) await browser.close(); await new Promise(resolve => server.close(resolve)); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
