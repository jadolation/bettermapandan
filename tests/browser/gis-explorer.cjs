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
  if (selector === "#gis-explore-tab" || selector === "#gis-layers-tab" || selector === ".gis-result" || selector === ".gis-layer button") {
    await page.focus(selector); await page.keyboard.press("Enter");
  } else await page.click(selector);
}
function fixture(lang, scenario = "normal") {
  const locale = JSON.parse(fs.readFileSync(path.join(repo, `locales/${lang}.json`))).gis;
  let html = fs.readFileSync(path.join(repo, "src/pages/gis.html"), "utf8").replace(/^---[\s\S]*?---/, "");
  html = html.replace(/\{\{GIS_([A-Z_]+)\}\}/g, (_, key) => esc(locale[key.toLowerCase()]));
  html = html.replace(/\{\{ASSET_BASE\}\}/g, "/");
  const layer = (id, type, extra = {}) => ({ id, title: { en: id, fil: id, pag: id }, group: "References",
    type, enabled: true, available: true, visible_by_default: false, legend: [], ...extra });
  const layers = [layer("barangays", "reference", { data_key: "GIS_BARANGAYS" }),
    layer("facilities", "inline-geojson", { data_key: "GIS_FACILITIES", semantic_role: "facility", visible_by_default: true }),
    layer("roads", "geojson", { url: "assets/gis/roads.geojson" }),
    layer("anchors", "geojson", { url: "assets/gis/anchors.geojson", semantic_role: "label_anchor" }),
    layer("raster", "raster-image-overlay", { images: [{ url: "assets/gis/map.png", bounds }], source_date: "2021-12-15", attribution: malicious,
      limitations: [malicious], legend: [{ color: "#c80", label: { en: "Class A", fil: "Klase A", pag: "Klase A" } }] }),
    layer("broken", "geojson", { url: "assets/gis/broken.geojson" }),
    layer("broken-image", "raster-image-overlay", { images: [{ url: "assets/gis/missing.png", bounds }] }),
    layer("unsupported", "wms"),
    layer("disabled", "geojson", { enabled: false, visible_by_default: true, url: "assets/gis/disabled.geojson" }),
    layer("unavailable", "geojson", { available: false, visible_by_default: true, url: "assets/gis/unavailable.geojson" }),
    layer("records", "reference", { data_key: "GIS_RECORDS" }),
    layer("other-records", "reference", { data_key: "GIS_RECORDS" }),
    layer("dpwh-projects", "geojson", { semantic_role: "dpwh_project", pane: "infrastructure", url: "assets/gis/dpwh.geojson" }),
    layer("boundaries", "geojson", { semantic_role: "barangay_boundary", pane: "administrative", url: "assets/gis/boundaries.geojson" }),
    layer("coarse", "geojson", { semantic_role: "barangay_reference_geometry", pane: "administrative", url: "assets/gis/coarse.geojson" }),
    layer("broken-boundaries", "geojson", { semantic_role: "barangay_boundary", url: "assets/gis/broken-boundaries.geojson" }),
    layer("physical-a", "raster-image-overlay", { pane: "physical", opacity: 0.3, exclusive_group: "physical-theme", images: [{ url: "assets/gis/map.png", bounds }, { url: "assets/gis/map.png", bounds }] }),
    layer("physical-b", "raster-image-overlay", { pane: "physical", opacity: 0.8, exclusive_group: "physical-theme", images: [{ url: "assets/gis/map.png", bounds }] }),
    layer("physical-fail", "raster-image-overlay", { pane: "physical", exclusive_group: "physical-theme", images: [{ url: "assets/gis/map.png", bounds }, { url: "assets/gis/missing.png", bounds }] }),
    layer("physical-late-fail", "raster-image-overlay", { pane: "physical", exclusive_group: "physical-theme", images: [{ url: "assets/gis/late-missing.png", bounds }] }),
    layer("physical-late", "raster-image-overlay", { pane: "physical", exclusive_group: "physical-theme", images: [{ url: "assets/gis/late.png", bounds }] }),
    layer("hazard", "raster-image-overlay", { pane: "hazards", images: [{ url: "assets/gis/map.png", bounds }] }),
    layer("hostile", "geojson", { visible_by_default: true, url: "assets/private/forbidden.geojson" })];
  for (let i = 1; i <= 7; i++) layers.push(layer("shared-raster-" + i, "raster-image-overlay", {
    pane: i < 5 ? "physical" : "hazards", opacity: i === 7 ? 0.6 : 0.4,
    exclusive_group: "thematic-rasters", images: [{ url: "assets/gis/map.png", bounds }] }));
  const values = {
    GIS_RESIDENTS_DATA: { labels: locale.resident },
    GIS_LAYERS_DATA: { schema_version: 1, metadata: { asset_base: "/" }, layers },
    GIS_FACILITIES_DATA: fc(scenario === "empty" ? [] : Array.from({ length: 16 }, (_, i) =>
      feature(i === 0 ? malicious + "</script><script>window.__injected=1</script>" : `Facility ${i}`, { type: "Point", coordinates: i < 2 ? [120.45, 16.03] : [120.45 + i / 10000, 16.03] }, { id: `fac-${i}`, category: ["Evacuation / gym", "School", "Health / medical", "Police / fire", "Barangay hall", "Other"][i % 6] }))),
    GIS_BARANGAYS_DATA: fc(Array.from({ length: 15 }, (_, i) => feature(`Barangay ${i}`, null, { gid: `PSGC${i}` }))),
    GIS_RECORDS_DATA: [ { name: "Project reference", layer_id: "records", project_id: "canonical-1", confidence: "explicit", evidence: "Source record test" },
      { name: "Other record", layer_id: "other-records", id: "other-ref" } ],
  };
  if (scenario === "legacy") values.GIS_RECORDS_DATA.forEach(row => { delete row.layer_id; });
  html = html.replace(/\{(GIS_\w+_DATA)\}/g, (_, key) => inline(values[key]));
  const replacements = {
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
  const stats = window.__gisTest = { markers: [], markerStyles: [], vectorStyles: [], images: [], imageItems: [], panes: {}, fits: 0, pans: 0, views: 0, vectors: 0, resizes: 0 };
  const bounds = () => ({ isValid: () => true, extend() { return this; } });
  function layer(buttonClass) {
    const item = { handlers: {}, children: [], on(event, fn) { this.handlers[event] = fn; return this; },
      addTo(target) { target.addLayer(this); return this; },
      addLayer(child) { this.children.push(child); if (this.container) child.mount(this.container); return this; },
      mount(container) { this.mounted = true; this.container = container; if (this.button) container.appendChild(this.button);
        this.children.forEach(child => child.mount(container)); if (this.handlers.add) this.handlers.add(); },
      remove() { this.mounted = false; this.container = null; if (this.button) this.button.remove(); this.children.forEach(child => child.remove()); },
      setOpacity(value) { this.options.opacity = value; return this; },
      setStyle(value) { Object.assign(this.options, value); return this; },
      getPane() { return stats.panes[this.options.pane]; },
      getElement() { return this.button; },
      getBounds: bounds, bindTooltip(value) { this.tooltip = value; return this; },
      openTooltip() { this.tooltipOpen = true; return this; }, closeTooltip() { this.tooltipOpen = false; return this; } };
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
       return { createPane(name) { const pane = document.createElement("div"); stats.panes[name] = pane; return pane; },
          getPane(name) { return stats.panes[name]; }, getZoom() { return 14; }, on() { return this; },
         setView() { stats.views++; return this; }, addLayer(item) { item.mount(container); return this; },
        removeLayer(item) { item.remove(); }, panTo() { stats.pans++; }, fitBounds() { stats.fits++; },
        invalidateSize() { stats.resizes++; }, getContainer() { return container; } };
    },
    tileLayer() { const item = layer(); setTimeout(() => { if (item.handlers.tileerror) item.handlers.tileerror(); }, 20); return item; },
    featureGroup: () => layer(), latLngBounds: bounds,
    divIcon: options => options,
    marker(coords, options) { const item = layer("gis-test-marker"); item.options = options;
      item.button.className += " " + options.icon.className; item.button.innerHTML = options.icon.html;
      item.button.title = options.title; item.button.setAttribute("aria-label", options.alt);
      item.button.style.width = options.icon.iconSize[0] + "px"; item.button.style.height = options.icon.iconSize[1] + "px";
      stats.markers.push(coords); stats.markerStyles.push(options); return item; },
    circleMarker(coords, options) { const item = layer("gis-test-marker"); item.options = options; stats.markers.push(coords); stats.markerStyles.push(options); return item; },
    geoJSON(payload, options = {}) { const item = layer(); for (const f of payload.features || [payload]) {
      stats.vectors++; const child = layer("gis-test-shape"); child.options = { ...options.style, pane: options.pane }; stats.vectorStyles.push(child.options); if (options.onEachFeature) options.onEachFeature(f, child); item.addLayer(child);
    } return item; },
    imageOverlay(url, bounds, options) { const item = layer(); item.options = options; stats.images.push(url); stats.imageItems.push(item); const image = new Image();
      image.onload = () => item.handlers.load && item.handlers.load(); image.onerror = () => item.handlers.error && item.handlers.error();
      image.src = url; return item; },
    control: { scale: () => ({ addTo() {} }) },
  };
  if (new URL(location.href).searchParams.get("data") === "fallback") { delete window.L.marker; delete window.L.divIcon; }
}

