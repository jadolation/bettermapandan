"use strict";
// Read-only built-artifact checks. Genuine cached Leaflet; no build or source overrides.
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const assert = require("node:assert/strict");

function argument(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i < 0) return fallback;
  assert.ok(process.argv[i + 1] && !process.argv[i + 1].startsWith("--"), `${name} needs a value`);
  return process.argv[i + 1];
}
const root = fs.realpathSync(argument("--root", "_site"));
assert.ok(fs.statSync(path.join(root, "gis/index.html")).isFile(), "Build the site before running this harness");
const screenshots = path.resolve("/tmp/kilo/gis-v33");
const puppeteer = require(process.env.PUPPETEER_CORE_PATH || [
  "/mnt/c/Users/jeydi/AppData/Roaming/npm/node_modules/lighthouse/node_modules/puppeteer-core",
  "/tmp/kilo/gis-test-deps/node_modules/puppeteer-core",
].find(p => fs.existsSync(p)) || "puppeteer-core");
const leafletJs = fs.readFileSync(process.env.GIS_LEAFLET_JS_PATH || "/tmp/kilo/leaflet.js", "utf8");
const leafletCss = fs.readFileSync(process.env.GIS_LEAFLET_CSS_PATH || "/tmp/kilo/leaflet.css", "utf8");
const neutralTile = '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#e8ece7"/></svg>';
const mime = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".geojson": "application/json", ".png": "image/png", ".svg": "image/svg+xml", ".woff2": "font/woff2" };
const server = http.createServer((req, res) => {
  try {
    if (req.method !== "GET" && req.method !== "HEAD") return res.writeHead(405).end();
    // A request target beginning // is still a local path, not a new authority.
    const pathname = decodeURIComponent(new URL("http://localhost" + req.url).pathname);
    let file = path.resolve(root, "." + pathname);
    if (!file.startsWith(root + path.sep)) return res.writeHead(403).end();
    if (fs.statSync(file).isDirectory()) file = path.join(file, "index.html");
    file = fs.realpathSync(file);
    if (!file.startsWith(root + path.sep)) return res.writeHead(403).end();
    const stat = fs.statSync(file);
    if (!stat.isFile() || stat.size > 16 * 1024 * 1024) return res.writeHead(413).end();
    res.setHeader("Content-Type", mime[path.extname(file)] || "application/octet-stream");
    res.setHeader("Cache-Control", "no-store");
    res.end(req.method === "HEAD" ? undefined : fs.readFileSync(file));
  } catch { res.writeHead(404).end(); }
});
server.requestTimeout = 15000;
server.headersTimeout = 10000;
server.maxRequestsPerSocket = 1000;

