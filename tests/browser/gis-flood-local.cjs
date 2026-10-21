"use strict";
// Geographic renderer checks against unmodified public HTML/manifest/PNG bytes.
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const assert = require("node:assert/strict");
const puppeteer = require(process.env.PUPPETEER_CORE_PATH || "puppeteer-core");
const repo = path.resolve(__dirname, "../..");
const root = path.resolve(process.argv[process.argv.indexOf("--root") + 1] || "_site");
const prepared = path.resolve(process.env.GIS_FLOOD_SCREENSHOT_DIR || "/tmp/kilo/flood-publication");
const report = JSON.parse(fs.readFileSync(path.join(repo, "datasets/GIS/flood/prepared/flood-susceptibility.registration.json")));
const osm = JSON.parse(fs.readFileSync(path.join(repo, "datasets/GIS/highways.geojson")));
osm.features = osm.features.filter(f => ["primary", "secondary", "tertiary"].includes(f.properties.highway) || f.properties.name === "Fire Tree Avenue" || f.properties.waterway === "river");
const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".geojson": "application/json", ".png": "image/png" };
const results = [];
const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL("http://localhost" + req.url).pathname);
  const file = path.resolve(root, "." + pathname, pathname.endsWith("/") ? "index.html" : "");
  if (!file.startsWith(root + path.sep)) return res.writeHead(403).end();
  fs.readFile(file, (error, bytes) => {
    if (error) return res.writeHead(404).end();
    res.setHeader("Content-Type", types[path.extname(file)] || "application/octet-stream"); res.end(bytes);
  });
});
(async () => {
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH, headless: true, args: ["--no-sandbox"] });
  try {
    for (const locale of ["", "fil/", "pag/"]) for (const width of [1440, 390]) {
      const page = await browser.newPage();
      await page.setViewport({ width, height: 1000 });
      await page.evaluateOnNewDocument(() => {
        document.addEventListener("load", event => {
          if (event.target.tagName !== "SCRIPT" || !/leaflet.*\.js/.test(event.target.src) || !window.L) return;
          const create = L.map;
          L.map = function (...args) { window.__localMap = create.apply(this, args); return window.__localMap; };
        }, true);
      });
      const errors = [];
      page.on("pageerror", e => errors.push(e.message));
      await page.setRequestInterception(true);
      page.on("request", request => {
        const url = request.url();
        if (/leaflet[^/]*\.js(?:\?|$)/.test(url)) return request.respond({ contentType: "text/javascript", headers: { "Access-Control-Allow-Origin": "*" }, body:
          fs.readFileSync(process.env.GIS_LEAFLET_JS_PATH) });
        if (/leaflet[^/]*\.css(?:\?|$)/.test(url)) return request.respond({ contentType: "text/css", headers: { "Access-Control-Allow-Origin": "*" }, body: fs.readFileSync(process.env.GIS_LEAFLET_CSS_PATH) });
        if (!url.startsWith(origin)) return request.abort();
        request.continue();
      });
      await page.goto(`${origin}/${locale}gis/`, { waitUntil: "networkidle0" });
      await page.waitForSelector('#gis-workspace[data-ready="true"]');
      const row = '.gis-layer[data-layer-id="flood-susceptibility"]';
      assert.deepEqual(errors, [], "Leaflet/runtime must initialize");
      assert.equal(await page.$eval(row + ' input[type="checkbox"]', e => e.disabled), false, "Local flood control enabled with genuine Leaflet");
      assert.equal(await page.$eval(row + ' input[type="checkbox"]', e => e.checked), false);
      await page.focus("#gis-layers-tab"); await page.keyboard.press("Enter");
      await page.$eval(row + ' input[type="checkbox"]', e => e.click());
      await page.waitForFunction(() => {
        const message = document.querySelector('[data-layer-id="flood-susceptibility"] small').textContent;
        return message === document.getElementById("gis-page").dataset.loaded || message === document.getElementById("gis-page").dataset.layerError;
      });
      assert.equal(await page.$eval(row + " small", e => e.textContent), await page.$eval("#gis-page", e => e.dataset.loaded), "Local imagery must actually load");
      const loaded = await page.evaluate(() => [...Object.values(window.__localMap._layers)].filter(l => l instanceof L.ImageOverlay).map(l => ({ url: l._url, opacity: l.options.opacity, loaded: l.getElement().complete && l.getElement().naturalWidth > 0, bounds: l.getBounds() })));
      assert.equal(loaded.length, 1); assert.equal(loaded[0].loaded, true); assert.equal(loaded[0].opacity, 0.6);
      assert.ok(loaded[0].url.includes("assets/gis/flood-susceptibility-0.png"));
      const legend = await page.$eval("#gis-legend", e => e.textContent);
      assert.ok(legend.includes("High") && legend.includes("Medium"), "Actual source classes appear in active legend");
      assert.equal(await page.evaluate(() => Number(window.__localMap.getPane("gis-hazards-raster").style.zIndex) < Number(window.__localMap.getPane("gis-facilities").style.zIndex)), true);
      await page.evaluate((osm, report) => {
        const map = window.__localMap;
        map.setView([16.020, 120.452], 13, { animate: false });
        L.geoJSON(osm, { style: { color: "#e000e0", weight: 2, opacity: 1, interactive: false } }).addTo(map);
        report.independent_candidates.points.forEach((p, i) => {
          const m = report.affine_pixel_to_lon_lat;
          const lon = p[0]*m[0][0] + p[1]*m[1][0] + m[2][0], lat = p[0]*m[0][1] + p[1]*m[1][1] + m[2][1];
          L.circleMarker([p[3], p[2]], { radius: 8, color: "#00ffff", fillOpacity: 0 }).bindTooltip("Independent OSM " + (i+1), { permanent: true }).addTo(map);
          L.polyline([[p[3], p[2]], [lat, lon]], { color: "#00ffff", weight: 3 }).addTo(map);
        });
        const banner = document.createElement("p"); banner.textContent = "Public generated raster; magenta = independent OSM roads/river, cyan = candidate central check points. Assumed WGS84; license not stated; no certified ground accuracy or safety inference.";
        banner.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:99999;background:#fff3b0;color:#111;padding:8px;font-size:13px"; document.body.appendChild(banner);
      }, osm, report);
      await page.focus("#gis-explore-tab"); await page.keyboard.press("Enter");
      await page.$eval("#gis-map", e => e.scrollIntoView({ block: "center" }));
      const prefix = `${locale.replace("/", "") || "en"}-${width}`;
      await page.screenshot({ path: path.join(prepared, `browser-${prefix}-overview.png`), fullPage: true });
      for (const [name, lat, lon] of [["central-checkpoints", 16.024, 120.456], ["pias-baloling-river", 16.035, 120.448], ["primicias", 15.998, 120.477], ["east-luyan-santa-maria-unresolved", 16.012, 120.476]]) {
        await page.evaluate((lat, lon) => window.__localMap.setView([lat, lon], 14, { animate: false }), lat, lon);
        await page.screenshot({ path: path.join(prepared, `browser-${prefix}-${name}.png`), fullPage: true });
      }
      const geography = await page.evaluate(report => {
        const map = window.__localMap, b = report.bounds;
        const overlay = Object.values(map._layers).find(l => l instanceof L.ImageOverlay);
        const image = overlay.getElement(), rect = image.getBoundingClientRect();
        const points = [[b.north, b.west, 0, 0], [b.south, b.east, rect.width, rect.height]];
        return points.map(([lat, lon, x, y]) => {
          const p = map.latLngToContainerPoint([lat, lon]), mr = map.getContainer().getBoundingClientRect();
          return Math.hypot(rect.left+x-mr.left-p.x, rect.top+y-mr.top-p.y);
        });
      }, report);
      assert.ok(geography.every(d => d < 2), "Actual north-up browser image corners agree with declared geographic bounds");
      assert.deepEqual(errors, []);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      results.push({ locale: locale || "en", width, leaflet: "1.9.4", imageryLoaded: true, initialOpacity: loaded[0].opacity, cornerScreenResidualPixels: geography });
      console.log(JSON.stringify(results.at(-1)));
      await page.close();
    }
    fs.writeFileSync(path.join(prepared, "browser-results.json"), JSON.stringify(results, null, 2) + "\n");
  } finally { await browser.close(); server.close(); }
})().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