async function v3Checks(page, locale) {
  const setSearch = async (query = "", id = "") => {
    await page.$eval("#gis-search", (el, value) => { el.value = value; el.dispatchEvent(new Event("input")); }, query);
    await click(page, "#gis-explore-tab");
  };
  const toggle = async (id, checked) => {
    await page.$eval(`[data-layer-id="${id}"] input[type="checkbox"]`, (el, value) => { if (el.checked !== value) el.click(); }, checked);
  };
  const loaded = async id => page.waitForFunction(id => document.querySelector(`[data-layer-id="${id}"] small`).textContent === document.getElementById("gis-page").dataset.loaded, {}, id);
  await page.keyboard.press("Escape");
  assert.equal(await page.$('[data-layer-id="records"] input[type="checkbox"]'), null, "References are not broken map toggles");
  await click(page, "#gis-layers-tab");
   assert.equal(await page.$('[data-layer-id="other-records"]'), null);
   assert.equal(await page.$('#gis-layer-filter'), null);
  assert.deepEqual(await page.evaluate(() => Object.fromEntries(Object.entries(window.__gisTest.panes).filter(([key]) => !key.endsWith("-raster")).map(([key, pane]) => [key, pane.style.zIndex]))),
    { "gis-physical": "250", "gis-radar": "350", "gis-hazards": "300", "gis-administrative": "400", "gis-infrastructure": "450", "gis-facilities": "500" });
  assert.ok(await page.evaluate(() => Object.entries(window.__gisTest.panes).filter(([key]) => key.endsWith("-raster")).every(([, pane]) => pane.style.pointerEvents === "none")));
  await toggle("raster", false);
  await toggle("facilities", false);
  assert.equal(await page.$eval("#gis-legend", el => el.hidden), true, "Empty configured legends do not invent map classes");
  await toggle("dpwh-projects", true); await toggle("dpwh-projects", false); await loaded("dpwh-projects");
  assert.equal(await page.$eval('[data-layer-id="dpwh-projects"] input', el => el.checked), false);
  assert.equal(await page.$eval("#gis-legend", el => el.hidden), true, "Late vector load does not resurrect a hidden layer");
  await toggle("dpwh-projects", true);
  assert.match(await page.$eval("#gis-legend", el => el.textContent), new RegExp(locale.status_completed));
  assert.match(await page.$eval("#gis-legend", el => el.textContent), new RegExp(locale.status_unknown));
  await setSearch("", "dpwh-projects");
  const source = await page.evaluate(async () => (await (await fetch("/assets/gis/dpwh.geojson")).json()).features);
  assert.equal(source.length, 40);
  assert.equal(source.filter(f => !f.geometry).length, 2);
   assert.equal(await page.$$eval(".gis-result", rows => rows.filter(r => r.gisFeature.properties.source_transaction_id).length), source.filter(f => f.geometry).length, "Only mapped DPWH records appear");
  const points = source.filter(f => f.geometry && f.geometry.type === "Point");
  const pointGroups = new Set(points.map(f => JSON.stringify(f.geometry.coordinates)));
  assert.equal(await page.evaluate(() => window.__gisTest.markerStyles.filter(style => style.pane === "gis-infrastructure").length), pointGroups.size, "Coordinate groups are derived, not frozen to the point count");
  await setSearch("canonical-1");
   assert.equal(await page.$$eval(".gis-result", rows => rows.length), 0, "Null projects and references are excluded");
  await setSearch("canonical-1", "records");
   assert.equal(await page.$$eval(".gis-result", rows => rows.length), 0);
  await setSearch("txn-2", "dpwh-projects");
  assert.equal(await page.$$eval(".gis-result", rows => rows.length), 11, "ID substring search retains txn-2 and txn-20 through txn-29");
  for (const query of ["Exact Contractor", "ongoing", "2025", locale.status_ongoing]) {
    await setSearch(query, "dpwh-projects");
    assert.equal(await page.$$eval(".gis-result", rows => rows.length), 1, `DPWH search: ${query}`);
  }
  await click(page, ".gis-result");
  const detail = await page.$eval("#gis-detail-content", el => el.textContent);
  assert.match(detail, /1,234,567\.89/); assert.match(detail, /42\.5%/); assert.match(detail, /2025-01-02/);
  assert.equal(await page.$eval('#gis-detail-content a[href*="transparency/"]', el => el.getAttribute("href")),
    (await page.$eval("html", el => el.lang)) === "en" ? "/transparency/projects/?project=canonical-2" : `/${await page.$eval("html", el => el.lang)}/transparency/projects/?project=canonical-2`, "Hostile URL falls back to exact canonical ID");
  await page.keyboard.press("Escape"); await setSearch("txn 3", "dpwh-projects"); await click(page, ".gis-result");
  assert.equal(await page.$eval('#gis-detail-content a[href*="transparency/"]', el => el.getAttribute("href")), "/transparency/infrastructure/#dpwh-project-txn%203");
  await page.keyboard.press("Escape");
  await setSearch("canonical-1", "dpwh-projects");
  const beforeNull = await page.evaluate(() => [window.__gisTest.pans, window.__gisTest.fits]);
   assert.deepEqual(await page.evaluate(() => [window.__gisTest.pans, window.__gisTest.fits]), beforeNull);
  await page.keyboard.press("Escape");

  await toggle("coarse", true); await loaded("coarse"); await setSearch("PSGC2");
  assert.equal(await page.$$eval(".gis-result", rows => rows.length), 1);
  assert.match(await page.$eval(".gis-result", el => el.textContent), /Coarse source name/);
  await click(page, ".gis-result");
  assert.ok((await page.$eval("#gis-detail-content", el => el.textContent)).includes(locale.coarse_geometry));
  await page.keyboard.press("Escape");
  await toggle("coarse", false); await setSearch("PSGC2");
   assert.equal(await page.$('.gis-result'), null, "Hidden coarse geometry and null references are absent");
   await toggle("boundaries", true); await loaded("boundaries");
  await setSearch("PSGC0");
  const beforeShape = await page.evaluate(() => window.__gisTest.fits);
   await click(page, ".gis-result");
  await page.waitForFunction(previous => window.__gisTest.fits > previous, {}, beforeShape);
  assert.match(await page.$eval("#gis-detail-content", el => el.textContent), /Canonical shape name/);
  await page.keyboard.press("Escape");
  await setSearch("PSGC0");
  assert.equal(await page.$$eval(".gis-result", rows => rows.length), 1);
  assert.match(await page.$eval(".gis-result", el => el.textContent), /Canonical shape name/);
  await setSearch("", "barangays");
   assert.ok(await page.$$eval(".gis-result", rows => rows.every(r => r.gisFeature.geometry)), "No null reference rows survive shape loading");
  // Explicit fallback scenario: retain coverage of the enhanced static directory.
  await page.$eval("#gis-directories", el => { el.hidden = false; });
  await click(page, '#gis-directories details:has(#gis-barangay-list) summary');
  await click(page, "#gis-barangay-list li button");
  await page.waitForFunction(() => document.getElementById("gis-detail-content").textContent.includes("Canonical shape name"));
  assert.match(await page.$eval("#gis-detail-content", el => el.textContent), /Canonical shape name/, "Static directory enhancement joins by gid, not name");
  await page.keyboard.press("Escape");
  await page.$eval("#gis-directories", el => { el.hidden = true; });
  await page.focus("#gis-search");
  assert.ok(await page.evaluate(() => window.__gisTest.vectorStyles.some(style => style.dashArray === "6 5")));

  await toggle("hazard", true); await loaded("hazard");
  await toggle("physical-a", true); await toggle("physical-a", false); await loaded("physical-a");
  assert.ok(await page.evaluate(() => window.__gisTest.imageItems.filter(item => item.options.pane === "gis-physical-raster" && item.options.opacity === 0.3).every(item => !item.mounted)), "Hidden imagery is not resurrected after loading");
  await toggle("physical-a", true);
  await click(page, "#gis-layers-tab");
  await page.$eval('[data-layer-id="physical-a"] input[type="range"]', el => { el.value = "44"; el.dispatchEvent(new Event("input")); });
  await page.focus('[data-layer-id="physical-a"] input[type="range"]'); await page.keyboard.press("ArrowRight");
  assert.ok(await page.evaluate(() => window.__gisTest.imageItems.filter(item => item.options.pane === "gis-physical-raster" && item.mounted).every(item => item.options.opacity === 0.45)), "Opacity updates every image in the active raster");
  assert.ok((await page.$eval('[data-layer-id="physical-a"] input[type="range"]', el => el.getAttribute("aria-valuetext"))).includes(locale.opacity));
  await toggle("physical-b", true); await loaded("physical-b");
  assert.equal(await page.$eval('[data-layer-id="physical-a"] input[type="checkbox"]', el => el.checked), false);
  assert.equal(await page.$eval('[data-layer-id="hazard"] input[type="checkbox"]', el => el.checked), false, "Thematic fills remain mutually exclusive");
  await toggle("physical-a", true);
  assert.equal(await page.$eval('[data-layer-id="physical-b"] input[type="checkbox"]', el => el.checked), false);
  assert.equal(await page.$eval('[data-layer-id="physical-a"] input[type="range"]', el => el.value), "45", "Opacity persists across toggles");
  const checked = id => page.$eval(`[data-layer-id="${id}"] input[type="checkbox"]`, el => el.checked);
  const failed = id => page.waitForFunction(id => document.querySelector(`[data-layer-id="${id}"] small`).textContent === document.getElementById("gis-page").dataset.layerError, {}, id);
  const viewport = await page.evaluate(() => [window.__gisTest.fits, window.__gisTest.pans, window.__gisTest.views]);
  await toggle("physical-fail", true); await failed("physical-fail");
  assert.equal(await checked("physical-a"), true, "Failed multi-image replacement restores previous usable layer");
  assert.equal(await checked("physical-fail"), false);
  assert.equal(await page.$eval('[data-layer-id="physical-fail"] input[type="checkbox"]', el => el.disabled), false, "Raster failure allows retry");
  await toggle("physical-fail", true); await failed("physical-fail");
  assert.equal(await checked("physical-a"), true, "Retry failure still restores previous layer");
  await toggle("physical-late-fail", true); await toggle("physical-b", true); await failed("physical-late-fail");
  assert.equal(await checked("physical-b"), true, "Late failure cannot replace newer selection with rollback");
  assert.equal(await checked("physical-a"), false);
  await toggle("physical-late", true); await toggle("physical-a", true); await loaded("physical-late");
  assert.equal(await checked("physical-a"), true, "Late success cannot replace newer selection");
  assert.equal(await checked("physical-late"), false);
  assert.deepEqual(await page.evaluate(() => [window.__gisTest.fits, window.__gisTest.pans, window.__gisTest.views]), viewport, "Rollback and races preserve viewport");
  assert.equal(await page.$eval('[data-layer-id="physical-a"] input[type="range"]', el => el.value), "45");
  await toggle("physical-a", false); await toggle("physical-b", false);
  await toggle("physical-fail", true); await failed("physical-fail");
  assert.equal(await checked("physical-fail"), false, "Failure without a previous raster leaves none selected");
  const facilitiesBefore = await checked("facilities");
  for (let i = 1; i <= 7; i++) {
    await toggle("shared-raster-" + i, true); await loaded("shared-raster-" + i);
    assert.equal(await page.$$eval('[data-layer-id^="shared-raster-"] input[type="checkbox"]', inputs => inputs.filter(el => el.checked).length), 1, "All seven physical/hazard/flood fixtures share one exclusive group");
  }
  assert.equal(await checked("facilities"), facilitiesBefore, "Seven-way thematic selection preserves facility overlay state");
  assert.ok(await page.evaluate(() => window.__gisTest.imageItems.every(item => item.options.interactive === false && item.getPane().style.pointerEvents === "none")));
  await click(page, "#gis-layers-tab");
}

