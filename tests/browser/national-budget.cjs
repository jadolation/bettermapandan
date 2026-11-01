"use strict";
// Exact staged HTML and scripts; API responses are intercepted raw fixtures.
// This suite does not establish live CORS, PDF availability, or geographic accuracy.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const puppeteer = require(process.env.PUPPETEER_CORE_PATH || "puppeteer-core");

const rootIndex = process.argv.indexOf("--root");
assert.ok(rootIndex >= 0 && process.argv[rootIndex + 1], "Pass --root _site");
const root = fs.realpathSync(path.resolve(process.argv[rootIndex + 1]));
const fixtureRoot = path.resolve(__dirname, "../fixtures/national-budget");
const datasets = ["dpwh", "fmr", "hfep", "nia"];
const locales = ["en", "fil", "pag"];
const widths = [320, 375, 430, 768, 1440];
const mime = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".woff2": "font/woff2", ".webmanifest": "application/manifest+json" };
const clone = value => JSON.parse(JSON.stringify(value));
const route = locale => `/${locale === "en" ? "" : locale + "/"}transparency/national-budget/`;

function stagedChecks() {
  for (const locale of locales) {
    const html = fs.readFileSync(path.join(root, route(locale), "index.html"), "utf8");
    assert.ok(!/\{(?:NATIONAL_BUDGET_|\{)[^}]+\}/.test(html), `${locale}: unresolved page placeholders`);
    const scripts = [...html.matchAll(/<script\b[^>]*\bsrc=["']([^"']*national-budget[^"']*)["'][^>]*>/g)].map(match => match[1]);
    assert.equal(scripts.length, 3, `${locale}: three feature scripts`);
    assert.deepEqual(scripts.map(src => path.basename(src)), ["national-budget-normalize.min.js", "national-budget-api.min.js", "national-budget-ui.min.js"]);
    for (const src of scripts) {
      const asset = new URL(src, "http://localhost" + route(locale)).pathname;
      assert.ok(fs.statSync(path.join(root, asset)).isFile(), `${locale}: staged script ${asset}`);
    }
  }
  for (const forbidden of ["tests/fixtures/national-budget", "tests/browser/national-budget.cjs", "src/data/pag-review.json", ".kilo", "_build"]) {
    assert.equal(fs.existsSync(path.join(root, forbidden)), false, `${forbidden} must not be staged`);
  }
}

function createServer() {
  return http.createServer((request, response) => {
    try {
      if (!["GET", "HEAD"].includes(request.method)) return response.writeHead(405).end();
      const pathname = decodeURIComponent(new URL("http://localhost" + request.url).pathname);
      let file = path.resolve(root, "." + pathname);
      if (!file.startsWith(root + path.sep)) return response.writeHead(403).end();
      if (fs.statSync(file).isDirectory()) file = path.join(file, "index.html");
      file = fs.realpathSync(file);
      if (!file.startsWith(root + path.sep)) return response.writeHead(403).end();
      response.setHeader("Content-Type", mime[path.extname(file)] || "application/octet-stream");
      response.setHeader("Cache-Control", "no-store");
      response.end(request.method === "HEAD" ? undefined : fs.readFileSync(file));
    } catch { response.writeHead(404).end(); }
  });
}

async function text(page, selector) {
  return page.$eval(selector, element => element.textContent);
}

async function keys(page, selector = "#nb-results") {
  return page.$$eval(`${selector} > [data-project-key]`, elements => elements.map(element => element.dataset.projectKey));
}

async function disclose(page, selector, open = true) {
  const disclosure = await page.$(selector);
  assert.ok(disclosure, `Missing native disclosure ${selector}`);
  assert.equal(await disclosure.evaluate(element => element.tagName), "DETAILS");
  if (await disclosure.evaluate(element => element.open) !== open) {
    const summary = await disclosure.$(":scope > summary");
    assert.ok(summary, `${selector}: direct summary`);
    await summary.focus();
    await page.keyboard.press("Enter");
    await page.waitForFunction((element, open) => element.open === open, {}, disclosure, open);
    assert.equal(await summary.evaluate(element => document.activeElement === element), true, `${selector}: disclosure retains keyboard focus`);
    await summary.dispose();
  }
  await disclosure.dispose();
}

async function reveal(page, selector) {
  const target = await page.$(selector);
  assert.ok(target, `Missing control ${selector}`);
  const disclosures = await page.$$("details");
  for (const disclosure of disclosures) {
    if (await disclosure.evaluate((element, target) => element !== target && element.contains(target) && !element.open, target)) {
      const summary = await disclosure.$(":scope > summary");
      await summary.focus();
      await page.keyboard.press("Enter");
      await page.waitForFunction(element => element.open, {}, disclosure);
      await summary.dispose();
    }
    await disclosure.dispose();
  }
  await target.dispose();
}

async function visible(page, selector) {
  return page.$eval(selector, element => {
    if (!element.checkVisibility()) return false;
    for (let parent = element.parentElement; parent; parent = parent.parentElement) {
      if (parent.tagName === "DETAILS" && !parent.open && !parent.querySelector(":scope > summary").contains(element)) return false;
    }
    return true;
  });
}

async function visibleText(page, selector) {
  return page.$eval(selector, element => element.innerText);
}

async function input(page, selector, value) {
  await reveal(page, selector);
  await page.$eval(selector, (element, value) => {
    element.value = value;
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  }, value);
}

async function layout(page, context) {
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${context}: horizontal overflow`);
  assert.ok(await page.$$eval("#nb-filters input, #nb-filters select", elements => elements.every(element => element.labels && element.labels.length)), `${context}: labeled controls`);
  assert.ok(await page.$eval("#nb-status", element => element.getAttribute("aria-live") === "polite" || element.getAttribute("role") === "status"), `${context}: polite results announcement`);
}

function fixtures() {
  return Object.fromEntries(datasets.map(dataset => [dataset, JSON.parse(fs.readFileSync(path.join(fixtureRoot, `${dataset}-list.json`), "utf8"))]));
}

async function openPage(browser, origin, locale, width, options = {}) {
  const page = await browser.newPage();
  page.setDefaultTimeout(15000);
  await page.setViewport({ width, height: 1000 });
  if (options.noJS) await page.setJavaScriptEnabled(false);
  const state = { requests: [], errors: [], localFailures: [], interceptionErrors: [], blocked: [], release: null };
  const responses = options.responses || fixtures();
  await page.evaluateOnNewDocument(() => {
    const create = URL.createObjectURL.bind(URL), revoke = URL.revokeObjectURL.bind(URL);
    const blobs = new Map();
    window.__budgetDownloads = [];
    window.__budgetRevoked = [];
    URL.createObjectURL = blob => { const url = create(blob); blobs.set(url, blob); return url; };
    URL.revokeObjectURL = url => { window.__budgetRevoked.push(url); return revoke(url); };
    const click = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function () {
      if (this.download && blobs.has(this.href)) {
        const entry = { filename: this.download, url: this.href, text: null };
        window.__budgetDownloads.push(entry);
        blobs.get(this.href).arrayBuffer().then(value => { entry.text = new TextDecoder("utf-8", { ignoreBOM: true }).decode(value); });
        return;
      }
      return click.call(this);
    };
  });
  page.on("pageerror", error => state.errors.push(error.message));
  page.on("console", message => {
    // Loopback preview intentionally differs from the production manifest origin.
    if (message.type() === "error" && !/Failed to load resource|Loading a manifest from 'https:\/\/bettermapandan\.org\/site\.webmanifest' violates/.test(message.text())) state.errors.push(message.text());
  });
  page.on("response", response => {
    if (response.url().startsWith(origin + "/") && response.status() >= 400) state.localFailures.push(`${response.status()} ${response.url()}`);
  });
  await page.setRequestInterception(true);
  page.on("request", request => {
    (async () => {
      const url = new URL(request.url());
      if (url.origin === origin) return request.continue();
      if (url.protocol === "data:" || url.protocol === "blob:") return request.continue();
      const match = url.pathname.match(/^\/api\/v1\/hgab\/2027\/datasets\/(dpwh|fmr|hfep|nia)\/projects(?:\/([^/]+))?\/?$/);
      if (url.origin !== "https://budget.bettergov.ph" || !match) {
        state.blocked.push(request.url());
        return request.abort();
      }
      const [, dataset, encodedId] = match;
      const id = encodedId ? decodeURIComponent(encodedId) : null;
      const record = { dataset, id, url: request.url(), offset: Number(url.searchParams.get("offset") || 0) };
      state.requests.push(record);
      assert.equal(request.method(), "GET", "API uses read-only GET");
      assert.equal(request.headers().authorization, undefined, "No API credentials");
      if (!id) {
        assert.equal(url.searchParams.get("q"), "Mapandan");
        assert.equal(url.searchParams.get("limit"), "50");
        assert.equal(url.searchParams.has("region"), false, "Do not hide review rows server-side");
      }
      if ((options.hold || options.holdDataset === dataset) && !id) await new Promise(resolve => {
        const previous = state.release;
        state.release = () => { if (previous) previous(); resolve(); };
      });
      const override = options.respond && await options.respond(record, state);
      if (override) return request.respond({ headers: { "Access-Control-Allow-Origin": "*" }, contentType: "application/json", ...override });
      const envelope = id
        ? JSON.parse(fs.readFileSync(path.join(fixtureRoot, `dpwh-detail-${id.split(":").at(-1)}.json`), "utf8"))
        : responses[dataset];
      return request.respond({ headers: { "Access-Control-Allow-Origin": "*" }, contentType: "application/json", body: JSON.stringify(envelope) });
    })().catch(async error => {
      state.interceptionErrors.push(error.stack || error.message);
      if (!request.isInterceptResolutionHandled()) await request.abort();
    });
  });
  await page.goto(origin + route(locale), { waitUntil: "domcontentloaded" });
  return { page, state, responses };
}

async function ready(page) {
  await page.waitForFunction(() => {
    const element = document.querySelector("#national-budget-page");
    return element && element.dataset.state && element.dataset.state !== "loading";
  });
}

function clean(state) {
  assert.deepEqual(state.interceptionErrors, [], "Fixture interception errors");
  assert.deepEqual(state.errors, [], "No unexpected console/page errors");
  assert.deepEqual(state.localFailures, [], "No missing staged resources");
  assert.equal(state.requests.some(request => /(?:bettergov\.ph|https:)/.test(request.id || "")), false);
}

async function download(page, selector) {
  await reveal(page, selector);
  const count = await page.evaluate(() => window.__budgetDownloads.length);
  await page.click(selector);
  await page.waitForFunction(count => window.__budgetDownloads.length > count && window.__budgetDownloads[count].text !== null, {}, count);
  await page.waitForFunction(count => window.__budgetRevoked.includes(window.__budgetDownloads[count].url), {}, count);
  return page.evaluate(count => window.__budgetDownloads[count], count);
}

function parseCSV(value) {
  const result = [], row = [];
  let cell = "", quoted = false;
  for (let index = value.charCodeAt(0) === 0xfeff ? 1 : 0; index < value.length; index++) {
    const char = value[index];
    if (char === '"') {
      if (quoted && value[index + 1] === '"') { cell += '"'; index++; }
      else quoted = !quoted;
    } else if (char === "," && !quoted) { row.push(cell); cell = ""; }
    else if (char === "\r" && value[index + 1] === "\n" && !quoted) {
      row.push(cell); result.push(row.splice(0)); cell = ""; index++;
    } else cell += char;
  }
  assert.equal(quoted, false, "Balanced CSV quoting");
  if (cell || row.length) { row.push(cell); result.push(row); }
  return result;
}

async function citizenHierarchy(page, responses, labels) {
  assert.equal(await page.$$eval("#national-budget-page details[open]", elements => elements.length), 0, "Initial view keeps every source/advanced disclosure closed");
  for (const selector of ["#nb-coverage", "#nb-more-filters", "#nb-technical-data", "#nb-notices"]) {
    assert.equal(await page.$eval(selector, element => element.tagName), "DETAILS", `${selector}: native progressive disclosure`);
  }
  assert.equal(await visible(page, "#nb-coverage-status"), true, "Compact coverage remains visible");
  assert.ok((await visibleText(page, "#nb-coverage-status")).trim());
  for (const selector of ["#nb-availability", "#nb-diagnostics", "#nb-export", "#nb-export-metadata"]) {
    assert.equal(await visible(page, selector), false, `${selector}: not upfront`);
  }
  assert.equal(await page.$eval("#nb-review-section", element => element.hidden), true, "No empty geography-review section");
  assert.equal(await visible(page, "#nb-next"), false, "Two-project result has no redundant pagination");
  const initialText = await visibleText(page, "#national-budget-page");
  for (const value of [responses.dpwh.meta.source_commit, responses.dpwh.meta.built_at, "nep_evidence_review", "house-reading:3923", "house-reading:3959", "amount_same", "exact_candidate", labels.reference_key, labels.confidence].filter(Boolean)) {
    assert.ok(!initialText.includes(value), `Technical value hidden initially: ${value}`);
  }
  assert.equal(await page.$$eval('#nb-filters input[type="search"]', elements => elements.filter(element => element.checkVisibility()).length), 1, "One visible basic project/barangay search");
  assert.equal(await visible(page, "#nb-search"), true);
  for (const selector of ["#nb-search", "#nb-category", "#nb-more-filters > summary", '.nb-project > details > summary']) {
    assert.ok(await page.$eval(selector, element => element.getBoundingClientRect().height >= 44), `${selector}: usable touch target after CSS compilation`);
  }
  assert.equal(await page.$eval("#nb-search", element => element.labels[0].textContent.trim()), labels.title_search, "Meaningful localized search label");
  const warning = 'article[data-project-key="dpwh:house-reading:3923"] .nb-source-review';
  assert.equal(await visible(page, warning), true, "Source warning visible while every disclosure is closed");
  assert.equal((await visibleText(page, warning)).trim(), labels.source_review_pending, "Concise localized source-review label");
  for (const row of responses.dpwh.data.rows) {
    const card = `article[data-project-key="dpwh:${row.id}"]`;
    assert.equal((await visibleText(page, card + " .nb-project-title")).trim(), row.title, "Official project title visible before source metadata");
    assert.equal(await page.$$eval(card + " .nb-project-amounts > div", elements => elements.length), 2, "Exactly two proposal amount columns");
    for (const version of ["nep", "house"]) {
      const selector = `${card} .nb-project-amounts [data-version="${version}"]`;
      assert.equal(await visible(page, selector), true, "Proposal amounts visible without disclosure");
      assert.ok((await visibleText(page, selector)).includes(new Intl.NumberFormat("en").format(row[version + "_php"])), "Exact 44M/5M proposal amount");
    }
    assert.equal(await page.$eval(card + " .nb-project-amounts", element => getComputedStyle(element).gridTemplateColumns.split(/\s+/).length), 2, "Amounts stay in two readable columns");
    assert.equal(await visible(page, card + " .nb-project-record"), false, "Full record/source metadata starts disclosed");
  }
  await disclose(page, "#nb-coverage");
  assert.equal(await page.$eval("#nb-coverage > summary", element => {
    const style = getComputedStyle(element);
    return style.outlineStyle === "solid" && Number.parseFloat(style.outlineWidth) >= 3;
  }), true, "Keyboard focus is visible in compiled CSS");
  const coverageText = await visibleText(page, "#nb-availability");
  for (const dataset of datasets) assert.ok(coverageText.includes(dataset.toUpperCase()), "Coverage explains every dataset on request");
  for (const value of [responses.dpwh.meta.source_commit, responses.dpwh.meta.built_at, "source_commit", "http_", "sum_disagreement"]) assert.ok(!coverageText.includes(value), "Coverage uses plain states instead of technical diagnostics");
  await disclose(page, "#nb-coverage", false);
  assert.equal(await page.evaluate(() => {
    const before = (a, b) => !!(document.querySelector(a).compareDocumentPosition(document.querySelector(b)) & Node.DOCUMENT_POSITION_FOLLOWING);
    return before("#nb-summary", "#nb-filters") && before("#nb-filters", "#nb-results") && before("#nb-results", "#nb-notices") && before("#nb-notices", "#nb-technical-data") && document.querySelector("#nb-technical-data").contains(document.querySelector("#nb-export"));
  }), true, "Projects and simple comparisons precede notices, diagnostics and exports");
}

async function normalCase(browser, origin, locale, width) {
  const { page, state, responses } = await openPage(browser, origin, locale, width);
  try {
    await ready(page);
    assert.deepEqual((await keys(page)).sort(), ["dpwh:house-reading:3923", "dpwh:house-reading:3959"]);
    assert.equal(await page.$eval("#national-budget-page", element => element.dataset.selectedCount), "2");
    assert.equal(state.requests.filter(request => !request.id).length, 4, "One list per dataset");
    assert.equal(state.requests.filter(request => request.id).length, 0, "Details are lazy");
    const labels = await page.evaluate(() => window.NATIONAL_BUDGET_LABELS);
    assert.ok(labels && typeof labels === "object", "Localized feature payload");
    await citizenHierarchy(page, responses, labels);
    const summaries = await text(page, '#nb-summary [data-stage="hgab3"]');
    const number = new Intl.NumberFormat(locale === "pag" ? "en" : locale);
    assert.ok(summaries.includes(number.format(49000000)), "Third-reading known subtotal is exactly 49M");
    assert.ok(!summaries.includes(number.format(98000000)), "Versions must never be added");
    for (const metric of ["nep", "house"]) assert.equal(await page.$eval(`#nb-summary [data-stage="hgab3"] [data-metric="${metric}"]`, element => element.dataset.value), "49000000");
    assert.equal(await page.$eval('#nb-summary [data-stage="hgab3"] [data-metric="delta"]', element => element.dataset.value), "0");
    assert.equal(await page.$$eval('#nb-summary [data-stage="hgab2"]', elements => elements.length), 0, "No empty second-reading card beside populated third-reading summary");
    const notices = await text(page, "#nb-notices");
    assert.ok(notices.includes(responses.dpwh.meta.notice), "Verbatim upstream notice");
    for (const disclaimer of responses.dpwh.disclaimers) assert.ok(notices.includes(disclaimer.body), "Verbatim upstream disclaimer");
    await disclose(page, "#nb-notices");
    assert.ok((await visibleText(page, "#nb-notice-content")).includes(responses.dpwh.meta.notice), "Original notice is readable when requested");
    for (const paragraph of [responses.dpwh.meta.notice, ...responses.dpwh.disclaimers.map(disclaimer => disclaimer.body)]) {
      assert.equal(await page.$$eval("#nb-notice-content p", (elements, paragraph) => elements.filter(element => element.textContent === paragraph).length, paragraph), 1, "Repeated dataset notices become one readable paragraph");
    }
    assert.equal(await page.$$eval("#nb-notice-content pre, #nb-notice-content dl", elements => elements.length), 0, "Legal notices are paragraphs, not raw JSON/key-value dumps");
    assert.equal(await page.$$eval("#nb-notice-content strong, #nb-notice-content h3", elements => elements.some(element => /^(id|body|url)$/i.test(element.textContent.trim()))), false, "No raw object-key headings in notices");
    await disclose(page, "#nb-notices", false);
    await layout(page, `${locale}/${width}`);
    assert.ok(await page.$$eval('a[href*="national-budget"]', elements => elements.some(element => element.getAttribute("aria-current") === "page" || element.classList.contains("active"))), "Active National Budget tab");
    assert.ok(await page.$$eval('select option', elements => elements.some(element => /national-budget/.test(element.value) && element.selected)), "Mobile National Budget option selected");
    assert.equal(await page.$eval('link[rel="canonical"]', element => new URL(element.href).pathname), route(locale));
    const links = await page.$$eval("a[href]", elements => elements.map(element => ({ href: element.href, target: element.target, rel: element.rel })));
    for (const href of ["https://budget.bettergov.ph/docs", "https://budget.bettergov.ph/hgab/2027/methodology"]) assert.ok(links.some(link => link.href === href), `Static source link: ${href}`);
    for (const row of responses.dpwh.data.rows) {
      for (const href of [row.url, row.pdf_url.nep, row.pdf_url.hgab3]) assert.ok(links.some(link => link.href === href), `Correct source and PDF file position: ${href}`);
    }
    const listCalls = state.requests.filter(request => !request.id).length;
    await input(page, "#nb-search", "Amanoaoac");
    assert.deepEqual(await keys(page), ["dpwh:house-reading:3923"]);
    await input(page, "#nb-search", "not-a-real-project-123");
    assert.equal((await keys(page)).length, 0, "Local no-match is distinct from upstream empty");
    assert.ok((await text(page, "#nb-status")).trim());
    await input(page, "#nb-search", "");
    await disclose(page, "#nb-more-filters");
    for (const selector of ["#nb-office", "#nb-status-filter", "#nb-include-review"]) assert.equal(await visible(page, selector), false, `${selector}: no-choice control hidden even with advanced filters open`);
    await input(page, "#nb-barangay", "Poblacion");
    assert.deepEqual(await keys(page), ["dpwh:house-reading:3959"], "Barangay search matches explicit title only");
    await input(page, "#nb-barangay", "");
    await page.select("#nb-category", "fmr");
    assert.equal((await keys(page)).length, 0);
    await page.select("#nb-category", "");
    const office = responses.dpwh.data.rows[0].office;
    await page.select("#nb-office", office);
    assert.equal((await keys(page)).length, 2);
    await page.select("#nb-office", "");
    await page.select("#nb-status-filter", responses.dpwh.data.rows[0].status_label);
    assert.equal((await keys(page)).length, 2);
    await page.select("#nb-status-filter", "");
    assert.equal(state.requests.filter(request => !request.id).length, listCalls, "All controls are local");
    const detail = 'details[data-project-key="dpwh:house-reading:3923"]';
    await disclose(page, detail);
    await page.waitForSelector(detail + ' .nb-detail[data-state="ready"]');
    assert.equal((await visibleText(page, detail + " > summary")).trim(), labels.details);
    assert.ok((await visibleText(page, detail)).includes("NEP amount still being checked against the scan"), "Readable upstream evidence label outside nested technical metadata");
    assert.ok((await visibleText(page, detail)).includes("nep_evidence_review"), "Exact flag retained in expanded source details");
    assert.equal(await visible(page, detail + " .nb-project-technical pre"), false, "Raw evidence stays behind a second technical disclosure");
    assert.equal(await page.$eval(detail, element => element.open), true, "Keyboard opens native details");
    assert.equal(state.requests.filter(request => request.id).length, 1);
    assert.ok(state.requests.find(request => request.id).url.endsWith("house-reading%3A3923"), "ID encoded exactly once");
    const detailLinks = await page.$$eval('article[data-project-key="dpwh:house-reading:3923"] a[href]', elements => elements.map(element => ({ href: element.href, target: element.target, rel: element.rel })));
    const row = responses.dpwh.data.rows.find(row => row.id === "house-reading:3923");
    for (const href of [row.url, row.pdf_url.nep, row.pdf_url.hgab3]) assert.ok(detailLinks.some(link => link.href === href), `Exact upstream/page-position link ${href}`);
    for (const href of [row.pdf_url.nep, row.pdf_url.hgab3]) {
      const selector = `${detail} a[href="${href}"]`;
      assert.equal(await visible(page, selector), true, "Expanded project makes source PDFs accessible without raw JSON");
      assert.ok((await visibleText(page, selector)).trim(), "PDF has readable link text");
    }
    assert.ok((await visibleText(page, detail + " .nb-project-record")).includes(row.title));
    assert.ok((await visibleText(page, detail + " .nb-project-record")).includes(row.office));
    assert.equal(await page.$$eval("#nb-notice-content p", (elements, paragraph) => elements.filter(element => element.textContent === paragraph).length, responses.dpwh.meta.notice), 1, "Loading project sources does not duplicate the shared notice");
    await disclose(page, detail + " .nb-project-technical");
    assert.ok((await visibleText(page, detail + " .nb-project-technical")).includes(row.id), "Technical source record still available on request");
    await disclose(page, detail + " .nb-project-technical", false);
    for (const link of detailLinks.filter(link => link.target === "_blank")) {
      assert.ok(link.rel.includes("noopener") && link.rel.includes("noreferrer"), "External tab protection");
    }
    await page.focus(detail + " > summary"); await page.keyboard.press("Enter");
    await page.keyboard.press("Enter");
    assert.equal(state.requests.filter(request => request.id).length, 1, "Reopening uses cached detail");
    const csv = await download(page, "#nb-export");
    assert.equal(csv.filename, "better-mapandan-national-budget-2027-mapandan.csv");
    assert.equal(csv.text.charCodeAt(0), 0xfeff, "UTF-8 BOM");
    assert.ok(csv.text.endsWith("\r\n") && !csv.text.replaceAll("\r\n", "").includes("\n"), "CRLF CSV record endings");
    const cells = parseCSV(csv.text);
    assert.equal(cells.length, 3);
    assert.deepEqual(cells[0], ["external_key", "fiscal_year", "dataset", "title", "program", "office", "nep_php", "house_php", "house_stage", "delta_php", "bridge_group", "held", "flags", "project_url", "nep_pdf_url", "house_pdf_url", "source_snapshot_date"]);
    assert.ok(cells.slice(1).every(row => row.length === 17));
    const metadata = JSON.parse((await download(page, "#nb-export-metadata")).text);
    assert.ok(JSON.stringify(metadata).includes(responses.dpwh.meta.source_commit), "Companion snapshot identity");
    assert.ok(JSON.stringify(metadata).includes(responses.dpwh.disclaimers[0].body), "Companion verbatim disclaimer");
    clean(state);
  } finally { await page.close(); }
}

async function noJSCase(browser, origin, locale) {
  const { page, state } = await openPage(browser, origin, locale, 375, { noJS: true });
  try {
    assert.equal(state.requests.length, 0, "No-JS never requests API");
    assert.ok(await page.$eval("noscript", element => element.textContent.trim().length > 30), "Meaningful localized no-JS explanation");
    assert.ok(await page.$$eval("#nb-filters input, #nb-filters select, #nb-export, #nb-export-metadata", elements => elements.length > 4 && elements.every(element => element.matches(":disabled"))), "Live controls disabled before JS");
    assert.ok(await page.$$eval('a[href="https://budget.bettergov.ph/hgab/2027/methodology"]', elements => elements.length > 0), "Source/methodology survives without JS");
    clean(state);
  } finally { await page.close(); }
}

function synthetic() {
  const responses = fixtures(), template = responses.dpwh.data.rows[0];
  function row(dataset, id, amount, extra = {}) {
    return { ...clone(template), dataset, id, title: `Synthetic Mapandan project ${id}`, office: "Synthetic office", nep_php: amount, hgab2_php: amount, hgab3_php: amount, house_php: amount, api_php: amount, delta_php: amount === null ? null : 0, flags: [], ...extra };
  }
  responses.dpwh.data.rows = Array.from({ length: 55 }, (_, index) => row("dpwh", `synthetic:${String(index).padStart(3, "0")}`, (index + 1) * 1000000));
  Object.assign(responses.dpwh.data.rows[0], {
    title: '\t=HYPERLINK("https://example.invalid","Mapandan, formula")',
    flags: ['\t@SUM(1,2)', 'quote" and newline\nflag'],
    url: "javascript:alert(1)",
    pdf_url: { nep: "https://evil.invalid/nep.pdf", hgab2: "javascript:alert(2)", hgab3: "https://user:password@budget-assets.bettergov.ph/fake.pdf" }
  });
  responses.dpwh.data.rows[1].title = '<img src=x onerror="window.__budgetXSS=1"> Mapandan synthetic';
  responses.fmr.data.rows = [
    row("fmr", "stage-two", 8000000, { nep_php: 9000000, delta_php: -1000000, bridge_group: "decreased", trace: "candidate_decrease", status_label: "Synthetic decrease candidate" }),
    row("fmr", "missing-region", 4000000, { region: null, region_key: null }),
    row("fmr", "office-only", 6000000, { title: "Synthetic project elsewhere", office: "Mapandan synthetic office" }),
    row("fmr", "excluded-region", 10000000, { region: "Region II", region_key: "II" }),
    row("fmr", "zero", 0),
    row("fmr", "unknown", null)
  ];
  for (const dataset of datasets) {
    const envelope = responses[dataset], rows = envelope.data.rows;
    Object.assign(envelope.meta, { total: rows.length, returned: rows.length, offset: 0 });
    envelope.data.total = rows.length;
    envelope.data.next_offset = null;
    for (const version of ["nep", "hgab2", "hgab3", "api"]) {
      const numbers = rows.map(row => row[`${version}_php`]).filter(value => typeof value === "number");
      envelope.data.sums[`${version}_php`] = numbers.length ? numbers.reduce((a, b) => a + b, 0) : null;
      envelope.data.sums.rows_with_amount[version] = numbers.length;
    }
  }
  return responses;
}

async function syntheticCase(browser, origin, locale) {
  const responses = synthetic();
  const { page, state } = await openPage(browser, origin, locale, 430, {
    responses,
    respond(request) {
      if (request.dataset !== "dpwh" || request.id) return null;
      const envelope = clone(responses.dpwh), rows = envelope.data.rows;
      envelope.data.rows = rows.slice(request.offset, request.offset + 50);
      envelope.meta.offset = request.offset;
      envelope.meta.returned = envelope.data.rows.length;
      envelope.data.next_offset = request.offset === 0 ? 50 : null;
      return { body: JSON.stringify(envelope) };
    }
  });
  try {
    await ready(page);
    assert.equal(await page.$eval("#national-budget-page", element => element.dataset.state), "ready", "Synthetic complete pagination reconciles raw sums");
    assert.equal(await page.$eval("#national-budget-page", element => element.dataset.selectedCount), "58");
    assert.equal((await keys(page)).length, 20, "Local UI page contains twenty records");
    assert.deepEqual(state.requests.filter(request => request.dataset === "dpwh").map(request => request.offset), [0, 50], "Raw pages followed sequentially");
    assert.equal((await keys(page, "#nb-review-results")).length, 2, "Both missing-region and office-only matches remain visible for review");
    assert.equal(await page.$eval("#nb-review-section", element => element.hidden), false, "Unverified matches expose the review section");
    assert.ok(!(await text(page, "#nb-results")).includes("excluded-region"));
    assert.equal(await page.evaluate(() => window.__budgetXSS), undefined, "Untrusted title never executes");
    assert.equal(await page.$$eval("#nb-results img", elements => elements.length), 0, "Title rendered as text");
    const stage2 = await text(page, '#nb-summary [data-stage="hgab2"]');
    const stage3 = await text(page, '#nb-summary [data-stage="hgab3"]');
    assert.ok(stage2.includes("8,000,000"), "Second-reading subtotal excludes review records");
    assert.ok(stage2.includes("9,000,000"), "Second-reading NEP denominator is separate");
    assert.ok(stage3.includes("1,540,000,000"), "Third-reading subtotal remains separate");
    assert.ok(!(await text(page, "#nb-summary")).includes("1,548,000,000"), "No mixed-reading headline");
    const calls = state.requests.length;
    await disclose(page, "#nb-more-filters");
    assert.equal(await visible(page, "#nb-office"), true, "Office filter appears with meaningful choices");
    assert.equal(await visible(page, "#nb-status-filter"), true, "Status filter appears with meaningful choices");
    assert.equal(await visible(page, "#nb-include-review"), true, "Review scope control appears for unverified records");
    await page.select("#nb-office", "Mapandan synthetic office");
    assert.equal((await keys(page)).length, 0, "Office-only match is outside default monetary/main scope");
    assert.deepEqual(await keys(page, "#nb-review-results"), ["fmr:office-only"]);
    await page.select("#nb-office", "");
    await page.select("#nb-status-filter", "Synthetic decrease candidate");
    assert.deepEqual(await keys(page), ["fmr:stage-two"], "Visible status filter selects its readable status");
    await page.select("#nb-status-filter", "");
    await page.select("#nb-sort", "house-desc");
    assert.equal((await keys(page))[0], "dpwh:synthetic:054");
    await page.click("#nb-next");
    assert.equal((await keys(page))[0], "dpwh:synthetic:034");
    await page.select("#nb-category", "fmr");
    assert.equal((await keys(page)).length, 3, "Filter resets UI pagination");
    assert.equal(await page.$eval("#nb-prev", element => element.disabled), true);
    await page.select("#nb-sort", "house-asc");
    assert.deepEqual(await keys(page), ["fmr:zero", "fmr:stage-two", "fmr:unknown"], "Zero sorts as zero; null sorts last");
    await page.select("#nb-category", "");
    const firstCSV = await download(page, "#nb-export");
    let cells = parseCSV(firstCSV.text), header = cells[0];
    assert.equal(cells.length - 1, 58, "Export includes selected rows beyond visible twenty");
    const objects = cells.slice(1).map(values => Object.fromEntries(header.map((key, index) => [key, values[index]])));
    assert.equal(objects.find(row => row.external_key === "fmr:zero").house_php, "0");
    assert.equal(objects.find(row => row.external_key === "fmr:unknown").house_php, "");
    assert.equal(objects.find(row => row.external_key === "fmr:stage-two").delta_php, "-1000000", "Numeric negatives remain numeric");
    const formula = objects.find(row => row.external_key === "dpwh:synthetic:000");
    assert.match(formula.title, /^'\s*=/, "Formula-prefixed textual cells neutralized");
    assert.ok(formula.flags.includes('quote" and newline\nflag') || formula.flags.includes('quote\\" and newline\\nflag'), "CSV quoting retains flag text");
    assert.equal(formula.project_url, "", "Unsafe source URL not exported as a link");
    assert.equal(formula.house_pdf_url, "", "Unsafe/credentialed document URL rejected");
    assert.ok(objects.every(row => !["fmr:missing-region", "fmr:office-only", "fmr:excluded-region"].includes(row.external_key)));
    await page.focus("#nb-include-review"); await page.keyboard.press("Space");
    assert.equal(await page.$eval("#nb-include-review", element => element.checked), true, "Keyboard review-scope control");
    assert.equal(await page.$eval("#national-budget-page", element => element.dataset.selectedCount), "60");
    assert.ok((await text(page, '#nb-summary [data-stage="hgab2"]')).includes("18,000,000"), "Explicit scope includes both unverified matches");
    cells = parseCSV((await download(page, "#nb-export")).text);
    assert.equal(cells.length - 1, 60);
    const ids = cells.slice(1).map(row => row[header.indexOf("external_key")]);
    assert.ok(ids.includes("fmr:missing-region") && ids.includes("fmr:office-only"));
    assert.ok(!ids.includes("fmr:excluded-region"));
    const metadata = JSON.parse((await download(page, "#nb-export-metadata")).text);
    assert.ok(JSON.stringify(metadata).includes("hgab2") && JSON.stringify(metadata).includes("hgab3"));
    assert.equal(metadata.filters.includeReview, true);
    assert.equal(metadata.selected_count, 60);
    assert.equal(metadata.datasets.find(item => item.dataset === "fmr").excluded_count, 1);
    assert.equal(metadata.datasets.find(item => item.dataset === "fmr").review_count, 2);
    await input(page, "#nb-search", "office-only");
    assert.equal((await keys(page)).length, 0, "Search is title-only, not office/ID fallback");
    assert.equal(await page.$eval("#nb-review-section", element => element.hidden), true, "Review section disappears when current filters leave no review records");
    assert.equal(state.requests.length, calls, "Sort/filter/review/export do not refetch lists");
    await layout(page, `synthetic/${locale}`);
    clean(state);
  } finally { await page.close(); }
}

async function stateCase(browser, origin, locale, mode) {
  const responses = fixtures();
  let failing = true;
  if (mode === "empty") {
    for (const dataset of datasets) {
      const envelope = responses[dataset];
      envelope.data.rows = [];
      envelope.data.total = 0;
      envelope.data.next_offset = null;
      Object.assign(envelope.meta, { total: 0, returned: 0, offset: 0 });
      for (const version of ["nep", "hgab2", "hgab3", "api"]) {
        envelope.data.sums[version + "_php"] = null;
        envelope.data.sums.rows_with_amount[version] = 0;
      }
    }
  }
  const { page, state } = await openPage(browser, origin, locale, 375, {
    responses,
    hold: mode === "loading",
    respond(request) {
      if (mode === "error") return { status: 422, body: '{"error":"synthetic invalid request"}' };
      if (mode === "partial-retry" && request.dataset === "hfep" && failing) return { status: 500, body: '{"error":"synthetic unavailable"}' };
      if (mode === "detail-retry" && request.id && failing) return { status: 422, body: '{"error":"synthetic detail unavailable"}' };
      if (mode === "partial-pages" && request.dataset === "dpwh") {
        if (request.offset > 0) return { status: 422, body: '{"error":"synthetic missing page"}' };
        const envelope = clone(responses.dpwh);
        envelope.data.total = 3;
        envelope.meta.total = 3;
        envelope.data.next_offset = 2;
        return { body: JSON.stringify(envelope) };
      }
      return null;
    }
  });
  try {
    if (mode === "loading") {
      await page.waitForFunction(() => document.querySelector("#national-budget-page").dataset.state === "loading");
      await page.waitForFunction(() => document.querySelectorAll('#nb-availability [data-state="loading"]').length === 4);
      assert.equal(await page.$eval("#nb-export", element => element.disabled), true);
      assert.equal((await keys(page)).length, 0);
      await page.waitForFunction(() => performance.getEntriesByType("resource").some(entry => /national-budget-ui/.test(entry.name)));
      assert.equal(state.requests.length, 4, "Independent requests start concurrently");
      state.release();
    }
    await ready(page);
    const rootState = await page.$eval("#national-budget-page", element => element.dataset.state);
    if (mode === "empty") {
      assert.equal(rootState, "empty", "Successful API empty is not an error");
      assert.equal((await keys(page)).length, 0);
      assert.ok(await page.$$eval("#nb-summary [data-metric]", elements => elements.every(element => element.dataset.value === "")), "No invented zero for no numeric values");
      assert.equal(await page.$eval("#nb-export", element => element.disabled), true);
      assert.equal(await page.$$eval("[data-retry-dataset]", elements => elements.length), 0);
    } else if (mode === "error") {
      assert.equal(rootState, "error", "All failed datasets never become successful empty");
      assert.equal(await page.$$eval("[data-retry-dataset]", elements => elements.length), 4);
      assert.equal(state.requests.length, 4, "422 is not automatically retried");
      assert.equal(await page.$eval("#nb-export", element => element.disabled), true);
      assert.ok(await page.$$eval("#nb-summary [data-metric]", elements => elements.every(element => element.dataset.value === "")));
    } else if (mode === "partial-retry" || mode === "partial-pages") {
      assert.equal(rootState, "partial", "Failure retains valid records with partial state");
      assert.equal((await keys(page)).length, 2);
      assert.equal(await page.$eval("#nb-export", element => element.disabled), false, "Partial export remains available with warning");
      const metadata = JSON.parse((await download(page, "#nb-export-metadata")).text);
      assert.equal(metadata.coverage, "partial");
      assert.equal(metadata.selected_count, 2);
      const failedDataset = mode === "partial-pages" ? "dpwh" : "hfep";
      assert.equal(metadata.datasets.find(item => item.dataset === failedDataset).status, mode === "partial-pages" ? "partial" : "error");
      assert.ok(await page.$eval("#nb-summary", element => !!element.querySelector('[data-partial="true"]')), "Partial summaries visibly qualified");
      if (mode === "partial-retry") {
        assert.equal(state.requests.filter(request => request.dataset === "hfep").length, 2, "5xx limited to two attempts");
        const before = Object.fromEntries(datasets.map(dataset => [dataset, state.requests.filter(request => request.dataset === dataset).length]));
        failing = false;
        await reveal(page, '[data-retry-dataset="hfep"]');
        assert.equal(await visible(page, '[data-retry-dataset="hfep"]'), true, "Dataset retry is accessible through coverage details");
        await page.click('[data-retry-dataset="hfep"]');
        await ready(page);
        assert.equal(await page.$eval("#national-budget-page", element => element.dataset.state), "ready");
        for (const dataset of datasets) assert.equal(state.requests.filter(request => request.dataset === dataset).length, before[dataset] + (dataset === "hfep" ? 1 : 0), "Retry reloads affected dataset only");
      }
    } else if (mode === "detail-retry") {
      const detail = 'details[data-project-key="dpwh:house-reading:3923"]';
      const amounts = await page.$$eval("#nb-summary [data-metric]", elements => elements.map(element => element.dataset.value));
      await page.focus(detail + " > summary"); await page.keyboard.press("Enter");
      await page.waitForSelector(detail + ' .nb-detail[data-state="error"]');
      assert.equal((await keys(page)).length, 2, "Detail failure preserves valid list rows");
      const row = responses.dpwh.data.rows.find(row => row.id === "house-reading:3923");
      assert.equal(await visible(page, `${detail} a[href="${row.pdf_url.hgab3}"]`), true, "List-sourced PDF remains accessible when detail API fails");
      assert.deepEqual(await page.$$eval("#nb-summary [data-metric]", elements => elements.map(element => element.dataset.value)), amounts);
      failing = false;
      await page.click(detail + " [data-retry-detail]");
      await page.waitForSelector(detail + ' .nb-detail[data-state="ready"]');
      assert.equal(state.requests.filter(request => request.id).length, 2, "Failed detail evicted for explicit retry");
      assert.equal(state.requests.filter(request => !request.id).length, 4);
    } else if (mode === "restore") {
      const amounts = await page.$$eval("#nb-summary [data-metric]", elements => elements.map(element => element.dataset.value));
      const before = state.requests.length;
      await page.evaluate(() => {
        window.dispatchEvent(new PageTransitionEvent("pagehide", { persisted: true }));
        window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: true }));
      });
      assert.equal(state.requests.length, before, "bfcache restoration does not refresh results automatically");
      const detail = 'details[data-project-key="dpwh:house-reading:3923"]';
      await page.focus(detail + " > summary"); await page.keyboard.press("Enter");
      await page.waitForSelector(detail + ' .nb-detail[data-state="ready"]');
      assert.equal(state.requests.filter(request => request.id).length, 1, "Restored page has a working detail client");
      assert.deepEqual(await page.$$eval("#nb-summary [data-metric]", elements => elements.map(element => element.dataset.value)), amounts);
    } else {
      assert.equal(rootState, "ready");
      assert.equal((await keys(page)).length, 2);
    }
    await layout(page, `${locale}/${mode}`);
    clean(state);
  } finally {
    if (state.release) state.release();
    await page.close();
  }
}