const selector = id => `[data-layer-id="${id}"] input[type="checkbox"]`;
async function view(page) {
  return page.evaluate(() => {
    const map = window.__statisticsMap, c = map.getCenter();
    return { lat: c.lat, lng: c.lng, zoom: map.getZoom() };
  });
}
async function unchanged(page, before) {
  const after = await view(page);
  assert.equal(after.zoom, before.zoom, "Unexpected zoom change");
  // Leaflet invalidateSize rounds the pixel origin when a legend resizes the map.
  const delta = await page.evaluate(({ before, after }) => {
    const map = window.__statisticsMap;
    return map.project([before.lat, before.lng], before.zoom).distanceTo(map.project([after.lat, after.lng], after.zoom));
  }, { before, after });
  assert.ok(delta <= 1,
    `Unexpected recenter: ${JSON.stringify({ before, after })}`);
}
async function toggle(page, id, checked = true) {
  await page.evaluate(() => document.querySelector("#gis-layers-tab").click());
  const control = await page.waitForSelector(selector(id), { visible: true });
  assert.equal(await control.evaluate(el => el.disabled), false, `${id} unavailable`);
  if (await control.evaluate(el => el.checked) !== checked) {
    await control.evaluate(el => el.scrollIntoView({ block: "center" }));
    await control.focus();
    await page.keyboard.press("Space");
  }
  await page.waitForFunction((id) => {
    const row = document.querySelector(`[data-layer-id="${id}"]`);
    return row && row.querySelector('[role="status"]').textContent === document.querySelector('#gis-page').dataset.loaded;
  }, {}, id);
}
function classesFor(values) {
  const sorted = values.filter(v => typeof v === "number" && Number.isFinite(v) && v >= 0).sort((a, b) => a - b);
  const distinct = [...new Set(sorted)];
  const ends = distinct.length <= 3 ? distinct : [...new Set([1, 2, 3].map(n => sorted[Math.ceil(sorted.length * n / 3) - 1]))];
  return ends.map((max, i) => ({ min: i ? sorted.find(v => v > ends[i - 1]) : sorted[0], max,
    color: ["#31875a", "#e8c44d", "#c84b47"][ends.length === 2 && i === 1 ? 2 : i] }));
}
function valuesFor(stats, mode, filters = {}) {
  const supported = Object.entries(stats.project_coverage.sources).some(([source, c]) => c.supported && (!filters.source || source === filters.source));
  const projects = stats.projects.filter(p => p.references.some(r => ["source", "year", "status"].every(key => !filters[key] || String(r[key] == null ? "unknown" : r[key]) === filters[key])));
  return Object.fromEntries(Object.entries(stats.barangays).map(([gid, b]) => [gid, mode === "population" ? b.population.count :
    supported && b.projects.count !== null ? new Set(projects.filter(p => p.barangay_gids.includes(gid)).map(p => p.project_id)).size : null]));
}
async function polygons(page) {
  return page.evaluate(() => {
    const result = [];
    window.__statisticsMap.eachLayer(layer => {
      if (!(layer instanceof L.Polygon) || !layer.feature) return;
      const gid = String(layer.feature.properties.gid || layer.feature.properties.psgc || "");
      if (!/^0105528\d{3}$/.test(gid)) return;
      const element = layer.getElement();
      result.push({ gid, id: L.stamp(layer), fill: element.getAttribute("fill").toLowerCase(), opacity: Number(element.getAttribute("fill-opacity")),
        keyboard: element.tabIndex === 0 && element.getAttribute("role") === "button" });
    });
    return result.sort((a, b) => a.gid.localeCompare(b.gid));
  });
}
async function checkMetric(page, stats, mode, filters = {}, identity) {
  const values = valuesFor(stats, mode, filters), classes = classesFor(Object.values(values));
  const actual = await polygons(page);
  assert.equal(actual.length, 15, `${mode}: exactly 15 shared rendered polygons`);
  assert.deepEqual(actual.map(p => p.gid), Object.keys(stats.barangays).sort());
  if (identity) assert.deepEqual(actual.map(p => p.id), identity, "Mode/filter switch recreated shared boundaries");
  for (const polygon of actual) {
    const value = values[polygon.gid];
    const expected = typeof value === "number" && classes.find(c => value >= c.min && value <= c.max);
    assert.equal(polygon.fill, expected ? expected.color : "#a6adb4", `${mode} ${polygon.gid}, filters ${JSON.stringify(filters)}, value ${value}`);
    assert.ok(polygon.opacity > 0, "Choropleth fill invisible");
    assert.ok(polygon.keyboard, "Boundary must be keyboard accessible");
  }
  const legend = await page.$eval("#gis-legend", el => ({ hidden: el.hidden, rows: [...el.querySelectorAll("p")].filter(p => p.querySelector(".gis-legend-swatch")).map(p => {
    const rgb = getComputedStyle(p.querySelector(".gis-legend-swatch")).backgroundColor.match(/\d+/g);
    return { label: p.textContent.trim(), color: "#" + rgb.slice(0, 3).map(v => Number(v).toString(16).padStart(2, "0")).join("") };
  }) }));
  assert.equal(legend.hidden, false);
  for (const entry of classes) {
    const lang = await page.$eval("html", el => el.lang);
    const format = new Intl.NumberFormat(lang);
    const label = format.format(entry.min) + (entry.min === entry.max ? "" : " - " + format.format(entry.max));
    assert.ok(legend.rows.some(row => row.label === label && row.color === entry.color), `Missing numeric legend class/color ${label}: ${JSON.stringify(legend)}`);
  }
  return actual.map(p => p.id);
}
async function filters(page, values) {
  for (const key of ["source", "year", "status"]) await page.select(`#gis-project-${key}`, values[key] || "");
}
async function selectBoundary(page, gid) {
  await page.evaluate(gid => {
    window.__statisticsMap.eachLayer(layer => {
      if (layer instanceof L.Polygon && layer.feature && String(layer.feature.properties.gid || layer.feature.properties.psgc) === gid) layer.getElement().focus();
    });
  }, gid);
  await page.keyboard.press("Enter");
  await page.waitForSelector("#gis-statistic-details:not([hidden])");
}

