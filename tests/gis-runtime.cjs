"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const gis = require("../assets/gis-map.js");
const layer = { type: "inline-geojson", enabled: true, available: true };
const feature = (geometry, properties = {}) => ({ type: "Feature", geometry, properties });
const point = (coords = [120.455, 16.03]) => feature({ type: "Point", coordinates: coords });
const collection = features => ({ type: "FeatureCollection", features });

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