async function progressiveEvidenceCase(browser, origin, locale) {
  const { page, state } = await openPage(browser, origin, locale, 375, { holdDataset: "hfep" });
  const detail = 'details[data-project-key="dpwh:house-reading:3923"]';
  try {
    await page.waitForSelector(detail);
    await page.focus(detail + " > summary");
    await page.keyboard.press("Enter");
    await page.waitForSelector(detail + ' .nb-detail[data-state="ready"]');
    assert.equal(await page.$eval(detail, element => element.open), true);
    assert.equal(await page.evaluate(selector => document.activeElement.matches(selector), detail + " > summary"), true);
    state.release();
    await ready(page);
    assert.equal(await page.$eval(detail, element => element.open), true, "Unrelated dataset completion preserves open evidence");
    assert.equal(await page.evaluate(selector => document.activeElement.matches(selector), detail + " > summary"), true, "Unrelated completion preserves keyboard focus");
    assert.equal(state.requests.filter(request => request.id).length, 1, "Evidence state is retained without refetch");
    clean(state);
  } finally {
    if (state.release) state.release();
    await page.close();
  }
}

async function stageDriftCase(browser, origin, locale) {
  const responses = fixtures();
  for (const dataset of datasets) responses[dataset].meta.house_stage = "hgab3";
  const { page, state } = await openPage(browser, origin, locale, 375, {
    responses,
    respond(request) {
      if (request.dataset !== "dpwh" || request.id) return null;
      const envelope = clone(responses.dpwh);
      envelope.data.rows = envelope.data.rows.slice(request.offset, request.offset + 1);
      Object.assign(envelope.meta, { offset: request.offset, returned: 1, house_stage: request.offset ? "hgab2" : "hgab3" });
      envelope.data.next_offset = request.offset ? null : 1;
      return { body: JSON.stringify(envelope) };
    }
  });
  try {
    await ready(page);
    assert.equal(await page.$eval("#national-budget-page", element => element.dataset.state), "partial");
    assert.equal(await page.$eval('#nb-summary [data-stage="hgab2"]', element => element.dataset.partial), "true", "Later-page stage inherits partial coverage");
    assert.ok((await text(page, '#nb-summary [data-stage="hgab2"]')).includes("DPWH"), "Later-page stage retains dataset attribution");
    assert.ok(!(await visibleText(page, "#national-budget-page")).includes("mixed_snapshot"), "Raw drift diagnostics are not upfront");
    await disclose(page, "#nb-technical-data");
    assert.ok((await visibleText(page, "#nb-diagnostics")).includes("mixed_snapshot"), "Original drift diagnostics remain available in technical data");
    clean(state);
  } finally { await page.close(); }
}

async function main() {
  stagedChecks();
  const server = createServer();
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  let browser;
  let cases = 0;
  try {
    browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome", headless: true, args: ["--no-sandbox"] });
    for (const locale of locales) {
      for (const width of widths) {
        console.log(`National budget: ${locale}/${width}/fixtures`);
        await normalCase(browser, origin, locale, width); cases++;
      }
      console.log(`National budget: ${locale}/no-js`);
      await noJSCase(browser, origin, locale); cases++;
      console.log(`National budget: ${locale}/synthetic-stage-review-export`);
      await syntheticCase(browser, origin, locale); cases++;
      console.log(`National budget: ${locale}/progressive-evidence-focus`);
      await progressiveEvidenceCase(browser, origin, locale); cases++;
      console.log(`National budget: ${locale}/mixed-stage-pagination`);
      await stageDriftCase(browser, origin, locale); cases++;
      for (const mode of ["loading", "empty", "error", "partial-retry", "partial-pages", "detail-retry", "restore"]) {
        console.log(`National budget: ${locale}/${mode}`);
        await stateCase(browser, origin, locale, mode); cases++;
      }
    }
    console.log(`National budget browser checks passed: ${cases} cases; no live API requests.`);
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
