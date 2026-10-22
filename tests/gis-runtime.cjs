"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const gis = require("../assets/gis-map.js");
const weather = require("../assets/gis-weather.js");
test("weather requests share a bounded hourly timeline and correct coordinates", () => {
  const url = new URL(weather.requestUrl([120.455, 16.03]));
  assert.equal(url.searchParams.get("latitude"), "16.03");
  assert.equal(url.searchParams.get("longitude"), "120.455");
  assert.equal(url.searchParams.get("forecast_hours"), "48");
  assert.equal(url.searchParams.get("timeformat"), "unixtime");
  assert.equal(url.searchParams.get("hourly").split(",").length, 5);
  assert.throws(() => weather.requestUrl([NaN, 16]));
  assert.throws(() => weather.requestUrl([120, 91]));
});
test("weather preserves zero and missing values, rejects malformed units and arrays", () => {
  const fields = ["temperature_2m", "apparent_temperature", "wind_speed_10m", "wind_direction_10m", "precipitation"];
  const units = ["°C", "°C", "km/h", "°", "mm"];
  const data = { hourly: { time: [1792627200, 1792630800] }, hourly_units: { time: "unixtime" } };
  fields.forEach((f, i) => { data.hourly[f] = [0, null]; data.hourly_units[f] = units[i]; });
  assert.deepEqual(weather.normalize(data)[0].values, [0, 0, 0, 0, 0]);
  assert.deepEqual(weather.normalize(data)[1].values, [null, null, null, null, null]);
  data.hourly.precipitation[0] = -1;
  assert.equal(weather.normalize(data)[0].values[4], null);
  data.hourly.precipitation.pop();
  assert.throws(() => weather.normalize(data));
  data.hourly.precipitation.push(null); data.hourly_units.temperature_2m = "°F";
  assert.throws(() => weather.normalize(data));
  assert.throws(() => weather.normalize({ error: true }));
});
test("weather displays PHT independently of device timezone and wind points downwind", () => {
  assert.match(weather.formatTime(Date.UTC(2026, 9, 22, 17, 0), "en"), /Oct 23.*01:00.*AM.*PHT/);
  assert.equal(weather.windRotation(0), 180);
  assert.equal(weather.windRotation(90), 270);
  assert.equal(weather.windRotation(180), 0);
});
const layer = { type: "inline-geojson", enabled: true, available: true };
const feature = (geometry, properties = {}) => ({ type: "Feature", geometry, properties });
const point = (coords = [120.455, 16.03]) => feature({ type: "Point", coordinates: coords });
const collection = features => ({ type: "FeatureCollection", features });