async function builtV3Checks(page) {
  const data = await page.evaluate(async () => {
    const layer = window.GIS_LAYERS.layers.find(layer => layer.semantic_role === "dpwh_project" && layer.enabled && layer.available);
    if (!layer) return null;
    const base = new URL(window.GIS_LAYERS.metadata.asset_base, location.href);
    return { layer, source: (await (await fetch(new URL(layer.url, base))).json()).features };
  });
  if (!data) return;
  const { layer, source } = data;
   await page.$eval(`[data-layer-id="${layer.id}"] input`, el => { if (!el.checked) el.click(); });
   await page.waitForFunction(id => document.querySelector(`[data-layer-id="${id}"] small`).textContent === document.getElementById("gis-page").dataset.loaded, {}, layer.id);
  await page.$eval("#gis-search", el => { el.value = ""; el.dispatchEvent(new Event("input")); });
   assert.equal(await page.$$eval(".gis-result", rows => rows.filter(r => r.gisFeature.properties.source_transaction_id).length), source.filter(f => f.geometry).length, "Built DPWH results include only visible mapped records");
  const groups = new Map();
  for (const f of source) if (f.geometry && f.geometry.type === "Point") {
    const key = JSON.stringify(f.geometry.coordinates); if (!groups.has(key)) groups.set(key, f);
  }
  const markers = await page.evaluate(() => window.__gisTest.markers.map((coordinates, index) => ({ coordinates, style: window.__gisTest.markerStyles[index] })));
  for (const f of groups.values()) {
    assert.ok(markers.some(marker => marker.style.pane === `gis-${layer.pane || "infrastructure"}` && marker.coordinates[0] === f.geometry.coordinates[1] && marker.coordinates[1] === f.geometry.coordinates[0]), "Built DPWH exact-coordinate group is created");
  }
  const nullRecord = source.find(f => !f.geometry);
  if (nullRecord) {
    await page.$eval("#gis-search", (el, id) => { el.value = id; el.dispatchEvent(new Event("input")); }, nullRecord.properties.id);
    const before = await page.evaluate(() => [window.__gisTest.pans, window.__gisTest.fits]);
    await click(page, "#gis-explore-tab");
     assert.equal(await page.$('.gis-result'), null);
    assert.deepEqual(await page.evaluate(() => [window.__gisTest.pans, window.__gisTest.fits]), before, "Built null DPWH does not navigate");
    await page.keyboard.press("Escape");
  }
  await page.$eval("#gis-search", el => { el.value = ""; el.dispatchEvent(new Event("input")); });
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
      if (pathname === "/assets/gis-weather.min.js") { res.setHeader("content-type", "text/javascript"); res.end(fs.readFileSync(path.join(repo, "assets/gis-weather.js"))); return; }
      if (pathname === "/assets/gis/late-missing.png") { setTimeout(() => res.writeHead(404).end(), 350); return; }
      if (pathname === "/assets/gis/late.png") { setTimeout(() => { res.setHeader("content-type", "image/png"); res.end(Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5wAAAABJRU5ErkJggg==", "base64")); }, 350); return; }
      if (pathname === "/assets/gis/map.png") {
        res.setHeader("content-type", "image/png"); res.end(Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5wAAAABJRU5ErkJggg==", "base64")); return;
      }
      const geometries = {
        roads: { type: "LineString", coordinates: [[120.44, 16.02], [120.46, 16.04]] },
        boundary: { type: "Polygon", coordinates: [[[120.44, 16.02], [120.46, 16.02], [120.46, 16.04], [120.44, 16.02]]] },
        anchors: { type: "Point", coordinates: [120.45, 16.03] },
      };
      if (pathname === "/assets/gis/dpwh.geojson") {
        const prefix = "";
        const rows = [
          feature("Project reference", null, { id: "txn-1", source_transaction_id: "txn-1", project_id: "canonical-1", project_url: prefix + "/transparency/projects/?project=canonical-1", status: "Completed", status_key: "completed" }),
          feature("Drainage works", geometries.anchors, { id: "txn-2", source_transaction_id: "txn-2", project_id: "canonical-2", project_url: "https://evil.invalid/transparency/projects/?project=canonical-2", status: "On-Going", status_key: "ongoing", fiscal_year: 2025, contractor: "Exact Contractor", contract_amount: 1234567.89, approved_budget: 2000000, accomplishment_percent: 42.5, actual_start_date: "2025-01-02" }),
          feature("Source only", geometries.anchors, { id: "txn 3", source_transaction_id: "txn 3", project_url: "/transparency/infrastructure/#dpwh-project-txn%203", status: "Not Started", status_key: "not_started" }),
          feature("Unreported works", { type: "Point", coordinates: [120.451, 16.031] }, { id: "txn-4", source_transaction_id: "txn-4", status_key: "unknown" }),
        ];
        for (let i = 5; i <= 40; i++) rows.push(feature(`Additional works ${i}`, i === 40 ? null : { type: "Point", coordinates: [120.45 + i / 10000, 16.032] }, { id: `txn-${i}`, source_transaction_id: `txn-${i}`, status_key: "completed" }));
        res.setHeader("content-type", "application/json"); setTimeout(() => res.end(JSON.stringify(fc(rows))), 100); return;
      }
      if (/^\/assets\/gis\/(boundaries|coarse)\.geojson$/.test(pathname)) {
        const coarse = pathname.includes("coarse");
        const rows = [feature(coarse ? "Coarse source name" : "Canonical shape name", geometries.boundary, { gid: coarse ? "PSGC2" : "PSGC0", source_name: "Different spelling", pop2024: 1656, source_date: "2016", limitations: ["Source geometry only"] }),
          feature("Unrelated same name", geometries.boundary, { gid: "PSGC_OTHER" })];
        res.setHeader("content-type", "application/json"); setTimeout(() => res.end(JSON.stringify(fc(rows))), 100); return;
      }
      const key = pathname.match(/^\/assets\/gis\/(roads|anchors)\.geojson$/);
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
        assert.equal(await page.$eval("#gis-directories", el => el.hidden && getComputedStyle(el).display === "none"), true, "Below-map fallback sections are absent from the initialized UI");
        assert.equal(await page.$eval("#gis-directory-link", el => el.hidden), true, "No focusable link targets the hidden fallback");
        assert.equal(await page.$$eval("#gis-directories a, #gis-directories button, #gis-directories summary", els => els.every(el => el.getClientRects().length === 0)), true, "Hidden fallback controls have no visible or keyboard-focusable boxes");
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
         assert.equal(await page.$('#gis-layer-filter'), null);
        await page.keyboard.press("Home");
        assert.equal(await page.$eval("#gis-search", el => el.value), "Facility");
        assert.equal(await page.evaluate(() => document.activeElement.id), "gis-explore-tab");
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
        if (!mobile) {
          await page.waitForFunction(() => Math.abs(document.querySelector(".gis-sidebar").getBoundingClientRect().bottom - document.querySelector(".gis-map-pane").getBoundingClientRect().bottom) <= 2);
          assert.ok(await page.$eval("#gis-results", el => el.clientHeight > 0 && el.scrollHeight > el.clientHeight), "Results have a bounded scroll region");
        } else {
          assert.ok(await page.$eval(".gis-sidebar", el => el.getBoundingClientRect().height <= 620), "Mobile sidebar stays bounded");
        }
        assert.equal(await page.evaluate(() => Number(document.getElementById("gis-facility-count").textContent) === window.GIS_FACILITIES.features.length + window.GIS_RECORDS.filter(row => ['evacuation-references', 'facility-references'].includes(row.layer_id)).length), true, "Facility count includes point and unresolved reference identities");
        assert.equal(await page.evaluate(() => document.getElementById("gis-facility-list").querySelectorAll("li").length === Number(document.getElementById("gis-facility-count").textContent)), true, "Static directory matches supplied facilities and references");
        if (fixtures) {
           assert.equal(await page.$eval("#gis-results", el => el.children.length), 16);
        }
        assert.equal(await page.$("#gis-status-filter"), null);
        if (!fixtures) {
          await click(page, "#gis-layers-tab");
          const before = await page.evaluate(() => [window.__gisTest.fits, window.__gisTest.views]);
          await page.$$eval('#gis-layer-list input[type="checkbox"]:not(:disabled)', inputs => inputs.forEach(input => { if (!input.checked) input.click(); }));
          await page.waitForFunction(() => [...document.querySelectorAll(".gis-layer small")].every(el => el.textContent !== document.getElementById("gis-page").dataset.loading));
          assert.equal(await page.$$eval(".gis-layer small", els => els.filter(el => el.textContent === document.getElementById("gis-page").dataset.layerError).length), 0, "Every generated available layer must load");
          assert.deepEqual(await page.evaluate(() => [window.__gisTest.fits, window.__gisTest.views]), before);
          assert.equal(page.url(), url, "Layer toggles must not navigate away from the map");
          await click(page, "#gis-explore-tab");
          await builtV3Checks(page);
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
          assert.equal(await page.$$eval("#gis-map .gis-test-marker", markers => markers.length), 15, "Created markers must actually attach to the feature group and map");
          assert.equal(await page.$$eval("#gis-map .gis-icon-marker svg path", paths => paths.length > 15), true, "Glyphs are actual SVG path nodes");
          assert.equal(await page.$eval("#gis-map .gis-icon-marker", el => el.textContent), "2", "Mixed coordinate group has a count, no raw path text");
          assert.ok((await page.$eval("#gis-map .gis-icon-marker", el => el.title)).includes(locale.category_school));
          assert.ok((await page.$eval("#gis-legend", el => el.textContent)).includes(locale.category_school), "Inline facilities legend is localized");
          assert.equal(await page.$eval(".gis-result", el => [...el.childNodes].filter(node => node.nodeType === Node.TEXT_NODE).length), 0, "Result title is not duplicated as a raw text node");
          await page.focus("#gis-map .gis-icon-marker"); await page.keyboard.press("Space");
          assert.equal(await page.$eval("#gis-map .gis-icon-marker", el => el.classList.contains("gis-marker-selected")), true);
          assert.equal(await page.$eval("#gis-map .gis-icon-marker", el => el.getAttribute("aria-pressed")), "true");
          await page.keyboard.press("Escape");
          assert.equal(await page.$eval("#gis-map .gis-icon-marker", el => el.classList.contains("gis-marker-selected")), false);
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
          for (const id of ["roads", "anchors", "raster", "broken", "broken-image"]) {
            const checkbox = await page.evaluateHandle(id => {
              return document.querySelector(`[data-layer-id="${id}"] input[type="checkbox"]`);
            }, id);
            await checkbox.asElement().evaluate(el => el.scrollIntoView({ block: "center", behavior: "instant" }));
            await checkbox.asElement().evaluate(el => el.click());
            if (id === "roads") assert.equal(await page.$eval('[data-layer-id="roads"] small', el => el.textContent), locale.loading);
          }
          await page.waitForFunction(() => [...document.querySelectorAll(".gis-layer small")].filter(el => el.textContent === document.getElementById("gis-page").dataset.layerError).length >= 3);
          await page.waitForFunction(() => window.__gisTest.vectors >= 1 && document.querySelector('[data-layer-id="anchors"] small').textContent === document.getElementById("gis-page").dataset.loaded);
          assert.deepEqual(await page.evaluate(() => [window.__gisTest.fits, window.__gisTest.views]), initial);
          assert.equal(await page.$eval("#gis-legend", el => !el.hidden), true);
          assert.ok(await page.evaluate(() => window.__gisTest.vectors >= 1));
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
           assert.equal(await page.$('.gis-result'), null);
           assert.deepEqual(await page.evaluate(() => [window.__gisTest.pans, window.__gisTest.fits]), navigation, "Null projects never navigate");
          await v3Checks(page, locale);
        }
        assert.deepEqual(errors, [], `Browser errors: ${errors}`);
        if (mobile) {
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2), true, "No horizontal overflow");
          await page.setViewport({ width: 320, height: 740 });
          assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2), true, "No narrow-mobile overflow");
          await page.keyboard.press("Escape");
          await click(page, "#gis-layers-tab");
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
      assert.equal(await nojs.$eval("#gis-directories", el => !el.hidden && getComputedStyle(el).display !== "none"), true);
      for (const selector of ["#gis-facility-list", "#gis-barangay-list"]) {
        await click(nojs, `#gis-directories details:has(${selector}) summary`);
        assert.equal(await nojs.$eval(selector, el => el.getClientRects().length > 0), true, "No-JS disclosures expose the static directory");
      }
      await nojs.focus("#gis-directories details:last-of-type summary");
      await nojs.keyboard.press("Enter");
      assert.equal(await nojs.$eval("#gis-directories details:last-of-type", el => el.open), true, "No-JS flood reference remains available");
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
      for (const lang of ["en", "fil", "pag"]) for (const scenario of ["empty", "missing", "legacy", "fallback"]) {
        const page = await browser.newPage(), errors = [];
        await page.evaluateOnNewDocument(leafletMock);
        await page.setRequestInterception(true);
        page.on("request", r => r.url().startsWith(origin) ? r.continue() : r.abort());
        page.on("pageerror", e => errors.push(e.message));
        await page.goto(`${origin}/fixtures/${lang}/gis/?data=${scenario}`, { waitUntil: "domcontentloaded" });
        await page.waitForSelector('#gis-workspace[data-ready="true"]');
         assert.equal(await page.$('#gis-layer-filter'), null);
         assert.equal(await page.$eval("#gis-results", el => el.children.length), ["legacy", "fallback"].includes(scenario) ? 16 : 0);
        assert.equal(await page.evaluate(() => window.__gisTest.markers.length), ["legacy", "fallback"].includes(scenario) ? 15 : 0);
        if (scenario === "legacy") {
           assert.equal(await page.$('[data-layer-id="other-records"]'), null, "Legacy references never become interactive rows");
        } else if (scenario === "empty") {
          assert.equal(await page.$eval("#gis-facility-empty", el => !el.hidden), true);
        } else if (scenario === "fallback") {
          assert.equal(await page.$$eval("#gis-map .gis-test-marker", markers => markers.length), 15, "Circle fallback markers attach to their group");
          await page.focus("#gis-map .gis-test-marker"); await page.keyboard.press("Enter");
          assert.equal(await page.$eval("#gis-details", el => el.hidden), false);
          await page.keyboard.press("Escape");
        } else {
           assert.equal(await page.$$eval(".gis-layer small", els => els.filter(el => el.textContent === document.getElementById("gis-page").dataset.layerError).length), 2, "Missing inline map payload and unsafe URL fail; hidden reference rows have no controls");
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
