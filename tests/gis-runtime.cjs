"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const gis = require("../assets/gis-map.js");
const layer = { type: "inline-geojson", enabled: true, available: true };
const feature = (geometry, properties = {}) => ({ type: "Feature", geometry, properties });
const point = (coords = [120.455, 16.03]) => feature({ type: "Point", coordinates: coords });
const collection = features => ({ type: "FeatureCollection", features });

test("static category glyphs produce path nodes, not SVG path text or injected data", () => {
  const expected = [
    ["Evacuation centers / gymnasiums", "home"], ["School", "graduation-cap"],
    ["Health / medical", "heart-pulse"], ["Police / fire", "shield"],
    ["Barangay hall", "landmark"], ["Other", "map-pin"],
  ];
  for (const [category, icon] of expected) {
    assert.equal(gis.categoryIcon(category), icon);
    const svg = gis.iconSvg(icon, gis.categoryColor(category), 20);
    assert.match(svg, /<path d="[Mm]/);
    assert.doesNotMatch(svg, />[Mm]\d|<svg[^>]*>[^<]/);
    assert.match(svg, /fill="none"/);
  }
  assert.equal(gis.categoryIcon("", "dpwh_project"), "hard-hat");
  assert.match(gis.iconSvg("hard-hat", "#287943", 20), /<path /);
  assert.match(gis.iconSvg("layers", "#53616a", 20), /<path /);
  assert.doesNotMatch(gis.iconSvg('<img src=x>', 'red" onload="alert(1)', '20" bad="1'), /onload|alert|<img|bad=/);
  for (const key of Object.keys(gis.statusColors)) assert.equal(gis.categoryColor("", "dpwh_project", key), gis.statusColors[key]);
  assert.equal(gis.categoryColor("", "dpwh_project", "unexpected"), gis.statusColors.unknown);
  const source = fs.readFileSync(require.resolve("../assets/gis-map.js"), "utf8");
  assert.equal((source.match(/function categoryIcon\(/g) || []).length, 1);
  assert.equal((source.match(/function categoryColor\(/g) || []).length, 1);
  assert.match(source, /marker\.addTo\(group\)/);
});

test("DPWH fallback fragments retain raw escaped row IDs and select the target page", () => {
  const id = 'txn /#%"<&';
  const projects = Array.from({ length: 41 }, (_, i) => ({ transaction_id: `txn-${i}` }));
  projects[40].transaction_id = id;
  const tbody = { innerHTML: "" }, search = { value: "", addEventListener() {} };
  let scrolled = 0, hashchange;
  const document = {
    querySelector: () => tbody, querySelectorAll: () => [], addEventListener() {},
    getElementById: key => key === "dpwh-search" ? search : key === "dpwh-project-" + id ? { scrollIntoView() { scrolled++; } } : null,
  };
  const window = { DPWH_PROJECTS: projects, location: { hash: "#dpwh-project-" + encodeURIComponent(id) },
    addEventListener(event, callback) { if (event === "hashchange") hashchange = callback; } };
  const context = vm.createContext({ window, document });
  vm.runInContext(fs.readFileSync(require.resolve("../assets/js/dpwh-table.js"), "utf8"), context);
  context.initDPWHTable();
  assert.match(tbody.innerHTML, /id="dpwh-project-txn \/#%&quot;&lt;&amp;"/);
  assert.equal((tbody.innerHTML.match(/<tr /g) || []).length, 1);
  assert.equal(scrolled, 1);
  window.location.hash = "#dpwh-project-txn-0";
  hashchange();
  assert.match(tbody.innerHTML, /id="dpwh-project-txn-0"/);
  assert.equal((tbody.innerHTML.match(/<tr /g) || []).length, 20);
  window.location.hash = "#dpwh-project-%E0%A4%A";
  assert.doesNotThrow(hashchange);
});

test("enabled available layers include all facilities without verification metadata", () => {
  assert.equal(gis.allowed(layer), true);
  const rows = Array.from({ length: 16 }, (_, i) => ({ ...point(), properties: { id: `fac-${i}`, verification_status: "needs_review" } }));
  assert.equal(gis.records(collection(rows)).length, 16);
  assert.equal(gis.records(collection(rows.map(row => ({ ...row, properties: {} })))).length, 16);
});
test("selection and technical availability are the only layer gates", () => {
  for (const status of ["candidate", "in_review", "blocked", "revoked", "unavailable", "invented"]) {
    assert.equal(gis.allowed({ ...layer, status, publishable: false, renderable_in_preview: false }), true);
  }
  for (const value of [false, "true", undefined]) {
    assert.equal(gis.allowed({ ...layer, enabled: value }), false);
    assert.equal(gis.allowed({ ...layer, available: value }), false);
  }
  assert.equal(gis.allowed({ ...layer, type: "wms" }), false);
  assert.equal(gis.allowed(null), false);
});
test("URL resolution handles all locale roots and only emitted GIS assets", () => {
  for (const prefix of ["", "/fil", "/pag"]) {
    const page = `http://localhost${prefix}/gis/`;
    const base = new URL(prefix ? "../../" : "../", page).href;
    assert.throws(() => gis.assetUrl("assets/gis-preview/roads.geojson", base, "http://localhost"));
    assert.equal(gis.assetUrl("assets/gis/roads.geojson", base, "http://localhost"), "http://localhost/assets/gis/roads.geojson");
  }
});
test("URLs reject schemes, origin changes, credentials, encoded paths and query redirects", () => {
  for (const raw of ["https://evil.test/assets/gis/x", "javascript:alert(1)", "data:foo", "//evil.test/x",
    "http://user@localhost/assets/gis/a", "assets/gis/%2e/a", "assets/gis/a?x=1",
    "assets/gis/a#x", "assets/gis/../../secret", "assets\\gis\\a", " assets/gis/a", "other/assets/gis/a"]) {
    assert.throws(() => gis.assetUrl(raw, "http://localhost/", "http://localhost"), raw);
  }
});
test("exact coordinate groups never jitter or merge nearby points", () => {
  const a = point(), b = point(), c = point([120.455001, 16.03]);
  const before = JSON.stringify([a, b, c]);
  const groups = gis.exactGroups([a, b, c, feature(null)]);
  assert.equal(groups.size, 2); assert.equal(groups.get("[120.455,16.03]").length, 2);
  assert.equal(JSON.stringify([a, b, c]), before);
});
test("default facility coordinate grouping retains every distinct source record", () => {
  const fs = require("node:fs"), path = require("node:path");
  const payload = JSON.parse(fs.readFileSync(path.join(__dirname, "../src/data/gis/facilities.geojson"), "utf8"));
  const before = JSON.stringify(payload);
  const rows = gis.records(payload), groups = gis.exactGroups(rows);
  assert.equal([...groups.values()].reduce((sum, items) => sum + items.length, 0), rows.length);
  for (const [key, items] of groups) for (const item of items) assert.equal(JSON.stringify(item.geometry.coordinates), key);
  assert.equal(JSON.stringify(payload), before);
});
test("null geometry and plain nonspatial records remain nonspatial", () => {
  const result = gis.records([feature(null, { name: "Barangay" }), { project_id: "real-id" }]);
  assert.deepEqual(result.map(r => r.geometry), [null, null]);
});
test("point, line, polygon and multi geometries validate without synthesis", () => {
  const ring = [[120, 16], [121, 16], [121, 17], [120, 16]];
  const shapes = [point(), feature({ type: "LineString", coordinates: ring }),
    feature({ type: "Polygon", coordinates: [ring] }), feature({ type: "MultiPolygon", coordinates: [[ring]] }),
    feature({ type: "MultiPoint", coordinates: ring }), feature({ type: "MultiLineString", coordinates: [ring] })];
  assert.deepEqual(gis.records(collection(shapes)), shapes);
});
test("malformed geometry rejects one collection rather than leaking unsafe coordinates", () => {
  for (const coords of [[NaN, 16], [Infinity, 16], [181, 16], [120, 91], ["120", 16], [120], [120, 16, 0]]) {
    assert.throws(() => gis.records(collection([point(coords)])));
  }
  for (const payload of [{}, { features: [] }, collection("bad"), collection([null]), collection([feature({ type: "Polygon", coordinates: [[[120, 16]]] })])]) {
    assert.throws(() => gis.records(payload));
  }
});
test("collections and vertex counts are bounded", () => {
  assert.throws(() => gis.records(Array(10001).fill(point())));
  assert.throws(() => gis.records(collection([feature({ type: "LineString", coordinates: Array(100001).fill([120, 16]) })])));
});
test("legacy review and publication properties never hide valid supplied records", () => {
  assert.equal(gis.records(collection([feature(null, { status: "candidate" }), point()])).length, 2);
  assert.equal(gis.records(collection([feature(null, { verification_status: "needs_review" })])).length, 1);
});
test("inspected raster bounds must be numeric and ordered", () => {
  assert.ok(gis.validBounds({ west: 120, south: 16, east: 121, north: 17 }));
  for (const bounds of [null, {}, { west: "120", south: 16, east: 121, north: 17 }, { west: 120, south: 17, east: 121, north: 16 }]) assert.ok(!gis.validBounds(bounds));
});
test("all tooltip fields escape HTML and quotes", () => {
  const unsafe = '</script><img src=x onerror="alert(1)"> & \'x\'';
  assert.doesNotMatch(gis.escapeHtml(unsafe), /<|>|"|'/);
  assert.match(gis.escapeHtml(unsafe), /&lt;\/script&gt;/);
});

test("opacity accepts finite numbers, clamps configured values and preserves zero", () => {
  assert.equal(gis.opacity(0), 0); assert.equal(gis.opacity(1), 1);
  assert.equal(gis.opacity(0.27), 0.27); assert.equal(gis.opacity(-4), 0); assert.equal(gis.opacity(8), 1);
  for (const value of [undefined, null, NaN, Infinity, "0.2", false]) assert.equal(gis.opacity(value), 0.65);
});
test("project links preserve exact safe URLs and never infer names or locations", () => {
  for (const lang of ["en", "fil", "pag"]) {
    const prefix = lang === "en" ? "" : "/" + lang;
    const project = { project_id: "canonical /&id", source_transaction_id: "source-1" };
    const canonical = prefix + "/transparency/projects/?project=canonical%20%2F%26id";
    assert.equal(gis.projectUrl({ ...project, project_url: canonical }, lang, "https://local.test"), canonical);
    for (const url of ["https://evil.test/transparency/projects/?project=x", "javascript:alert(1)", "//evil.test/x", "/transparency/projects/?project=another", "/transparency/projects/?project=canonical%20%2F%26id&next=x", "/transparency/infrastructure/#dpwh-project-wrong", "/other/"]) {
      assert.equal(gis.projectUrl({ ...project, project_url: url }, lang, "https://local.test"), canonical);
    }
    const source = { source_transaction_id: "txn /1" };
    const fallback = prefix + "/transparency/infrastructure/#dpwh-project-txn%20%2F1";
    assert.equal(gis.projectUrl({ ...source, project_url: fallback }, lang, "https://local.test"), fallback);
    assert.equal(gis.projectUrl(source, lang, "https://local.test"), fallback);
    const strict = prefix + "/transparency/infrastructure/#dpwh-project-txn%27%28%29%21%2A";
    assert.equal(gis.projectUrl({ source_transaction_id: "txn'()!*", project_url: strict }, lang, "https://local.test"), strict);
    assert.equal(gis.projectUrl({ source_transaction_id: "txn'()!*" }, lang, "https://local.test"), strict);
    assert.equal(gis.projectUrl({ name: "Looks like a project", project_url: "/transparency/projects/?project=invented" }, lang, "https://local.test"), null);
  }
});
test("default results dedup only explicit IDs, preferring DPWH and usable barangay shapes", () => {
  const state = (id, semantic_role, features, extra = {}) => ({ layer: { id, semantic_role, available: true }, features, overlay: {}, visible: true, ...extra });
  const ref = feature(null, { name: "Reference", project_id: "canonical-1" });
  const dpwh = feature(null, { name: "Different project name", project_id: "canonical-1" });
  const unlinked = feature(null, { name: "Different project name" });
  const barangay = feature(null, { name: "Canonical name", gid: "gid-1" });
  const shape = feature({ type: "Polygon", coordinates: [[[120, 16], [121, 16], [121, 17], [120, 16]]] }, { name: "Source spelling", gid: "gid-1" });
  const unrelated = feature(null, { name: "Source spelling", gid: "gid-2" });
  const refs = state("refs", "project_reference", [ref, unlinked]);
  const projects = state("dpwh", "dpwh_project", [dpwh]);
  const directory = state("barangays", "reference", [barangay, unrelated]);
  const shapes = state("shape", "barangay_boundary", [shape]);
  const before = JSON.stringify([refs, projects, directory, shapes]);
  assert.deepEqual(gis.defaultEntries([refs, projects, directory, shapes]).map(entry => entry.feature), [unlinked, dpwh, unrelated, shape]);
  assert.equal(JSON.stringify([refs, projects, directory, shapes]), before);
  assert.ok(gis.defaultEntries([directory, { ...shapes, overlay: null }]).some(entry => entry.feature === barangay), "Failed shape loading never erases null references");
  assert.ok(gis.defaultEntries([directory, state("shape", "barangay_boundary", [feature(null, { gid: "gid-1" })])]).some(entry => entry.feature === barangay));
  const coarse = state("coarse", "barangay_reference_geometry", [shape], { visible: false });
  assert.deepEqual(gis.defaultEntries([directory, coarse]).map(entry => entry.feature), [barangay, unrelated]);
  assert.deepEqual(gis.defaultEntries([directory, { ...coarse, visible: true }]).map(entry => entry.feature), [unrelated, shape]);
  const actual = { ...shape, properties: { ...shape.properties, name: "Actual boundary" } };
  assert.deepEqual(gis.defaultEntries([directory, { ...coarse, visible: true }, state("actual", "barangay_boundary", [actual])]).map(entry => entry.feature), [unrelated, actual]);
});
test("pane ordering and status palette are explicit rather than inferred from titles", () => {
  assert.deepEqual(gis.panes, { physical: 250, hazards: 300, administrative: 400, infrastructure: 450, facilities: 500 });
  assert.deepEqual(Object.keys(gis.statusColors), ["completed", "ongoing", "not_started", "unknown"]);
  assert.equal(new Set(Object.values(gis.statusColors)).size, 4);
});