async function screenshot(page, locale, mode, width) {
  const previous = await view(page);
  await page.evaluate(() => {
    const map = window.__statisticsMap, boundaries = [];
    map.eachLayer(layer => { if (layer instanceof L.Polygon && layer.feature) boundaries.push(layer); });
    // Deliberate evidence framing, separate from layer/filter viewport assertions.
    map.fitBounds(L.featureGroup(boundaries).getBounds(), { animate: false, padding: [12, 12] });
    const legend = document.querySelector("#gis-legend"), heading = [...legend.querySelectorAll("h3")].at(-1);
    if (heading) legend.scrollTop += heading.getBoundingClientRect().top - legend.getBoundingClientRect().top;
    const control = document.querySelector('[data-layer-id="barangay-population"]');
    const sidebar = document.querySelector(".gis-sidebar");
    if (control && sidebar) sidebar.scrollTop += control.getBoundingClientRect().top - sidebar.getBoundingClientRect().top - 60;
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  });
  await page.screenshot({ path: path.join(screenshots, `gis-${locale}-${mode}-${width}.png`), fullPage: true });
  await page.screenshot({ path: path.join(screenshots, `gis-${locale}-${mode}-${width}-viewport.png`) });
  if (mode === "projects") {
    await page.$eval("#gis-project-filters", el => el.scrollIntoView({ block: "center", behavior: "instant" }));
    await page.screenshot({ path: path.join(screenshots, `gis-${locale}-${mode}-${width}-filters.png`) });
    await page.evaluate(() => window.scrollTo({ top: 0, left: 0, behavior: "instant" }));
  }
  await page.evaluate(previous => window.__statisticsMap.setView([previous.lat, previous.lng], previous.zoom, { animate: false }), previous);
}

async function openPage(browser, origin, locale, width, failure) {
  const page = await browser.newPage();
  page.setDefaultTimeout(15000);
  await page.setViewport({ width, height: width < 600 ? 844 : 1000 });
  const errors = [], localFailures = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => {
    // The production-origin PWA manifest is intentionally outside this loopback origin.
    const localOriginManifestCsp = /Loading a manifest from 'https:\/\/bettermapandan\.org\/site\.webmanifest' violates/.test(message.text());
    if (message.type() === "error" && !/Failed to load resource/.test(message.text()) && !localOriginManifestCsp) errors.push(message.text());
  });
  await page.setRequestInterception(true);
  const state = { failure, statsRequests: 0 };
  await page.evaluateOnNewDocument(() => {
    // Observe the UMD exports without changing the cached script bytes/SRI.
    let leaflet;
    Object.defineProperty(window, "L", { configurable: true, get: () => leaflet, set(value) {
      leaflet = value;
      if (!value || typeof value !== "object") return;
      if (value.Map) {
        value.Map.addInitHook(function () { window.__statisticsMap = this; });
        return;
      }
      let MapClass;
      Object.defineProperty(value, "Map", { configurable: true, enumerable: true, get: () => MapClass, set(Map) {
        MapClass = Map;
        Map.addInitHook(function () { window.__statisticsMap = this; });
      } });
    } });
  });
  page.on("request", request => {
    const url = request.url();
    if (/leaflet[^/]*\.js(?:\?|$)/.test(url)) return request.respond({ headers: { "Access-Control-Allow-Origin": "*" }, contentType: "text/javascript", body: leafletJs });
    if (/leaflet[^/]*\.css(?:\?|$)/.test(url)) return request.respond({ headers: { "Access-Control-Allow-Origin": "*" }, contentType: "text/css", body: leafletCss });
    if (/^https:\/\/tile\.openstreetmap\.org\//.test(url)) return request.respond({ contentType: "image/svg+xml", body: neutralTile });
    if (!url.startsWith(origin + "/")) return request.abort();
    if (/barangay-statistics\.json(?:\?|$)/.test(url)) {
      state.statsRequests++;
      if (state.failure === "missing") return request.respond({ status: 404, contentType: "application/json", body: "{}" });
      if (state.failure === "malformed") return request.respond({ contentType: "application/json", body: '{"schema_version":1,"barangays":[]}' });
    }
    return request.continue();
  });
  page.on("response", response => {
    if (response.url().startsWith(origin + "/") && response.status() >= 400 && !/barangay-statistics\.json/.test(response.url())) localFailures.push(`${response.status()} ${response.url()}`);
  });
  await page.goto(`${origin}/${locale === "en" ? "" : locale + "/"}gis/`, { waitUntil: "load" });
  await page.waitForSelector(".leaflet-marker-icon.gis-icon-marker > svg");
  await page.evaluate(css => {
    assertLeaflet();
    function assertLeaflet() { if (L.version !== "1.9.4" || !window.__statisticsMap) throw Error("Expected genuine Leaflet 1.9.4"); }
    const style = document.createElement("style"); style.textContent = css; document.head.append(style);
  }, leafletCss);
  return { page, errors, localFailures, state };
}

