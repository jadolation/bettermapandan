"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const crypto = require("node:crypto");
const ROOT = path.resolve(__dirname, "..");
const FIXTURES = path.join(__dirname, "fixtures/national-budget");
const fixture = name => JSON.parse(fs.readFileSync(path.join(FIXTURES, name + ".json"), "utf8"));
const clone = value => JSON.parse(JSON.stringify(value));
function runtime() {
  const window = {};
  const context = vm.createContext({ window, URL, AbortController, setTimeout, clearTimeout, TypeError, Date, Intl });
  for (const file of ["national-budget-normalize.js", "national-budget-api.js", "national-budget-ui.js"]) {
    vm.runInContext(fs.readFileSync(path.join(ROOT, "assets/js", file), "utf8"), context, { filename: file });
  }
  return window.NationalBudget;
}
function response(body, status = 200, retryAfter = null) {
  return { ok: status >= 200 && status < 300, status, headers: { get: () => retryAfter }, json: async () => clone(body) };
}
function envelope(rows, changes = {}) {
  const e = fixture("dpwh-list");
  e.data.rows = clone(rows);
  e.data.total = rows.length;
  e.data.next_offset = null;
  e.meta.offset = 0;
  e.meta.returned = rows.length;
  e.meta.total = rows.length;
  for (const version of ["nep", "hgab2", "hgab3", "api"]) {
    const amounts = rows.map(r => r[version + "_php"]).filter(v => typeof v === "number");
    e.data.sums[version + "_php"] = amounts.length ? amounts.reduce((a, b) => a + b, 0) : null;
  }
  Object.assign(e.data, changes);
  return e;
}
const raw = (changes = {}) => Object.assign(clone(fixture("dpwh-list").data.rows[0]), changes);
const norm = (api, changes = {}, meta = {}) => api.normalize(raw(changes), Object.assign(fixture("dpwh-list").meta, meta));
function clientFor(api, handler, options = {}) {
  let calls = 0;
  const urls = [];
  const client = api.createClient({ sleep: async () => {}, ...options, fetch: async (url, config) => {
    calls++; urls.push(url); return handler(url, config, calls);
  } });
  return { client, urls, calls: () => calls };
}

