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
      if (process.env.GIS_MARKER_SCREENSHOT_DIR && locale === "" && width !== 320) await page.screenshot({ path: path.join(process.env.GIS_MARKER_SCREENSHOT_DIR, `gis-centered-markers-${width}.png`), fullPage: true });
      console.log(JSON.stringify({ root, locale: locale || "en", width, markers: measurements.length / 2, maxOffset: Math.max(...measurements.map(m => Math.max(Math.abs(m.dx), Math.abs(m.dy)))), badges: measurements.filter(m => m.badge).length / 2 }));
      await page.close();
    }
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