async function normalCase(browser, origin, locale, width) {
  const { page, errors, localFailures, state } = await openPage(browser, origin, locale, width);
  try {
    const manifest = await page.evaluate(() => window.GIS_LAYERS);
    for (const [id, metric] of [["barangay-population", "population"], ["barangay-projects", "projects"]]) {
      const layer = manifest.layers.find(l => l.id === id);
      assert.ok(layer && layer.type === "choropleth" && layer.metric === metric && layer.geometry_layer === "barangay-boundaries", `Missing mode ${id}`);
    }
    const stats = await page.evaluate(async () => {
      const layer = GIS_LAYERS.layers.find(l => l.id === "barangay-population");
      return (await fetch(new URL(layer.statistics_url, new URL(GIS_LAYERS.metadata.asset_base, location.href)))).json();
    });
    assert.equal(Object.keys(stats.barangays).length, 15);
    // Deliberately move away from the home viewport before all toggle/filter tests.
    await page.evaluate(() => window.__statisticsMap.setView([16.04, 120.46], 14, { animate: false }));
    const before = await view(page);
    const initialStatsRequests = state.statsRequests;
    await toggle(page, "barangay-population");
    const identity = await checkMetric(page, stats, "population");
    await unchanged(page, before);
    await selectBoundary(page, Object.keys(stats.barangays)[0]);
    assert.match(await page.$eval("#gis-statistic-details", el => el.textContent), /2024/);
    await unchanged(page, before);
    await page.keyboard.press("Escape");
    assert.ok(await page.evaluate(() => document.activeElement.matches('path[role="button"]')));
    await screenshot(page, locale, "population", width);
    await toggle(page, "barangay-projects");
    assert.equal(await page.$eval(selector("barangay-population"), el => el.checked), false);
    await checkMetric(page, stats, "projects", {}, identity);
    await unchanged(page, before);
    const options = await page.$eval("#gis-project-filters", el => Object.fromEntries([...el.querySelectorAll("select")].map(s => [s.id.replace("gis-project-", ""), [...s.options].filter(o => !o.disabled && o.value).map(o => o.value)])));
    for (const [source, coverage] of Object.entries(stats.project_coverage.sources)) {
      assert.equal(await page.$eval(`#gis-project-source option[value="${source}"]`, el => el.disabled), !coverage.supported,
        `Unsupported ${source} coverage must not be presented as zero`);
    }
    for (const key of ["source", "year", "status"]) {
      assert.ok(options[key].length, `No supported ${key} filters`);
      for (const value of options[key]) {
        await filters(page, { [key]: value });
        await checkMetric(page, stats, "projects", { [key]: value }, identity);
        await unchanged(page, before);
      }
    }
    // Combined filters must match ONE reference, then count unique project IDs.
    for (const source of options.source) {
      const reference = stats.projects.flatMap(p => p.references).find(r => r.source === source);
      if (!reference) continue;
      const combined = { source, year: String(reference.year == null ? "unknown" : reference.year), status: reference.status };
      await filters(page, combined);
      await checkMetric(page, stats, "projects", combined, identity);
      await unchanged(page, before);
    }
    await filters(page, {});
    const assigned = stats.projects.find(p => p.barangay_gids.length);
    assert.ok(assigned, "Expected documented barangay project assignment");
    await selectBoundary(page, assigned.barangay_gids[0]);
    const links = await page.$$eval('#gis-statistic-details a[href*="project="]', els => els.map(a => a.href));
    assert.ok(links.length, "Expected locale-aware project links");
    for (const link of links) {
      const url = new URL(link);
      assert.equal(url.pathname, `/${locale === "en" ? "" : locale + "/"}transparency/projects/`);
      assert.ok(stats.projects.some(p => p.project_id === url.searchParams.get("project")));
    }
    await page.keyboard.press("Escape");
    await screenshot(page, locale, "projects", width);
    const markerIndex = await page.evaluate(() => {
      const map = document.querySelector("#gis-map").getBoundingClientRect();
      return [...document.querySelectorAll('.leaflet-marker-icon.gis-icon-marker[role="button"]')].findIndex(el => {
        const box = el.getBoundingClientRect();
        return box.left > map.left + 60 && box.right < map.right - 60 && box.top > map.top + 60 && box.bottom < map.bottom - 60;
      });
    });
    assert.ok(markerIndex >= 0, "Expected an onscreen marker for keyboard selection without Leaflet focus auto-pan");
    const marker = (await page.$$('.leaflet-marker-icon.gis-icon-marker[role="button"]'))[markerIndex];
    await marker.focus();
    await page.keyboard.press("Enter");
    await page.waitForSelector("#gis-details:not([hidden])");
    assert.equal(await marker.evaluate(el => el.getAttribute("aria-pressed")), "true");
    await page.keyboard.press("Escape");
    assert.ok(await marker.evaluate(el => document.activeElement === el));
    await unchanged(page, before);
    const rasters = manifest.layers.filter(l => l.type === "raster-image-overlay" && l.enabled && l.available);
    assert.ok(rasters.length, "Expected available reference rasters");
    for (const raster of rasters) {
      await toggle(page, raster.id);
      assert.equal(await page.$eval(selector("barangay-projects"), el => el.checked), false);
      assert.ok(await page.$$eval(".leaflet-image-layer", els => els.length > 0));
      await unchanged(page, before);
      await toggle(page, "barangay-population");
      assert.equal(await page.$eval(selector(raster.id), el => el.checked), false);
      assert.equal(await page.$$eval(".leaflet-image-layer", els => els.length), 0);
      await checkMetric(page, stats, "population", {}, identity);
      await unchanged(page, before);
    }
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "Horizontal viewport overflow");
    assert.deepEqual(errors, [], "Browser JavaScript errors");
    assert.deepEqual(localFailures, [], "Missing local resources");
    assert.equal(state.statsRequests - initialStatsRequests, 1, "Modes must reuse the successfully loaded statistics");
    console.log(JSON.stringify({ locale, width, polygons: 15, sharedGeometry: true, filterOptions: options, statsRequests: state.statsRequests, screenshots: 5, errors: 0 }));
  } finally { await page.close(); }
}

