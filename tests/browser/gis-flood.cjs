"use strict";
// Genuine Leaflet on the exact built artifact, plus unsupported-library/no-JS checks.
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");
const assert = require("node:assert/strict");
const root = path.resolve(process.argv[process.argv.indexOf("--root") + 1] || "_site");
const puppeteer = require(process.env.PUPPETEER_CORE_PATH || "puppeteer-core");
const official = "https://mapandan.gov.ph/disaster-awareness/";
const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".geojson": "application/json", ".png": "image/png" };
const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL("http://localhost" + req.url).pathname).replace(/\/+/g, "/");
  const file = path.resolve(root, "." + pathname, pathname.endsWith("/") ? "index.html" : "");
  if (!file.startsWith(root + path.sep)) return res.writeHead(403).end();
  fs.readFile(file, (error, data) => {
    if (error) return res.writeHead(404).end();
    res.setHeader("Content-Type", types[path.extname(file)] || "application/octet-stream"); res.end(data);
  });
});
(async () => {
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH, headless: true, args: ["--no-sandbox"] });
  try {
    const origin = `http://127.0.0.1:${server.address().port}`;
    for (const locale of ["", "fil/", "pag/"]) for (const width of [1440, 390]) for (const mode of ["leaflet", "unsupported", "no-js"]) {
      const page = await browser.newPage();
      await page.setViewport({ width, height: 900 });
      const errors = [], requests = [];
      page.on("pageerror", error => errors.push(error.message));
      page.on("request", request => requests.push(request.url()));
      if (mode === "no-js") await page.setJavaScriptEnabled(false);
      await page.setRequestInterception(true);
      page.on("request", request => {
        const url = request.url();
        if (/leaflet[^/]*\.js(?:\?|$)/.test(url)) {
          if (mode === "unsupported") return request.abort();
          return request.respond({ contentType: "text/javascript", headers: { "Access-Control-Allow-Origin": "*" }, body: fs.readFileSync(process.env.GIS_LEAFLET_JS_PATH) });
        }
        if (/leaflet[^/]*\.css(?:\?|$)/.test(url)) return request.respond({ contentType: "text/css", headers: { "Access-Control-Allow-Origin": "*" }, body: fs.readFileSync(process.env.GIS_LEAFLET_CSS_PATH) });
        if (!url.startsWith(origin)) return request.abort();
        request.continue();
      });
      await page.goto(`${origin}/${locale}gis/`, { waitUntil: "networkidle0" });
      assert.equal(await page.$eval("#gis-flood-reference a", a => a.href), official);
      assert.ok(await page.$eval("#gis-flood-reference p", p => p.textContent.length > 100));
      if (mode !== "no-js") {
        await page.waitForSelector('#gis-workspace[data-ready="true"]');
        const payload = await page.evaluate(() => {
          const layer = window.GIS_LAYERS.layers.find(l => l.id === "flood-susceptibility");
          return { layer, count: window.GIS_BARANGAYS.features.length };
        });
        assert.equal(payload.count, 15);
        assert.equal(payload.layer.type, "raster-image-overlay");
        assert.equal(payload.layer.available, true);
        assert.equal(payload.layer.visible_by_default, false);
        assert.equal(payload.layer.images.length, 1);
        assert.equal(payload.layer.images[0].url, "assets/gis/flood-susceptibility-0.png");
        await page.focus("#gis-layers-tab"); await page.keyboard.press("Enter");
        const row = '.gis-layer[data-layer-id="flood-susceptibility"]';
        assert.equal(await page.$eval(row + " a", a => a.href), official);
        assert.equal(await page.$eval(row + ' input[type="checkbox"]', e => e.checked), false);
        assert.equal(await page.$eval(row + ' input[type="checkbox"]', e => e.disabled), mode !== "leaflet");
        assert.ok(!(await page.$eval(row + ' small', e => e.textContent)).includes("failed"));
        await page.focus(row + " a");
        assert.equal(await page.evaluate(() => document.activeElement.href), official);
        if (mode === "leaflet") {
          assert.equal(await page.evaluate(() => L.version), "1.9.4");
          assert.ok(await page.$eval("#gis-map", map => map.getBoundingClientRect().height > 100));
          assert.ok(!requests.some(url => /flood-susceptibility-0\.png/.test(url)), "Default-off flood artwork is lazy loaded");
          await page.$eval(row + ' input[type="checkbox"]', e => e.click());
          await page.waitForFunction(() => [...document.querySelectorAll("#gis-map img")].some(img => /flood-susceptibility-0\.png/.test(img.src) && img.complete && img.naturalWidth === 2018));
          assert.ok((await page.$eval("#gis-legend", e => e.textContent)).includes("High"));
          assert.ok((await page.$eval("#gis-legend", e => e.textContent)).includes("Medium"));
        }
      }
      assert.equal(requests.filter(url => /flood-susceptibility-0\.png/.test(url)).length, mode === "leaflet" ? 1 : 0);
      assert.ok(!requests.some(url => /Mapandan-Hazard-Map|\.kmz(?:\?|$)/i.test(url)), "No original JPEG or KMZ fetched by browser");
      assert.deepEqual(errors, []);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth), false);
      if (process.env.GIS_FLOOD_SCREENSHOT_DIR) {
        fs.mkdirSync(process.env.GIS_FLOOD_SCREENSHOT_DIR, { recursive: true });
        await page.screenshot({ path: path.join(process.env.GIS_FLOOD_SCREENSHOT_DIR, `flood-${locale.replace("/", "") || "en"}-${width}-${mode}.png`), fullPage: true });
      }
      console.log(JSON.stringify({ locale: locale || "en", width, mode, source: official, artworkRequests: mode === "leaflet" ? 1 : 0 }));
      await page.close();
    }
  } finally { await browser.close(); server.close(); }
})().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