test("raw fixture captures retain exact bytes and source provenance", () => {
  const manifest = fixture("manifest");
  assert.equal(manifest.files.length, 6);
  for (const entry of manifest.files) {
    const bytes = fs.readFileSync(path.join(FIXTURES, entry.file));
    assert.equal(crypto.createHash("sha256").update(bytes).digest("hex"), entry.sha256);
    assert.match(entry.url, /^https:\/\/budget\.bettergov\.ph\/api\/v1\/hgab\/2027\/datasets\//);
    assert.ok(Number.isFinite(Date.parse(entry.retrieved_at)));
    const e = JSON.parse(bytes);
    assert.equal(e.meta.source_commit, "a0caa778442cdae5583f5a006ea7401dab00e5ac");
    assert.equal(e.meta.built_at, "2026-10-26T08:46:14.383Z");
  }
});

test("exact fixture normalization and 49M third-reading paired comparison", () => {
  const api = runtime(), e = fixture("dpwh-list");
  api.validateEnvelope(e, { dataset: "dpwh" });
  const rows = e.data.rows.map(row => api.normalize(row, e.meta));
  assert.deepEqual(Array.from(rows, r => r.key), ["dpwh:house-reading:3959", "dpwh:house-reading:3923"]);
  assert.deepEqual(Array.from(rows, r => r.amounts.house), [44000000, 5000000]);
  assert.deepEqual(Array.from(rows, r => r.pages.nep), [372, 371]);
  assert.deepEqual(Array.from(rows, r => r.pages.hgab3), [335, 333]);
  for (const r of rows) {
    assert.equal(r.geography, "included"); assert.equal(r.held, false);
    assert.equal(r.pdf.house, r.pdf.hgab3); assert.equal(r.amounts.delta, 0);
    assert.equal(r.meta, e.meta); assert.equal(r.raw.lon, null);
    assert.equal(r.contractor, undefined); assert.equal(r.completion, undefined);
  }
  const [s] = api.summarize(rows);
  assert.equal(s.stage, "hgab3"); assert.equal(s.nep.value, 49000000);
  assert.equal(s.house.value, 49000000); assert.equal(s.delta.value, 0); assert.equal(s.pairedCount, 2);
  assert.deepEqual(Array.from(rows[1].flags), ["nep_evidence_review"]);
});

test("all fixture lists are independent complete results; empty amounts stay null", async () => {
  const api = runtime();
  const { client, urls } = clientFor(api, url => response(fixture(url.match(/datasets\/([^/]+)/)[1] + "-list")));
  const all = await Promise.all(api.DATASETS.map(key => client.loadDataset(key)));
  assert.equal(all.length, 4);
  all.forEach(result => {
    assert.equal(result.status, "complete"); assert.equal(result.pages.length, 1);
    assert.deepEqual(clone(result.disclaimers), fixture(result.dataset + "-list").disclaimers);
  });
  for (const r of all.slice(1)) {
    assert.equal(r.meta.house_stage, "hgab2"); assert.equal(r.records.length, 0);
    assert.equal(r.pages[0].sums.nep_php, null);
  }
  assert.ok(urls.every(url => url.endsWith("?q=Mapandan&limit=50&offset=0") && !url.includes("region=")));
});

test("second and third readings stay separate, unknown stage is nonaggregatable", () => {
  const api = runtime();
  const third = norm(api), second = norm(api, { dataset: "fmr", hgab2_php: 12, house_php: 12, delta_php: null }, { dataset_key: "fmr", house_stage: "hgab2" });
  const groups = api.summarize([third, second]);
  assert.equal(groups.length, 2); assert.equal(groups[0].house.value, 12);
  assert.equal(groups[1].house.value, 44000000); assert.equal(second.pdf.house, second.pdf.hgab2);
  const unknown = norm(api, {}, { house_stage: "future" });
  assert.equal(unknown.aggregatable, false); assert.equal(unknown.amounts.house, null);
  assert.equal(api.summarize([unknown])[0].house.value, null);
});

test("missing region and non-title results need review; explicit other region excluded", () => {
  const api = runtime();
  assert.equal(norm(api, { region: null, region_key: null }).geography, "review");
  assert.equal(norm(api, { title: "A road", office: "Mapandan office" }).geography, "review");
  assert.equal(norm(api, { region: "Region II", region_key: "II" }).geography, "excluded");
  assert.equal(norm(api, { region: "Region II", region_key: null }).geography, "excluded");
  assert.equal(norm(api, { region: "Region II", region_key: "I" }).geography, "excluded");
  assert.equal(norm(api, { title: "Mapandano road" }).titleMatch, false);
  assert.equal(norm(api, { region_key: null }).geography, "included");
});

test("null, zero, held, one-sided, scope-review and unknown status remain qualified", () => {
  const api = runtime();
  const zero = norm(api, { nep_php: 0, hgab3_php: 0, house_php: 0 });
  assert.equal(zero.amounts.delta, 0); assert.equal(api.summarize([zero])[0].house.value, 0);
  for (const changes of [{ held: true }, { held: null }, { bridge_group: "scope_review" }, { bridge_group: "future" }, { trace: "future" },
    { nep_php: null, delta_php: null }, { hgab3_php: null, house_php: null, delta_php: null }]) {
    const row = norm(api, changes), [summary] = api.summarize([row]);
    assert.equal(row.comparable, false); assert.equal(summary.delta.value, null);
    assert.equal(summary.pairedCount, 0); assert.equal(summary.qualifiedCount, 1);
  }
  assert.equal(api.summarize([norm(api, { bridge_group: "future" })])[0].house.value, null);
  assert.equal(api.summarize([norm(api, { trace: "future" })])[0].house.value, null);
});

test("money is never coerced and unsafe arithmetic becomes unavailable", () => {
  const api = runtime();
  for (const invalid of ["0", "44000000", false, {}, [], 1.1, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1]) {
    assert.throws(() => norm(api, { nep_php: invalid }), /invalid_amount/);
  }
  assert.throws(() => norm(api, { house_php: 3 }), /alias/);
  assert.throws(() => norm(api, { house_php: null }), /alias/);
  assert.throws(() => norm(api, { delta_php: 5 }), /delta/);
  const large = norm(api, { nep_php: Number.MAX_SAFE_INTEGER, hgab3_php: Number.MAX_SAFE_INTEGER, house_php: Number.MAX_SAFE_INTEGER });
  const s = api.summarize([large, large])[0];
  assert.equal(s.house.value, null); assert.equal(s.house.overflow, true);
  const wide = norm(api, { nep_php: -Number.MAX_SAFE_INTEGER, hgab3_php: Number.MAX_SAFE_INTEGER, house_php: Number.MAX_SAFE_INTEGER, delta_php: null });
  assert.equal(wide.amounts.delta, null); assert.equal(wide.comparable, false);
});

test("URLs permit only expected HTTPS hosts without credentials", () => {
  const api = runtime();
  for (const bad of ["javascript:alert(1)", "http://budget.bettergov.ph/", "https://evil.test/", "https://budget.bettergov.ph.evil.test/",
    "https://u:p@budget.bettergov.ph/", "//budget.bettergov.ph/", "https://budget.bettergov.ph:444/", "https://budget.bettergov.ph/\nfoo"]) assert.equal(api.safeUrl(bad), null);
  assert.equal(api.safeUrl("https://budget-assets.bettergov.ph/a.pdf#page=3"), "https://budget-assets.bettergov.ph/a.pdf#page=3");
  const row = norm(api, { title: "<img onerror=alert(1)> Mapandan", url: "javascript:alert(1)", pdf_url: { hgab3: "https://evil.test/a.pdf" } });
  assert.equal(row.title, "<img onerror=alert(1)> Mapandan"); assert.equal(row.url, null); assert.equal(row.pdf.house, null);
});

test("CSV uses exact 17 columns, BOM, CRLF, quoting, deterministic flags and injection protection", () => {
  const api = runtime();
  const row = norm(api, { title: ' \t=HYPERLINK("x")\nMapandan', flags: ["z", "@evil", "a"], program: "-cmd", pap: "+cmd", office: "\r@cmd",
    nep_php: 44000001, delta_php: -1, trace: "candidate_decrease", bridge_group: "decreased" });
  const csv = api.csv([row]);
  assert.ok(csv.startsWith("\ufeffexternal_key,fiscal_year,dataset,"));
  assert.equal(csv.slice(1).split("\r\n")[0], "external_key,fiscal_year,dataset,title,program,office,nep_php,house_php,house_stage,delta_php,bridge_group,held,flags,project_url,nep_pdf_url,house_pdf_url,source_snapshot_date");
  assert.equal(csv.slice(1).split("\r\n")[0].split(",").length, 17);
  assert.match(csv, /"' \t=HYPERLINK\(""x""\)\nMapandan"/);
  assert.match(csv, /'-cmd,/); assert.match(csv, /,-1,/);
  assert.match(csv, /'@evil;a;z/); assert.ok(csv.endsWith("\r\n"));
  const zero = api.csv([norm(api, { nep_php: null, house_php: 0, hgab3_php: 0, delta_php: null })]);
  assert.match(zero, /,,0,hgab3,,unchanged,false,/);
  assert.equal(api.csv(Array.from({ length: 51 }, () => row)).match(/house-reading:3959/g).length, 51);
});

test("essential metadata and invalid envelopes fail, not empty-success", async () => {
  const api = runtime();
  for (const mutate of [e => delete e.meta, e => delete e.meta.source_commit, e => e.meta.fiscal_year = 2026,
    e => e.meta.dataset_key = "fmr", e => e.meta.currency = "USD", e => e.meta.scale = "millions",
    e => e.data.rows = {}, e => delete e.data.next_offset, e => e.disclaimers = null]) {
    const e = fixture("dpwh-list"); mutate(e);
    const { client, calls } = clientFor(api, () => response(e));
    const result = await client.loadDataset("dpwh");
    assert.equal(result.status, "error"); assert.ok(result.error); assert.equal(calls(), 1);
  }
});

test("malformed rows quarantined while valid records survive with partial summaries", async () => {
  const api = runtime(), good = raw();
  const e = envelope([good, raw({ id: "bad", nep_php: "44" }), { id: "broken" }]);
  const { client } = clientFor(api, () => response(e));
  const result = await client.loadDataset("dpwh");
  assert.equal(result.status, "partial"); assert.equal(result.records.length, 1); assert.equal(result.invalidCount, 2);
  assert.equal(api.summarize(result.records)[0].partial, true);
});

test("client caches successful loads, deduplicates inflight and reloads explicitly", async () => {
  const api = runtime();
  const { client, calls } = clientFor(api, () => response(fixture("dpwh-list")));
  const a = client.loadDataset("dpwh"), b = client.loadDataset("dpwh");
  assert.equal(a, b); await a; await client.loadDataset("dpwh"); assert.equal(calls(), 1);
  await client.loadDataset("dpwh", { reload: true }); assert.equal(calls(), 2);
});

test("datasets load concurrently with independent failures", async () => {
  const api = runtime();
  const { client } = clientFor(api, url => url.includes("/dpwh/") ? response({}, 404) : response(fixture(url.match(/datasets\/([^/]+)/)[1] + "-list")));
  const results = await Promise.all(api.DATASETS.map(key => client.loadDataset(key)));
  assert.equal(results[0].status, "error"); assert.ok(results.slice(1).every(r => r.status === "complete"));
});

test("sequential pagination completes and reconciles raw scope before geographic exclusion", async () => {
  const api = runtime();
  const rows = [raw(), raw({ id: "other", region_key: "II" })];
  const first = envelope(rows); first.data.rows = [rows[0]]; first.meta.returned = 1; first.data.next_offset = 1;
  const second = clone(first); second.data.rows = [rows[1]]; second.meta.offset = 1; second.data.next_offset = null;
  const { client, urls } = clientFor(api, (_, __, n) => response(n === 1 ? first : second));
  const result = await client.loadDataset("dpwh");
  assert.equal(result.status, "complete"); assert.equal(result.records.length, 1); assert.equal(result.excludedCount, 1);
  assert.equal(urls.length, 2); assert.match(urls[1], /offset=1$/); assert.equal(result.pages.length, 2);
});

test("repeated pages, offset regressions, premature end and inconsistent totals are partial", async () => {
  const api = runtime();
  for (const mode of ["repeat", "back", "skip", "early", "total", "offset", "returned"]) {
    const first = envelope([raw()], { total: 2, next_offset: 1 }); first.meta.total = 2;
    const second = envelope([raw({ id: "second" })]); second.meta.offset = 1; second.data.total = 2; second.meta.total = 2;
    if (mode === "repeat") second.data.rows = clone(first.data.rows);
    if (mode === "back") first.data.next_offset = 0;
    if (mode === "skip") first.data.next_offset = 3;
    if (mode === "early") first.data.next_offset = null;
    if (mode === "total") second.data.total = 3;
    if (mode === "offset") second.meta.offset = 9;
    if (mode === "returned") second.meta.returned = 9;
    const { client } = clientFor(api, (_, __, n) => response(n === 1 ? first : second));
    const result = await client.loadDataset("dpwh");
    assert.equal(result.status, "partial", mode); assert.ok(result.warnings.length, mode);
  }
});

test("duplicate IDs preserve flags, conflicting duplicates never last-write-win", async () => {
  const api = runtime();
  const e = envelope([raw(), raw({ flags: ["review"], title: "Changed Mapandan" })]);
  const { client } = clientFor(api, () => response(e));
  const result = await client.loadDataset("dpwh");
  assert.equal(result.status, "partial"); assert.equal(result.records.length, 1);
  assert.ok(result.warnings.includes("conflicting_duplicate"));
  assert.equal(result.records[0].title, raw().title); assert.ok(result.records[0].flags.includes("review"));
});

test("snapshot/stage drift retains provenance but never complete coverage", async () => {
  const api = runtime();
  for (const change of [{ source_commit: "different" }, { built_at: "2026-10-27T08:46:14.383Z" }, { house_stage: "hgab2" }, { source_repo: "https://github.com/another/source" }]) {
    const first = envelope([raw()], { total: 2, next_offset: 1 }); first.meta.total = 2;
    const second = envelope([raw({ id: "other" })], { total: 2 }); second.meta.total = 2; second.meta.offset = 1;
    Object.assign(second.meta, change);
    const { client } = clientFor(api, (_, __, n) => response(n === 1 ? first : second));
    const result = await client.loadDataset("dpwh");
    assert.equal(result.status, "partial"); assert.ok(result.warnings.includes("mixed_snapshot"));
    assert.equal(result.pages.length, 2);
  }
});

test("safety limits are injectable and enforced without claiming completeness", async () => {
  const api = runtime();
  for (const options of [{ maxPages: 1 }, { maxRows: 1 }]) {
    const e = envelope([raw(), raw({ id: "second" })], { total: 3, next_offset: 2 }); e.meta.total = 3;
    const { client, calls } = clientFor(api, () => response(e), options);
    const result = await client.loadDataset("dpwh");
    assert.equal(result.status, "partial"); assert.ok(result.warnings.includes("safety_cap")); assert.equal(calls(), 1);
    if (options.maxRows) assert.equal(result.records.length, 1);
  }
});

test("upstream aggregate mismatch is partial and empty null differs from zero", async () => {
  const api = runtime();
  for (const e of [fixture("dpwh-list"), fixture("fmr-list")]) {
    e.data.sums.nep_php = 0;
    const { client } = clientFor(api, () => response(e));
    const result = await client.loadDataset(e.meta.dataset_key);
    assert.equal(result.status, "partial"); assert.ok(result.warnings.includes("sum_disagreement"));
  }
});

test("HTTP 500/429 and network failures retry at most twice; failures evicted for retry", async () => {
  const api = runtime();
  for (const status of [500, 503, 429]) {
    const { client, calls } = clientFor(api, (_, __, n) => n === 1 ? response({}, status) : response(fixture("dpwh-list")));
    assert.equal((await client.loadDataset("dpwh")).status, "complete"); assert.equal(calls(), 2);
  }
  const { client, calls } = clientFor(api, (_, __, n) => { if (n <= 2) throw new TypeError("offline"); return response(fixture("dpwh-list")); });
  assert.equal((await client.loadDataset("dpwh")).status, "error"); assert.equal(calls(), 2);
  assert.equal((await client.loadDataset("dpwh")).status, "complete"); assert.equal(calls(), 3);
});

test("4xx, malformed JSON and schemas do not retry", async () => {
  const api = runtime();
  for (const status of [400, 401, 403, 404]) {
    const { client, calls } = clientFor(api, () => response({}, status));
    assert.equal((await client.loadDataset("dpwh")).status, "error"); assert.equal(calls(), 1);
  }
  const bad = response(null); bad.json = async () => { throw new SyntaxError("bad JSON"); };
  const { client, calls } = clientFor(api, () => bad);
  assert.equal((await client.loadDataset("dpwh")).error, "invalid_json"); assert.equal(calls(), 1);
});

test("Retry-After seconds/dates honored only within wait budget", async () => {
  const api = runtime();
  for (const value of ["2", "Sun, 01 Nov 2026 00:00:02 GMT"]) {
    const waits = [];
    const { client } = clientFor(api, (_, __, n) => n === 1 ? response({}, 429, value) : response(fixture("dpwh-list")), {
      now: () => Date.parse("2026-11-01T00:00:00Z"), sleep: async ms => waits.push(ms) });
    assert.equal((await client.loadDataset("dpwh")).status, "complete"); assert.deepEqual(waits, [2000]);
  }
  const { client, calls } = clientFor(api, () => response({}, 429, "31"));
  assert.equal((await client.loadDataset("dpwh")).error, "retry_after_budget"); assert.equal(calls(), 1);
});

test("timeouts abort each attempt; navigation abort is terminal", async () => {
  const api = runtime();
  const pending = (_, { signal }) => new Promise((resolve, reject) => {
    signal.addEventListener("abort", () => { const error = new Error("aborted"); error.name = "AbortError"; reject(error); }, { once: true });
  });
  const timed = clientFor(api, pending, { timeoutMs: 2 });
  assert.equal((await timed.client.loadDataset("dpwh")).error, "timeout"); assert.equal(timed.calls(), 2);
  const leaving = clientFor(api, pending);
  const promise = leaving.client.loadDataset("dpwh"); leaving.client.abort();
  const result = await promise;
  assert.equal(result.status, "error"); assert.equal(result.error, "aborted"); assert.equal(leaving.calls(), 1);
  const controller = new AbortController(); controller.abort();
  const before = clientFor(api, pending);
  assert.equal((await before.client.loadDataset("dpwh", { signal: controller.signal })).error, "aborted");
  assert.equal(before.calls(), 0);
});

test("partial network failure retains first page rather than erasing valid list", async () => {
  const api = runtime();
  const first = envelope([raw()], { total: 2, next_offset: 1 }); first.meta.total = 2;
  const { client } = clientFor(api, (_, __, n) => n === 1 ? response(first) : response({}, 500));
  const result = await client.loadDataset("dpwh");
  assert.equal(result.status, "partial"); assert.equal(result.records.length, 1); assert.equal(result.error, "http_500");
});

test("detail fetched on demand, ID encoded once, evidence unchanged and cached", async () => {
  const api = runtime();
  const e = fixture("dpwh-list"), row = api.normalize(e.data.rows[1], e.meta);
  const { client, urls, calls } = clientFor(api, () => response(fixture("dpwh-detail-3923")));
  assert.equal(calls(), 0);
  const [a, b] = await Promise.all([client.detail(row), client.detail(row)]);
  assert.equal(calls(), 1); assert.equal(a.mixedSnapshot, false);
  assert.equal(a.raw.id, b.raw.id); assert.match(urls[0], /house-reading%3A3923$/);
  assert.deepEqual(clone(a.raw.labels), fixture("dpwh-detail-3923").data.labels);
  assert.match(JSON.stringify(a.raw.record), /native_row_ambiguity/);
  assert.match(JSON.stringify(a.raw.labels), /NEP amount still being checked against the scan/);
});

test("detail failure and different snapshot never overwrite list amounts", async () => {
  const api = runtime(), row = norm(api);
  const broken = clientFor(api, () => response({}, 404));
  await assert.rejects(broken.client.detail(row), /http_404/); assert.equal(row.amounts.house, 44000000);
  const e = fixture("dpwh-detail-3959"); e.meta.source_commit = "different";
  const drift = clientFor(api, () => response(e));
  assert.equal((await drift.client.detail(row)).mixedSnapshot, true);
  assert.equal(row.meta.source_commit, fixture("dpwh-list").meta.source_commit);
  e.data.id = "wrong";
  await assert.rejects(clientFor(api, () => response(e)).client.detail(row), /detail_id_mismatch/);
});

test("known upstream status traces classify only consistent paired comparisons", () => {
  const api = runtime();
  for (const [trace, bridge_group, nep, house, comparable] of [
    ["candidate_increase", "increased", 1, 2, true],
    ["outside_api_then_candidate_decrease", "decreased", 2, 1, true],
    ["house_only_candidate", "house_only", null, 1, false],
    ["nep_only_candidate", "nep_only", 1, null, false],
    ["segment_scope_review", "scope_review", 1, 2, false],
    ["amount_same", "unchanged", 1, 2, false],
  ]) {
    const row = norm(api, { trace, bridge_group, nep_php: nep, hgab3_php: house, house_php: house, delta_php: null });
    assert.equal(row.aggregatable, true, trace); assert.equal(row.comparable, comparable, trace);
    assert.equal(api.summarize([row])[0].delta.value, comparable ? house - nep : null, trace);
  }
});

test("failed detail identity/schema validation evicts its cache for retry", async () => {
  const api = runtime(), row = norm(api);
  const wrong = fixture("dpwh-detail-3959"); wrong.data.id = "wrong";
  const { client, calls } = clientFor(api, (_, __, n) => response(n === 1 ? wrong : fixture("dpwh-detail-3959")));
  await assert.rejects(client.detail(row), /detail_id_mismatch/);
  assert.equal((await client.detail(row)).record.id, row.id); assert.equal(calls(), 2);
});

test("navigation abort interrupts Retry-After without another attempt", async () => {
  const api = runtime();
  const { client, calls } = clientFor(api, () => response({}, 429, "20"), { sleep: undefined });
  const pending = client.loadDataset("dpwh");
  await new Promise(resolve => setImmediate(resolve));
  client.abort();
  assert.equal((await pending).error, "aborted"); assert.equal(calls(), 1);
});

test("hard page safety ceiling cannot be raised above 100", async () => {
  const api = runtime();
  const { client, calls } = clientFor(api, (_, __, n) => {
    const e = envelope([raw({ id: "row-" + n })], { total: 101, next_offset: n });
    e.meta.offset = n - 1; e.meta.total = 101;
    return response(e);
  }, { maxPages: 1000 });
  const result = await client.loadDataset("dpwh");
  assert.equal(calls(), 100); assert.equal(result.records.length, 100);
  assert.equal(result.status, "partial"); assert.ok(result.warnings.includes("safety_cap"));
});

test("hard row safety ceiling cannot be raised above 5000", async () => {
  const api = runtime();
  const base = raw();
  const rows = Array.from({ length: 5001 }, (_, n) => ({ ...base, id: "row-" + n }));
  const { client } = clientFor(api, () => response(envelope(rows)), { maxRows: 10000 });
  const result = await client.loadDataset("dpwh");
  assert.equal(result.records.length, 5000); assert.equal(result.status, "partial");
  assert.ok(result.warnings.includes("safety_cap"));
});

test("pure UI filtering/sorting matches full export scope, nulls last and stable ID ties", () => {
  const api = runtime();
  const rows = [norm(api, { id: "z" }), norm(api, { id: "a" }),
    norm(api, { id: "null", nep_php: null, hgab3_php: null, house_php: null, delta_php: null }),
    norm(api, { id: "review", region: null, region_key: null }),
    norm(api, { id: "excluded", region_key: "II" })];
  for (const sort of ["house-desc", "house-asc", "nep-desc", "nep-asc"]) {
    const selected = api.selectRows(rows, { sort });
    assert.equal(selected.length, 4); assert.equal(selected[3].id, "null");
    assert.deepEqual(Array.from(selected.slice(0, 3), r => r.id), ["a", "review", "z"]);
  }
  assert.equal(api.selectRows(rows, { search: "slope", barangay: "Poblacion", category: "dpwh", office: rows[0].office, status: rows[0].status_label }).length, 4);
  assert.equal(api.selectRows(rows, { search: "absent" }).length, 0);
  assert.equal(api.selectRows(rows, { category: "fmr" }).length, 0);
  assert.equal(api.selectRows(rows, { barangay: "Amanoaoac" }).length, 0);
  const review = api.selectRows(rows).filter(row => row.geography === "review");
  const included = api.selectRows(rows).filter(row => row.geography === "included");
  assert.equal(included.length, 3); assert.equal(review.length, 1);
  assert.equal(api.summarize(included)[0].count, 3);
  assert.equal(api.summarize(included.concat(review))[0].count, 4);
});

test("CSV neutralizes every control-prefixed formula introducer, including flags and keys", () => {
  const api = runtime();
  for (const prefix of ["=", "+", "-", "@", "\t =", "\u0001-", "\u2003@", "\r\n+"]) {
    const row = norm(api, { title: prefix + "Mapandan", flags: [prefix + "flag"], program: prefix + "program", office: prefix + "office" });
    row.key = prefix + "external-key";
    const csv = api.csv([row]);
    for (const suffix of ["Mapandan", "flag", "program", "office", "external-key"]) {
      assert.ok(csv.includes("'" + prefix + suffix), JSON.stringify(prefix + suffix));
    }
  }
});

test("CSV exports deltas only for eligible comparisons, including calculated source-null pairs", () => {
  const api = runtime();
  for (const [changes, meta, expected] of [
    [{ nep_php: 1, hgab3_php: 2, house_php: 2, delta_php: null, trace: "segment_scope_review", bridge_group: "scope_review" }, {}, ""],
    [{ held: true }, {}, ""],
    [{ trace: "future" }, {}, ""],
    [{ bridge_group: "future" }, {}, ""],
    [{}, { house_stage: "future" }, ""],
    [{ delta_php: null }, {}, "0"],
    [{ nep_php: 2, hgab3_php: 1, house_php: 1, delta_php: -1, trace: "candidate_decrease", bridge_group: "decreased" }, {}, "-1"],
    [{ nep_php: 1, hgab3_php: 2, house_php: 2, delta_php: null, trace: "candidate_increase", bridge_group: "increased" }, {}, "1"],
  ]) {
    const row = norm(api, { title: "Mapandan", program: "Program", office: "Office", ...changes }, meta);
    // These fixture fields have no embedded CSV delimiters.
    const fields = api.csv([row]).split("\r\n")[1].split(",");
    assert.equal(fields[9], expected, JSON.stringify({ changes, meta }));
    assert.equal(row.comparable, expected !== "");
    assert.equal(row.raw.delta_php, Object.hasOwn(changes, "delta_php") ? changes.delta_php : 0);
  }
});

test("malformed essential metadata fails without retry or successful caching", async () => {
  const api = runtime();
  for (const changes of [
    { source_commit: " \t\n" }, { house_stage: " " }, { notice: " " },
    ...["not-a-date", "2026-10-26", "2026-10-26T08:46:14", "2026-02-30T08:46:14Z", "2026-13-01T00:00:00Z",
      "2026-10-26T24:00:00Z", "2026-10-26T08:46:60Z", "2026-10-26T08:46:14+24:00", " 2026-10-26T08:46:14Z"].map(built_at => ({ built_at })),
    ...[" ", "not-a-repo", "http://github.com/owner/repo", "https://evil.test/owner/repo", "https://github.com.evil.test/owner/repo",
      "https://u:p@github.com/owner/repo", "https://github.com/owner", "https://github.com/owner/repo/tree/main",
      "https://github.com/owner/repo?x=1", "https://github.com/owner/repo#readme", "https://github.com/owner/.."].map(source_repo => ({ source_repo })),
  ]) {
    const e = fixture("dpwh-list"); Object.assign(e.meta, changes);
    assert.throws(() => api.validateEnvelope(e, { dataset: "dpwh" }), /invalid_metadata/);
    const detail = fixture("dpwh-detail-3959"); Object.assign(detail.meta, changes);
    assert.throws(() => api.validateEnvelope(detail, { dataset: "dpwh", detail: true }), /invalid_metadata/);
    const { client, calls } = clientFor(api, (_, __, n) => response(n === 1 ? e : fixture("dpwh-list")));
    const failed = await client.loadDataset("dpwh");
    assert.equal(failed.status, "error"); assert.equal(failed.error, "invalid_metadata"); assert.equal(calls(), 1);
    assert.equal((await client.loadDataset("dpwh")).status, "complete"); assert.equal(calls(), 2);
  }
});

test("valid ISO timestamps and opaque source identifiers are preserved verbatim", () => {
  const api = runtime();
  for (const built_at of ["2026-10-26T08:46:14.383Z", "2026-10-26T08:46:14Z", "2024-02-29T08:46:14.1+08:00"]) {
    const e = fixture("dpwh-list");
    Object.assign(e.meta, { built_at, source_commit: "snapshot-release_2026.10", source_repo: "https://github.com/owner/repository.git" });
    assert.equal(api.validateEnvelope(e, { dataset: "dpwh" }), e);
    assert.equal(e.meta.built_at, built_at);
    assert.equal(e.meta.source_commit, "snapshot-release_2026.10");
    assert.equal(e.meta.source_repo, "https://github.com/owner/repository.git");
  }
});