async function failureCase(browser, origin, failure) {
  const { page, errors, localFailures, state } = await openPage(browser, origin, "en", 1440, failure);
  try {
    const before = await view(page);
    const markers = await page.$$eval(".gis-icon-marker", els => els.length);
    await page.evaluate(() => document.querySelector("#gis-layers-tab").click());
    await page.click(selector("barangay-population"));
    await page.waitForFunction(() => {
      const row = document.querySelector('[data-layer-id="barangay-population"]');
      return !row.querySelector("input").checked && row.querySelector('[role="status"]').textContent.trim();
    });
    assert.equal(await page.$$eval(".gis-icon-marker", els => els.length), markers, "Stats failure removed existing markers");
    await unchanged(page, before);
    await page.focus(".gis-icon-marker");
    await page.keyboard.press("Enter");
    await page.waitForSelector("#gis-details:not([hidden])");
    await page.keyboard.press("Escape");
    state.failure = null;
    await toggle(page, "barangay-population");
    assert.equal((await polygons(page)).length, 15, "Retry did not recover statistics");
    await unchanged(page, before);
    assert.deepEqual(errors, []);
    assert.deepEqual(localFailures, []);
    console.log(JSON.stringify({ failure, preservedMap: true, retryRecovered: true, errors: 0 }));
  } finally { await page.close(); }
}

(async () => {
  let browser;
  const deadline = setTimeout(() => { console.error("Statistics browser harness exceeded 300-second bound"); process.exit(1); }, 300000);
  try {
    fs.mkdirSync(screenshots, { recursive: true });
    await new Promise((resolve, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", resolve); });
    const origin = `http://127.0.0.1:${server.address().port}`;
    browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || "/opt/google/chrome/chrome", headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
    for (const locale of ["en", "fil", "pag"]) for (const width of [1440, 390]) await normalCase(browser, origin, locale, width);
    for (const failure of ["missing", "malformed"]) await failureCase(browser, origin, failure);
    console.log("PASS: 6 genuine Leaflet locale/viewport cases, 2 failure/retry cases, 30 screenshots (12 full-page, 12 viewport, 6 filters)");
  } finally {
    if (browser) await browser.close();
    server.closeAllConnections();
    if (server.listening) await new Promise(resolve => server.close(resolve));
    clearTimeout(deadline);
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