test("static category glyphs produce path nodes, not SVG path text or injected data", () => {
  const expected = [
    ["listed-evacuation", "home"], ["School", "graduation-cap"],
    ["Gymnasium", "map-pin"],
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

test("DPWH colors consistently represent completed, ongoing, not-started and stopped projects", () => {
  assert.deepEqual(gis.statusColors, {
    completed: "#287943", ongoing: "#b66b08", not_started: "#c0392b",
    stopped: "#c0392b", unknown: "#737373",
  });
  for (const [status, color] of Object.entries(gis.statusColors)) {
    assert.equal(gis.categoryColor("", "dpwh_project", status), color);
    assert.match(gis.iconSvg("hard-hat", color, 20), new RegExp(`stroke="${color}"`));
  }
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
   const state = (id, semantic_role, features, extra = {}) => ({ layer: { id, semantic_role, available: true }, features, items: new Map(features.map(f => [f, {}])), overlay: {}, visible: true, ...extra });
  const ref = feature(null, { name: "Reference", project_id: "canonical-1" });
   const dpwh = feature(point().geometry, { name: "Different project name", project_id: "canonical-1" });
  const unlinked = feature(null, { name: "Different project name" });
  const barangay = feature(null, { name: "Canonical name", gid: "gid-1" });
  const shape = feature({ type: "Polygon", coordinates: [[[120, 16], [121, 16], [121, 17], [120, 16]]] }, { name: "Source spelling", gid: "gid-1" });
  const unrelated = feature(null, { name: "Source spelling", gid: "gid-2" });
  const refs = state("refs", "project_reference", [ref, unlinked]);
  const projects = state("dpwh", "dpwh_project", [dpwh]);
  const directory = state("barangays", "reference", [barangay, unrelated]);
  const shapes = state("shape", "barangay_boundary", [shape]);
  const before = JSON.stringify([refs, projects, directory, shapes]);
   assert.deepEqual(gis.defaultEntries([refs, projects, directory, shapes]).map(entry => entry.feature), [dpwh, shape]);
  assert.equal(JSON.stringify([refs, projects, directory, shapes]), before);
   assert.deepEqual(gis.defaultEntries([directory, { ...shapes, overlay: null }]), []);
   assert.deepEqual(gis.defaultEntries([directory, state("shape", "barangay_boundary", [feature(null, { gid: "gid-1" })])]), []);
  const coarse = state("coarse", "barangay_reference_geometry", [shape], { visible: false });
   assert.deepEqual(gis.defaultEntries([directory, coarse]), []);
   assert.deepEqual(gis.defaultEntries([directory, { ...coarse, visible: true }]).map(entry => entry.feature), [shape]);
  const actual = { ...shape, properties: { ...shape.properties, name: "Actual boundary" } };
   assert.deepEqual(gis.defaultEntries([directory, { ...coarse, visible: true }, state("actual", "barangay_boundary", [actual])]).map(entry => entry.feature), [actual]);
   const hidden = { ...shapes, visible: false };
   assert.deepEqual(gis.defaultEntries([hidden]), []);
   assert.deepEqual(gis.defaultEntries([hidden], hidden).map(e => e.feature), [shape]);
   assert.deepEqual(gis.defaultEntries([{ ...shapes, items: new Map() }]), []);
   const linked = feature(point().geometry, { canonical_facility_id: "fac-1" });
   const canonical = feature(point().geometry, { id: "fac-1" });
   const facilities = state("facilities", "facility", [canonical]); facilities.layer.data_key = "GIS_FACILITIES";
   assert.deepEqual(gis.defaultEntries([state("linked", "facility", [linked]), { ...facilities, visible: false }]).map(e => e.feature), [linked]);
});
test("pane ordering and status palette are explicit rather than inferred from titles", () => {
  assert.deepEqual(gis.panes, { physical: 250, hazards: 300, administrative: 400, infrastructure: 450, facilities: 500 });
  assert.deepEqual(Object.keys(gis.statusColors), ["completed", "ongoing", "not_started", "stopped", "unknown"]);
  assert.equal(new Set(Object.values(gis.statusColors)).size, 4);
});

test("statistics use deterministic tie-preserving sequential quantiles with fewer classes", () => {
  assert.deepEqual(gis.quantiles([null, undefined, "0", NaN, Infinity, -1]), []);
  assert.deepEqual(gis.quantiles([0, 0, 0]), [{ min: 0, max: 0, color: "#31875A" }]);
  assert.deepEqual(gis.quantiles([0, 0, 7]), [{ min: 0, max: 0, color: "#31875A" }, { min: 7, max: 7, color: "#C84B47" }]);
  assert.deepEqual(gis.quantiles([3, 2, 1]), [{ min: 1, max: 1, color: "#31875A" }, { min: 2, max: 2, color: "#E8C44D" }, { min: 3, max: 3, color: "#C84B47" }]);
  const values = [0, 0, 0, 0, 1, 2, 3, 4, 5, 5, 5, 5], before = [...values];
  const classes = gis.quantiles(values);
  assert.deepEqual(values, before);
  assert.deepEqual(gis.quantiles([...values].reverse()), classes);
  assert.equal(classes.length, 3);
  assert.equal(gis.statisticColor(0, classes), "#31875A");
  assert.equal(gis.statisticColor(null, classes), "#A6ADB4");
  assert.equal(gis.statisticColor("0", classes), "#A6ADB4");
  for (const value of new Set(values)) assert.equal(classes.filter(c => value >= c.min && value <= c.max).length, 1);
});

test("project filters intersect on the same source reference before canonical-ID union", () => {
  const references = [{ source: "dpwh", year: 2024, status: "ongoing" }, { source: "dilg", year: 2023, status: "completed" }];
  const project = { project_id: "canonical-1", barangay_gids: ["one", "two"], references };
  const data = { projects: [project, { ...project }, { project_id: "canonical-2", references: [{ source: "dpwh", year: null, status: "unknown" }] }] };
  assert.deepEqual(gis.filteredProjects(data, { source: "dpwh", year: "2023", status: "completed" }), []);
  assert.deepEqual(gis.filteredProjects(data, { source: "dpwh", year: "2024", status: "completed" }), []);
  assert.deepEqual(gis.filteredProjects(data, { source: "dilg", year: "2023", status: "completed" }), [project]);
  assert.equal(gis.filteredProjects(data, {}).length, 2);
  assert.equal(gis.filteredProjects(data, { year: "unknown", status: "unknown" })[0].project_id, "canonical-2");
  assert.equal(gis.matchingReferences(project, { source: "dilg" })[0].year, 2023);
});

function statisticsFixture() {
  const gids = Array.from({ length: 15 }, (_, i) => "0105528" + String(i + 1).padStart(3, "0"));
  return { schema_version: 1, municipality_psgc: "0105528000", population: { year: 2024, total: 0, status: "available", provenance: [] },
    barangays: Object.fromEntries(gids.map(gid => [gid, { gid, name: gid, population: { count: 0, year: 2024, status: "available", share: null }, projects: { count: 0, ids: [], status: "scoped" } }])),
    projects: [], project_coverage: { sources: { dpwh: { supported: true }, philgeps: { supported: false } } } };
}

test("barangay assignment belongs to the matching source reference, not its project union", () => {
  const project = { barangay_gids: ["one", "two"], references: [
    { source: "dpwh", year: 2024, status: "ongoing", barangay_gids: ["one"] },
    { source: "dilg", year: 2023, status: "completed", barangay_gids: ["two"] },
  ] };
  assert.equal(gis.projectInBarangay(project, { source: "dpwh" }, "two"), false);
  assert.equal(gis.projectInBarangay(project, { year: "2023" }, "one"), false);
  assert.equal(gis.projectInBarangay(project, {}, "two"), true);
});

test("statistics validation distinguishes missing population and scoped zero, rejecting bad joins", () => {
  const data = statisticsFixture();
  assert.equal(gis.validateStatistics(data), data);
  data.barangays["0105528001"].population.count = null;
  data.barangays["0105528001"].population.status = "missing";
  assert.equal(gis.validateStatistics(data).barangays["0105528002"].population.count, 0);
  const invalid = mutate => { const copy = JSON.parse(JSON.stringify(data)); mutate(copy); assert.throws(() => gis.validateStatistics(copy)); };
  invalid(d => { d.schema_version = 2; });
  invalid(d => { d.municipality_psgc = "0105529000"; });
  invalid(d => { delete d.barangays["0105528001"]; });
  invalid(d => { d.barangays["0105528001"].population.count = -1; });
  invalid(d => { d.barangays["0105528001"].population.share = 2; });
  invalid(d => { d.barangays["0105528001"].population.year = 2020; });
  invalid(d => { d.barangays["0105528001"].projects.ids = ["invented"]; });
  invalid(d => { d.project_coverage.sources.dpwh.supported = "true"; });
  invalid(d => { d.projects = [{ project_id: "one", name: "Project", barangay_gids: ["0105528001"], references: [{ source: "dpwh", year: 2024, status: "ongoing" }] }]; });
  data.projects.push({ project_id: "one", name: "Project", barangay_gids: ["0105528001", "0105528002"], references: [{ source: "dpwh", year: 2024, status: "ongoing", barangay_gids: ["0105528001", "0105528002"] }] });
  for (const gid of ["0105528001", "0105528002"]) data.barangays[gid].projects = { count: 1, ids: ["one"], status: "scoped" };
  assert.equal(gis.validateStatistics(data), data);
  invalid(d => { d.projects.push(d.projects[0]); });
  invalid(d => { d.projects[0].references[0].source = "invented"; });
});

test("radar only accepts trusted, ordered past frame paths", () => {
  const data = {host: "https://tilecache.rainviewer.com", radar: {past: [{time: 1700000000, path: "/v2/radar/1700000000"}]}};
  assert.match(weather.normalizeRadar(data)[0].url, /256\/\{z\}/);
  assert.equal(weather.normalizeRadar(data)[0].time, 1700000000000);
  assert.throws(() => weather.normalizeRadar({...data, host: "https://evil.example"}));
  assert.throws(() => weather.normalizeRadar({ ...data, radar: {past: []} }));
  data.radar.past[0].path = "/v2/radar/../../other";
  assert.throws(() => weather.normalizeRadar(data));
});
