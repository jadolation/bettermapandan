"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(path.join(root, "assets/gis-map.js"), "utf8");

function facility(name, coords = [120.455, 16.03], overrides = {}) {
  return { type: "Feature", geometry: { type: "Point", coordinates: coords }, properties: {
    name, category: "School", verification_status: "source_verified", location_precision: "approximate",
    coordinate_method: "plus_code_cell_center", provenance: {
      source: "Example source", source_url: "https://example.org/record", last_verified: "2026-10-19",
    }, ...overrides,
  } };
}

function run({ features = [], locale = "en", missingLibrary = false, brokenMap = false, loading = false,
  metadata = { coordinate_bounds: { south: 15.98, west: 120.42, north: 16.05, east: 120.49 } } } = {}) {
  const strings = JSON.parse(fs.readFileSync(path.join(root, `locales/${locale}.json`), "utf8")).gis;
  const messages = Object.fromEntries(Object.entries(strings).map(([key, value]) =>
    [key.replace(/_([a-z])/g, (_, c) => c.toUpperCase()), value]));
  const nodes = {};
  for (const id of ["gis-page", "gis-map", "gis-map-fallback", "gis-map-status", "gis-facility-count",
    "gis-marker-count", "gis-facility-empty", "gis-barangay-list", "gis-facility-list"]) {
    nodes[id] = { dataset: {}, hidden: false, textContent: "", innerHTML: "STATIC DIRECTORY" };
  }
  nodes["gis-page"].dataset = messages;
  const controls = {};
  nodes["gis-map"].querySelector = selector => controls[selector] ||= {
    setAttribute(key, value) { this[key] = value; },
  };
  const events = {};
  const added = [];
  const markers = [];
  const rectangles = [];
  const layers = [];
  function layer() { return { addTo(target) { added.push({ layer: this, target }); return this; } }; }
  const tiles = { ...layer(), on(event, fn) { events[event] = fn; return this; } };
  const map = { setView(center, zoom) { this.center = center; this.zoom = zoom; return this; },
    invalidateSize() {}, getContainer() { return nodes["gis-map"]; } };
  const L = {
    map() { if (brokenMap) throw Error("Map failed"); return map; },
    tileLayer(url, options) { tiles.url = url; tiles.options = options; return tiles; },
    layerGroup: layer,
    rectangle(coords) { rectangles.push(coords); return layer(); },
    circleMarker(coords) { const marker = { ...layer(), coords, bindPopup(html) { this.popup = html; return this; } };
      markers.push(marker); return marker; },
    control: { layers(base, overlays) { layers.push({ base, overlays }); return layer(); } },
  };
  let domReady;
  const document = { readyState: loading ? "loading" : "complete", getElementById: id => nodes[id],
    addEventListener(event, callback) { assert.equal(event, "DOMContentLoaded"); domReady = callback; } };
  const window = { GIS_FACILITIES: { features }, GIS_LAYERS: { metadata }, addEventListener() {} };
  const context = { window, document, console };
  if (!missingLibrary) context.L = L;
  vm.runInNewContext(source, context);
  return { nodes, strings, added, markers, rectangles, tiles, map, layers, events, ready: () => domReady() };
}

test("empty approved payload activates OSM and leaves static directories intact", () => {
  const r = run();
  assert.ok(r.added.some(item => item.layer === r.tiles && item.target === r.map));
  assert.match(r.tiles.options.attribution, /https:\/\/www.openstreetmap.org\/copyright/);
  assert.equal(r.nodes["gis-facility-count"].textContent, "0");
  assert.equal(r.nodes["gis-marker-count"].textContent, "0");
  assert.equal(r.nodes["gis-facility-empty"].hidden, false);
  assert.equal(r.nodes["gis-barangay-list"].innerHTML, "STATIC DIRECTORY");
  assert.equal(r.nodes["gis-facility-list"].innerHTML, "STATIC DIRECTORY");
  assert.equal(r.rectangles.length, 1);
});

test("rejects malformed candidates and counts only valid rendered records", () => {
  const invalid = [null, {}, { properties: null }, facility("NaN", [NaN, 16]),
    facility("Infinity", [120, Infinity]), facility("String", ["120", 16]),
    facility("Range", [181, 16]), facility("Range", [120, 91]), facility("Short", [120]),
    facility("3D", [120, 16, 0]), facility("Status", undefined, { verification_status: "needs_review" }),
    facility(""), { ...facility("Polygon"), geometry: { type: "Polygon", coordinates: [] } }];
  const r = run({ features: [...invalid, facility("Good")] });
  assert.equal(r.markers.length, 1);
  assert.equal(r.nodes["gis-facility-count"].textContent, "1");
  assert.equal(r.nodes["gis-facility-empty"].hidden, true);
  assert.equal(run({ features: "not an array" }).markers.length, 0);
});

test("groups exact coordinates without jitter, retains distinct records and warns about colocation", () => {
  const r = run({ features: [facility("Police"), facility("Fire"), facility("Nearby", [120.455001, 16.03])] });
  assert.equal(r.markers.length, 2);
  assert.equal(r.nodes["gis-facility-count"].textContent, "3");
  assert.equal(r.nodes["gis-marker-count"].textContent, "2");
  assert.equal(JSON.stringify(r.markers[0].coords), "[16.03,120.455]");
  assert.match(r.markers[0].popup, /Police/);
  assert.match(r.markers[0].popup, /Fire/);
  assert.ok(r.markers[0].popup.includes(r.strings.shared));
});

test("popups escape records and allow only HTTP(S) source links", () => {
  const r = run({ features: [facility('<img src=x onerror="alert(1)">', undefined, {
    address: "<script>bad()</script>", provenance: { source: "<evil>", source_url: "javascript:alert(1)" },
  }), facility("Safe", [120.46, 16.03])] });
  assert.doesNotMatch(r.markers[0].popup, /<img|<script|href=/);
  assert.match(r.markers[0].popup, /&lt;img/);
  assert.match(r.markers[1].popup, /href="https:\/\/example.org\/record"/);
  assert.ok(r.markers[1].popup.includes(r.strings.cell_center));
});

for (const locale of ["en", "fil", "pag"]) {
  test(`${locale}: localized controls, failures and precision messages`, () => {
    const r = run({ locale, features: [facility("School")] });
    assert.ok(r.layers[0].base[r.strings.basemap]);
    assert.ok(r.layers[0].overlays[r.strings.facilities]);
    assert.equal(r.nodes["gis-map"].querySelector(".leaflet-control-zoom-in")["aria-label"], r.strings.zoom_in);
    assert.ok(r.markers[0].popup.includes(r.strings.cell_center));
    r.events.load();
    assert.equal(r.nodes["gis-map-fallback"].hidden, true);
    r.events.tileerror();
    r.events.load();
    assert.equal(r.nodes["gis-map-fallback"].hidden, false);
    assert.equal(r.nodes["gis-map-status"].textContent, r.strings.tile_error);
    assert.equal(r.nodes["gis-facility-list"].innerHTML, "STATIC DIRECTORY");
    const missing = run({ locale, missingLibrary: true });
    assert.equal(missing.nodes["gis-map-status"].textContent, r.strings.library_error);
    assert.equal(missing.nodes["gis-map"].hidden, true);
    assert.equal(missing.nodes["gis-facility-list"].innerHTML, "STATIC DIRECTORY");
  });
}

test("map initialization errors preserve fallback and directories", () => {
  const r = run({ brokenMap: true });
  assert.equal(r.nodes["gis-map-status"].textContent, r.strings.map_error);
  assert.equal(r.nodes["gis-map-fallback"].hidden, false);
  assert.equal(r.nodes["gis-barangay-list"].innerHTML, "STATIC DIRECTORY");
});

test("DOMContentLoaded initialization is idempotent and invalid metadata is ignored", () => {
  const r = run({ loading: true, metadata: { default_map_center: [999, 16], default_zoom: "14",
    coordinate_bounds: { south: "15", west: 120, north: 16, east: 121 } } });
  assert.equal(r.layers.length, 0);
  r.ready();
  r.ready();
  assert.equal(r.layers.length, 1);
  assert.equal(r.rectangles.length, 0);
  assert.equal(JSON.stringify(r.map.center), "[16.03,120.455]");
  assert.equal(r.map.zoom, 14);
});
